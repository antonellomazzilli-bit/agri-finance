import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
import time

st.set_page_config(page_title="Scadenzario e Tranche", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def format_euro(val):
    try:
        val = float(val)
    except:
        val = 0.0
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data_json = r.json()
        content = base64.b64decode(data_json["content"]).decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
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
    # --- 🧹 NORMALIZZAZIONE DATI (IL SALVAVITA) ---
    if 'stato' not in df.columns:
        df['stato'] = 'Saldato'
        
    # Puliamo la colonna da spazi invisibili, campi nulli e forziamo la maiuscola
    df['stato'] = df['stato'].fillna('Saldato').astype(str).str.strip().str.title()
    df['data'] = df['data'].fillna("Data Sconosciuta").astype(str)
    df['categoria'] = df['categoria'].fillna("Generica").astype(str)
    
   # --- FILTRO GLOBALE (ISOLAMENTO HR) ---
    # Prende le Uscite NON saldate, ma IGNORA le categorie gestite a parte nell'Estratto Conto Dipendenti
    cat_escluse = ['Manodopera', 'Manodopera Extra', 'Busta Paga', 'Saldo Extra']
    df_impegnati = df[(df['stato'] != 'Saldato') & (df['tipo'] == 'Uscita') & (~df['categoria'].isin(cat_escluse))].copy()
    
    if df_impegnati.empty:
        st.success("🎉 Ottimo! Non ci sono pagamenti in sospeso. Tutto saldato.")
    else:
        st.subheader("⚠️ Spese in attesa di saldo")
        
        # Creiamo un selettore visivo delle pendenze
        df_impegnati['visualizza'] = df_impegnati['data'] + " | " + df_impegnati['categoria'] + " | Residuo: " + df_impegnati['importo'].astype(str) + " €"
        scelta = st.selectbox("Seleziona quale spesa vuoi pagare (interamente o a tranche):", df_impegnati['visualizza'].tolist())
        
        # Troviamo l'indice originale nel database della riga scelta
        idx_originale = df_impegnati[df_impegnati['visualizza'] == scelta].index[0]
        riga_selezionata = df.loc[idx_originale]
        importo_originario = float(riga_selezionata['importo'])
        
        st.divider()
        st.subheader(f"Pagamento Tranche per: {riga_selezionata['categoria']}")
        st.info(f"Dettagli spesa originaria: {riga_selezionata['descrizione']} di complessivi {format_euro(importo_originario)}")
        
        with st.form("form_tranche"):
            data_pagamento = st.date_input("Data di questo pagamento", value=datetime.today())
            importo_tranche = st.number_input("Importo della tranche da pagare (€)", min_value=0.01, step=10.0, format="%.2f")
            nota_tranche = st.text_input("Nota sul pagamento (es. Pagato con bonifico, Assegno num...)")
            
            paga_button = st.form_submit_button("💳 Registra Pagamento Tranche", type="primary")
            
        if paga_button:
            # BLOCCO DI SICUREZZA ANTI-ERRORE
            if importo_tranche > importo_originario:
                st.error(f"⚠️ Operazione negata: stai cercando di pagare {format_euro(importo_tranche)}, ma il debito residuo è di soli {format_euro(importo_originario)}.")
            else:
                importo_residuo = importo_originario - importo_tranche
                
                # 1. Creiamo la riga della Tranche clonando l'originale
                nuova_tranche_dict = riga_selezionata.to_dict()
                nuova_tranche_dict['data'] = data_pagamento.strftime('%d-%m-%Y')
                nuova_tranche_dict['descrizione'] = f"TRANCHE di: {riga_selezionata['descrizione']} | Note: {nota_tranche}"
                nuova_tranche_dict['importo'] = importo_tranche
                nuova_tranche_dict['stato'] = 'Saldato'
                
                # 2. Aggiorniamo l'impegno originario
                if importo_residuo <= 0.01:
                    df.at[idx_originale, 'stato'] = 'Saldato'
                    df.at[idx_originale, 'importo'] = 0.0
                    df.at[idx_originale, 'descrizione'] = f"{riga_selezionata['descrizione']} (Estinto completamente)"
                    msg_commit = f"Estinto debito {riga_selezionata['categoria']}"
                else:
                    df.at[idx_originale, 'importo'] = importo_residuo
                    df.at[idx_originale, 'descrizione'] = f"{riga_selezionata['descrizione']} | Già versati {importo_tranche}€ il {data_pagamento.strftime('%d/%m/%Y')}"
                    msg_commit = f"Pagata tranche di {importo_tranche}€ per {riga_selezionata['categoria']}"
                
                # Aggiungiamo la nuova riga al dataframe generale
                df_aggiornato = pd.concat([df, pd.DataFrame([nuova_tranche_dict])], ignore_index=True)
                
                # Pulizia di sicurezza
                if 'visualizza' in df_aggiornato.columns: df_aggiornato = df_aggiornato.drop(columns=['visualizza'])
                
                with st.spinner("Salvataggio operazione in corso..."):
                    if update_github_file(df_aggiornato, sha, msg_commit):
                        st.success(f"Tranche di {format_euro(importo_tranche)} registrata con successo! Residuo aggiornato.")
                        time.sleep(1.5)
                        st.rerun()
else:
    st.info("Database vuoto o non raggiungibile.")
