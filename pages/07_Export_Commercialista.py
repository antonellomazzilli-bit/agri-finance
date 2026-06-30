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
DRIVE_FILE_ID = st.secrets["DRIVE_FILE_ID"]

MESI_NOMI = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile", 5: "Maggio", 6: "Giugno",
    7: "Luglio", 8: "Agosto", 9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
}

def load_github_data():
    """Scarica i nuovi dati inseriti da smartphone."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def load_drive_sheet_data(nome_mese):
    """Scarica il foglio specifico del mese saltando i titoli in alto."""
    try:
        drive_url = f"https://docs.google.com/spreadsheets/d/{DRIVE_FILE_ID}/export?format=xlsx"
        r = requests.get(drive_url)
        if r.status_code == 200:
            # Sfruttiamo 'skiprows=2' perché i dati reali partono dalla riga 3 del foglio excel
            df_sheet = pd.read_excel(io.BytesIO(r.content), sheet_name=nome_mese, skiprows=2)
            return df_sheet
    except:
        pass
    return pd.DataFrame()

def parse_descrizione_operaio(descrizione):
    """Scompone la nota dell'app per l'esportazione pulita."""
    try:
        if "|" in str(descrizione):
            parti = descrizione.split("|")
            nome = parti[0].strip()
            info_tempo = parti[1].strip()
            giornate = float(info_tempo.split(" gg")[0].strip())
            
            ore = 0.0
            if "(" in info_tempo:
                ore = float(info_tempo.split("(")[1].split(" ore")[0].strip())
                
            tipo_paga = parti[2].strip() if len(parti) > 2 else "Paga Intera"
            note_attivita = parti[3].strip() if len(parti) > 3 else "-"
            return nome, giornate, ore, tipo_paga, note_attivita
    except:
        pass
    return "Non specificato", 0.0, 0.0, "Generale", str(descrizione)

def formatta_data_excel(val_data, anno):
    """Uniforma le date brevi dell'excel (es: 05/01) nel formato completo per le buste paga."""
    if pd.isna(val_data):
        return ""
    val_str = str(val_data).strip()
    if "/" in val_str:
        parti = val_str.split("/")
        giorno = parti[0].zfill(2)
        mese = parti[1].zfill(2)
        return f"{giorno}/{mese}/{anno}"
    try:
        dt = pd.to_datetime(val_data, errors='coerce')
        if not pd.isna(dt):
            return dt.strftime(f"%d/%m/{anno}")
    except:
        pass
    return val_str

st.title("📄 Esportazione Registro Presenze per Buste Paga")
st.markdown("Genera il file Excel mensile unificato (Storico Excel + Inserimenti da Smartphone) da inviare al commercialista.")

# --- INTERFACCIA DI SELEZIONE ---
col1, col2 = st.columns(2)
with col1:
    anno_sel = st.selectbox("Seleziona l'Anno di riferimento:", [2026, 2025])
with col2:
    mese_sel = st.selectbox("Seleziona il Mese da esportare:", list(MESI_NOMI.keys()), format_func=lambda x: MESI_NOMI[x], index=datetime.now().month - 1)

nome_mese_stringa = MESI_NOMI[mese_sel]

with st.spinner(f"Estrazione e unificazione dei dati di {nome_mese_stringa} in corso..."):
    df_git = load_github_data()
    df_sheet = load_drive_sheet_data(nome_mese_stringa)
    
    righe_commercialista = []
    
    # --- PARTE 1: ELABORAZIONE FOGLIO EXCEL (STORICO DRIVE) ---
    if not df_sheet.empty:
        df_sheet.columns = df_sheet.columns.astype(str).str.strip()
        
        # Identificazione dinamica delle colonne per posizione o nome simile
        col_data = [c for c in df_sheet.columns if 'data' in c.lower()][0] if any('data' in c.lower() for c in df_sheet.columns) else None
        col_spalm = [c for c in df_sheet.columns if 'spalm' in c.lower() or 'giorn' in c.lower() or 'gg' in c.lower()][0] if any('spalm' in c.lower() or 'giorn' in c.lower() or 'gg' in c.lower() for c in df_sheet.columns) else None
        col_ore = [c for c in df_sheet.columns if 'ore' in c.lower()][0] if any('ore' in c.lower() for c in df_sheet.columns) else None
        col_costo = [c for c in df_sheet.columns if 'costo' in c.lower() or 'lavoro' in c.lower() or 'giorno' in c.lower()][0] if any('costo' in c.lower() or 'lavoro' in c.lower() or 'giorno' in c.lower() for c in df_sheet.columns) else None
        col_note = [c for c in df_sheet.columns if 'note' in c.lower() or 'commess' in c.lower()][0] if any('note' in c.lower() or 'commess' in c.lower() for c in df_sheet.columns) else None
        
        if col_data and col_spalm:
            for _, row in df_sheet.iterrows():
                val_data = row.get(col_data)
                if pd.isna(val_data) or "totale" in str(val_data).lower():
                    continue
                
                gg_val = pd.to_numeric(row.get(col_spalm), errors='coerce')
                ore_val = pd.to_numeric(row.get(col_ore), errors='coerce') if col_ore else 0.0
                costo_val = pd.to_numeric(row.get(col_costo), errors='coerce') if col_costo else 0.0
                
                gg_clean = gg_val if pd.notna(gg_val) else 0.0
                ore_clean = ore_val if pd.notna(ore_val) else 0.0
                costo_clean = costo_val if pd.notna(costo_val) else 0.0
                
                # Consideriamo solo i giorni in cui c'è stata effettiva presenza o un costo di manodopera
                if gg_clean > 0 or ore_clean > 0 or costo_clean > 0:
                    data_completa = formatta_data_excel(val_data, anno_sel)
                    nota_testo = str(row.get(col_note)) if col_note and pd.notna(row.get(col_note)) else "Registro Presenze"
                    
                    righe_commercialista.append({
                        "Data Lavoro": data_completa,
                        "Nome e Cognome Dipendente": "Operaio (Da Registro Excel)",
                        "Giornate Lavorate": gg_clean,
                        "Ore Effettive": ore_clean,
                        "Tipologia Compenso": "Paga Ordinaria",
                        "Importo Corrisposto (€)": costo_clean,
                        "Stato Pagamento": "Saldato (Archivio)",
                        "Note / Attività Svolta": nota_testo
                    })

    # --- PARTE 2: ELABORAZIONE NUOVI MOVIMENTI (APP GITHUB) ---
    if not df_git.empty:
        df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
        df_git = df_git.dropna(subset=['data_dt'])
        
        # Filtriamo per anno, mese e categoria specifica
        df_filtrato_app = df_git[
            (df_git['data_dt'].dt.year == anno_sel) & 
            (df_git['data_dt'].dt.month == mese_sel) & 
            (df_git['categoria'] == 'Manodopera')
        ]
        
        for _, row in df_filtrato_app.iterrows():
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

    # --- VISIONE FINALE E GENERAZIONE FILE ---
    if righe_commercialista:
        df_export = pd.DataFrame(righe_commercialista)
        
        # Ordiniamo per data di lavoro per dare una struttura pulita cronologica
        df_export = df_export.sort_values(by="Data Lavoro")
        
        st.divider()
        st.subheader(f"👀 Anteprima Cedolino Presenze: {nome_mese_stringa} {anno_sel}")
        st.dataframe(df_export, use_container_width=True)
        
        # Generazione file Excel in memoria
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name="Presenze_Commercialista")
        buffer.seek(0)
        
        st.divider()
        st.download_button(
            label="📥 Scarica il file Excel per il Commercialista",
            data=buffer,
            file_name=f"Presenze_Dipendenti_{nome_mese_stringa}_{anno_sel}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success(f"File generato con successo! Contiene tutte le attività di {nome_mese_stringa}.")
    else:
        st.warning(f"Nessun dato di manodopera trovato per il mese di {nome_mese_stringa} {anno_sel} né su Drive né sull'App.")
