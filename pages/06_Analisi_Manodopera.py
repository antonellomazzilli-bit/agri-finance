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
            # Carichiamo il file Excel ignorando le intestazioni automatiche per gestirle noi a posizione
            df_excel = pd.read_excel(io.BytesIO(r.content), sheet_name=0, header=None)
            return df_excel
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

# --- INTERFACCIA LATERALE (FILTRO CALENDARIO) ---
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

# --- TRATTAMENTO DATI EXCEL POSIZIONALE ---
giornate_storiche_filtrate = 0.0
dettaglio_righe_drive = []

if not df_drive_raw.empty:
    # Cerchiamo l'indice della colonna che contiene materialmente i nomi dei mesi nelle celle
    idx_colonna_mesi = None
    for col_idx in range(df_drive_raw.shape[1]):
        if df_drive_raw[col_idx].astype(str).str.lower().str.strip().isin(MESI_MAP.keys()).any():
            idx_colonna_mesi = col_idx
            break
            
    # Se troviamo la colonna dei mesi, applichiamo la logica posizionale specchio del tuo Excel
    if idx_colonna_mesi is not None:
        for _, row in df_drive_raw.iterrows():
            mese_originale = str(row[idx_colonna_mesi]).strip()
            mese_testo = mese_originale.lower()
            
            if mese_testo in MESI_MAP:
                num_mese = MESI_MAP[mese_testo]
                
                # Estrazione posizionale basata sull'ordine esatto delle tue colonne:
                # Mese (0), Giornate (1), Ore (2), Costo (3), Spese Extra (4), Acconto (5), Saldo (6)
                valore_giornate = pd.to_numeric(row[idx_colonna_mesi + 1], errors='coerce')
                valore_giornate = valore_giornate if pd.notna(valore_giornate) else 0.0
                
                start_ym = start_date.year * 12 + start_date.month
                end_ym = end_date.year * 12 + end_date.month
                drive_ym = anno_corrente * 12 + num_mese
                
                incluso = start_ym <= drive_ym <= end_ym
                status_visto = "Incluso" if incluso else "Escluso"
                
                if incluso:
                    giornate_storiche_filtrate += valore_giornate
                
                # Recuperiamo in modo sicuro i dati dalle colonne successive per posizione numerica (+1, +2, +3...)
                dettaglio_righe_drive.append({
                    "Stato Filtro": status_visto,
                    "Mese": mese_originale,
                    "Giornate Spalate": valore_giornate,
                    "Ore Effettive": row[idx_colonna_mesi + 2] if (idx_colonna_mesi + 2) < len(row) else "-",
                    "Costo Lavoro (€)": row[idx_colonna_mesi + 3] if (idx_colonna_mesi + 3) < len(row) else "-",
                    "Spese Extra (€)": row[idx_colonna_mesi + 4] if (idx_colonna_mesi + 4) < len(row) else "-",
                    "Acconto (€)": row[idx_colonna_mesi + 5] if (idx_colonna_mesi + 5) < len(row) else "-",
                    "Saldo Finale (€)": row[idx_colonna_mesi + 6] if (idx_colonna_mesi + 6) < len(row) else "-"
                })

# --- ESTRAZIONE DATI SMARTPHONE (GITHUB) ---
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

# --- SEZIONE CRUSCOTTO METRICHE ---
grand_totale_giornate = giornate_storiche_filtrate + totale_giornate_app_filtrate

c1, c2, c3 = st.columns(3)
c1.metric("Giornate Storiche (Excel)", f"{giornate_storiche_filtrate:,.1f} gg".replace(".", ","))
c2.metric("Nuove Giornate (Da App)", f"{totale_giornate_app_filtrate:,.1f} gg".replace(".", ","))
c3.metric("TOTALE GIORNATE PERIODO", f"{grand_totale_giornate:,.1f} gg".replace(".", ","))

st.divider()

# --- TABELLA INTERFACCIA OPERAI APP ---
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

# --- FOGLIO DI CONTROLLO COMPLETO CON LE TUE INTESTAZIONI ---
st.subheader("📋 Foglio di Controllo Esteso: Storico da Drive")
st.write("Visualizzazione ordinata secondo lo schema ufficiale del tuo archivio Excel.")

if dettaglio_righe_drive:
    df_dettaglio_excel = pd.DataFrame(dettaglio_righe_drive)
    
    # Ordinamento fisso delle colonne specchio del tuo Excel
    ordine_colonne = ["Stato Filtro", "Mese", "Giornate Spalate", "Ore Effettive", "Costo Lavoro (€)", "Spese Extra (€)", "Acconto (€)", "Saldo Finale (€)"]
    df_dettaglio_excel = df_dettaglio_excel[ordine_colonne]
    
    # Formattazione per pulizia visiva delle celle monetarie e dei decimali
    for col in ["Costo Lavoro (€)", "Spese Extra (€)", "Acconto (€)", "Saldo Finale (€)"]:
        df_dettaglio_excel[col] = df_dettaglio_excel[col].apply(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(x, (int, float)) else x)
    
    df_dettaglio_excel["Giornate Spalate"] = df_dettaglio_excel["Giornate Spalate"].apply(lambda x: f"{x:,.1f}".replace(".", ",") if isinstance(x, (int, float)) else x)

    # Logica di colorazione riga
    def colora_intera_riga(row):
        color = '#E8F5E9' if 'Incluso' in row['Stato Filtro'] else '#FFEBEE'
        text_color = '#2E7D32' if 'Incluso' in row['Stato Filtro'] else '#C62828'
        return [f'background-color: {color}; color: {text_color}; font-weight: bold;'] * len(row)
    
    st.dataframe(df_dettaglio_excel.style.apply(colora_intera_riga, axis=1), use_container_width=True)
else:
    st.warning("Nessun dato trovato su Drive. Verifica che il foglio 'Riepilogo Annuale' contenga dati validi.")
