import streamlit as st
import pandas as pd
import requests
import base64
import io
import re

st.set_page_config(page_title="Analisi Giornate Operai", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"
DRIVE_FILE_ID = st.secrets["DRIVE_FILE_ID"]

def load_github_data():
    """Scarica il database centrale da GitHub."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def load_drive_historical_giornate():
    """Estrae il totale delle giornate pagate dallo storico di Google Drive."""
    try:
        drive_url = f"https://docs.google.com/spreadsheets/d/{DRIVE_FILE_ID}/export?format=xlsx"
        r = requests.get(drive_url)
        if r.status_code == 200:
            df_excel = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
            df_excel.columns = df_excel.columns.str.strip()
            
            # Identifica la colonna delle giornate (es. 'Giornate Spalate' o simili)
            colonna_giornate = [col for col in df_excel.columns if 'Giornate' in col]
            if colonna_giornate:
                return pd.to_numeric(df_excel[colonna_giornate[0]], errors='coerce').sum()
    except:
        pass
    return 0.0

def estrai_info_operaio(descrizione):
    """Scompone la descrizione dell'app per estrarre Nome e Numero Giornate."""
    try:
        # Il formato dell'app è: "Nome | X gg (Y ore) | ..."
        if "|" in str(descrizione):
            parti = descrizione.split("|")
            nome = parti[0].strip()
            
            # Estraiamo il numero di giornate dalla seconda parte (es. "1.5 gg")
            gg_testo = parti[1].strip()
            giornate = float(gg_testo.split(" ")[0])
            return nome, giornate
    except:
        pass
    return "Non specificato", 0.0

# --- LOGICA DI ELABORAZIONE ---
st.title("👥 Monitoraggio e Conteggio Giornate Operai")
st.markdown("Visualizza il riepilogo complessivo delle giornate di lavoro liquidate (Olive).")

df_git = load_github_data()
giornate_storiche_drive = load_drive_historical_giornate()

# Filtriamo solo le uscite legate alla Manodopera effettivamente Saldate
if not df_git.empty:
    df_manodopera = df_git[(df_git['categoria'] == 'Manodopera') & (df_git['stato'] == 'Saldato')].copy()
    
    # Applichiamo la funzione di estrazione dati su ogni riga dell'app
    nomi_operai = []
    giornate_app_lista = []
    
    for idx, row in df_manodopera.iterrows():
        nome, gg = estrai_info_operaio(row['descrizione'])
        nomi_operai.append(nome)
        giornate_app_lista.append(gg)
        
    df_manodopera['Operaio'] = nomi_operai
    df_manodopera['Giornate_Intere'] = giornate_app_lista
    
    # Calcolo totali complessivi
    totale_giornate_app = df_manodopera['Giornate_Intere'].sum()
    grand_totale_giornate = giornate_storiche_drive + totale_giornate_app
    costo_totale_manodopera = df_manodopera['importo'].sum()

    # --- METRICHE VISIVE IN ALTO ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Giornate Storiche (Drive)", f"{giornate_storiche_drive:,.1f} gg".replace(".", ","))
    c2.metric("Nuove Giornate (Da App)", f"{totale_giornate_app:,.1f} gg".replace(".", ","))
    c3.metric("TOTALE GIORNATE PAGATE", f"{grand_totale_giornate:,.1f} gg".replace(".", ","))

    st.divider()

    # --- DETTAGLIO PER SINGOLO OPERAIO (DATI REGISTRATI DA APP) ---
    st.subheader("📊 Analisi per Singolo Operaio (Nuove Registrazioni)")
    st.write("Questo dettaglio mostra la ripartizione dei giorni e dei compensi estratti dai dati inseriti da smartphone:")
    
    if not df_manodopera.empty:
        # Raggruppiamo i dati per capire quanto ha lavorato e quanto è costato ogni singolo operaio
        report_operai = df_manodopera.groupby('Operaio').agg({
            'Giornate_Intere': 'sum',
            'importo': 'sum'
        }).reset_index()
        
        report_operai.columns = ['Nome Operaio', 'Totale Giornate Lavorate', 'Totale Pagato (€)']
        
        # Formattazione per la tabella finale
        report_operai['Totale Giornate Lavorate'] = report_operai['Totale Giornate Lavorate'].map(lambda x: f"{x:,.1f} gg".replace(".", ","))
        report_operai['Totale Pagato (€)'] = report_operai['Totale Pagato (€)'].map(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        st.table(report_operai)
        
        # Elenco cronologico completo di riscontro
        with st.expander("Visualizza lo storico di tutti i pagamenti manodopera"):
            df_cronologico = df_manodopera[['data', 'Operaio', 'Giornate_Intere', 'importo']].copy()
            df_cronologico.columns = ['Data', 'Operaio', 'Giornate', 'Importo Liquidato']
            df_cronologico['Importo Liquidato'] = df_cronologico['Importo Liquidato'].map(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(df_cronologico.sort_values(by='Data', ascending=False), use_container_width=True)
            
    else:
        st.info("Nessuna nuova giornata registrata tramite l'applicazione corrente. I dati storici sono inclusi nel conteggio generale in alto.")
else:
    st.info("Database centrale non raggiungibile o vuoto.")
