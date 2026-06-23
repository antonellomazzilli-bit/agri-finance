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
            return pd.read_excel(io.BytesIO(r.content), sheet_name=0)
    except:
        pass
    return pd.DataFrame()

def estrai_info_operaio(descrizione):
    try:
        if "|" in str(descrizione):
            parti = descrizione.split("|")
            nome = parti[0].strip()
            giornate = float(parti[1].strip().split(" ")[0])
            return nome, giornate
    except:
        pass
    return "Non specificato", 0.0

st.title("👥 Monitoraggio Giornate per Periodo")
st.markdown("Seleziona un intervallo di date per filtrare lo storico delle giornate liquidate.")

df_git_raw = load_github_data()
df_drive_raw = load_drive_data_raw()

# --- INTERFACCIA LATERALE: CALENDARIO E MAPPATURA EXCEL ---
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

# --- SISTEMA DI CORREZIONE MANUALE COLONNE (FAILSAFE) ---
col_mesi_auto = None
col_giornate_auto = None

if not df_drive_raw.empty:
    # 1. Tentativo di Auto-Rilevamento Silenzioso
    for col in df_drive_raw.columns:
        if df_drive_raw[col].astype(str).str.lower().str.strip().isin(MESI_MAP.keys()).any():
            col_mesi_auto = col
            break
            
    for col in df_drive_raw.columns:
        name = str(col).lower()
        valori_iniziali = df_drive_raw[col].head(10).astype(str).str.lower()
        # Escludiamo le colonne che palesemente parlano di soldi
        if 'acconto' in name or 'saldo' in name or valori_iniziali.str.contains('acconto|saldo|€').any():
            continue
        if 'giornat' in name or 'spalate' in name or name == 'gg' or valori_iniziali.str.contains('giornat|spalate').any():
            col_giornate_auto = col
            break
            
    # 2. Interfaccia di Controllo Utente
    st.sidebar.divider()
    st.sidebar.subheader("⚙️ Mappatura File Excel")
    st.sidebar.write("Se i dati di Drive non tornano, forza le colonne corrette qui sotto:")
    
    # Creiamo un dizionario visivo per mostrare all'utente l'anteprima delle colonne
    opzioni_colonne = {}
    for col in df_drive_raw.columns:
        valori_validi = df_drive_raw[col].dropna().astype(str).tolist()
        anteprima = ", ".join(valori_validi[:3]) if valori_validi else "Vuota"
        if len(anteprima) > 25: anteprima = anteprima[:25] + "..."
        nome_pulito = str(col).replace("Unnamed: ", "Col. ")
        opzioni_colonne[col] = f"{nome_pulito} [es: {anteprima}]"

    idx_m = list(opzioni_colonne.keys()).index(col_mesi_auto) if col_mesi_auto in opzioni_colonne else 0
    idx_g = list(opzioni_colonne.keys()).index(col_giornate_auto) if col_giornate_auto in opzioni_colonne else (1 if len(opzioni_colonne) > 1 else 0)

    # I menu a tendina sovrascrivono l'auto-rilevamento
    colonna_mesi_scelta = st.sidebar.selectbox("Dov'è la colonna dei Mesi?", options=list(opzioni_colonne.keys()), format_func=lambda x: opzioni_colonne[x], index=idx_m)
    colonna_giornate_scelta = st.sidebar.selectbox("Dov'è la colonna delle Giornate?", options=list(opzioni_colonne.keys()), format_func=lambda x: opzioni_colonne[x], index=idx_g)

st.info(f"📊 Analisi attiva dal **{start_date.strftime('%d/%m/%Y')}** al **{end_date.strftime('%d/%m/%Y')}**")

# --- ESTRAZIONE DATI DRIVE (Usando le colonne scelte) ---
giornate_storiche_filtrate = 0.0
dettaglio_righe_drive = []

if not df_drive_raw.empty and colonna_mesi_scelta and colonna_giornate_scelta:
    for _, row in df_drive_raw.iterrows():
        mese_originale = str(row[colonna_mesi_scelta]).strip()
        mese_testo = mese_originale.lower()
        valore_giornate = pd.to_numeric(row[colonna_giornate_scelta], errors='coerce')
        
        if mese_testo in MESI_MAP and pd.notna(valore_giornate):
            num_mese = MESI_MAP[mese_testo]
            
            start_ym = start_date.year * 12 + start_date.month
            end_ym = end_date.year * 12 + end_date.month
            drive_ym = anno_corrente * 12 + num_mese
            
            incluso = start_ym <= drive_ym <= end_ym
            status_visto = "Incluso nel calcolo" if incluso else "Escluso dal periodo"
            
            if incluso:
                giornate_storiche_filtrate += valore_giornate
            
            dettaglio_righe_drive.append({
                "Mese Excel": mese_originale,
                "Giornate Rilevate": f"{valore_giornate:,.1f} gg".replace(".", ","),
                "Stato": status_visto
            })

# --- ESTRAZIONE DATI APP ---
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
c1.metric("Giornate Storiche Drive", f"{giornate_storiche_filtrate:,.1f} gg".replace(".", ","))
c2.metric("Nuove Giornate App", f"{totale_giornate_app_filtrate:,.1f} gg".replace(".", ","))
c3.metric("TOTALE GIORNATE PERIODO", f"{grand_totale_giornate:,.1f} gg".replace(".", ","))

st.divider()

# --- TABELLE VISUALI ---
st.subheader("📊 Dettaglio Personale (Dati inseriti da App)")
if not df_operai_filtrato.empty:
    report_operai = df_operai_filtrato.groupby('Operaio').agg({'Giornate_Intere': 'sum', 'importo': 'sum'}).reset_index()
    report_operai.columns = ['Nome Operaio', 'Giornate Lavorate', 'Costo Liquidato']
    report_operai['Giornate Lavorate'] = report_operai['Giornate Lavorate'].map(lambda x: f"{x:,.1f} gg".replace(".", ","))
    report_operai['Costo Liquidato'] = report_operai['Costo Liquidato'].map(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.table(report_operai)
else:
    st.write("Nessuna registrazione in questo intervallo di date sull'applicazione.")

st.divider()
st.subheader("📋 Foglio di Controllo: Storico Mensile da Drive")

if dettaglio_righe_drive:
    df_dettaglio_excel = pd.DataFrame(dettaglio_righe_drive)
    def colora_stato(val):
        color = '#E8F5E9' if 'Incluso' in val else '#FFEBEE'
        text_color = '#2E7D32' if 'Incluso' in val else '#C62828'
        return f'background-color: {color}; color: {text_color}; font-weight: bold;'
    st.table(df_dettaglio_excel.style.map(colora_stato, subset=['Stato']))
else:
    st.warning("Nessun dato corrispondente trovato su Drive con queste colonne.")
