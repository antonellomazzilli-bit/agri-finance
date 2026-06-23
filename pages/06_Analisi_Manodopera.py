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

# --- INTERFACCIA LATERALE ---
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

# --- MAPPATURA EXCEL ---
col_mesi_auto = None
col_giornate_auto = None

if not df_drive_raw.empty:
    for col in df_drive_raw.columns:
        if df_drive_raw[col].astype(str).str.lower().str.strip().isin(MESI_MAP.keys()).any():
            col_mesi_auto = col
            break
            
    for col in df_drive_raw.columns:
        name = str(col).lower()
        valori_iniziali = df_drive_raw[col].head(10).astype(str).str.lower()
        if 'acconto' in name or 'saldo' in name or valori_iniziali.str.contains('acconto|saldo|€').any():
            continue
        if 'giornat' in name or 'spalate' in name or name == 'gg' or valori_iniziali.str.contains('giornat|spalate').any():
            col_giornate_auto = col
            break
            
    st.sidebar.divider()
    st.sidebar.subheader("⚙️ Mappatura File Excel")
    
    opzioni_colonne = {}
    for col in df_drive_raw.columns:
        valori_validi = df_drive_raw[col].dropna().astype(str).tolist()
        anteprima = ", ".join(valori_validi[:3]) if valori_validi else "Vuota"
        if len(anteprima) > 25: anteprima = anteprima[:25] + "..."
        nome_pulito = str(col).replace("Unnamed: ", "Col. ")
        opzioni_colonne[col] = f"{nome_pulito} [es: {anteprima}]"

    idx_m = list(opzioni_colonne.keys()).index(col_mesi_auto) if col_mesi_auto in opzioni_colonne else 0
    idx_g = list(opzioni_colonne.keys()).index(col_giornate_auto) if col_giornate_auto in opzioni_colonne else (1 if len(opzioni_colonne) > 1 else 0)

    colonna_mesi_scelta = st.sidebar.selectbox("Colonna dei Mesi:", options=list(opzioni_colonne.keys()), format_func=lambda x: opzioni_colonne[x], index=idx_m)
    colonna_giornate_scelta = st.sidebar.selectbox("Colonna delle Giornate:", options=list(opzioni_colonne.keys()), format_func=lambda x: opzioni_colonne[x], index=idx_g)

st.info(f"📊 Analisi attiva dal **{start_date.strftime('%d/%m/%Y')}** al **{end_date.strftime('%d/%m/%Y')}**")

# --- ESTRAZIONE DATI DRIVE (Dinamica su tutte le colonne) ---
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
            status_visto = "Incluso" if incluso else "Escluso"
            
            if incluso:
                giornate_storiche_filtrate += valore_giornate
            
            # Estrazione completa della riga come dizionario
            riga_completa = row.to_dict()
            riga_completa['Stato Filtro'] = status_visto
            dettaglio_righe_drive.append(riga_completa)

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
st.subheader("📋 Foglio di Controllo Esteso: Storico da Drive")
st.write("Tutti i dati originali rilevati dal file Excel per i mesi tracciati. Usa la barra di scorrimento in basso per vedere tutte le colonne.")

if dettaglio_righe_drive:
    df_dettaglio_excel = pd.DataFrame(dettaglio_righe_drive)
    
    # Pulizia: Rimuove colonne del tutto vuote (create da spazi o formattazioni invisibili su Excel)
    df_dettaglio_excel = df_dettaglio_excel.dropna(axis=1, how='all')
    
    # Sposta la colonna 'Stato Filtro' all'inizio per comodità visiva
    cols = list(df_dettaglio_excel.columns)
    if 'Stato Filtro' in cols:
        cols.remove('Stato Filtro')
        cols.insert(0, 'Stato Filtro')
        df_dettaglio_excel = df_dettaglio_excel[cols]
    
    # Coloriamo l'intera riga in base allo stato
    def colora_intera_riga(row):
        color = '#E8F5E9' if 'Incluso' in row['Stato Filtro'] else '#FFEBEE'
        text_color = '#2E7D32' if 'Incluso' in row['Stato Filtro'] else '#C62828'
        return [f'background-color: {color}; color: {text_color}; font-weight: bold;'] * len(row)
    
    # st.dataframe permette lo scrolling orizzontale se le colonne sono molte
    st.dataframe(df_dettaglio_excel.style.apply(colora_intera_riga, axis=1), use_container_width=True)
else:
    st.warning("Nessun dato corrispondente trovato su Drive con queste colonne.")
