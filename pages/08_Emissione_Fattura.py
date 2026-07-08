import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Importazioni per la generazione del PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Emissione Fatture", layout="wide")

st.title("🧾 Generatore Fatture Commerciali")
st.markdown("Compila i campi sottostanti per generare automaticamente una fattura in formato PDF pronta da inviare ai clienti o da stampare.")

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
    numero_fattura = st.text_input("Numero Fattura:", value="1")
    data_fattura = st.date_input("Data Fattura:", format="DD/MM/YYYY")
    metodo_pagamento = st.text_input("Metodo di Pagamento:", value="Bonifico Bancario")

st.divider()

# --- SEZIONE 2: VOCI FATTURA (TABELLA INTERATTIVA) ---
st.subheader("🛒 Dettaglio Prodotti / Servizi")
st.write("Aggiungi o rimuovi le righe della fattura modificando la tabella qui sotto. I calcoli verranno eseguiti in automatico.")

# Tabella di partenza precompilata con un esempio agricolo
df_iniziale = pd.DataFrame([
    {
        "Descrizione": "Olio Extra Vergine di Oliva - Lattina 5L", 
        "Quantità": 1.0, 
        "Prezzo Unitario (€)": 50.00, 
        "Aliquota IVA (%)": 4.0
    }
])

# st.data_editor permette all'utente di aggiungere/rimuovere righe dinamicamente
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

# --- CALCOLI AUTOMATICI ---
if not df_voci.empty:
    df_voci['Imponibile Riga'] = df_voci['Quantità'] * df_voci['Prezzo Unitario (€)']
    df_voci['Imposta Riga'] = df_voci['Imponibile Riga'] * (df_voci['Aliquota IVA (%)'] / 100)
    
    totale_imponibile = df_voci['Imponibile Riga'].sum()
    totale_iva = df_voci['Imposta Riga'].sum()
    totale_fattura = totale_imponibile + totale_iva

    # Mostriamo i totali a schermo
    st.divider()
    c_tot1, c_tot2, c_tot3 = st.columns(3)
    c_tot1.metric("Totale Imponibile", f"€ {totale_imponibile:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c_tot2.metric("Totale IVA", f"€ {totale_iva:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c_tot3.metric("TOTALE DA PAGARE", f"€ {totale_fattura:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # --- GENERAZIONE PDF ---
    st.write("")
    if st.button("📄 Genera Fattura in PDF", type="primary"):
        with st.spinner("Creazione del documento in corso..."):
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

            # Intestazione Documento
            story.append(Paragraph(f"<b>{mittente_nome.upper()}</b>", style_title))
            story.append(Paragraph(f"{mittente_indirizzo} | P.IVA/C.F.: {mittente_piva}", style_subtitle))
            
            # Blocco Dati Fattura e Cliente
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

            # Tabella Prodotti
            table_data = [[
                Paragraph("<b>Descrizione</b>", style_th),
                Paragraph("<b>Q.tà</b>", style_th),
                Paragraph("<b>Prezzo Un.</b>", style_th),
                Paragraph("<b>IVA</b>", style_th),
                Paragraph("<b>Importo</b>", style_th)
            ]]
            
            for _, r in df_voci.iterrows():
                if pd.notna(r['Descrizione']) and r['Descrizione'].strip() != "":
                    table_data.append([
                        Paragraph(str(r['Descrizione']), style_td_left),
                        Paragraph(f"{r['Quantità']:.2f}", style_td),
                        Paragraph(f"&euro; {r['Prezzo Unitario (€)']:.2f}", style_td),
                        Paragraph(f"{r['Aliquota IVA (%)']:.0f}%", style_td),
                        Paragraph(f"&euro; {r['Imponibile Riga']:.2f}", style_td_right)
                    ])
                    
            t_items = Table(table_data, colWidths=[230, 50, 70, 50, 110])
            t_items.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2E7D32")), # Verde agricolo scuro
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

            # Blocco Totali
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
            
            # Note a piè di pagina (Metodo di pagamento)
            story.append(Spacer(1, 40))
            story.append(Paragraph(f"<b>Metodo di Pagamento concordato:</b> {metodo_pagamento}", style_normal))

            # Costruzione PDF
            doc.build(story)
            buffer_pdf.seek(0)
            
            st.success("Fattura generata con successo!")
            st.download_button(
                label="📥 Scarica Fattura (.pdf)",
                data=buffer_pdf,
                file_name=f"Fattura_{numero_fattura}_{mittente_nome.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
else:
    st.warning("Aggiungi almeno un prodotto o servizio per generare la fattura.")
