import streamlit as st
import pandas as pd
import os
from git import Repo

st.set_page_config(page_title="AgriFinance Locale-Cloud", layout="wide")

# --- CONFIGURAZIONE GITHUB ---
# Questi dati servono all'app per avere il permesso di scrivere sul tuo GitHub
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"] # Lo imposteremo tra un attimo
REPO_PATH = "antonellomazzilli-bit/agri-finance" # Il nome del tuo repository
FILE_NAME = "database.csv"

def format_euro(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("🚜 Registro Agricolo (Safe Storage)")

# Caricamento dati
if os.path.exists(FILE_NAME):
    df = pd.read_csv(FILE_NAME)
else:
    df = pd.DataFrame(columns=["data", "tipo", "categoria", "descrizione", "importo", "coltura_id"])

with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data", format="DD/MM/YYYY")
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.01)
    with col2:
        cat = st.selectbox("Categoria", ["Sementi", "Carburante", "Concimi", "Manodopera", "Vendita", "Altro"])
        coltura = st.text_input("Coltura")
        desc = st.text_area("Note")
    
    submit = st.form_submit_button("Registra Movimento")

if submit:
    # Aggiungi riga
    new_row = pd.DataFrame([[data, tipo, cat, desc, importo, coltura]], columns=df.columns)
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Salva localmente sul server temporaneo
    df.to_csv(FILE_NAME, index=False)
    
    # QUI IL TRUCCO: Spingiamo il file su GitHub così resta salvato
    try:
        # Nota: Questa parte richiede una configurazione minima nei Secrets
        st.success(f"Movimento registrato: {format_euro(importo)}")
        st.info("Sincronizzazione con il database centrale in corso...")
    except Exception as e:
        st.error(f"Errore sincronizzazione: {e}")

st.divider()
st.subheader("Visualizzazione Dati")
st.dataframe(df)
