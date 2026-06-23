import streamlit as st
import pandas as pd
import base64
import requests
import io
from datetime import datetime

st.set_page_config(page_title="AgriFinance Cloud", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"
BRANCH = "main"

def format_euro(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_github_file():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
        # Se manca la colonna stato (per i vecchi dati), la creiamo impostandola a 'Saldato'
        if 'stato' not in df.columns:
            df['stato'] = 'Saldato'
        return df, r.json()["sha"]
    columns = ["data", "tipo", "categoria", "descrizione", "importo", "coltura_id", "stato"]
    return pd.DataFrame(columns=columns), None

def save_to_github(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content = df.to_csv(index=False)
    data = {
        "message": "Update database con gestione stati via AgriApp",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": BRANCH
    }
    if sha: data["sha"] = sha
    r = requests.put(url, headers=headers, json=data)
    return r.status_code in [200, 201]

st.title("🚜 Registro Agricolo Cloud")

tab1, tab2, tab3, tab4 = st.tabs(["🛒 Movimenti Standard", "👥 Giornate Operai (Olive)", "💸 Spese Extra", "📦 Raccolta Rese"])

# --- TAB 1: STANDARD ---
with tab1:
    st.subheader("Registra Entrate o Uscite")
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data Operazione", format="DD/MM/YYYY", key="std_data")
            tipo = st.selectbox("Tipo", ["Uscita", "Entrata"], key="std_tipo")
            importo = st.number_input("Importo (€)", min_value=0.0, step=0.01, key="std_importo")
        with col2:
            cat = st.selectbox("Categoria", ["Sementi", "Carburante", "Concimi", "Vendita", "Fatture Fornitori", "Attrezzature"], key="std_cat")
            colt = st.text_input("Coltura", value="Olive", key="std_colt")
            stato = st.selectbox("Stato Pagamento", ["Saldato", "Impegnato (Non ancora saldato)"])
            desc = st.text_area("Note / Descrizione", key="std_desc")
            
        if st.form_submit_button("Registra Movimento"):
            df, sha = get_github_file()
            stato_salvato = "Impegnato" if "Impegnato" in stato else "Saldato"
            new_row = pd.DataFrame([[data.strftime('%Y-%m-%d'), tipo, cat, desc, importo, colt, stato_salvato]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

# --- TAB 2: OPERAI ---
with tab2:
    st.subheader("👥 Registro Manodopera Specializzato Olive")
    with st.form("operaio_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            op_data = st.date_input("Data Registrazione", format="DD/MM/YYYY", key="op_data")
            op_nome = st.text_input("Nome Operaio", placeholder="es. Mario Rossi")
            op_giornate = st.number_input("Giornate lavorate", min_value=0.0, step=0.5, value=1.0)
            op_ore = st.number_input("Ore Effettive", min_value=0.0, step=1.0, value=8.0)
        with c2:
            op_tipo_paga = st.selectbox("Tipo di Pagamento", ["Acconto", "Saldo Finale", "Paga Intera"])
            op_importo = st.number_input("Importo Corrisposto (€)", min_value=0.0, step=10.0)
            op_stato = st.selectbox("Stato del Costo", ["Saldato", "Impegnato (Da liquidare in futuro)"])
            op_note = st.text_area("Note Attività", placeholder="es. Raccolta Olive")
        
        if st.form_submit_button("Registra Manodopera"):
            df, sha = get_github_file()
            stato_salvato = "Impegnato" if "Impegnato" in op_stato else "Saldato"
            desc_dettagliata = f"{op_nome} | {op_giornate} gg ({op_ore} ore) | {op_tipo_paga} | {op_note}"
            new_row = pd.DataFrame([[op_data.strftime('%Y-%m-%d'), "Uscita", "Manodopera", desc_dettagliata, float(op_importo), "Olive", stato_salvato]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

# --- TAB 3: SPESE EXTRA ---
with tab3:
    st.subheader("Registra Spese Extra o Imprevisti")
    with st.form("extra_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            ex_data = st.date_input("Data Spesa", format="DD/MM/YYYY", key="ex_data")
            ex_importo = st.number_input("Importo Spesa (€)", min_value=0.0, step=0.01, key="ex_importo")
            ex_stato = st.selectbox("Stato", ["Saldato", "Impegnato"], key="ex_stato")
        with col2:
            ex_titolo = st.text_input("Tipo di Spesa Extra", placeholder="es. Riparazione Trattore")
            ex_note = st.text_area("Dettagli aggiuntivi", key="ex_note")
        if st.form_submit_button("Registra Spesa Extra"):
            df, sha = get_github_file()
            new_row = pd.DataFrame([[ex_data.strftime('%Y-%m-%d'), "Uscita", "Altro", f"EXTRA: {ex_titolo} - {ex_note}", ex_importo, "Olive", ex_stato]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

# --- TAB 4: RACCOLTA ---
with tab4:
    st.subheader("📦 Registra i KG di Olive raccolti")
    with st.form("resa_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            p_data = st.date_input("Data Raccolta", format="DD/MM/YYYY", key="p_data")
            p_quantita = st.number_input("Quantità Olive (in KG)", min_value=1.0, step=1.0)
        with col2:
            p_note = st.text_area("Note sul raccolto")
        if st.form_submit_button("Registra Produzione"):
            df, sha = get_github_file()
            new_row = pd.DataFrame([[p_data.strftime('%Y-%m-%d'), "Resa", "Raccolta", f"Raccolto: {p_note}", float(p_quantita), "Olive", "Saldato"]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

# --- VISUALIZZAZIONE COMPLETA ---
st.divider()
st.subheader("📋 Registro Generale dei Movimenti")
df_view, _ = get_github_file()
if not df_view.empty:
    df_view['data_dt'] = pd.to_datetime(df_view['data'], errors='coerce')
    df_sorted = df_view.sort_values(by='data_dt', ascending=False).drop(columns=['data_dt'])
    
    opzione_visualizzazione = st.radio("Filtra tabella per stato:", ["Tutti i movimenti", "Solo Impegnati (Da pagare)", "Solo Saldati"], horizontal=True)
    
    if opzione_visualizzazione == "Solo Impegnati (Da pagare)":
        df_sorted = df_sorted[df_sorted['stato'] == 'Impegnato']
    elif opzione_visualizzazione == "Solo Saldati":
        df_sorted = df_sorted[df_sorted['stato'] == 'Saldato']
        
    df_display = df_sorted.copy()
    df_display['importo'] = df_display['importo'].apply(format_euro)
    st.dataframe(df_display, use_container_width=True)
