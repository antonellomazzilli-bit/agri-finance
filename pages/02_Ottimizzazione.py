import streamlit as st
import pandas as pd
import requests
import base64
import io

st.set_page_config(page_title="Analisi Margini", layout="wide")

# --- CONFIGURAZIONE GITHUB ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def load_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        # Correzione: uso di io.StringIO per compatibilità con le nuove versioni di pandas
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

st.title("📊 Analisi e Ottimizzazione")

df = load_data()

if not df.empty:
    # Convertiamo la data per poter filtrare per anno
    df['data'] = pd.to_datetime(df['data'])
    anni = sorted(df['data'].dt.year.unique(), reverse=True)
    anno_sel = st.selectbox("Seleziona l'anno di analisi", anni)
    
    df_anno = df[df['data'].dt.year == anno_sel]
    
    # Calcolo metriche totali
    entrate = df_anno[df_anno['tipo'] == 'Entrata']['importo'].sum()
    uscite = df_anno[df_anno['tipo'] == 'Uscita']['importo'].sum()
    bilancio = entrate - uscite
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Entrate Totali", f"€ {entrate:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Uscite Totali", f"€ {uscite:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Margine Netto", f"€ {bilancio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta=float(bilancio))

    st.divider()
    
    # Grafico redditività per coltura
    st.subheader("Profitto per singola Coltura")
    # Calcoliamo la differenza tra entrate e uscite raggruppate per coltura
    df_coltura = df_anno.groupby(['coltura_id', 'tipo'])['importo'].sum().unstack(fill_value=0)
    if 'Entrata' not in df_coltura: df_coltura['Entrata'] = 0
    if 'Uscita' not in df_coltura: df_coltura['Uscita'] = 0
    df_coltura['Margine'] = df_coltura['Entrata'] - df_coltura['Uscita']
    
    st.bar_chart(df_coltura['Margine'])
    
    st.dataframe(df_coltura.style.format("€ {:.2f}"), use_container_width=True)
else:
    st.info("Nessun dato trovato nel database. Inizia a registrare i movimenti nella pagina principale.")
