import streamlit as st
import pandas as pd
import requests
import base64
import json
from datetime import datetime

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
        # Se il file non esiste ancora, crea un DataFrame vuoto con le colonne corrette
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

# --- INTERFACCIA MOBILE ---
st.title("🚜 Area Personale")
st.markdown("Usa questo modulo per comunicare a fine giornata i lavori svolti o le spese sostenute.")

# Recupera il database delle richieste in background
df_richieste, sha_attuale = get_richieste()

# Modulo di inserimento semplice e a prova di errore
with st.container(border=True):
    nome_dipendente = st.selectbox("👤 Chi sei?", ["Seleziona il tuo nome...", "Iannone Felice"])
    
    tipo_inserimento = st.radio("🛠️ Cosa devi comunicare?", ["Tempo di Lavoro", "Spese Vive / Rimborsi"], horizontal=False)
    
    st.divider()
    
    if tipo_inserimento == "Tempo di Lavoro":
        valore_input = st.number_input("⏱️ Ore Lavorate (Oggi)", min_value=0.0, max_value=16.0, step=0.5)
        etichetta_valore = "Ore"
    else:
        valore_input = st.number_input("💶 Importo Anticipato (€)", min_value=0.0, max_value=500.0, step=5.0)
        etichetta_valore = "Euro"
        
    note_input = st.text_area("📝 Descrizione (Cosa hai fatto o cosa hai comprato?)", placeholder="Es. Potatura ulivi, oppure acquisto fascette...", height=100)
    
    invia_btn = st.button("Invia all'Azienda 🚀", type="primary", use_container_width=True)

# --- LOGICA DI SALVATAGGIO ---
if invia_btn:
    if nome_dipendente == "Seleziona il tuo nome...":
        st.error("⚠️ Seleziona prima il tuo nome!")
    elif valore_input <= 0:
        st.error("⚠️ Inserisci un valore maggiore di zero.")
    elif len(note_input) < 3:
        st.error("⚠️ Scrivi una breve descrizione del lavoro o della spesa.")
    else:
        nuova_riga = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'lavoratore': nome_dipendente,
            'tipo': tipo_inserimento,
            'valore': f"{valore_input} {etichetta_valore}",
            'note': note_input,
            'stato': "In Attesa"
        }
        
        df_richieste = pd.concat([df_richieste, pd.DataFrame([nuova_riga])], ignore_index=True)
        
        with st.spinner("Invio in corso..."):
            if salva_richiesta(df_richieste, sha_attuale):
                st.success("✅ Dati inviati con successo all'amministrazione!")
            else:
                st.error("❌ Errore di rete. Riprova.")
