import streamlit as st
import pandas as pd
import io
import requests
import base64
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def load_data_from_github():
    """Recupera i dati dal repository GitHub."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

# --- LOGICA DI EXPORT EXCEL ---
def generate_excel(df):
    """Genera un file Excel formattato professionalmente."""
    output = io.BytesIO()
    # Utilizzo di xlsxwriter come engine per formattazioni avanzate
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Report_Costi')
        
        workbook  = writer.book
        worksheet = writer.sheets['Report_Costi']

        # Formati: Intestazione e Valuta
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top',
            'fg_color': '#2E7D32', 'font_color': 'white', 'border': 1
        })
        currency_format = workbook.add_format({'num_format': '€ #,##0.00'})

        # Applica formato intestazione
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 15) # Larghezza colonne

        # Aggiunta riga Totale in fondo
        last_row = len(df) + 1
        worksheet.write(last_row, 3, "TOTALE GENERALE:", workbook.add_format({'bold': True}))
        worksheet.write_formula(last_row, 4, f'=SUM(E2:E{last_row})', currency_format)

    return output.getvalue()

# --- LOGICA DI EXPORT PDF ---
def generate_pdf(df):
    """Genera un report PDF sintetico con tabella e grafico."""
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Professionale
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(46, 125, 50) # Verde Agricolo
    pdf.cell(0, 10, "REPORT FINANZIARIO AGRI-FINANCE", ln=True, align='C')
    
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Data Export: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    # Tabella Costi Principali (prime 15 righe per brevità nel PDF)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Sintesi Movimenti Recenti", ln=True)
    pdf.set_font("Arial", '', 10)
    
    # Header Tabella
    pdf.set_fill_color(200, 220, 200)
    pdf.cell(30, 8, "Data", 1, 0, 'C', True)
    pdf.cell(60, 8, "Categoria", 1, 0, 'C', True)
    pdf.cell(60, 8, "Coltura", 1, 0, 'C', True)
    pdf.cell(40, 8, "Importo", 1, 1, 'C', True)

    # Dati Tabella (limitati)
    for i, row in df.tail(15).iterrows():
        pdf.cell(30, 8, str(row['data']), 1)
        pdf.cell(60, 8, str(row['categoria']), 1)
        pdf.cell(60, 8, str(row['coltura_id']), 1)
        pdf.cell(40, 8, f"{row['importo']:.2f} EUR", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA STREAMLIT ---
st.title("📂 Centro Esportazione Dati")
st.markdown("Esporta i tuoi dati analitici in formati pronti per l'archiviazione o l'invio al commercialista.")

df = load_data_from_github()

if df.empty:
    st.error("⚠️ Il database è vuoto. Non ci sono dati da esportare.")
else:
    st.success(f"Trovati {len(df)} movimenti nel database.")
    
    # Anteprima dei dati
    with st.expander("Visualizza anteprima dati da esportare"):
        st.dataframe(df, use_container_width=True)

    st.divider()
    
    col1, col2 = st.columns(2)
    
    nome_file_base = f"Report_Costi_{datetime.now().strftime('%Y-%m-%d')}"

    with col1:
        st.subheader("Excel")
        st.write("Ideale per analisi dettagliate e calcoli.")
        excel_data = generate_excel(df)
        st.download_button(
            label="📥 Scarica Excel (.xlsx)",
            data=excel_data,
            file_name=f"{nome_file_base}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        st.subheader("PDF")
        st.write("Ideale per invio rapido e stampa.")
        try:
            pdf_data = generate_pdf(df)
            st.download_button(
                label="📥 Scarica PDF (.pdf)",
                data=pdf_data,
                file_name=f"{nome_file_base}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Errore generazione PDF: {e}")
