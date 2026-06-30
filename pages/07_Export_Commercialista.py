import streamlit as st
import pandas as pd
import requests
import base64
import io
import calendar
from datetime import datetime, date

# Per l'esportazione in PDF con layout professionale
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Export Commercialista", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"
DRIVE_FILE_ID = st.secrets["DRIVE_FILE_ID"]

MESI_MAP = {
    'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6,
    'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
}

MESI_NOMI = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile", 5: "Maggio", 6: "Giugno",
    7: "Luglio", 8: "Agosto", 9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
}

def load_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def load_drive_data_raw():
    try:
        drive_url = f"https://docs.google.com/spreadsheets/d/{DRIVE_FILE_ID}/export?format=xlsx"
        r = requests.get(drive_url)
        if r.status_code == 200:
            return pd.read_excel(io.BytesIO(r.content), sheet_name=0, header=None)
    except:
        pass
    return pd.DataFrame()

def parse_descrizione_operaio(descrizione):
    try:
        if "|" in str(descrizione):
            parti = descrizione.split("|")
            nome = parti[0].strip()
            info_tempo = parti[1].strip()
            giornate = float(info_tempo.split(" gg")[0].strip())
            ore = float(info_tempo.split("(")[1].split(" ore")[0].strip()) if "(" in info_tempo else 0.0
            return nome, giornate, ore
    except:
        pass
    return "Specificato da App", 0.0, 0.0

def is_festivo_italiano(d):
    if d.weekday() in [5, 6]:
        return True
    festivita_fisse = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    if (d.month, d.day) in festivita_fisse:
        return True
    if d.year == 2026 and d.month == 4 and d.day == 6:  # Pasquetta 2026
        return True
    return False

st.title("📄 Centro Esportazione Presenze e Cedolini")
st.markdown("Configura i dettagli anagrafici e genera il report strutturato per lo studio commerciale.")

# --- SEZIONE INSERIMENTO DATI DINAMICI ---
st.subheader("🏢 Informazioni Registro ed Anagrafica")
col_az1, col_az2 = st.columns(2)
with col_az1:
    nome_azienda = st.text_input("Ragione Sociale Azienda / Ente:", value="L'ORO DI SAN VITTORE di Mazzilli Antonio")
with col_az2:
    nome_dipendente = st.text_input("Nome e Cognome Dipendente (Per Storico Excel):", value="Iannone Felice")

st.divider()

# --- FILTRI TEMPORALI ---
col1, col2 = st.columns(2)
with col1:
    anno_sel = st.selectbox("Anno di riferimento:", [2026, 2025])
with col2:
    mese_sel = st.selectbox("Mese da elaborare:", list(MESI_NOMI.keys()), format_func=lambda x: MESI_NOMI[x], index=datetime.now().month - 1)

nome_mese_stringa = MESI_NOMI[mese_sel]

with st.spinner("Generazione prospetti in corso..."):
    df_git = load_github_data()
    df_drive_raw = load_drive_data_raw()
    
    giornate_totali_excel = 0.0
    righe_commercialista = []
    
    # 1. LETTURA POSIZIONALE EXCEL DRIVE
    if not df_drive_raw.empty:
        idx_colonna_mesi = None
        for col_idx in range(df_drive_raw.shape[1]):
            if df_drive_raw[col_idx].astype(str).str.lower().str.strip().isin(MESI_MAP.keys()).any():
                idx_colonna_mesi = col_idx
                break
                
        if idx_colonna_mesi is not None:
            def get_sicuro(lista_valori, indice_desiderato, default=0.0):
                if indice_desiderato < len(lista_valori):
                    valore = lista_valori[indice_desiderato]
                    return valore if pd.notna(valore) else default
                return default

            for _, row in df_drive_raw.iterrows():
                valori_riga = row.tolist()
                if idx_colonna_mesi < len(valori_riga):
                    mese_excel_testo = str(valori_riga[idx_colonna_mesi]).strip().lower()
                    if MESI_MAP.get(mese_excel_testo) == mese_sel:
                        giornate_totali_excel = pd.to_numeric(get_sicuro(valori_riga, idx_colonna_mesi + 1), errors='coerce')
                        giornate_totali_excel = giornate_totali_excel if pd.notna(giornate_totali_excel) else 0.0
                        break

    # 2. ALGORITMO SPALMATURA FERIALE
    if giornate_totali_excel > 0:
        _, num_giorni_mese = calendar.monthrange(anno_sel, mese_sel)
        giorni_utili_feriali = [date(anno_sel, mese_sel, g) for g in range(1, num_giorni_mese + 1) if not is_festivo_italiano(date(anno_sel, mese_sel, g))]
        
        giornate_rimanenti = giornate_totali_excel
        
        for d in giorni_utili_feriali:
            if giornate_rimanenti <= 0: break
            quota_giorno = min(1.0, giornate_rimanenti)
            giornate_rimanenti -= quota_giorno
            
            righe_commercialista.append({
                "Data": d.strftime('%d/%m/%Y'),
                "Dipendente": nome_dipendente,
                "Giornate": quota_giorno,
                "Ore": quota_giorno * 8.0,
                "Note": ""  # Campo Note vuoto
            })

    # 3. INTEGRAZIONE INSERIMENTI APP (GITHUB)
    if not df_git.empty:
        df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
        df_filtrato_app = df_git[(df_git['data_dt'].dt.year == anno_sel) & (df_git['data_dt'].dt.month == mese_sel) & (df_git['categoria'] == 'Manodopera')]
        
        for _, row in df_filtrato_app.iterrows():
            nome, gg, ore = parse_descrizione_operaio(row['descrizione'])
            righe_commercialista.append({
                "Data": row['data_dt'].strftime('%d/%m/%Y'),
                "Dipendente": nome,
                "Giornate": gg,
                "Ore": ore,
                "Note": ""  # Campo Note vuoto
            })

    # --- GENERAZIONE OUTPUTS ---
    if righe_commercialista:
        df_export = pd.DataFrame(righe_commercialista)
        df_export['dt_sort'] = pd.to_datetime(df_export['Data'], format='%d/%m/%Y')
        df_export = df_export.sort_values(by="dt_sort").drop(columns=['dt_sort'])
        
        # Anteprima a schermo
        st.subheader("👀 Anteprima del Prospetto Pulito")
        
        c_inf1, c_inf2 = st.columns(2)
        c_inf1.info(f"**Azienda:** {nome_azienda}  \n**Periodo:** {nome_mese_stringa} {anno_sel}")
        c_inf2.info(f"**Totale Giornate Rilevate:** {df_export['Giornate'].sum():,.1f} gg")
        
        st.dataframe(df_export, use_container_width=True)
        
        st.divider()
        st.subheader("📥 Scarica il Report Aggiornato")
        
        col_btn1, col_btn2 = st.columns(2)
        
        # --- GENERAZIONE EXCEL ---
        with col_btn1:
            buffer_xl = io.BytesIO()
            with pd.ExcelWriter(buffer_xl, engine='openpyxl') as writer:
                df_meta = pd.DataFrame([
                    ["RAGIONE SOCIALE:", nome_azienda],
                    ["DOCUMENTO:", "Prospetto Registro Presenze Mensili"],
                    ["PERIODO:", f"{nome_mese_stringa} {anno_sel}"],
                    ["", ""]
                ])
                df_meta.to_excel(writer, index=False, header=False, sheet_name="Presenze")
                df_export.to_excel(writer, index=False, startrow=5, sheet_name="Presenze")
            buffer_xl.seek(0)
            
            st.download_button(
                label="🟢 Scarica Foglio Excel (.xlsx)",
                data=buffer_xl,
                file_name=f"Presenze_{nome_mese_stringa}_{anno_sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        # --- GENERAZIONE PDF ---
        with col_btn2:
            buffer_pdf = io.BytesIO()
            doc = SimpleDocTemplate(buffer_pdf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            story = []
            
            styles = getSampleStyleSheet()
            style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#1A237E"), spaceAfter=10)
            style_meta = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=11, leading=16, textColor=colors.HexColor("#333333"))
            style_th = ParagraphStyle('TH', parent=styles['Normal'], fontSize=10, fontName="Helvetica-Bold", textColor=colors.white, alignment=1)
            style_td = ParagraphStyle('TD', parent=styles['Normal'], fontSize=9, alignment=1)
            
            # Intestazione Formale PDF
            story.append(Paragraph(f"<b>{nome_azienda.upper()}</b>", style_title))
            story.append(Paragraph(f"<b>Documento:</b> Prospetto Riepilogativo Presenze per Studio Commerciale", style_meta))
            story.append(Paragraph(f"<b>Periodo di Competenza:</b> {nome_mese_stringa} {anno_sel}", style_meta))
            story.append(Spacer(1, 15))
            
            # Struttura Tabella PDF (4 Colonne Dati + Note Vuote Più Larga)
            table_data = [[
                Paragraph("<b>Data</b>", style_th),
                Paragraph("<b>Dipendente</b>", style_th),
                Paragraph("<b>GG</b>", style_th),
                Paragraph("<b>Ore</b>", style_th),
                Paragraph("<b>Note</b>", style_th)
            ]]
            
            for _, r in df_export.iterrows():
                table_data.append([
                    Paragraph(r['Data'], style_td),
                    Paragraph(r['Dipendente'], style_td),
                    Paragraph(f"{r['Giornate']:.1f}", style_td),
                    Paragraph(f"{r['Ore']:.1f}", style_td),
                    Paragraph(r['Note'], style_td)  # Passa stringa vuota
                ])
                
            # Larghezze riproporzionate sulle 5 colonne rimaste
            t = Table(table_data, colWidths=[70, 140, 45, 45, 145])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A237E")),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('TOPPADDING', (0,0), (-1,0), 6),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F5F5F5"), colors.white]),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
                ('TOPPADDING', (0,1), (-1,-1), 5),
                ('BOTTOMPADDING', (0,1), (-1,-1), 5),
            ]))
            story.append(t)
            
            # Blocco Firme
            story.append(Spacer(1, 40))
            data_firme = [
                [Paragraph("Firma del Responsabile / Datore di Lavoro", style_td), Paragraph("Timbro Aziendale per Accettazione", style_td)]
            ]
            t_firme = Table(data_firme, colWidths=[220, 220])
            t_firme.setStyle(TableStyle([
                ('LINEBELOW', (0,0), (0,0), 0.5, colors.HexColor("#999999")),
                ('LINEBELOW', (1,0), (1,0), 0.5, colors.HexColor("#999999")),
                ('BOTTOMPADDING', (0,0), (-1,-1), 40),
            ]))
            story.append(t_firme)
            
            doc.build(story)
            buffer_pdf.seek(0)
            
            st.download_button(
                label="🔴 Scarica Documento PDF (.pdf)",
                data=buffer_pdf,
                file_name=f"Presenze_{nome_mese_stringa}_{anno_sel}.pdf",
                mime="application/pdf"
            )
    else:
        st.warning(f"Nessun dato disponibile per il mese di {nome_mese_stringa} {anno_sel}.")
