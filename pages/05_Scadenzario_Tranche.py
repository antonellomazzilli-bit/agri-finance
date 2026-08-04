import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime

st.set_page_config(page_title="Scadenzario e Tranche", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def format_euro(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data_json = r.json()
        content = base64.b64decode(data_json["content"]).decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
        
        # --- 🧹 NORMALIZZAZIONE COLONNA STATO ---
        if 'stato' not in df.columns:
            df['stato'] = 'Saldato'
        else:
            # Assicuriamoci che non ci siano spazi o differenze tra maiuscole/minuscole
            df['stato'] = df['stato'].fillna('Saldato').astype(str).str.strip().str.title()
            
        return df, data_json["sha"]
    return pd.DataFrame(), None

def update_github_file(df, sha, msg):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False)
    payload = {"message": msg, "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"), "sha": sha, "branch": "main"}
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

st.title("💸 Gestione Pagamenti Impegnati e Tranche")
st.markdown("Usa questa pagina per monitorare i debiti commerciali o gli impegni finanziari e registrarne i pagamenti parziali.")

df, sha = get_github_data()

if not df.empty:
    # --- NUOVO FILTRO GLOBALE: Prende TUTTE le Uscite che NON sono etichettate come "Saldato" ---
    df_impegnati = df[(df['stato'] != 'Saldato') & (df['tipo'] == 'Uscita')].copy()
