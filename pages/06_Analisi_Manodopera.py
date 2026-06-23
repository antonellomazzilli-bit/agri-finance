import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime

st.set_page_config(page_title="Analisi Giornate Operai", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"
DRIVE_FILE_ID = st.secrets["DRIVE_FILE_ID"]

MESI_MAP = {
    'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6,
    'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
}

def load_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def load_drive_data_raw():
    try:
        drive_url = f"https://docs.google.com/spreadsheets/d/{DRIVE_FILE_ID}/export?format=xlsx"
        r = requests.get(drive_url)
        if r.status_code == 200:
            df_excel = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
            return df_excel
    except:
        pass
    return pd.DataFrame()

def estrai_info_operaio(descrizione):
    try:
        if "|" in str(descrizione):
            parti = descrizione.split("|")
            nome = parti[0].strip()
            gg_testo = parti[1].strip()
            giornate = float(gg_testo.split(" ")[0])
            return nome, giornate
    except:
        pass
    return "Non specificato", 0.0

st.title("👥 Monitoraggio Giornate per Periodo")
st.markdown("Seleziona un intervallo di date per filtrare lo storico delle giornate liquidate.")

df_git_raw = load_github_data()
df_drive_raw = load_drive_data_raw()

# --- INTERFACCIA CALENDARIO ---
st.sidebar.subheader("📅 Filtro Periodo")
oggi = datetime.now().date()
anno_corrente = oggi.year

periodo = st.sidebar.date_input(
    "Seleziona l'intervallo di date:",
    value=(datetime(anno_corrente, 1, 1).date(), oggi),
    format="DD/MM/YYYY"
)

if isinstance(periodo, tuple) and len(periodo) == 2:
    start_date, end_date = periodo
else:
    start_date, end_date = datetime(anno_corrente, 1, 1).date(), oggi

st.info(f"📊 Analisi attiva dal **{start_date.strftime('%d/%m/%Y')}** al **{end_date.strftime('%d/%m/%Y')}**")

# --- DATA HUNTER & DETTAGLIO DRIVE ---
giornate_storiche_filtrate = 0.0
dettaglio_righe_drive = []  # Lista per salvare il dettaglio visivo del foglio Excel

if not df_drive_raw.empty:
    col_mesi = None
    col_giornate = None
    
    for col in df_drive_raw.columns:
        if df_drive_raw[col].astype(str).str.lower().str.strip().isin(MESI_MAP.keys()).any():
            col_mesi = col
            break
            
    for col in df_drive_raw.columns:
        name = str(col).lower()
        if 'giornat' in name or 'spalate' in name or 'gg' == name:
            col_giornate = col
            break
            
    if col_giornate is None and col_mesi is not None:
        idx_mesi = df_drive_raw.columns.get_loc(col_mesi)
        if idx_mesi + 1 < len(df_drive_raw.columns):
            col_giornate = df_drive_raw.columns[idx_mesi + 1]

    if col_mesi is not None and col_giornate is not None:
        for _, row in df_drive_raw.iterrows():
            mese_originale = str(row[col_mesi]).strip()
            mese_testo = mese_originale.lower()
            valore_giornate = pd.to_numeric(row[col_giornate], errors='coerce')
            
            if mese_testo in MESI_MAP and pd.notna(valore_giornate):
                num_mese = MESI_MAP[mese_testo]
                
                start_ym = start_date.year * 12 + start_date.month
                end_ym = end_date.year * 12 + end_date.month
                drive_ym = anno_corrente * 12 + num_mese
                
                # Verifichiamo se il mese è incluso nel periodo
                incluso = start_ym <= drive_ym <= end_ym
                status_visto = "Incluso nel calcolo" if incluso else "Escluso dal periodo"
                
                if incluso:
                    giornate_storiche_filtrate += valore_giornate
                
                # Salviamo la riga per mostrarla nel dettaglio richiesto
                dettaglio_righe_drive.append({
                    "Mese Foglio Excel": mese_originale,
                    "Giornate Rilevate": f"{valore_giornate:,.1f} gg".replace(".", ","),
                    "Stato Filtro": status_visto
                })

# --- ELABORAZIONE APP GITHUB ---
totale_giornate_app_filtrate = 0.0
df_operai_filtrato = pd.DataFrame()

if not df_git_raw.empty:
    df_git_raw['data_dt'] = pd.to_datetime(df_git_raw['data'], errors='coerce').dt.date
    df_git_filtrato = df_git_raw[(df_git_raw['data_dt'] >= start_date) & (df_git_raw['data_dt'] <= end_date)].copy()
    df_manodopera = df_git_filtrato[(df_git_filtrato['categoria'] == 'Manodopera') & (df_git_filtrato['stato'] == 'Saldato')].copy()
    
    if not df_manodopera.empty:
        nomi_operai = []
        giornate_app_lista = []
        
        for idx, row in df_manodopera.iterrows():
            nome, gg = estrai_info_operaio(row['descrizione'])
            nomi_operai.append(nome)
            giornate_app_lista.append(gg)
            
        df_manodopera['Operaio'] = nomi_operai
        df_manodopera['Giornate_Intere'] = giornate_app_lista
        
        totale_giornate_app_filtrate = df_manodopera['Giornate_Intere'].sum()
        df_operai_filtrato = df_manodopera

# --- METRICHE PRINCIPALI ---
grand_totale_giornate = giornate_storiche_filtrate + totale_giornate_app_filtrate

c1, c2, c3 = st.columns(3)
c1.metric("Giornate Drive nel periodo", f"{giornate_storiche_filtrate:,.1f} gg".replace(".", ","))
c2.metric("Giornate App nel periodo", f"{totale_giornate_app_filtrate:,.1f} gg".replace(".", ","))
c3.metric("TOTALE GIORNATE PERIODO", f"{grand_totale_giornate:,.1f} gg".replace(".", ","))

st.divider()

# --- TABELLA 1: DETTAGLIO NUOVI OPERAI DA APP ---
st.subheader("📊 Distribuzione del Personale (Dati inseriti da App)")
if not df_operai_filtrato.empty:
    report_operai = df_operai_filtrato.groupby('Operaio').agg({
        'Giornate_Intere': 'sum',
        'importo': 'sum'
    }).reset_index()
    
    report_operai.columns = ['Nome Operaio', 'Giornate Lavorate', 'Costo Liquidato']
    report_operai['Giornate Lavorate'] = report_operai['Giornate Lavorate'].map(lambda x: f"{x:,.1f} gg".replace(".", ","))
    report_operai['Costo Liquidato'] = report_operai['Costo Liquidato'].map(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.table(report_operai)
    
    with st.expander("Vedi registro analitico delle singole registrazioni da smartphone"):
        df_cronologico = df_operai_filtrato[['data', 'Operaio', 'Giornate_Intere', 'importo', 'descrizione']].copy()
        df_cronologico.columns = ['Data', 'Operaio', 'Giornate', 'Importo', 'Dettaglio Inserito']
        df_cronologico['Importo'] = df_cronologico['Importo'].map(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.dataframe(df_cronologico.sort_values(by='Data', ascending=False), use_container_width=True)
else:
    st.write("Nessuna nuova giornata registrata tramite l'applicazione nell'intervallo selezionato.")

st.divider()

# --- NUOVA SEZIONE: DETTAGLIO FILE EXCEL DRIVE ---
st.subheader("📋 Foglio di Controllo: Storico Mensile da Drive")
st.write("Di seguito trovi l'elenco esatto delle voci mensili estratte dal tuo file Excel su Google Drive in base al filtro temporale selezionato:")

if dettaglio_righe_drive:
    df_dettaglio_excel = pd.DataFrame(dettaglio_righe_drive)
    
    # Coloriamo lo sfondo per capire al volo cosa è incluso e cosa no
    def colora_stato(val):
        color = '#E8F5E9' if 'Incluso' in val else '#FFEBEE'
        text_color = '#2E7D32' if 'Incluso' in val else '#C62828'
        return f'background-color: {color}; color: {text_color}; font-weight: bold;'
        
    st.table(df_dettaglio_excel.style.applymap(colora_stato, subset=['Stato Filtro']))
else:
    st.warning("⚠️ Non è stato possibile estrarre righe valide dal file di Drive. Verifica che la struttura del foglio contenga i nomi dei mesi e i valori numerici delle giornate.")
