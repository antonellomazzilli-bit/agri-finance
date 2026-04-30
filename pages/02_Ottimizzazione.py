import streamlit as st
import pandas as pd
import requests
import base64

st.set_page_config(page_title="Analisi Margini", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def load_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        from io import StringIO
        return pd.read_csv(StringIO(content))
    return pd.DataFrame()

st.title("📊 Analisi e Ottimizzazione")
df = load_data()

if not df.empty:
    df['data'] = pd.to_datetime(df['data'])
    anno = st.selectbox("Anno", sorted(df['data'].dt.year.unique(), reverse=True))
    df_anno = df[df['data'].dt.year == anno]
    
    e = df_anno[df_anno['tipo'] == 'Entrata']['importo'].sum()
    u = df_anno[df_anno['tipo'] == 'Uscita']['importo'].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Entrate", f"€ {e:,.2f}".replace(".", "X").replace(",", ".").replace("X", ","))
    c2.metric("Uscite", f"€ {u:,.2f}".replace(".", "X").replace(",", ".").replace("X", ","))
    
    st.subheader("Margine per Coltura")
    # Logica raggruppamento per coltura_id
    res = df_anno.groupby('coltura_id')['importo'].sum().reset_index()
    st.bar_chart(data=res, x='coltura_id', y='importo')
else:
    st.warning("Database non trovato o vuoto.")
