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

# --- INTERFACCIA MOBILE ---
st.title("🚜 Area Personale")

df_richieste, sha_attuale = get_richieste()

nome_dipendente = st.selectbox("👤 Chi sei?", ["Seleziona il tuo nome...", "Iannone Felice"])

if nome_dipendente != "Seleziona il tuo nome...":
    # Creazione delle due sezioni: Inserimento e Tabella Riepilogo
    tab1, tab2 = st.tabs(["📝 Inserisci Dati", "📅 Tabella Mensile"])
    
    # ==========================================
    # --- TAB 1: INSERIMENTO CON DATA SPECIFICA ---
    # ==========================================
    with tab1:
        st.markdown("Compila i campi. Scegli il giorno esatto a cui si riferisce il lavoro o la spesa.")
        with st.container(border=True):
            # IL NUOVO CALENDARIO
            data_lavoro = st.date_input("📅 Giorno di riferimento", value=datetime.today(), format="DD/MM/YYYY")
            st.divider()
            
            # Campo 1: Ore
            st.markdown("### ⏱️ Tempo di Lavoro")
            ore_input = st.number_input("Ore Lavorate", min_value=0.0, max_value=24.0, step=0.5, value=0.0)
            
            # Campo 2: Spese
            st.markdown("### 💶 Spese Vive / Anticipi")
            spesa_input = st.number_input("Importo Speso (€)", min_value=0.0, max_value=500.0, step=1.0, value=0.0)
            
            st.divider()
            
            note_input = st.text_area("📝 Note Aggiuntive (Obbligatorie se inserisci dati)", placeholder="Es. Potatura ulivi, oppure scontrino gasolio...", height=80)
            
            invia_btn = st.button("Invia all'Azienda 🚀", type="primary", use_container_width=True)

        if invia_btn:
            if ore_input == 0 and spesa_input == 0:
                st.error("⚠️ Inserisci almeno le ore di lavoro o una spesa.")
            elif len(note_input) < 3:
                st.error("⚠️ Scrivi una breve descrizione nel campo note.")
            else:
                nuove_righe = []
                data_formattata = data_lavoro.strftime("%d/%m/%Y")
                timestamp_invio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Iniezione sicura della data nelle note per non rompere il database principale
                if ore_input > 0:
                    nuove_righe.append({
                        'timestamp': timestamp_invio,
                        'lavoratore': nome_dipendente,
                        'tipo': "Tempo di Lavoro",
                        'valore': f"{ore_input} Ore",
                        'note': f"[Lavoro del {data_formattata}] {note_input}",
                        'stato': "In Attesa"
                    })
                    
                if spesa_input > 0:
                    nuove_righe.append({
                        'timestamp': timestamp_invio,
                        'lavoratore': nome_dipendente,
                        'tipo': "Spese Vive / Rimborsi",
                        'valore': f"{spesa_input} Euro",
                        'note': f"[Spesa del {data_formattata}] {note_input}",
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

    # ==========================================
    # --- TAB 2: TABELLA RIEPILOGATIVA PERSONALE ---
    # ==========================================
    with tab2:
        st.markdown("### 📊 Il tuo Foglio Presenze")
        st.markdown("Qui vedi tutto ciò che hai inviato finora e lo stato di approvazione aziendale.")
        
        if not df_richieste.empty:
            # Filtriamo il database per mostrare solo i dati del dipendente connesso
            df_mio = df_richieste[df_richieste['lavoratore'] == nome_dipendente].copy()
            
            if not df_mio.empty:
                # Estraiamo la data che era stata salvata nella nota per formare una tabella pulita
                def estrai_data_nota(testo):
                    if "[Lavoro del" in testo or "[Spesa del" in testo:
                        try:
                            return testo.split("]")[0].split("del ")[1]
                        except:
                            return "Data non spec."
                    return "Data non spec."
                    
                df_mio['Giorno'] = df_mio['note'].apply(estrai_data_nota)
                
                # Ripuliamo la nota per togliere la data tra parentesi
                df_mio['Note'] = df_mio['note'].apply(lambda x: x.split("] ")[1] if "]" in x else x)
                
                # Selezioniamo e riordiniamo le colonne da far vedere al dipendente
                df_display = df_mio[['Giorno', 'tipo', 'valore', 'Note', 'stato']].copy()
                df_display.columns = ['Data', 'Categoria', 'Quantità', 'Descrizione', 'Stato Approvazione']
                
                # Mostriamo la tabella (hide_index toglie i numeri di riga per renderla più pulita)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.info("Nessuna registrazione o spesa inviata finora.")
        else:
            st.info("Nessuna registrazione o spesa inviata finora.")
else:
    st.info("Seleziona il tuo nome per accedere alle funzionalità.")
