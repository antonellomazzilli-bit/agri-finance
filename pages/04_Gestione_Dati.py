import streamlit as st
import pandas as pd
import requests
import base64

st.set_page_config(page_title="Gestione Dati", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def get_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        from io import StringIO
        return pd.read_csv(StringIO(content)), r.json()["sha"]
    return pd.DataFrame(), None

def update_github(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content = df.to_csv(index=False)
    data = {
        "message": "Delete row via AgriApp",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "sha": sha
    }
    requests.put(url, headers=headers, json=data)

st.title("✏️ Gestione Database")
df, sha = get_data()

if not df.empty:
    st.write("Seleziona una riga da eliminare:")
    df['id_temp'] = df.index
    selected_row = st.selectbox("Movimento", df.apply(lambda r: f"{r['data']} - {r['categoria']} - {r['importo']}€", axis=1))
    
    if st.button("🗑️ Elimina Definitivamente"):
        idx = df[df.apply(lambda r: f"{r['data']} - {r['categoria']} - {r['importo']}€", axis=1) == selected_row].index[0]
        df = df.drop(idx).drop(columns=['id_temp'], errors='ignore')
        update_github(df, sha)
        st.success("Riga eliminata! L'app si riavvierà...")
        st.rerun()
else:
    st.info("Nessun dato da gestire.")
