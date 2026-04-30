import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Ottimizzazione", layout="wide")
DB_NAME = 'agri_finance.db'

def format_it(val):
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def load_data():
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM transactions", conn)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'], errors='coerce')
            df = df.dropna(subset=['data'])
            df['anno'] = df['data'].dt.year.astype(int)
        return df

st.title("📊 Analisi e Ottimizzazione")
df = load_data()

if not df.empty:
    anni = sorted(df['anno'].unique(), reverse=True)
    anno_sel = st.selectbox("Anno", anni)
    df_anno = df[df['anno'] == anno_sel]

    # Metriche formattate
    entrate = df_anno[df_anno['tipo'] == 'Entrata']['importo'].sum()
    uscite = df_anno[df_anno['tipo'] == 'Uscita']['importo'].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Totale Entrate", format_it(entrate))
    c2.metric("Totale Uscite", format_it(uscite))

    # Tabella ROI
    st.subheader("Efficienza per Coltura")
    stats = []
    for c in df_anno['coltura_id'].unique():
        e = df_anno[(df_anno['coltura_id'] == c) & (df_anno['tipo'] == 'Entrata')]['importo'].sum()
        u = df_anno[(df_anno['coltura_id'] == c) & (df_anno['tipo'] == 'Uscita')]['importo'].sum()
        roi = ((e - u) / u * 100) if u > 0 else 0
        stats.append({"Coltura": c, "Entrate": format_it(e), "Uscite": format_it(u), "ROI": f"{roi:.2f} %"})
    
    st.table(pd.DataFrame(stats))
