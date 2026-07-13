import streamlit as st
import pandas as pd
import requests
import base64
import io
import time
import calendar
from datetime import datetime, date

# Per l'esportazione in PDF con layout professionale
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Export Commercialista", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

MESI_NOMI = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile", 5: "Maggio", 6: "Giugno",
    7: "Luglio", 8: "Agosto", 9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
}

GIORNI_SETTIMANA_ITA = {
    0: "lun", 1: "mar", 2: "mer", 3: "gio", 4: "ven", 5: "sab", 6: "dom"
}

def load_github_data():
    timestamp = int(time.time())
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}?ref=main&t={timestamp}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Cache-Control": "no-cache"
    }
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def parse_descrizione_operaio(descrizione):
    try:
        if "|" in str(descrizione):
            parti = descrizione.split("|")
            nome = parti[0].strip()
            info_tempo = parti[1].strip()
            giornate = float(info_tempo.split(" gg")[0].strip())
            return nome, giornate
    except:
        pass
    return "Specificato da App", 0.0

def is_festivo_italiano(d):
    if d.weekday() in [5, 6]:
        return True
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

st.title("📄 Centro Esportazione Presenze (Busta Paga)")
st.markdown("Generazione del registro presenze orizzontale strutturato per lo studio commerciale.")

st.subheader("🏢 Informazioni Registro ed Anagrafica")
col_az1, col_az2 = st.columns(2)
with col_az1:
    nome_azienda = st.text_input("Ragione Sociale Azienda / Ente:", value="IMPRESA AGRICOLA L'ORO DI SAN VITTORE di Mazzilli Antonio")
with col_az2:
    ANAGRAFICA_DIPENDENTI = ["Iannone Felice", "--- Inserisci Altro Dipendente ---"]
    scelta_dip = st.selectbox("Dipendente da esportare:", ANAGRAFICA_DIPENDENTI)
    if scelta_dip == "--- Inserisci Altro Dipendente ---":
        nome_dipendente = st.text_input("Scrivi Nome e Cognome esatti:")
    else:
        nome_dipendente = scelta_dip
    nome_dipendente = nome_dipendente.strip() if nome_dipendente else "Iannone Felice"

st.divider()

col1, col2 = st.columns(2)
with col1:
    anno_sel = st.selectbox("Anno di riferimento:", [2026, 2025, 2027])
with col2:
    mese_sel = st.selectbox("Mese da elaborare:", list(MESI_NOMI.keys()), format_func=lambda x: MESI_NOMI[x], index=datetime.now().month - 1)

nome_mese_stringa = MESI_NOMI[mese_sel]

with st.spinner("Lettura database cloud in corso (Senza Cache)..."):
    df_git = load_github_data()
    giorni_occupati = {}
    
    _, num_giorni_mese = calendar.monthrange(anno_sel, mese_sel)
    giorni_utili_feriali = [date(anno_sel, mese_sel, g) for g in range(1, num_giorni_mese + 1) if not is_festivo_italiano(date(anno_sel, mese_sel, g))]
    
    movimenti_bulk = []
    
    if not df_git.empty:
        df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
        df_filtrato_app = df_git[(df_git['data_dt'].dt.year == anno_sel) & (df_git['data_dt'].dt.month == mese_sel) & (df_git['categoria'] == 'Manodopera')]
        
        for _, row in df_filtrato_app.iterrows():
            nome, gg = parse_descrizione_operaio(row['descrizione'])
            if nome.lower() == nome_dipendente.lower():
                if pd.notna(row['data_dt']):
                    data_app = row['data_dt'].date()
                    if 0 < gg <= 1.0:
                        giorni_occupati[data_app] = giorni_occupati.get(data_app, 0.0) + gg
                    elif gg > 1.0:
                        movimenti_bulk.append({"nome": nome_dipendente, "gg": gg})

    for bulk in movimenti_bulk:
        gg_rimanenti = bulk["gg"]
        for d in giorni_utili_feriali:
            if gg_rimanenti <= 0: break
            spazio_disponibile = 1.0 - giorni_occupati.get(d, 0.0)
            if spazio_disponibile > 0:
                quota = min(spazio_disponibile, gg_rimanenti)
                gg_rimanenti -= quota
                giorni_occupati[d] = giorni_occupati.get(d, 0.0) + quota

    riga_0 = [nome_azienda] + [""] * 32
    riga_1 = ["ANNO =", str(anno_sel)] + [""] * 31
    
    riga_giorni_sett = [""]
    riga_date = ["COGNOME E NOME"]
    
    for g in range(1, 32):
        if g <= num_giorni_mese:
            d = date(anno_sel, mese_sel, g)
            giorno_sett = GIORNI_SETTIMANA_ITA[d.weekday()]
            nome_mese_abbrev = nome_mese_stringa[:3].lower()
            data_str = f"{g}-{nome_mese_abbrev}"
            riga_giorni_sett.append(giorno_sett)
            riga_date.append(data_str)
        else:
            riga_giorni_sett.append("")
            riga_date.append("")
            
    riga_giorni_sett.extend(["Colonna3", ""])
    riga_date.extend(["Colonna3", "G.L"])
    
    riga_presenze = [nome_dipendente]
    totale_giorni_lavorati = 0.0
    
    for g in range(1, 32):
        if g <= num_giorni_mese:
            d = date(anno_sel, mese_sel, g)
            presenza = giorni_occupati.get(d, 0.0)
            if presenza > 0:
                val_mostrato = int(presenza) if presenza.is_integer() else presenza
                riga_presenze.append(val_mostrato)
                totale_giorni_lavorati += presenza
            else:
                riga_presenze.append("")
        else:
            riga_presenze.append("")
            
    riga_presenze.append("")
    riga_presenze.append(int(totale_giorni_lavorati) if totale_giorni_lavorati.is_integer() else totale_giorni_lavorati)
    
    colonne_df = [f"Col{i}" for i in range(len(riga_date))]
    dati_export = [riga_0, riga_1, riga_giorni_sett, riga_date, riga_presenze]
    
    for _ in range(5):
        dati_export.append([""] * len(riga_date))
        
    df_export = pd.DataFrame(dati_export, columns=colonne_df)

    st.subheader("👀 Anteprima Modulo Busta Paga")
    c_inf1, c_inf2 = st.columns(2)
    c_inf1.info(f"**Periodo:** {nome_mese_stringa} {anno_sel}")
    c_inf2.info(f"**Totale Giornate Lavorate:** {totale_giorni_lavorati:,.1f} gg")
    
    st.dataframe(df_export, use_container_width=True, hide_index=True)
    st.divider()
    
    st.subheader("📥 Scarica il Report per Commercialista")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        buffer_xl = io.BytesIO()
        with pd.ExcelWriter(buffer_xl, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, header=False, sheet_name=nome_dipendente.split()[0][:31])
            workbook = writer.book
            worksheet = writer.sheets[nome_dipendente.split()[0][:31]]
            for col_num, _ in enumerate(df_export.columns):
                col_letter = chr(65 + col_num) if col_num < 26 else chr(64 + col_num // 26) + chr(65 + col_num % 26)
                if col_num == 0:
                    worksheet.column_dimensions[col_letter].width = 30
                else:
                    worksheet.column_dimensions[col_letter].width = 6
        buffer_xl.seek(0)
        st.download_button(
            label="🟢 Scarica Foglio Excel (.xlsx)",
            data=buffer_xl,
            file_name=f"Presenze_{nome_dipendente.replace(' ', '_')}_{nome_mese_stringa}_{anno_sel}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    with col_btn2:
        buffer_pdf = io.BytesIO()
        doc = SimpleDocTemplate(buffer_pdf, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        story = []
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=12, leading=14, fontName="Helvetica-Bold")
        style_th = ParagraphStyle('TH', parent=styles['Normal'], fontSize=7, fontName="Helvetica-Bold", alignment=1)
        style_td = ParagraphStyle('TD', parent=styles['Normal'], fontSize=7, alignment=1)
        style_td_nome = ParagraphStyle('TD_Nome', parent=styles['Normal'], fontSize=8, fontName="Helvetica-Bold", alignment=0)
        
        story.append(Paragraph(nome_azienda.upper(), style_title))
        story.append(Paragraph(f"ANNO = {anno_sel} - MESE = {nome_mese_stringa.upper()}", style_title))
        story.append(Spacer(1, 15))
        
        table_data = []
        pdf_riga_giorni = [""] + riga_giorni_sett[1:num_giorni_mese+1] + [""]
        pdf_riga_date = ["COGNOME E NOME"] + riga_date[1:num_giorni_mese+1] + ["G.L"]
        pdf_riga_pres = [Paragraph(nome_dipendente, style_td_nome)] + riga_presenze[1:num_giorni_mese+1] + [riga_presenze[-1]]
        
        pdf_riga_giorni = [Paragraph(str(x), style_th) for x in pdf_riga_giorni]
        pdf_riga_date = [Paragraph(str(x), style_th) for x in pdf_riga_date]
        
        row_pres_formatted = [pdf_riga_pres[0]]
        for val in pdf_riga_pres[1:]:
            row_pres_formatted.append(Paragraph(str(val) if val != "" else "", style_td))
            
        table_data.append(pdf_riga_giorni)
        table_data.append(pdf_riga_date)
        table_data.append(row_pres_formatted)
        
        w_nome = 140
        w_tot = 30
        w_giorno = (780 - w_nome - w_tot) / num_giorni_mese
        col_widths = [w_nome] + [w_giorno]*num_giorni_mese + [w_tot]
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#E0E0E0")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t)
        
        story.append(Spacer(1, 50))
        data_firme = [
            [Paragraph("Firma del Lavoratore", style_td_nome), Paragraph("Timbro e Firma Azienda", style_td_nome)]
        ]
        t_firme = Table(data_firme, colWidths=[390, 390])
        t_firme.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (0,0), 0.5, colors.black),
            ('LINEBELOW', (1,0), (1,0), 0.5, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(t_firme)
        
        doc.build(story)
        buffer_pdf.seek(0)
        
        st.download_button(
            label="🔴 Scarica Documento PDF (.pdf)",
            data=buffer_pdf,
            file_name=f"Presenze_{nome_dipendente.replace(' ', '_')}_{nome_mese_stringa}_{anno_sel}.pdf",
            mime="application/pdf"
        )
