import streamlit as st
import pandas as pd
import requests
import base64
import io
import calendar
from datetime import datetime, date

st.set_page_config(page_title="Export Commercialista", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"
DRIVE_FILE_ID = st.secrets["DRIVE_FILE_ID"]

MESI_MAP = {
    'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6,
    'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
}

MESI_NOMI = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile", 5: "Maggio", 6: "Giugno",
    7: "Luglio", 8: "Agosto", 9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
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
            return pd.read_excel(io.BytesIO(r.content), sheet_name=0, header=None)
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

def is_festivo_italiano(d):
    """Rileva se una data corrisponde a un fine settimana o a una festività nazionale italiana."""
    if d.weekday() in [5, 6]:  # Sabato o Domenica
        return True
    
    # Festività nazionali fisse italiane
    festivita_fisse = [
        (1, 1),   # Capodanno
        (1, 6),   # Epifania
        (4, 25),  # Liberazione
        (5, 1),   # Festa del Lavoro
        (6, 2),   # Festa della Repubblica
        (8, 15),  # Ferragosto
        (11, 1),  # Ognissanti
        (12, 8),  # Immacolata
        (12, 25), # Natale
        (12, 26)  # Santo Stefano
    ]
    if (d.month, d.day) in festivita_fisse:
        return True
        
    # Lunedì dell'Angelo (Pasquetta) temporanea per gli anni di riferimento
    if d.year == 2025 and d.month == 4 and d.day == 21:
        return True
    if d.year == 2026 and d.month == 4 and d.day == 6:
        return True
        
    return False

st.title("📄 Esportazione Registro Presenze per Buste Paga")
st.markdown("Genera un file Excel mensile unificato con la spalmatura automatica delle giornate storiche sui giorni feriali utili.")

# --- INTERFACCIA DI SELEZIONE ---
col1, col2 = st.columns(2)
with col1:
    anno_sel = st.selectbox("Seleziona l'Anno di riferimento:", [2026, 2025])
with col2:
    mese_sel = st.selectbox("Seleziona il Mese da esportare:", list(MESI_NOMI.keys()), format_func=lambda x: MESI_NOMI[x], index=datetime.now().month - 1)

nome_mese_stringa = MESI_NOMI[mese_sel]

with st.spinner(f"Estrazione, pianificazione e spalmatura giorni per {nome_mese_stringa}..."):
    df_git = load_github_data()
    df_drive_raw = load_drive_data_raw()
    
    giornate_totali_excel = 0.0
    costo_totale_excel = 0.0
    righe_commercialista = []
    
    # --- PARTE 1: ESTRAZIONE TOTALI DA RIEPILOGO DRIVE (LIST-BASED) ---
    if not df_drive_raw.empty:
        idx_colonna_mesi = None
        for col_idx in range(df_drive_raw.shape[1]):
            colonna_dati = df_drive_raw.iloc[:, col_idx]
            if colonna_dati.astype(str).str.lower().str.strip().isin(MESI_MAP.keys()).any():
                idx_colonna_mesi = col_idx
                break
                
        if idx_colonna_mesi is not None:
            def get_sicuro(lista_valori, indice_desiderato, default=0.0):
                if indice_desiderato < len(lista_valori):
                    valore = lista_valori[indice_desiderato]
                    return valore if pd.notna(valore) else default
                return default

            for _, row in df_drive_raw.iterrows():
                valori_riga = row.tolist()
                if idx_colonna_mesi < len(valori_riga):
                    mese_excel_testo = str(valori_riga[idx_colonna_mesi]).strip().lower()
                    
                    if m_num := MESI_MAP.get(mese_excel_testo):
                        if m_num == list(MESI_MAP.values())[mese_sel - 1]:
                            # Estraiamo giornate totali e costo totale del lavoro dal riepilogo
                            giornate_raw = get_sicuro(valori_riga, idx_colonna_mesi + 1, default=0.0)
                            costo_raw = get_sicuro(valori_riga, idx_colonna_mesi + 3, default=0.0)
                            
                            giornate_totali_excel = pd.to_numeric(giornate_raw, errors='coerce')
                            costo_totale_excel = pd.to_numeric(costo_raw, errors='coerce')
                            
                            giornate_totali_excel = giornate_totali_excel if pd.notna(giornate_totali_excel) else 0.0
                            costo_totale_excel = costo_totale_excel if pd.notna(costo_totale_excel) else 0.0
                            break

    # --- PARTE 2: ALGORITMO DI SPALMATURA SUI GIORNI FERIALI ---
    if giornate_totali_excel > 0:
        # Generiamo tutti i giorni utili del mese escludendo sabati, domeniche e feste
        _, num_giorni_mese = calendar.monthrange(anno_sel, mese_sel)
        giorni_utili_feriali = []
        for g in range(1, num_giorni_mese + 1):
            data_corrente = date(anno_sel, mese_sel, g)
            if not is_festivo_italiano(data_corrente):
                giorni_utili_feriali.append(data_corrente)
                
        # Calcoliamo la paga giornaliera teorica per ripartirla correttamente
        tariffa_giornaliera = costo_totale_excel / giornate_totali_excel if giornate_totali_excel > 0 else 0.0
        giornate_rimanenti = giornate_totali_excel
        
        # Distribuiamo il monte giornate sui feriali utili
        for d in giorni_utili_feriali:
            if giornate_rimanenti <= 0:
                break
            quota_giorno = min(1.0, giornate_rimanenti)
            giornate_rimanenti -= quota_giorno
            
            ore_effettive = quota_giorno * 8.0
            costo_ripartito = tariffa_giornaliera * quota_giorno
            
            righe_commercialista.append({
                "Data Lavoro": d.strftime('%d/%m/%Y'),
                "Nome e Cognome Dipendente": "Operaio (Da Registro Excel)",
                "Giornate Lavorate": quota_giorno,
                "Ore Effettive": ore_effettive,
                "Tipologia Compenso": "Paga Ordinaria",
                "Importo Corrisposto (€)": costo_ripartito,
                "Stato Pagamento": "Saldato (Archivio)",
                "Note / Attività Svolta": f"Spalmatura automatica feriale - Totale mensile Excel: {giornate_totali_excel} gg"
            })

    # --- PARTE 3: ACCODA LE GIORNATE INSERITE IN TEMPO REALE DA SMARTPHONE ---
    if not df_git.empty:
        df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
        df_git = df_git.dropna(subset=['data_dt'])
        
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
                "Note / Attività Svolta": f"{note} (Da App - Coltura: {row['coltura_id']})"
            })

    # --- GENERAZIONE INTERFACCIA E FILE EXCEL ---
    if righe_commercialista:
        df_export = pd.DataFrame(righe_commercialista)
        
        # Ordiniamo cronologicamente per data lavoro
        df_export['data_ordinamento'] = pd.to_datetime(df_export['Data Lavoro'], format='%d/%m/%Y')
        df_export = df_export.sort_values(by="data_ordinamento").drop(columns=['data_ordinamento'])
        
        st.divider()
        st.subheader(f"👀 Anteprima Prospetto Presenze: {nome_mese_stringa} {anno_sel}")
        st.write(f"Rilevate da Excel: **{giornate_totali_excel:,.1f}** giornate complessive spalmatede nei giorni lavorativi utili.")
        
        # Visualizzazione formattata pulita delle valute
        df_visualizzazione = df_export.copy()
        df_visualizzazione['Importo Corrisposto (€)'] = df_visualizzazione['Importo Corrisposto (€)'].apply(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(x, (int, float)) else x)
        df_visualizzazione['Giornate Lavorate'] = df_visualizzazione['Giornate Lavorate'].apply(lambda x: f"{x:,.1f}".replace(".", ",") if isinstance(x, (int, float)) else x)
        df_visualizzazione['Ore Effettive'] = df_visualizzazione['Ore Effettive'].apply(lambda x: f"{x:,.1f}".replace(".", ",") if isinstance(x, (int, float)) else x)
        
        st.dataframe(df_visualizzazione, use_container_width=True)
        
        # Generazione file binario Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name="Presenze_Commercialista")
        buffer.seek(0)
        
        st.divider()
        st.download_button(
            label="📥 Scarica il file Excel per il Commercialista",
            data=buffer,
            file_name=f"Presenze_Conformi_{nome_mese_stringa}_{anno_sel}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("File generato con successo. Le giornate storiche sono state ripartite escludendo festivi e fine settimana.")
    else:
        st.warning(f"Nessuna giornata di lavoro trovata per {nome_mese_stringa} {anno_sel} nel Riepilogo di Drive o sull'applicazione.")
