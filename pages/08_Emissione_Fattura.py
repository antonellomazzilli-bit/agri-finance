import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime

# Per l'esportazione in PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Emissione Fatture", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
COUNTER_FILE = "contatore_fatture.txt"

def get_invoice_counter():
    """Recupera il numero della prossima fattura dal cloud."""
    url = f"https://api.github.com/repos/{REPO}/contents/{COUNTER_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        try:
            return int(content.strip()), data["sha"]
        except:
            return 1, data["sha"]
    return 1, None

def update_invoice_counter(nuovo_numero, sha):
    """Salva in modo permanente il nuovo numero per la fattura successiva."""
    url = f"https://api.github.com/repos/{REPO}/contents/{COUNTER_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content_b64 = base64.b64encode(str(nuovo_numero).encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"Avanzamento automatico contatore fatture a {nuovo_numero}",
        "content": content_b64,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

# --- INIZIALIZZAZIONE CONTATORE ---
if 'counter_caricato' not in st.session_state:
    num_attuale, sha_attuale = get_invoice_counter()
    st.session_state.num_fattura = num_attuale
    st.session_state.sha_fattura = sha_attuale
    st.session_state.counter_caricato = True

def esegui_aggiornamento_contatore(numero_emesso, sha_attuale):
    """Callback: Scatta nel momento esatto in cui si clicca 'Scarica'"""
    if st.session_state.salva_cont_chk:
        prossimo_numero = numero_emesso + 1
        update_invoice_counter(prossimo_numero, sha_attuale)
        # Svuota la memoria temporanea forzando l'app a scaricare il nuovo numero al prossimo riavvio
        del st.session_state['counter_caricato']

st.title("🧾 Generatore Fatture Commerciali")
st.markdown("Compila i campi. Il contatore avanzerà in automatico non appena scaricherai il documento PDF.")

# --- SEZIONE 1: DATI MITTENTE E FATTURA ---
st.subheader("🏢 Dati Fattura e Intestazione")
col_mit1, col_mit2, col_mit3 = st.columns(3)

with col_mit1:
    mittente_nome = st.text_input("Ragione Sociale Mittente:", value="L'ORO DI SAN VITTORE di Mazzilli Antonio")
    mittente_indirizzo = st.text_input("Indirizzo Mittente:", placeholder="Via Roma 1, 70033 Corato (BA)")
    mittente_piva = st.text_input("Partita IVA / Codice Fiscale Mittente:", placeholder="IT01234567890")

with col_mit2:
    cliente_nome = st.text_input("Ragione Sociale Cliente:", placeholder="Mario Rossi S.r.l.")
    cliente_indirizzo = st.text_input("Indirizzo Cliente:", placeholder="Via Milano 10, 20100 Milano (MI)")
    cliente_piva = st.text_input("P.IVA / C.F. Cliente:", placeholder="IT98765432100")

with col_mit3:
    numero_fattura = st.number_input("Numero Fattura:", min_value=1, value=st.session_state.num_fattura, step=1)
    data_fattura = st.date_input("Data Fattura:", format="DD/MM/YYYY")
    metodo_pagamento = st.text_input("Metodo di Pagamento:", value="Bonifico Bancario")

st.divider()

# --- SEZIONE 2: VOCI FATTURA (TABELLA INTERATTIVA) ---
st.subheader("🛒 Dettaglio Prodotti / Servizi")
st.write("Aggiungi o rimuovi le righe. Il calcolo di imponibile e IVA viene eseguito in tempo reale.")

df_iniziale = pd.DataFrame([
    {
        "Descrizione": "Olio Extra Vergine di Oliva - Lattina 5L", 
        "Quantità": 1.0, 
        "Prezzo Unitario (€)": 50.00, 
        "Aliquota IVA (%)": 4.0
    }
])

df_voci = st.data_editor(
    df_iniziale, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "Quantità": st.column_config.NumberColumn(min_value=0.1, format="%.2f"),
        "Prezzo Unitario (€)": st.column_config.NumberColumn(min_value=0.0, format="€ %.2f"),
        "Aliquota IVA (%)": st.column_config.NumberColumn(min_value=0.0, max_value=22.0, format="%d %%")
    }
)

# --- CALCOLI AUTOMATICI E GENERAZIONE PDF REACTIVE ---
if not df_voci.empty:
    df_voci['Imponibile Riga'] = df_voci['Quantità'] * df_voci['Prezzo Unitario (€)']
    df_voci['Imposta Riga'] = df_voci['Imponibile Riga'] * (df_voci['Aliquota IVA (%)'] / 100)
    
    totale_imponibile = df_voci['Imponibile Riga'].sum()
    totale_iva = df_voci['Imposta Riga'].sum()
    totale_fattura = totale_imponibile + totale_iva

    st.divider()
    c_tot1, c_tot2, c_tot3 = st.columns(3)
    c_tot1.metric("Totale Imponibile", f"€ {totale_imponibile:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c_tot2.metric("Totale IVA", f"€ {totale_iva:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c_tot3.metric("TOTALE DA PAGARE", f"€ {totale_fattura:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # --- MOTORE PDF ---
    buffer_pdf = io.BytesIO()
    doc = SimpleDocTemplate(buffer_pdf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor("#2E7D32"), spaceAfter=5)
    style_subtitle = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=10, textColor=colors.gray, spaceAfter=20)
    style_normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10, spaceAfter=2)
    style_bold = ParagraphStyle('Bold', parent=styles['Normal'], fontSize=10, fontName="Helvetica-Bold", spaceAfter=2)
    
    style_th = ParagraphStyle('TH', parent=styles['Normal'], fontSize=10, fontName="Helvetica-Bold", textColor=colors.white, alignment=1)
    style_td = ParagraphStyle('TD', parent=styles['Normal'], fontSize=10, alignment=1)
    style_td_left = ParagraphStyle('TD_Left', parent=styles['Normal'], fontSize=10, alignment=0)
    style_td_right = ParagraphStyle('TD_Right', parent=styles['Normal'], fontSize=10, alignment=2)

    story.append(Paragraph(f"<b>{mittente_nome.upper()}</b>", style_title))
    story.append(Paragraph(f"{mittente_indirizzo} | P.IVA/C.F.: {mittente_piva}", style_subtitle))
    
    dati_header = [
        [
            Paragraph(f"<b>FATTURA N°:</b> {numero_fattura}<br/><b>Data:</b> {data_fattura.strftime('%d/%m/%Y')}", style_normal),
            Paragraph(f"<b>Spett.le</b><br/>{cliente_nome}<br/>{cliente_indirizzo}<br/>P.IVA/C.F.: {cliente_piva}", style_normal)
        ]
    ]
    t_header = Table(dati_header, colWidths=[250, 260])
    t_header.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))

    table_data = [[
        Paragraph("<b>Descrizione</b>", style_th),
        Paragraph("<b>Q.tà</b>", style_th),
        Paragraph("<b>Prezzo Un.</b>", style_th),
        Paragraph("<b>IVA</b>", style_th),
        Paragraph("<b>Importo</b>", style_th)
    ]]
    
    for _, r in df_voci.iterrows():
        if pd.notna(r['Descrizione']) and str(r['Descrizione']).strip() != "":
            table_data.append([
                Paragraph(str(r['Descrizione']), style_td_left),
                Paragraph(f"{r['Quantità']:.2f}", style_td),
                Paragraph(f"&euro; {r['Prezzo Unitario (€)']:.2f}", style_td),
                Paragraph(f"{r['Aliquota IVA (%)']:.0f}%", style_td),
                Paragraph(f"&euro; {r['Imponibile Riga']:.2f}", style_td_right)
            ])
            
    t_items = Table(table_data, colWidths=[230, 50, 70, 50, 110])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2E7D32")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F9F9F9"), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
        ('TOPPADDING', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 8),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 20))

    dati_totali = [
        ["", Paragraph("<b>Totale Imponibile:</b>", style_td_right), Paragraph(f"&euro; {totale_imponibile:.2f}", style_td_right)],
        ["", Paragraph("<b>Totale IVA:</b>", style_td_right), Paragraph(f"&euro; {totale_iva:.2f}", style_td_right)],
        ["", Paragraph("<b>TOTALE DOCUMENTO:</b>", style_bold), Paragraph(f"<b>&euro; {totale_fattura:.2f}</b>", style_bold)]
    ]
    t_totali = Table(dati_totali, colWidths=[250, 150, 110])
    t_totali.setStyle(TableStyle([
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('LINEABOVE', (2,2), (2,2), 1, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_totali)
    
    story.append(Spacer(1, 40))
    story.append(Paragraph(f"<b>Metodo di Pagamento concordato:</b> {metodo_pagamento}", style_normal))

    doc.build(story)
    buffer_pdf.seek(0)
    
    # --- ZONA DOWNLOAD E AGGIORNAMENTO CONTATORE ---
    st.divider()
    st.subheader("📥 Esportazione ed Emissione")
    
    # Checkbox per decidere se far scattare il numeratore
    st.checkbox("Avanza numeratore per la prossima fattura", value=True, key="salva_cont_chk")
    
    nome_file_cliente = str(cliente_nome).strip().replace(' ', '_') if str(cliente_nome).strip() else "Cliente_Standard"
    
    # Il pulsante scarica il file e contemporaneamente lancia la funzione di aggiornamento
    st.download_button(
        label=f"🔴 Scarica FATTURA N° {numero_fattura} (.pdf)",
        data=buffer_pdf,
        file_name=f"Fattura_{numero_fattura}_{nome_file_cliente}.pdf",
        mime="application/pdf",
        on_click=esegui_aggiornamento_contatore,
        args=(numero_fattura, st.session_state.sha_fattura)
    )
