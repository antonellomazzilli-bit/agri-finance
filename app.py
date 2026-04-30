import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="AgriFinance - Inserimento", layout="wide")

# Funzione per formattare i numeri alla "italiana" nelle tabelle
def format_euro(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- DB SETUP ---
conn = sqlite3.connect('agri_finance.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS transactions 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, tipo TEXT, 
              categoria TEXT, descrizione TEXT, importo REAL, coltura_id TEXT)''')
conn.commit()

st.title("🚜 Inserimento Movimenti Agricoli")

with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data Operazione", format="DD/MM/YYYY")
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.01, format="%.2f")
    with col2:
        cat = st.selectbox("Categoria", ["Sementi", "Carburante", "Concimi", "Manodopera", "Vendita", "Altro"])
        coltura = st.text_input("Coltura (es. Olivo, Grano)")
        desc = st.text_area("Note / Descrizione")
    
    submit = st.form_submit_button("Registra Movimento")

if submit:
    c.execute("INSERT INTO transactions (data, tipo, categoria, descrizione, importo, coltura_id) VALUES (?,?,?,?,?,?)",
              (data, tipo, cat, desc, importo, coltura))
    conn.commit()
    st.success(f"Registrato: {format_euro(importo)}")

# Tabella riepilogativa formattata
st.subheader("Ultimi inserimenti")
df = pd.read_sql_query("SELECT * FROM transactions ORDER BY data DESC LIMIT 10", conn)
if not df.empty:
    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
    df['importo'] = df['importo'].apply(format_euro)
    st.table(df.drop(columns=['id']))