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

def load_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def load_drive_data_raw():
    """Scarica il file Excel grezzo da Drive."""
    try:
        drive_url = f"https://docs.google.com/spreadsheets/d/{DRIVE_FILE_ID}/export?format=xlsx"
        r = requests.get(drive_url)
        if r.status_code == 200:
            df_excel = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
            df_excel.columns = df_excel.columns.astype(str).str.strip()
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

# --- DIZIONARIO PER CONVERTIRE I MESI TESTUALI DI DRIVE IN NUMERI ---
MESI_MAP = {
    'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6,
    'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
}

st.title("👥 Monitoraggio Giornate per Periodo")
st.markdown("Seleziona un intervallo di date per filtrare lo storico delle giornate liquidate.")

# --- 1. CARICAMENTO DATI ---
df_git_raw = load_github_data()
df_drive_raw = load_drive_data_raw()

# --- 2. INTERFACCIA DI FILTRO TEMPORALE (INTERVALLO DI DATE) ---
st.sidebar.subheader("📅 Filtro Periodo")
oggi = datetime.now().date()
anno_corrente = oggi.year

# Impostiamo di default l'inizio dell'anno corrente fino a oggi
periodo = st.sidebar.date_input(
    "Seleziona l'intervallo di date:",
    value=(datetime(anno_corrente, 1, 1).date(), oggi),
    format="DD/MM/YYYY"
)

# Gestione di sicurezza se l'utente seleziona solo una data invece di un intervallo
if isinstance(periodo, tuple) and len(periodo) == 2:
    start_date, end_date = periodo
else:
    start_date, end_date = datetime(anno_corrente, 1, 1).date(), oggi

st.info(f"📊 Analisi attiva dal **{start_date.strftime('%d/%m/%Y')}** al **{end_date.strftime('%d/%m/%Y')}**")

# --- 3. ELABORAZIONE DATI STORICI (DRIVE) CON FILTRO TEMPORALE ---
giornate_storiche_filtrate = 0.0

if not df_drive_raw.empty:
    st.sidebar.success("✅ File Drive Connesso correttamente!")
    
    # Mostriamo un'anteprima di debug per capire come sono scritte le colonne su Excel
    with st.expander("🔍 Debug: Vedi cosa c'è dentro il file Excel di Drive"):
        st.write("Colonne trovate nel tuo Excel:", list(df_drive_raw.columns))
        st.dataframe(df_drive_raw.head(5))
    
    # Cerchiamo le colonne delle giornate e dei mesi nel tuo file Excel (più varianti possibili)
    col_giornate = [c for c in df_drive_raw.columns if 'giornat' in c.lower() or 'giorn' in c.lower() or c.lower() == 'gg']
    col_mesi = [c for c in df_drive_raw.columns if 'mese' in c.lower() or 'data' in c.lower() or 'periodo' in c.lower()]
    
    if col_giornate and col_mesi:
        c_giornate = col_giornate[0]
        c_mesi = col_mesi[0]
        
        for _, row in df_drive_raw.iterrows():
            valore_giornate = pd.to_numeric(row[c_giornate], errors='coerce')
            if pd.isna(valore_giornate):
                continue
                
            cella_mese = str(row[c_mesi]).strip().lower()
            
            # CASO 1: Nel file Excel c'è una data vera (es. 01/01/2026 o 2026-01-15)
            try:
                data_letta = pd.to_datetime(row[c_mesi], errors='coerce').date()
                if not pd.isna(data_letta):
                    if start_date <= data_letta <= end_date:
                        giornate_storiche_filtrate += valore_giornate
                    continue
            except:
                pass
            
            # CASO 2: Nel file Excel c'è il nome del mese scritto a testo (es. "gennaio")
            if cella_mese in MESI_MAP:
                num_mese = MESI_MAP[cella_mese]
                data_mese = datetime(anno_corrente, num_mese, 1).date()
                if start_date <= data_mese <= end_date:
                    giornate_storiche_filtrate += valore_giornate

# --- 4. ELABORAZIONE NUOVI DATI (GITHUB) CON FILTRO TEMPORALE ---
totale_giornate_app_filtrate = 0.0
df_operai_filtrato = pd.DataFrame()

if not df_git_raw.empty:
    df_git_raw['data_dt'] = pd.to_datetime(df_git_raw['data'], errors='coerce').dt.date
    # Applichiamo il filtro data sulle righe di GitHub
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

# --- 5. CALCOLO FINALE E METRICHE VISIVE ---
grand_totale_giornate = giornate_storiche_filtrate + totale_giornate_app_filtrate

c1, c2, c3 = st.columns(3)
c1.metric("Giornate Drive nel periodo", f"{giornate_storiche_filtrate:,.1f} gg".replace(".", ","))
c2.metric("Giornate App nel periodo", f"{totale_giornate_app_filtrate:,.1f} gg".replace(".", ","))
c3.metric("TOTALE GIORNATE PERIODO", f"{grand_totale_giornate:,.1f} gg".replace(".", ","))

st.divider()

# --- TABELLA DETTAGLIATA ---
st.subheader("📊 Distribuzione del Personale nel periodo selezionato")

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
    st.write("Nessuna nuova registrazione manodopera presente in questo intervallo di date.")
