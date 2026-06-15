import streamlit as st
import pandas as pd
import base64
import requests
import io
from datetime import datetime

st.set_page_config(page_title="AgriFinance Cloud", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
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
        return pd.read_csv(io.StringIO(content)), r.json()["sha"]
    columns = ["data", "tipo", "categoria", "descrizione", "importo", "coltura_id"]
    return pd.DataFrame(columns=columns), None

def save_to_github(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content = df.to_csv(index=False)
    data = {
        "message": "Update database.csv via AgriApp",
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
    st.subheader("Registra Entrate o Uscite Standard")
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data Operazione", format="DD/MM/YYYY", key="std_data")
            tipo = st.selectbox("Tipo", ["Uscita", "Entrata"], key="std_tipo")
            importo = st.number_input("Importo (€)", min_value=0.0, step=0.01, key="std_importo")
        with col2:
            cat = st.selectbox("Categoria", ["Sementi", "Carburante", "Concimi", "Vendita"], key="std_cat")
            colt = st.text_input("Coltura", value="Olive", key="std_colt")
            desc = st.text_area("Note / Descrizione", key="std_desc")
        if st.form_submit_button("Registra Movimento"):
            df, sha = get_github_file()
            new_row = pd.DataFrame([[data.strftime('%Y-%m-%d'), tipo, cat, desc, importo, colt]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

# --- TAB 2: GIORNATE OPERAI (Struttura Excel integrata) ---
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
            op_note = st.text_area("Note Attività", placeholder="es. Raccolta Olive, Potatura")
        
        if st.form_submit_button("Registra Manodopera"):
            df, sha = get_github_file()
            # Costruiamo una descrizione dettagliata che mantenga la logica del tuo Excel
            desc_dettagliata = f"{op_nome} | {op_giornate} gg ({op_ore} ore) | Tipo: {op_tipo_paga} | Note: {op_note}"
            
            new_row = pd.DataFrame([[
                op_data.strftime('%Y-%m-%d'), 
                "Uscita", 
                "Manodopera", 
                desc_dettagliata, 
                float(op_importo), 
                "Olive" # Forza la coltura a Olive come richiesto
            ]], columns=df.columns)
            
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha):
                st.success(f"Registrata operazione di manodopera: {format_euro(op_importo)}")
                st.rerun()

# --- TAB 3: SPESE EXTRA ---
with tab3:
    st.subheader("Registra Spese Extra o Imprevisti")
    with st.form("extra_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            ex_data = st.date_input("Data Spesa", format="DD/MM/YYYY", key="ex_data")
            ex_importo = st.number_input("Importo Spesa (€)", min_value=0.0, step=0.01, key="ex_importo")
        with col2:
            ex_titolo = st.text_input("Tipo di Spesa Extra", placeholder="es. Riparazione Frattura Scuotitore")
            ex_note = st.text_area("Dettagli aggiuntivi", key="ex_note")
        if st.form_submit_button("Registra Spesa Extra"):
            df, sha = get_github_file()
            new_row = pd.DataFrame([[ex_data.strftime('%Y-%m-%d'), "Uscita", "Altro", f"EXTRA: {ex_titolo} - {ex_note}", ex_importo, "Olive"]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

# --- TAB 4: RACCOLTA RESE ---
with tab4:
    st.subheader("📦 Registra i KG di Olive raccolti")
    with st.form("resa_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            p_data = st.date_input("Data Raccolta", format="DD/MM/YYYY", key="p_data")
            p_quantita = st.number_input("Quantità Olive (in KG)", min_value=1.0, step=1.0)
        with col2:
            p_note = st.text_area("Note sul raccolto", placeholder="es. Molitura presso Frantoio X")
        if st.form_submit_button("Registra Produzione"):
            df, sha = get_github_file()
            new_row = pd.DataFrame([[p_data.strftime('%Y-%m-%d'), "Resa", "Raccolta", f"Raccolto: {p_note}", float(p_quantita), "Olive"]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success(f"Registrati {p_quantita} KG di Olive"); st.rerun()

# --- VISUALIZZAZIONE COMPLETA E ORDINATA ---
st.divider()
st.subheader("📋 Registro dei Movimenti su Cloud (GitHub)")

df_view, _ = get_github_file()

if not df_view.empty:
    # 1. Convertiamo la data in formato corretto per poter ordinare
    df_view['data_dt'] = pd.to_datetime(df_view['data'], errors='coerce')
    
    # 2. Ordiniamo la tabella: i più recenti appariranno in alto
    df_sorted = df_view.sort_values(by='data_dt', ascending=False).drop(columns=['data_dt'])
    
    # 3. Formattiamo l'importo in Euro per una lettura pulita
    df_display = df_sorted.copy()
    df_display['importo'] = df_display['importo'].apply(format_euro)
    
    # 4. Opzione per scegliere quanti vederne
    opzione_visualizzazione = st.radio(
        "Filtro visualizzazione:",
        ["Mostra solo gli ultimi 20 movimenti", "Mostra l'intero archivio storico"],
        horizontal=True
    )
    
    if opzione_visualizzazione == "Mostra solo gli ultimi 20 movimenti":
        st.dataframe(df_display.head(20), use_container_width=True)
    else:
        st.dataframe(df_display, use_container_width=True)
else:
    st.info("Nessun movimento registrato nel file centrale di GitHub.")
df_view, _ = get_github_file()
if not df_view.empty:
    st.dataframe(df_view.tail(10), use_container_width=True)
