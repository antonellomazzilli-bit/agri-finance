import streamlit as st
import pandas as pd
import requests
import base64
import io

st.set_page_config(page_title="Analisi Margini e KPI", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def load_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def format_it(val):
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("📊 Analisi, Ottimizzazione e Costi di Produzione")
df = load_data()

if not df.empty:
    df['data'] = pd.to_datetime(df['data'])
    anni = sorted(df['data'].dt.year.unique(), reverse=True)
    anno_sel = st.selectbox("Seleziona l'anno di analisi", anni)
    df_anno = df[df['data'].dt.year == anno_sel]
    
    # Calcoli finanziari standard
    entrate = df_anno[df_anno['tipo'] == 'Entrata']['importo'].sum()
    uscite = df_anno[df_anno['tipo'] == 'Uscita']['importo'].sum()
    
    col1, col2 = st.columns(2)
    col1.metric("Entrate Totali", format_it(entrate))
    col2.metric("Uscite Totali", format_it(uscite))

    st.divider()
    st.subheader("🎯 Costo di Produzione Unitario per Coltura")
    
    stats = []
    # Analizziamo ogni coltura presente nell'anno
    colture = [c for c in df_anno['coltura_id'].unique() if c and c != "Generale / Extra"]
    
    for c in colture:
        df_c = df_anno[df_anno['coltura_id'] == c]
        
        e_c = df_c[df_c['tipo'] == 'Entrata']['importo'].sum()
        u_c = df_c[df_c['tipo'] == 'Uscita']['importo'].sum()
        
        # Estraiamo i KG totali raccolti (tipo == 'Resa')
        kg_raccolti = df_c[df_c['tipo'] == 'Resa']['importo'].sum()
        
        # Calcolo del costo al KG (Uscite della coltura / KG raccolti)
        costo_unitario = (u_c / kg_raccolti) if kg_raccolti > 0 else 0.0
        
        stats.append({
            "Coltura": c,
            "Spese Totali (€)": format_it(u_c),
            "Totale Raccolto (KG)": f"{kg_raccolti:,.0f} Kg".replace(",", "."),
            "Costo di Produzione": f"{costo_unitario:,.2f} €/Kg".replace(".", ","),
            "Ricavi Vendite (€)": format_it(e_c)
        })
    
    if stats:
        st.table(pd.DataFrame(stats))
    else:
        st.write("Nessuna coltura specifica tracciata per quest'anno.")
else:
    st.info("Database vuoto.")
