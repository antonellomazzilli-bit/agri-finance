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

# Mappatura per convertire i testi in indici mensili
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

# --- DATA HUNTER: ELABORAZIONE DRIVE ---
giornate_storiche_filtrate = 0.0

if not df_drive_raw.empty:
    col_mesi = None
    col_giornate = None
    
    # 1. Troviamo la colonna dei Mesi cercando la parola 'gennaio' dentro le celle
    for col in df_drive_raw.columns:
        if df_drive_raw[col].astype(str).str.lower().str.strip().isin(MESI_MAP.keys()).any():
            col_mesi = col
            break
            
    # 2. Troviamo la colonna delle Giornate (tramite intestazione)
    for col in df_drive_raw.columns:
        name = str(col).lower()
        if 'giornat' in name or 'spalate' in name or 'gg' == name:
            col_giornate = col
            break
            
    # Fallback: Se l'intestazione è vuota, prendiamo la colonna subito a destra dei mesi
    if col_giornate is None and col_mesi is not None:
        idx_mesi = df_drive_raw.columns.get_loc(col_mesi)
        if idx_mesi + 1 < len(df_drive_raw.columns):
            col_giornate = df_drive_raw.columns[idx_mesi + 1]

    # 3. Estrazione e Filtro
    if col_mesi is not None and col_giornate is not None:
        for _, row in df_drive_raw.iterrows():
            mese_testo = str(row[col_mesi]).strip().lower()
            valore_giornate = pd.to_numeric(row[col_giornate], errors='coerce')
            
            if mese_testo in MESI_MAP and pd.notna(valore_giornate):
                num_mese = MESI_MAP[mese_testo]
                
                # Calcolo infallibile per l'inclusione del mese nel periodo selezionato
                start_ym = start_date.year * 12 + start_date.month
                end_ym = end_date.year * 12 + end_date.month
                drive_ym = anno_corrente * 12 + num_mese
                
                if start_ym <= drive_ym <= end_ym:
                    giornate_storiche_filtrate += valore_giornate

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

# --- METRICHE E TABELLE VISIVE ---
grand_totale_giornate = giornate_storiche_filtrate + totale_giornate_app_filtrate

c1, c2, c3 = st.columns(3)
c1.metric("Giornate Drive nel periodo", f"{giornate_storiche_filtrate:,.1f} gg".replace(".", ","))
c2.metric("Giornate App nel periodo", f"{totale_giornate_app_filtrate:,.1f} gg".replace(".", ","))
c3.metric("TOTALE GIORNATE PERIODO", f"{grand_totale_giornate:,.1f} gg".replace(".", ","))

st.divider()

st.subheader("📊 Distribuzione del Personale nel periodo")

if not df_operai_filtrato.empty:
    report_operai = df_operai_filtrato.groupby('Operaio').agg({
        'Giornate_Intere': 'sum',
        'importo': 'sum'
    }).reset_index()
    
    report_operai.columns = ['Nome Operaio', 'Giornate Lavorate nel Periodo', 'Costo Liquidato nel Periodo']
    report_operai['Giornate Lavorate nel Periodo'] = report_operai['Giornate Lavorate nel Periodo'].map(lambda x: f"{x:,.1f} gg".replace(".", ","))
    report_operai['Costo Liquidato nel Periodo'] = report_operai['Costo Liquidato nel Periodo'].map(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    st.table(report_operai)
    
    with st.expander("Vedi elenco dettagliato dei giorni inclusi in questo intervallo"):
        df_cronologico = df_operai_filtrato[['data', 'Operaio', 'Giornate_Intere', 'importo', 'descrizione']].copy()
        df_cronologico.columns = ['Data', 'Operaio', 'Giornate', 'Importo', 'Dettaglio Inserito']
        df_cronologico['Importo'] = df_cronologico['Importo'].map(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.dataframe(df_cronologico.sort_values(by='Data', ascending=False), use_container_width=True)
else:
    st.write("Nessuna nuova registrazione manodopera presente in questo intervallo di date sull'applicazione.")
