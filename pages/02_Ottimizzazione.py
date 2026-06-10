import streamlit as st
import pandas as pd
import requests
import base64
import io

st.set_page_config(page_title="Analisi Margini e KPI", layout="wide")

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

def load_drive_historical_costs():
    """Scarica ed estrae i costi storici aggregati dal file Excel di Google Drive."""
    try:
        # Generazione URL export diretto per file Excel senza autenticazione obbligatoria
        drive_url = f"https://docs.google.com/spreadsheets/d/{DRIVE_FILE_ID}/export?format=xlsx"
        r = requests.get(drive_url)
        if r.status_code == 200:
            # Legge il primo foglio dell'excel (Riepilogo)
            df_excel = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
            
            # Pulisce i nomi delle colonne per sicurezza eliminando spazi extra
            df_excel.columns = df_excel.columns.str.strip()
            
            # Somma le colonne del tuo file Excel: Costo Lavoro (€) e Spese Extra (€)
            costo_lavoro_drive = pd.to_numeric(df_excel["Costo Lavoro (€)"], errors='coerce').sum()
            spese_extra_drive = pd.to_numeric(df_excel["Spese Extra (€)"], errors='coerce').sum()
            
            return costo_lavoro_drive + spese_extra_drive
    except Exception as e:
        st.sidebar.error(f"Nota: Impossibile leggere lo storico da Drive. Controlla la condivisione del file. Dettaglio: {e}")
    return 0.0

def format_it(val):
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("📊 Calcolo Costi di Produzione (Fusi con Drive)")

df_git = load_github_data()
costo_storico_drive = load_drive_historical_costs()

if not df_git.empty:
    df_git['data'] = pd.to_datetime(df_git['data'])
    
    # Concentriamo tutta l'analisi esclusivamente sulla coltura "Olive"
    df_olive = df_git[df_git['coltura_id'] == 'Olive']
    
    # Calcolo spese inserite da App
    spese_app = df_olive[df_olive['tipo'] == 'Uscita']['importo'].sum()
    ricavi_app = df_olive[df_olive['tipo'] == 'Entrata']['importo'].sum()
    
    # SOMMA ARCHITETTURALE DEI DUE ELEMENTI (GitHub + Storico Excel Drive)
    spese_totali_oliveto = spese_app + costo_storico_drive
    
    # Quantità di olive totali raccolte (tab 4)
    kg_raccolti = df_olive[df_olive['tipo'] == 'Resa']['importo'].sum()
    
    # Calcolo del KPI Finale
    costo_di_produzione_kg = (spese_totali_oliveto / kg_raccolti) if kg_raccolti > 0 else 0.0

    # Layout Visivo
    st.subheader("Analisi Finanziaria Coltura: Olive")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Costi Storici (Excel Drive)", format_it(costo_storico_drive))
    c2.metric("Nuovi Costi (Da App)", format_it(spese_app))
    c3.metric("Costo Totale Oliveto", format_it(spese_totali_oliveto))
    
    st.divider()
    
    kpi1, kpi2 = st.columns(2)
    with kpi1:
        st.metric("📦 Totale Raccolto", f"{kg_raccolti:,.0f} Kg".replace(",", "."))
    with kpi2:
        st.metric("🎯 COSTO DI PRODUZIONE REALISTICO", f"{costo_di_produzione_kg:,.2f} €/Kg".replace(".", ","), 
                  help="Calcolato dividendo la somma di tutti i costi (Drive + App) per i Kg totali raccolti")

    if kg_raccolti == 0:
        st.warning("💡 Inserisci i Kg totali raccolti nel Tab 'Raccolta Rese' dell'applicazione per sbloccare il costo di produzione unitario.")
else:
    st.info("Nessun movimento trovato su GitHub.")
