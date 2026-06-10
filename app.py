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

# Aggiunto il quarto TAB per la raccolta delle rese fische
tab1, tab2, tab3, tab4 = st.tabs(["🛒 Movimenti Standard", "👥 Giornate Operai", "💸 Spese Extra", "📦 Raccolta Rese"])

# --- TAB 1, 2, 3 rimangono invariati rispetto a prima ---
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
            colt = st.text_input("Coltura", key="std_colt")
            desc = st.text_area("Note / Descrizione", key="std_desc")
        if st.form_submit_button("Registra Movimento"):
            df, sha = get_github_file()
            new_row = pd.DataFrame([[data.strftime('%Y-%m-%d'), tipo, cat, desc, importo, colt]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

with tab2:
    st.subheader("Registra Registro Manodopera")
    with st.form("operaio_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            op_data = st.date_input("Data Lavoro", format="DD/MM/YYYY", key="op_data")
            op_nome = st.text_input("Nome Operaio / Nota", placeholder="es. Mario Rossi")
            op_giornate = st.number_input("Numero di Giornate lavorate", min_value=0.5, step=0.5, value=1.0)
        with col2:
            op_paga = st.number_input("Costo Totale Giornata (€)", min_value=0.0, step=5.0, value=50.0)
            op_colt = st.text_input("Coltura Associata", placeholder="es. Olivo", key="op_colt")
            op_note = st.text_area("Note Attività", placeholder="es. Potatura o Raccolta")
        if st.form_submit_button("Registra Giornata Operaio"):
            df, sha = get_github_file()
            costo_totale = op_giornate * op_paga
            descrizione_completa = f"{op_nome} ({op_giornate} gg) - {op_note}"
            new_row = pd.DataFrame([[op_data.strftime('%Y-%m-%d'), "Uscita", "Manodopera", descrizione_completa, costo_totale, op_colt]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

with tab3:
    st.subheader("Registra Spese Extra o Imprevisti")
    with st.form("extra_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            ex_data = st.date_input("Data Spesa", format="DD/MM/YYYY", key="ex_data")
            ex_importo = st.number_input("Importo Spesa (€)", min_value=0.0, step=0.01, key="ex_importo")
        with col2:
            ex_titolo = st.text_input("Tipo di Spesa Extra", placeholder="es. Riparazione Trattore")
            ex_note = st.text_area("Dettagli aggiuntivi", key="ex_note")
        if st.form_submit_button("Registra Spesa Extra"):
            df, sha = get_github_file()
            new_row = pd.DataFrame([[ex_data.strftime('%Y-%m-%d'), "Uscita", "Altro", f"EXTRA: {ex_titolo} - {ex_note}", ex_importo, "Generale / Extra"]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha): st.success("Registrato!"); st.rerun()

# --- NUOVO TAB 4: RACCOLTA RESE (PRODUZIONE FISICA) ---
with tab4:
    st.subheader("Registra i Quintali/Kg raccolti nei campi")
    with st.form("resa_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            p_data = st.date_input("Data Raccolta", format="DD/MM/YYYY", key="p_data")
            p_quantita = st.number_input("Quantità Raccolta (in KG)", min_value=1.0, step=1.0, help="Inserisci il peso sempre in KG per uniformità")
        with col2:
            p_colt = st.text_input("Coltura", placeholder="es. Olivo, Grano", key="p_colt")
            p_note = st.text_area("Note sul raccolto", placeholder="es. appezzamento Nord, qualità ottima")
            
        if st.form_submit_button("Registra Produzione"):
            df, sha = get_github_file()
            # Salviamo usando tipo="Resa" e l'importo indicherà i KG
            new_row = pd.DataFrame([[
                p_data.strftime('%Y-%m-%d'), 
                "Resa", 
                "Raccolta", 
                f"Produzione fisica: {p_note}", 
                float(p_quantita), 
                p_colt
            ]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha):
                st.success(f"Registrati {p_quantita} KG di produzione per {p_colt}")
                st.rerun()

st.divider()
st.subheader("Ultimi Movimenti Registrati")
df_view, _ = get_github_file()
if not df_view.empty:
    st.dataframe(df_view.tail(10), use_container_width=True)
