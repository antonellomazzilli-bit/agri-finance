import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime

st.set_page_config(page_title="Gestione e Modifica Database", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE GITHUB ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def get_github_data():
    """Scarica il file csv centrale da GitHub."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data_json = r.json()
        content = base64.b64decode(data_json["content"]).decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
        return df, data_json["sha"]
    return pd.DataFrame(), None

def update_github_file(df, sha, commit_message="Aggiornamento record via AgriApp"):
    """Sovrascrive il file su GitHub con il nuovo dataframe aggiornato."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False)
    
    payload = {
        "message": commit_message,
        "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": "main"
    }
    
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

st.title("✏️ Gestione e Modifica Movimenti")
st.markdown("Seleziona un movimento per correggerlo o eliminarlo definitivamente dal cloud.")

df, sha = get_github_data()

if not df.empty:
    # Creiamo un'etichetta di anteprima leggibile per la casella di selezione
    df['data_it'] = pd.to_datetime(df['data'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['etichetta_selezione'] = df['data_it'].astype(str) + " | " + df['categoria'].astype(str) + " | " + df['tipo'].astype(str) + " | " + df['importo'].apply(lambda x: f"{x:,.2f} €".replace(".", "X").replace(",", ".").replace("X", ","))
    
    # Menu a tendina per pescare il movimento da modificare
    lista_movimenti = df['etichetta_selezione'].tolist()
    movimento_scelto = st.selectbox("Scegli il movimento da gestire:", lista_movimenti)
    
    # Individuiamo l'esatta riga nel database
    idx_record = df[df['etichetta_selezione'] == movimiento_scelto].index[0]
    riga_corrente = df.loc[idx_record]
    
    st.divider()
    st.subheader("🛠️ Pannello di Correzione")
    
    # Conversione della data per il calendario di Streamlit
    try:
        data_default = pd.to_datetime(riga_corrente['data']).date()
    except:
        data_default = datetime.now().date()
        
    # FORM DI MODIFICA (i campi appaiono già compilati con i vecchi dati)
    with st.form("form_correzione_dati"):
        col1, col2 = st.columns(2)
        with col1:
            nuova_data = st.date_input("Data Operazione", value=data_default, format="DD/MM/YYYY")
            nuovo_tipo = st.selectbox("Tipo Flusso", ["Uscita", "Entrata", "Resa"], index=["Uscita", "Entrata", "Resa"].index(riga_corrente['tipo']) if riga_corrente['tipo'] in ["Uscita", "Entrata", "Resa"] else 0)
            nuovo_importo = st.number_input("Importo / Quantità KG", value=float(riga_corrente['importo']), min_value=0.0, step=0.01, format="%.2f")
        with col2:
            nuova_cat = st.text_input("Categoria", value=str(riga_corrente['categoria']), help="es. Manodopera, Carburante, Raccolta")
            nuova_colt = st.text_input("Coltura Associata", value=str(riga_corrente['coltura_id']))
            nuova_desc = st.text_area("Note / Descrizione", value=str(riga_corrente['descrizione']))
            
        salva_variazioni = st.form_submit_button("💾 Salva le Modifiche nel Cloud")
        
    if salva_variazioni:
        # Puliamo il DataFrame dalle colonne provvisorie di visualizzazione
        df_pulito = df.drop(columns=['etichetta_selezione', 'data_it'])
        
        # Assegniamo i nuovi dati alla riga selezionata
        df_pulito.at[idx_record, 'data'] = nuova_data.strftime('%Y-%m-%d')
        df_pulito.at[idx_record, 'tipo'] = nuovo_tipo
        df_pulito.at[idx_record, 'categoria'] = nuova_cat
        df_pulito.at[idx_record, 'importo'] = float(nuovo_importo)
        df_pulito.at[idx_record, 'coltura_id'] = nuova_colt
        df_pulito.at[idx_record, 'descrizione'] = nuova_desc
        
        with st.spinner("Sincronizzazione modifiche con GitHub in corso..."):
            if update_github_file(df_pulito, sha, commit_message=f"Modifica riga del {nuova_data.strftime('%d/%m/%Y')}"):
                st.success("✅ Modifiche salvate correttamente!")
                st.rerun()
            else:
                st.error("❌ Errore durante il salvataggio su GitHub.")
                
    # SEZIONE ELIMINAZIONE IN FONDO
    st.divider()
    with st.expander("⚠️ Zona di Rimozione Rimedi Rapidi"):
        st.write("Cliccando il pulsante sottostante il movimento verrà cancellato in modo definitivo.")
        if st.button("🗑️ Elimina definitivamente questo movimento", type="secondary"):
            df_tagliato = df.drop(idx_record).drop(columns=['etichetta_selezione', 'data_it'])
            with st.spinner("Rimozione record da GitHub..."):
                if update_github_file(df_tagliato, sha, commit_message=f"Eliminato movimento del {riga_corrente['data']}"):
                    st.warning("Movimento eliminato con successo!")
                    st.rerun()
                else:
                    st.error("❌ Errore durante l'eliminazione del record.")
else:
    st.info("Il database centrale è vuoto. Inserisci i dati nella schermata principale.")
