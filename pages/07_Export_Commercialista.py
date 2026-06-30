import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime

st.set_page_config(page_title="Export Commercialista", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def load_github_data():
    """Scarica il database centrale cloud."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def parse_descrizione_operaio(descrizione):
    """Scompone la stringa salvata nel database per l'esportazione pulita."""
    try:
        if "|" in str(descrizione):
            parti = descrizione.split("|")
            nome = parti[0].strip()
            
            # Estrazione Giornate e Ore
            info_tempo = parti[1].strip() # Es: "1.0 gg (8.0 ore)"
            giornate = float(info_tempo.split(" gg")[0].strip())
            
            ore = 0.0
            if "(" in info_tempo:
                ore_testo = info_tempo.split("(")[1].split(" ore")[0].strip()
                ore = float(ore_testo)
                
            # Tipo di pagamento (Acconto / Saldo / Paga Intera)
            tipo_paga = parti[2].strip() if len(parti) > 2 else "Paga Intera"
            
            # Eventuali note aggiuntive sull'attività svolta
            note_attivita = parti[3].strip() if len(parti) > 3 else "-"
            
            return nome, giornate, ore, tipo_paga, note_attivita
    except:
        pass
    return "Non specificato", 0.0, 0.0, "Generale", str(descrizione)

st.title("📄 Esportazione Registro Presenze per Buste Paga")
st.markdown("Filtra le giornate per mese e genera il file Excel strutturato da trasmettere al commercialista.")

df_git = load_github_data()

if not df_git.empty:
    # Conversione e pulizia date
    df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
    df_git = df_git.dropna(subset=['data_dt'])
    
    # Estraiamo gli anni e i mesi disponibili nel database per i filtri
    df_git['Anno'] = df_git['data_dt'].dt.year
    df_git['Mese_Num'] = df_git['data_dt'].dt.month
    
    anni_disponibili = sorted(df_git['Anno'].unique(), reverse=True)
    
    col1, col2 = st.columns(2)
    with col1:
        anno_sel = st.selectbox("Seleziona l'Anno di riferimento", anni_disponibili)
    with col2:
        mesi_nomi = {
            1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile", 5: "Maggio", 6: "Giugno",
            7: "Luglio", 8: "Agosto", 9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
        }
        df_anno = df_git[df_git['Anno'] == anno_sel]
        mesi_disponibili = sorted(df_anno['Mese_Num'].unique())
        mese_sel = st.selectbox("Seleziona il Mese da esportare", mesi_disponibili, format_func=lambda x: mesi_nomi[x])

    # Filtriamo solo le righe di manodopera del periodo selezionato
    df_filtrato = df_anno[(df_anno['Mese_Num'] == mese_sel) & (df_anno['categoria'] == 'Manodopera')]

    if df_filtrato.empty:
        st.info(f"💡 Nessun dato di manodopera registrato per il mese di {mesi_nomi[mese_sel]} {anno_sel}.")
    else:
        # Costruzione della tabella finale per il consulente del lavoro
        righe_commercialista = []
        
        for idx, row in df_filtrato.iterrows():
            nome, gg, ore, tipo_paga, note = parse_descrizione_operaio(row['descrizione'])
            
            righe_commercialista.append({
                "Data Lavoro": row['data_dt'].strftime('%d/%m/%Y'),
                "Nome e Cognome Dipendente": nome,
                "Giornate Lavorate": gg,
                "Ore Effettive": ore,
                "Tipologia Compenso": tipo_paga,
                "Importo Corrisposto (€)": row['importo'],
                "Stato Pagamento": row['stato'],
                "Note / Attività Svolta": f"{note} (Coltura: {row['coltura_id']})"
            })
            
        df_export = pd.DataFrame(righe_commercialista).sort_values(by="Data Lavoro")
        
        st.divider()
        st.subheader(f"👀 Anteprima dei dati di {mesi_nomi[mese_sel]} {anno_sel}")
        st.dataframe(df_export, use_container_width=True)
        
        # --- CREAZIONE BUFFER EXCEL ---
        buffer = io.BytesIO()
        # Generiamo il foglio excel sfruttando openpyxl (già presente nei requisiti dell'app)
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name="Riepilogo_Presenze")
            
        buffer.seek(0)
        
        nome_file_excel = f"Presenze_Dipendenti_{mesi_nomi[mese_sel]}_{anno_sel}.xlsx"
        
        # Pulsante di download nativo
        st.download_button(
            label="📥 Scarica il file Excel per il Commercialista",
            data=buffer,
            file_name=nome_file_excel,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("File generato con successo! Puoi scaricarlo sul computer o sul telefono ed inviarlo direttamente.")
else:
    st.info("Database centrale vuoto o non raggiungibile.")
