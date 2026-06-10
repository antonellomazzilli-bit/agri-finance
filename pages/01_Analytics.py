import streamlit as st
import pandas as pd
import requests
import base64
import io
import plotly.express as px

st.set_page_config(page_title="Business Intelligence Agricola", layout="wide")

# --- CONFIGURAZIONE GITHUB ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def load_data_from_github():
    """Recupera i dati dal file database.csv su GitHub."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

# Funzione per formattare la valuta nel grafico
def format_it(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("📊 Business Intelligence Agricola")
st.markdown("Analisi delle performance finanziarie e dei costi colturali.")

# Caricamento Dati
df = load_data_from_github()

if df.empty or len(df) == 0:
    st.info("💡 Il database è vuoto o non esiste ancora su GitHub. Inserisci il primo movimento nella pagina principale per vedere le analisi.")
else:
    # Pre-elaborazione dati sicura
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['importo'] = pd.to_numeric(df['importo'], errors='coerce').fillna(0.0)
    df = df.dropna(subset=['data'])
    
    # Filtro Anno
    df['anno'] = df['data'].dt.year
    anni_disponibili = sorted(df['anno'].unique(), reverse=True)
    anno_selezionato = st.selectbox("Seleziona Anno di Analisi", anni_disponibili)
    
    df_filtrato = df[df['anno'] == anno_selezionato]

    st.divider()

    # --- GRAFICO 1: DISTRIBUZIONE DEI COSTI (USCITE) ---
    st.subheader("📌 Distribuzione delle Spese per Categoria")
    df_uscite = df_filtrato[df_filtrato['tipo'] == 'Uscita']
    
    if not df_uscite.empty:
        df_cat = df_uscite.groupby('categoria')['importo'].sum().reset_index()
        
        fig_torta = px.pie(
            df_cat, 
            values='importo', 
            names='categoria', 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Dark2
        )
        fig_torta.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_torta, use_container_width=True)
    else:
        st.write("Nessuna spesa registrata per l'anno selezionato.")

    st.divider()

    # --- GRAFICO 2: ENTRATE VS USCITE NEL TEMPO ---
    st.subheader("📈 Andamento Finanziario Mensile")
    df_filtrato['mese'] = df_filtrato['data'].dt.strftime('%m - %B')
    
    df_trend = df_filtrato.groupby(['mese', 'tipo'])['importo'].sum().reset_index().sort_values('mese')
    
    if not df_trend.empty:
        fig_barre = px.bar(
            df_trend, 
            x='mese', 
            y='importo', 
            color='tipo', 
            barmode='group',
            labels={'importo': 'Totale (€)', 'mese': 'Mese', 'tipo': 'Flusso'},
            color_discrete_map={'Entrata': '#2E7D32', 'Uscita': '#C62828'} # Verde vs Rosso
        )
        st.plotly_chart(fig_barre, use_container_width=True)
    else:
        st.write("Dati insufficienti per generare il grafico mensile.")
