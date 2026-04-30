import streamlit as st
import pandas as pd
import requests
import base64
import io

st.set_page_config(page_title="Gestione Database", layout="wide")

# --- CONFIGURAZIONE GITHUB ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def get_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data_json = r.json()
        content = base64.b64decode(data_json["content"]).decode("utf-8")
        # Correzione: uso di io.StringIO
        df = pd.read_csv(io.StringIO(content))
        return df, data_json["sha"]
    return pd.DataFrame(), None

def update_github_file(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False)
    
    payload = {
        "message": "Eliminazione riga correzione dati",
        "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": "main"
    }
    
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

st.title("✏️ Manutenzione Dati")
st.write("Usa questa pagina per eliminare registrazioni errate dal database cloud.")

df, sha = get_github_data()

if not df.empty:
    # Creiamo una descrizione leggibile per la selezione
    df['desc_scelta'] = df['data'].astype(str) + " | " + df['categoria'] + " | " + df['importo'].astype(str) + " €"
    
    operazione_da_eliminare = st.selectbox("Seleziona l'operazione da cancellare:", df['desc_scelta'].tolist())
    
    if st.button("🗑️ Elimina questa operazione"):
        # Troviamo l'indice della riga selezionata
        indice = df[df['desc_scelta'] == operazione_da_eliminare].index[0]
        
        # Creiamo il nuovo dataframe senza quella riga
        df_nuovo = df.drop(indice).drop(columns=['desc_scelta'])
        
        with st.spinner("Aggiornamento database su GitHub..."):
            if update_github_file(df_nuovo, sha):
                st.success("Operazione eliminata con successo!")
                st.rerun()
            else:
                st.error("Errore durante la sincronizzazione con GitHub.")
    
    st.divider()
    st.subheader("Contenuto attuale del database")
    st.dataframe(df.drop(columns=['desc_scelta']), use_container_width=True)
else:
    st.info("Il database è vuoto.")
