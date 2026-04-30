import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Ottimizzazione Cloud", layout="wide")

def format_it(val):
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("📊 Analisi e Ottimizzazione (Cloud)")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    # Preparazione dati
    df['data'] = pd.to_datetime(df['data'])
    df['anno'] = df['data'].dt.year
    
    anni = sorted(df['anno'].unique(), reverse=True)
    anno_sel = st.selectbox("Seleziona Anno di Analisi", anni)
    df_anno = df[df['anno'] == anno_sel]

    # Metriche
    e_tot = df_anno[df_anno['tipo'] == 'Entrata']['importo'].sum()
    u_tot = df_anno[df_anno['tipo'] == 'Uscita']['importo'].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Totale Entrate", format_it(e_tot))
    c2.metric("Totale Uscite", format_it(u_tot))

    st.subheader("Redditività per Coltura")
    stats = []
    for c in df_anno['coltura_id'].unique():
        if not c: continue
        e = df_anno[(df_anno['coltura_id'] == c) & (df_anno['tipo'] == 'Entrata')]['importo'].sum()
        u = df_anno[(df_anno['coltura_id'] == c) & (df_anno['tipo'] == 'Uscita')]['importo'].sum()
        roi = ((e - u) / u * 100) if u > 0 else 0
        stats.append({
            "Coltura": c, 
            "Entrate": format_it(e), 
            "Uscite": format_it(u), 
            "Margine": format_it(e-u),
            "ROI": f"{roi:,.2f} %".replace(".", ",")
        })
    
    if stats:
        st.table(pd.DataFrame(stats))
else:
    st.info("Nessun dato trovato nel foglio Google.")
