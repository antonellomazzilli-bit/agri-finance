import streamlit as st
import pandas as pd
import requests
import base64
import json
from datetime import datetime
import time

# Configurazione ottimizzata per Smartphone
st.set_page_config(page_title="Portale Lavoratore", page_icon="🚜", layout="centered")

# --- CONNESSIONE GITHUB (File Isolato) ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_RICHIESTE = "richieste_sospese.csv"

def get_richieste():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_RICHIESTE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        from io import StringIO
        return pd.read_csv(StringIO(content)), data['sha']
    else:
        colonne = ['timestamp', 'lavoratore', 'tipo', 'valore', 'note', 'stato']
        return pd.DataFrame(columns=colonne), None

def salva_richiesta(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_RICHIESTE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    csv_data = df.to_csv(index=False)
    encoded_data = base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')
    
    payload = {"message": "Nuova richiesta dipendente", "content": encoded_data}
    if sha: payload["sha"] = sha
        
    r = requests.put(url, headers=headers, data=json.dumps(payload))
    return r.status_code in [200, 201]

# --- INTERFACCIA MOBILE SEMPLIFICATA ---
st.title("🚜 Area Personale")
st.markdown("Compila i campi qui sotto. Puoi inserire solo le ore, solo le spese, o **entrambi insieme!**")

df_richieste, sha_attuale = get_richieste()

with st.container(border=True):
    nome_dipendente = st.selectbox("👤 Chi sei?", ["Seleziona il tuo nome...", "Iannone Felice"])
    
    st.divider()
    
    # Campo 1: Ore (Preimpostato a 0)
    st.markdown("### ⏱️ Tempo di Lavoro")
    ore_input = st.number_input("Ore Lavorate (Oggi)", min_value=0.0, max_value=16.0, step=0.5, value=0.0)
    
    # Campo 2: Spese (Preimpostato a 0)
    st.markdown("### 💶 Spese Vive / Anticipi")
    spesa_input = st.number_input("Importo Speso (€)", min_value=0.0, max_value=500.0, step=1.0, value=0.0)
    
    st.divider()
    
    note_input = st.text_area("📝 Descrizione (Obbligatoria)", placeholder="Es. Potatura ulivi (8 ore). Comprato benzina decespugliatore (20€).", height=100)
    
    invia_btn = st.button("Invia all'Azienda 🚀", type="primary", use_container_width=True)

# --- LOGICA DI INVIO MULTIPLO ---
if invia_btn:
    if nome_dipendente == "Seleziona il tuo nome...":
        st.error("⚠️ Seleziona prima il tuo nome!")
    elif ore_input == 0 and spesa_input == 0:
        st.error("⚠️ Inserisci almeno le ore di lavoro o una spesa.")
    elif len(note_input) < 3:
        st.error("⚠️ Scrivi una breve descrizione nel campo note.")
    else:
        nuove_righe = []
        timestamp_ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Se ha inserito le ore, crea la prima notifica
        if ore_input > 0:
            nuove_righe.append({
                'timestamp': timestamp_ora,
                'lavoratore': nome_dipendente,
                'tipo': "Tempo di Lavoro",
                'valore': f"{ore_input} Ore",
                'note': note_input,
                'stato': "In Attesa"
            })
            
        # Se ha inserito anche le spese, crea la seconda notifica
        if spesa_input > 0:
            nuove_righe.append({
                'timestamp': timestamp_ora,
                'lavoratore': nome_dipendente,
                'tipo': "Spese Vive / Rimborsi",
                'valore': f"{spesa_input} Euro",
                'note': note_input,
                'stato': "In Attesa"
            })
            
        df_richieste = pd.concat([df_richieste, pd.DataFrame(nuove_righe)], ignore_index=True)
        
        with st.spinner("Invio in corso..."):
            if salva_richiesta(df_richieste, sha_attuale):
                st.success("✅ Dati inviati con successo all'amministrazione!")
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ Errore di rete. Riprova.")
