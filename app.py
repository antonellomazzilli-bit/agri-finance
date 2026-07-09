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

def save_to_github(df, sha, commit_msg="Update database via AgriApp"):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content = df.to_csv(index=False)
    data = {
        "message": commit_msg,
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
            cat = st.selectbox("Categoria", ["Sementi", "Carburante", "Concimi", "Vendita", "Fatture Fornitori", "Attrezzature", "Altro"], key="std_cat")
            colt = st.text_input("Coltura", value="Olive", key="std_colt")
            stato = st.selectbox("Stato Pagamento", ["Saldato", "Impegnato (Non ancora saldato)"])
            desc = st.text_area("Note / Descrizione", key="std_desc")
            
        if st.form_submit_button("Registra Movimento"):
            df, sha = get_github_file()
            stato_salvato = "Impegnato" if "Impegnato" in stato else "Saldato"
            new_row = pd.DataFrame([[data.strftime('%Y-%m-%d'), tipo, cat, desc, importo, colt, stato_salvato]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha, "Aggiunto Movimento Standard"): 
                st.success("Registrato!"); st.rerun()

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
            if save_to_github(df, sha, "Aggiunto Movimento Manodopera"): 
                st.success("Registrato!"); st.rerun()

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
            if save_to_github(df, sha, "Aggiunto Movimento Extra"): 
                st.success("Registrato!"); st.rerun()

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
            if save_to_github(df, sha, "Aggiunto Movimento Raccolta"): 
                st.success("Registrato!"); st.rerun()


# --- SEZIONE GESTIONE: MODIFICA / ELIMINA ---
st.divider()
with st.expander("✏️ Gestione Movimenti (Modifica o Elimina)"):
    df_mod, sha_mod = get_github_file()
    
    if not df_mod.empty:
        # Creiamo un'etichetta visiva per riconoscere facilmente la riga
        df_mod['idx_string'] = df_mod.index.astype(str)
        df_mod['etichetta'] = df_mod['idx_string'] + " | " + df_mod['data'] + " | " + df_mod['categoria'] + " | € " + df_mod['importo'].astype(str)
        
        # Ordiniamo la lista dal più recente al più vecchio
        lista_opzioni = df_mod['etichetta'].tolist()[::-1]
        
        selezione = st.selectbox("Seleziona il movimento su cui operare:", lista_opzioni)
        
        if selezione:
            # Estrapoliamo l'ID esatto della riga
            id_riga = int(selezione.split(" | ")[0])
            riga_dati = df_mod.loc[id_riga]
            
            with st.form("form_modifica"):
                st.write("**Modifica i dati sottostanti o scegli di eliminare il movimento.**")
                c_mod1, c_mod2 = st.columns(2)
                
                with c_mod1:
                    try:
                        data_corrente = datetime.strptime(str(riga_dati['data']), "%Y-%m-%d").date()
                    except:
                        data_corrente = datetime.today().date()
                        
                    mod_data = st.date_input("Nuova Data", value=data_corrente)
                    
                    tipi_validi = ["Uscita", "Entrata", "Resa"]
                    idx_tipo = tipi_validi.index(riga_dati['tipo']) if riga_dati['tipo'] in tipi_validi else 0
                    mod_tipo = st.selectbox("Nuovo Tipo", tipi_validi, index=idx_tipo)
                    
                    mod_importo = st.number_input("Nuovo Importo (€)", value=float(riga_dati['importo']), step=10.0)
                    mod_colt = st.text_input("Nuova Coltura", value=str(riga_dati['coltura_id']))
                
                with c_mod2:
                    categorie = ["Sementi", "Carburante", "Concimi", "Vendita", "Fatture Fornitori", "Attrezzature", "Manodopera", "Raccolta", "Altro"]
                    idx_cat = categorie.index(riga_dati['categoria']) if riga_dati['categoria'] in categorie else 8
                    mod_cat = st.selectbox("Nuova Categoria", categorie, index=idx_cat)
                    
                    stato_corrente = "Impegnato" if "Impegnato" in str(riga_dati['stato']) else "Saldato"
                    mod_stato = st.selectbox("Nuovo Stato", ["Saldato", "Impegnato"], index=0 if stato_corrente == "Saldato" else 1)
                    
                    mod_desc = st.text_area("Nuova Descrizione", value=str(riga_dati['descrizione']))
                
                azione = st.radio("Azione da eseguire:", ["🔄 Aggiorna Movimento", "❌ Elimina Definitivamente"], index=0)
                
                if st.form_submit_button("Conferma Operazione"):
                    # Rileggiamo il file un attimo prima di salvare per prevenire conflitti
                    df_latest, sha_latest = get_github_file()
                    
                    if "Aggiorna" in azione:
                        df_latest.at[id_riga, 'data'] = mod_data.strftime('%Y-%m-%d')
                        df_latest.at[id_riga, 'tipo'] = mod_tipo
                        df_latest.at[id_riga, 'categoria'] = mod_cat
                        df_latest.at[id_riga, 'descrizione'] = mod_desc
                        df_latest.at[id_riga, 'importo'] = mod_importo
                        df_latest.at[id_riga, 'coltura_id'] = mod_colt
                        df_latest.at[id_riga, 'stato'] = mod_stato
                        msg_commit = f"Modificato movimento ID: {id_riga}"
                    else:
                        # Eliminazione della riga
                        df_latest = df_latest.drop(id_riga)
                        msg_commit = f"Eliminato movimento ID: {id_riga}"
                        
                    with st.spinner("Sincronizzazione col database in corso..."):
                        if save_to_github(df_latest, sha_latest, msg_commit):
                            st.success("Operazione eseguita con successo!")
                            st.rerun()
    else:
        st.info("Nessun movimento presente nel database.")


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
