import streamlit as st
import pandas as pd
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="AgriFinance Cloud", layout="wide")

# --- CONFIGURAZIONE GITHUB ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"
BRANCH = "main"

def format_euro(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

import io  # Aggiungi questa riga in alto insieme agli altri import

def get_github_file():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        # Questa è la riga corretta che sostituisce quella che dava errore:
        return pd.read_csv(io.StringIO(content)), r.json()["sha"]
    
    # Se il file non esiste ancora, creiamo un dataframe vuoto con le colonne giuste
    columns = ["data", "tipo", "categoria", "descrizione", "importo", "coltura_id"]
    return pd.DataFrame(columns=columns), None

def save_to_github(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content = df.to_csv(index=False)
    data = {
        "message": "Update database.csv via AgriApp",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": BRANCH
    }
    if sha: data["sha"] = sha
    r = requests.put(url, headers=headers, json=data)
    return r.status_code in [200, 201]

st.title("🚜 Registro Agricolo Cloud")

with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data Operazione", format="DD/MM/YYYY")
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.01)
    with col2:
        cat = st.selectbox("Categoria", ["Sementi", "Carburante", "Concimi", "Manodopera", "Vendita", "Altro"])
        colt = st.text_input("Coltura")
        desc = st.text_area("Note")
    
    if st.form_submit_button("Registra Movimento"):
        df, sha = get_github_file()
        new_row = pd.DataFrame([[data.strftime('%Y-%m-%d'), tipo, cat, desc, importo, colt]], columns=df.columns)
        df = pd.concat([df, new_row], ignore_index=True)
        if save_to_github(df, sha):
            st.success(f"Registrato con successo: {format_euro(importo)}")
            st.balloons()
        else:
            st.error("Errore nel salvataggio su GitHub.")

st.divider()
st.subheader("Ultimi Movimenti")
df_view, _ = get_github_file()
if not df_view.empty:
    st.dataframe(df_view.tail(10), use_container_width=True)
