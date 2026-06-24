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
    """Funzione di formattazione monetaria (Mancava nel vecchio codice)"""
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data_json = r.json()
        content = base64.b64decode(data_json["content"]).decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
        if 'stato' not in df.columns:
            df['stato'] = 'Saldato'
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
    # Filtriamo solo i movimenti impegnati ancora aperti
    df_impegnati = df[(df['stato'] == 'Impegnato') & (df['tipo'] == 'Uscita')].copy()
    
    if df_impegnati.empty:
        st.success("🎉 Ottimo! Non ci sono pagamenti impegnati in sospeso. Tutto saldato.")
    else:
        st.subheader("⚠️ Spese Impegnate in attesa di saldo")
        
        # Creiamo un selettore visivo delle pendenze
        df_impegnati['visualizza'] = df_impegnati['data'] + " | " + df_impegnati['categoria'] + " | Totale residuo: " + df_impegnati['importo'].astype(str) + " €"
        scelta = st.selectbox("Seleziona quale spesa vuoi pagare (interamente o a tranche):", df_impegnati['visualizza'].tolist())
        
        # Troviamo l'indice originale nel database della riga scelta
        idx_originale = df_impegnati[df_impegnati['visualizza'] == scelta].index[0]
        riga_selezionata = df.loc[idx_originale]
        
        st.divider()
        st.subheader(f"Pagamento Tranche per: {riga_selezionata['categoria']}")
        st.info(f"Dettagli spesa originaria: {riga_selezionata['descrizione']} di complessivi {format_euro(riga_selezionata['importo'])}")
        
        with st.form("form_tranche"):
            data_pagamento = st.date_input("Data di questo pagamento", format="DD/MM/YYYY")
            importo_tranche = st.number_input("Importo della tranche da pagare (€)", min_value=0.01, max_value=float(riga_selezionata['importo']), step=10.0, format="%.2f")
            nota_tranche = st.text_input("Nota sul pagamento (es. Pagato con bonifico, Assegno num...)")
            
            paga_button = st.form_submit_button("💳 Registra Pagamento Tranche")
            
        if paga_button:
            importo_residuo = float(riga_selezionata['importo']) - float(importo_tranche)
            
            # 1. Creiamo la riga della Tranche Effettiva come Uscita SALDATA
            nuova_tranche = pd.DataFrame([[
                data_pagamento.strftime('%Y-%m-%d'),
                "Uscita",
                riga_selezionata['categoria'],
                f"TRANCHE di: {riga_selezionata['descrizione']} | Note: {nota_tranche}",
                float(importo_tranche),
                riga_selezionata['coltura_id'],
                "Saldato" 
            ]], columns=df.columns)
            
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
            
            df_aggiornato = pd.concat([df, nuova_tranche], ignore_index=True)
            
            if 'visualizza' in df_aggiornato.columns: df_aggiornato = df_aggiornato.drop(columns=['visualizza'])
            if 'data_it' in df_aggiornato.columns: df_aggiornato = df_aggiornato.drop(columns=['data_it'])
            
            with st.spinner("Salvataggio operazione in corso..."):
                if update_github_file(df_aggiornato, sha, msg_commit):
                    st.success(f"Tranche di {format_euro(importo_tranche)} registrata con successo! Residuo aggiornato.")
                    # Usiamo st.rerun() in modo sicuro pulendo lo stato precedente
                    st.rerun()
                else:
                    st.error("Errore di sincronizzazione con GitHub.")
else:
    st.info("Database vuoto o non raggiungibile.")
