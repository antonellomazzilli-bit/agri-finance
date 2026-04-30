import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Gestione Dati", layout="wide")
DB_NAME = 'agri_finance.db'

def load_data():
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM transactions ORDER BY data DESC", conn)
        if not df.empty:
            df['data_dt'] = pd.to_datetime(df['data'])
        return df

st.title("✏️ Modifica Movimenti")
df = load_data()

if not df.empty:
    # Formato visualizzazione nella lista: 29/04/2026 | Carburante | € 1.200,50
    df['label'] = df['data_dt'].dt.strftime('%d/%m/%Y') + " | " + df['categoria'] + " | € " + \
                  df['importo'].map('{:,.2f}'.format).str.replace(",", "X").str.replace(".", ",").replace("X", ".")
    
    scelta = st.selectbox("Seleziona movimento", df['label'].tolist())
    riga = df[df['label'] == scelta].iloc[0]

    with st.form("edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_data = st.date_input("Data", value=riga['data_dt'], format="DD/MM/YYYY")
            n_imp = st.number_input("Importo (€)", value=float(riga['importo']), format="%.2f", step=0.01)
        with c2:
            n_cat = st.text_input("Categoria", value=riga['categoria'])
            n_colt = st.text_input("Coltura", value=riga['coltura_id'])
        
        n_desc = st.text_area("Descrizione", value=riga['descrizione'])
        
        if st.form_submit_button("Aggiorna"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("UPDATE transactions SET data=?, importo=?, categoria=?, coltura_id=?, descrizione=? WHERE id=?",
                             (n_data, n_imp, n_cat, n_colt, n_desc, int(riga['id'])))
            st.success("Modifica salvata!")
            st.rerun()