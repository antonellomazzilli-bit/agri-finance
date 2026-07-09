import streamlit as st
import pandas as pd
import requests
import base64
import io
import calendar
import math
from datetime import datetime, date

# Per l'esportazione in PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Pianificatore Manodopera", layout="wide")

# --- CONFIGURAZIONE E COLLEGAMENTO ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

# Nuovi pesi: 85% del lavoro concentrato tra Ottobre e Marzo (Raccolta e Potatura)
PESI_OLIVO = [10, 15, 15, 3, 3, 2, 2, 2, 3, 15, 20, 10]
MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

def load_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def estrai_giornate_operaio(descrizione, nome_target):
    try:
        if "|" in str(descrizione) and nome_target.lower() in str(descrizione).lower():
            parti = descrizione.split("|")
            info_tempo = parti[1].strip()
            return float(info_tempo.split(" gg")[0].strip())
    except:
        pass
    return 0.0

def is_festivo_italiano(d):
    # Esclude categoricamente sia il Sabato (5) che la Domenica (6)
    if d.weekday() in [5, 6]:
        return True
    # Elenco dei giorni rossi nazionali + San Cataldo (10 Maggio)
    festivita_fisse = [
        (1, 1), (1, 6), (4, 25), (5, 1), (5, 10), (6, 2), 
        (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)
    ]
    if (d.month, d.day) in festivita_fisse:
        return True
    if d.year == 2025 and d.month == 4 and d.day == 21: return True
    if d.year == 2026 and d.month == 4 and d.day == 6: return True
    if d.year == 2027 and d.month == 3 and d.day == 29: return True
    return False

def calcola_giorni_lavorativi(anno, mese):
    _, num_giorni = calendar.monthrange(anno, mese)
    lavorativi = 0
    for g in range(1, num_giorni + 1):
        if not is_festivo_italiano(date(anno, mese, g)):
            lavorativi += 1
    return lavorativi

st.title("📅 Pianificatore Annuale Manodopera")
st.markdown("Imposta il **Totale Mese** desiderato. Il sistema spingerà in automatico i giorni avanzati sui mesi vuoti.")

# --- IMPOSTAZIONI E RUBRICA ---
col_set1, col_set2, col_set3 = st.columns(3)
with col_set1:
    anno_sel = st.selectbox("Anno di Pianificazione:", [2026, 2025, 2027])
with col_set2:
    # Rubrica Blindata
    ANAGRAFICA_DIPENDENTI = ["Iannone Felice", "--- Inserisci Altro Dipendente ---"]
    scelta_dip = st.selectbox("Dipendente sotto contratto:", ANAGRAFICA_DIPENDENTI)
    if scelta_dip == "--- Inserisci Altro Dipendente ---":
        dipendente_target = st.text_input("Scrivi Nome e Cognome esatti:")
    else:
        dipendente_target = scelta_dip
    dipendente_target = dipendente_target.strip() if dipendente_target else "Iannone Felice"
    
with col_set3:
    tetto_giornate = st.number_input("Target Giornate Annuali:", min_value=1, value=160, step=1)

st.divider()

with st.spinner("Sincronizzazione calendario e lettura database..."):
    df_git = load_github_data()
    giornate_effettive = [0.0] * 12
    
    if not df_git.empty:
        df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
        df_lavoro = df_git[(df_git['data_dt'].dt.year == anno_sel) & (df_git['categoria'] == 'Manodopera')]
        
        for _, row in df_lavoro.iterrows():
            gg_lavorate = estrai_giornate_operaio(row['descrizione'], dipendente_target)
            if gg_lavorate > 0 and pd.notna(row['data_dt']):
                mese_idx = row['data_dt'].month - 1
                giornate_effettive[mese_idx] += gg_lavorate

    if 'totali_manuali' not in st.session_state or st.session_state.get('anno_plan') != anno_sel:
        st.session_state.totali_manuali = {i: None for i in range(12)}
        st.session_state.anno_plan = anno_sel
        if 'editor_pianificatore' in st.session_state:
            del st.session_state['editor_pianificatore']

    # --- CALCOLO CAPIENZE E LIMITI ---
    capienza_massima = [calcola_giorni_lavorativi(anno_sel, i + 1) for i in range(12)]
    
    totali_mese = [0] * 12
    giornate_da_spalmare = tetto_giornate
    mesi_da_calcolare = []

    mese_corrente = datetime.today().month
    anno_corrente = datetime.today().year

    # 1. Assegnazione Consuntivi, Forzature e Mesi Bloccati
    for i in range(12):
        mese_num = i + 1
        min_giorni_possibili = int(math.ceil(giornate_effettive[i])) 
        
        is_closed = False
        if anno_sel < anno_corrente:
            is_closed = True
        elif anno_sel == anno_corrente and mese_num < mese_corrente:
            is_closed = True

        if st.session_state.totali_manuali[i] is not None:
            valore_forzato = int(st.session_state.totali_manuali[i])
            valore_forzato = max(min_giorni_possibili, min(valore_forzato, capienza_massima[i]))
            
            totali_mese[i] = valore_forzato
            giornate_da_spalmare -= valore_forzato
            
        elif is_closed:
            totali_mese[i] = min_giorni_possibili
            giornate_da_spalmare -= min_giorni_possibili
            
        else:
            totali_mese[i] = min_giorni_possibili
            giornate_da_spalmare -= min_giorni_possibili
            mesi_da_calcolare.append(i)

    # 2. Spalmatura Algoritmica per Numeri Interi sui mesi liberi
    while giornate_da_spalmare > 0 and sum([(capienza_massima[i] - totali_mese[i]) for i in mesi_da_calcolare]) > 0:
        best_month = None
        lowest_ratio = float('inf')
        
        for i in mesi_da_calcolare:
            if totali_mese[i] < capienza_massima[i]:
                peso = PESI_OLIVO[i] if PESI_OLIVO[i] > 0 else 0.1
                ratio = totali_mese[i] / peso
                if ratio < lowest_ratio:
                    lowest_ratio = ratio
                    best_month = i
                    
        if best_month is not None:
            totali_mese[best_month] += 1
            giornate_da_spalmare -= 1
        else:
            break

    # --- TABELLA INTERATTIVA ---
    dati_tabella = []
    for i in range(12):
        da_fare = max(0.0, totali_mese[i] - giornate_effettive[i])
        dati_tabella.append({
            "Mese": MESI[i],
            "Capienza Calendario": capienza_massima[i],
            "Consuntivate (Fatte)": giornate_effettive[i],
            "Da Lavorare (Restanti)": da_fare,
            "TOTALE MESE (Modificabile)": totali_mese[i]
        })
        
    df_plan = pd.DataFrame(dati_tabella)

    def applica_modifiche_tabella():
        edits = st.session_state.editor_pianificatore.get("edited_rows", {})
        for idx_str, modifiche in edits.items():
            if "TOTALE MESE (Modificabile)" in modifiche:
                val = modifiche["TOTALE MESE (Modificabile)"]
                if val is None:
                    st.session_state.totali_manuali[int(idx_str)] = None
                else:
                    st.session_state.totali_manuali[int(idx_str)] = int(val)

    st.subheader("⚙️ Regolazione Dinamica dei Totali")
    st.write("Modifica solo l'ultima colonna (**TOTALE MESE**). Se cancelli un numero lasciando la cella vuota, sbloccherai il mese permettendo all'algoritmo di lavorarci in autonomia.")
    
    df_modificato = st.data_editor(
        df_plan,
        disabled=["Mese", "Capienza Calendario", "Consuntivate (Fatte)", "Da Lavorare (Restanti)"],
        hide_index=True,
        use_container_width=True,
        key="editor_pianificatore",
        on_change=applica_modifiche_tabella,
        column_config={
            "Capienza Calendario": st.column_config.NumberColumn(format="%d gg lav."),
            "Consuntivate (Fatte)": st.column_config.NumberColumn(format="%.1f gg"),
            "Da Lavorare (Restanti)": st.column_config.NumberColumn(format="%.1f gg"),
            "TOTALE MESE (Modificabile)": st.column_config.NumberColumn(format="%d gg", min_value=0, step=1)
        }
    )

    # --- NUOVO CAMPO SOMMA VISIBILE ---
    totale_generale = df_modificato["TOTALE MESE (Modificabile)"].sum()
    
    colore_somma = "#4CAF50" # Verde se perfetto
    if totale_generale > tetto_giornate:
        colore_somma = "#F44336" # Rosso se sfora
    elif totale_generale < tetto_giornate:
        colore_somma = "#FF9800" # Arancione se mancano giorni
        
    st.markdown(f"""
        <div style="text-align: right; font-size: 18px; margin-top: 5px; padding-right: 15px; background-color: #f8f9fa; padding: 10px; border-radius: 5px; border: 1px solid #ddd;">
            <b>🧮 SOMMA TOTALE COLONNA:</b> &nbsp;&nbsp;
            <span style="font-size: 24px; font-weight: bold; color: {colore_somma};">{totale_generale}</span> 
            <span style="color: #666;"> / {tetto_giornate} gg</span>
        </div>
    """, unsafe_allow_html=True)
    # -----------------------------------
    
    st.divider()
    c_res1, c_res2 = st.columns(2)
    
    with c_res1:
        if totale_generale > tetto_giornate:
            st.error(f"⚠️ ATTENZIONE: Stai sforando il tetto di {tetto_giornate} giornate!")
        elif totale_generale < tetto_giornate:
            if giornate_da_spalmare > 0:
                st.warning(f"⚖️ Tetto non raggiunto. **Calendario feriale dei mesi liberi completamente saturo!** Devi cancellare/sbloccare le forzature da qualche altro mese per fare spazio.")
            else:
                st.warning(f"⚖️ Tetto non raggiunto. Mancano ancora {tetto_giornate - totale_generale} giorni.")
        else:
            st.success(f"✅ Perfetto! L'allocazione raggiunge esattamente le **{tetto_giornate} giornate** contrattuali.")
            
    with c_res2:
        if st.button("🔄 Ripristina Calcoli di Default"):
            st.session_state.totali_manuali = {i: None for i in range(12)}
            if 'editor_pianificatore' in st.session_state:
                del st.session_state['editor_pianificatore']
            st.rerun()

    # --- ESPORTAZIONE PDF PER COMMERCIALISTA ---
    st.divider()
    st.subheader("📥 Esporta Piano Previsionale per Consulente del Lavoro")
    
    buffer_pdf = io.BytesIO()
    doc = SimpleDocTemplate(buffer_pdf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor("#1A237E"), spaceAfter=5)
    style_meta = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#333333"))
    style_th = ParagraphStyle('TH', parent=styles['Normal'], fontSize=10, fontName="Helvetica-Bold", textColor=colors.white, alignment=1)
    style_td = ParagraphStyle('TD', parent=styles['Normal'], fontSize=10, alignment=1)
    
    nome_azienda = "L'ORO DI SAN VITTORE di Mazzilli Antonio"
    story.append(Paragraph(f"<b>{nome_azienda.upper()}</b>", style_title))
    story.append(Paragraph(f"<b>Documento:</b> Piano Previsionale di Manodopera Agricola", style_meta))
    story.append(Paragraph(f"<b>Lavoratore:</b> {dipendente_target}", style_meta))
    story.append(Paragraph(f"<b>Anno di Competenza:</b> {anno_sel}", style_meta))
    story.append(Paragraph(f"<b>Target Contrattuale:</b> {tetto_giornate} giornate", style_meta))
    story.append(Spacer(1, 20))
    
    pdf_table_data = [[
        Paragraph("<b>Mese</b>", style_th),
        Paragraph("<b>Già Lavorate</b>", style_th),
        Paragraph("<b>Da Lavorare</b>", style_th),
        Paragraph("<b>TOTALE MESE</b>", style_th)
    ]]
    
    for i in range(12):
        pdf_table_data.append([
            Paragraph(df_modificato.iloc[i]["Mese"], style_td),
            Paragraph(f"{df_modificato.iloc[i]['Consuntivate (Fatte)']:.1f}", style_td),
            Paragraph(f"{df_modificato.iloc[i]['Da Lavorare (Restanti)']:.1f}", style_td),
            Paragraph(f"<b>{df_modificato.iloc[i]['TOTALE MESE (Modificabile)']}</b>", style_td)
        ])
        
    totale_cons = df_modificato['Consuntivate (Fatte)'].sum()
    totale_rest = df_modificato['Da Lavorare (Restanti)'].sum()
    
    pdf_table_data.append([
        Paragraph("<b>TOTALE ANNUALE</b>", style_th),
        Paragraph(f"<b>{totale_cons:.1f}</b>", style_th),
        Paragraph(f"<b>{totale_rest:.1f}</b>", style_th),
        Paragraph(f"<b>{totale_generale}</b>", style_th)
    ])
    
    t = Table(pdf_table_data, colWidths=[120, 130, 130, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A237E")),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#4CAF50")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.HexColor("#F9F9F9"), colors.white]),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    
    story.append(Spacer(1, 40))
    story.append(Paragraph("<i>Il presente documento costituisce una proiezione organizzativa per la gestione del fondo agricolo e potrà subire variazioni in base alle necessità colturali reali.</i>", style_meta))
    
    doc.build(story)
    buffer_pdf.seek(0)
    
    st.download_button(
        label="🔴 Scarica Documento PDF (.pdf)",
        data=buffer_pdf,
        file_name=f"Piano_Manodopera_{dipendente_target.replace(' ', '_')}_{anno_sel}.pdf",
        mime="application/pdf"
    )
