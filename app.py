import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="AgriFinance Cloud", layout="wide")

# Funzione formato Euro
def format_euro(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("🚜 Inserimento Movimenti (Cloud)")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Form di inserimento
with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data", format="DD/MM/YYYY")
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.01, format="%.2f")
    with col2:
        cat = st.selectbox("Categoria", ["Sementi", "Carburante", "Concimi", "Manodopera", "Vendita", "Altro"])
        coltura = st.text_input("Coltura")
        desc = st.text_area("Note")
    
    submit = st.form_submit_button("Registra su Cloud")

if submit:
    # Carica dati esistenti
    existing_data = conn.read(ttl=0)
    
    # Crea nuova riga
    new_row = pd.DataFrame([{
        "data": data.strftime('%Y-%m-%d'),
        "tipo": tipo,
        "categoria": cat,
        "descrizione": desc,
        "importo": importo,
        "coltura_id": coltura
    }])
    
    # Unisci e aggiorna
    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
    conn.update(data=updated_df)
    st.success(f"Dato salvato su Google Sheets: {format_euro(importo)}")

st.divider()
st.subheader("Ultimi Movimenti Registrati")
data_preview = conn.read(ttl=0).tail(10)
if not data_preview.empty:
    st.dataframe(data_preview)
