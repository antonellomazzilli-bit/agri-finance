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
            
            # --- RUBRICA A TENDINA DIPENDENTI ---
            ANAGRAFICA_DIPENDENTI = ["Iannone Felice", "--- Inserisci Altro Dipendente ---"]
            scelta_dip = st.selectbox("Seleziona Dipendente:", ANAGRAFICA_DIPENDENTI)

            if scelta_dip == "--- Inserisci Altro Dipendente ---":
                op_nome = st.text_input("Scrivi Nome e Cognome esatti:")
            else:
                op_nome = scelta_dip

            # Pulizia automatica spazi vuoti
            op_nome = op_nome.strip() if op_nome else "Iannone Felice"
            # ------------------------------------
            
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


# --- TABELLA DI SELEZIONE GENERALE INTERATTIVA ---
st.divider()
st.subheader("📋 Registro Generale dei Movimenti")
st.markdown("💡 *Seleziona una riga spuntando il cerchietto a sinistra per caricarla nel modulo di Modifica/Cancellazione in basso.*")

df_view, sha_view = get_github_file()

id_riga_selezionata = None

if not df_view.empty:
    opzione_visualizzazione = st.radio("Filtra tabella per stato:", ["Tutti i movimenti", "Solo Impegnati (Da pagare)", "Solo Saldati"], horizontal=True)
    
    df_filtrato = df_view.copy()
    if opzione_visualizzazione == "Solo Impegnati (Da pagare)":
        df_filtrato = df_filtrato[df_filtrato['stato'] == 'Impegnato']
    elif opzione_visualizzazione == "Solo Saldati":
        df_filtrato = df_filtrato[df_filtrato['stato'] == 'Saldato']
        
    df_filtrato['data_dt'] = pd.to_datetime(df_filtrato['data'], errors='coerce')
    df_filtrato = df_filtrato.sort_values(by='data_dt', ascending=False).drop(columns=['data_dt'])
    
    df_display = df_filtrato.copy()
    df_display['importo'] = df_display['importo'].apply(format_euro)
    
    selezione_griglia = st.dataframe(
        df_display, 
        use_container_width=True, 
        on_select="rerun", 
        selection_mode="single-row"
    )
    
    if selezione_griglia and selezione_griglia.get("selection", {}).get("rows"):
        indice_visualizzato = selezione_griglia["selection"]["rows"][0]
        id_riga_selezionata = df_filtrato.index[indice_visualizzato]


# --- SEZIONE FORM DINAMICO ---
if id_riga_selezionata is not None:
    st.write("")
    riga_dati = df_view.loc[id_riga_selezionata]
    
    with st.expander(f"✏️ MODIFICA O ELIMINA: Riga Selezionata (ID: {id_riga_selezionata})", expanded=True):
        with st.form("form_modifica_diretta"):
            c_mod1, c_mod2 = st.columns(2)
            
            with c_mod1:
                try:
                    data_corrente = datetime.strptime(str(riga_dati['data']), "%Y-%m-%d").date()
                except:
                    data_corrente = datetime.today().date()
                    
                mod_data = st.date_input("Data Operazione", value=data_corrente)
                
                tipi_validi = ["Uscita", "Entrata", "Resa"]
                idx_tipo = tipi_validi.index(riga_dati['tipo']) if riga_dati['tipo'] in tipi_validi else 0
                mod_tipo = st.selectbox("Tipo", tipi_validi, index=idx_tipo)
                
                mod_importo = st.number_input("Importo (€)", value=float(riga_dati['importo']), step=1.0, format="%.2f")
                mod_colt = st.text_input("Coltura", value=str(riga_dati['coltura_id']))
            
            with c_mod2:
                categorie = ["Sementi", "Carburante", "Concimi", "Vendita", "Fatture Fornitori", "Attrezzature", "Manodopera", "Raccolta", "Altro"]
                idx_cat = categorie.index(riga_dati['categoria']) if riga_dati['categoria'] in categorie else 8
                mod_cat = st.selectbox("Categoria", categorie, index=idx_cat)
                
                stato_corrente = "Impegnato" if "Impegnato" in str(riga_dati['stato']) else "Saldato"
                mod_stato = st.selectbox("Stato Pagamento", ["Saldato", "Impegnato"], index=0 if stato_corrente == "Saldato" else 1)
                
                mod_desc = st.text_area("Note / Descrizione", value=str(riga_dati['descrizione']))
            
            azione = st.radio("Scegli l'operazione da effettuare:", ["🔄 Salva modifiche ed aggiorna", "❌ Elimina definitivamente questo movimento"], index=0)
            
            if st.form_submit_button("🚀 Esegui Operazione sul Database"):
                df_latest, sha_latest = get_github_file()
                
                if "Salva" in azione:
                    df_latest.at[id_riga_selezionata, 'data'] = mod_data.strftime('%Y-%m-%d')
                    df_latest.at[id_riga_selezionata, 'tipo'] = mod_tipo
                    df_latest.at[id_riga_selezionata, 'categoria'] = mod_cat
                    df_latest.at[id_riga_selezionata, 'descrizione'] = mod_desc
                    df_latest.at[id_riga_selezionata, 'importo'] = mod_importo
                    df_latest.at[id_riga_selezionata, 'coltura_id'] = mod_colt
                    df_latest.at[id_riga_selezionata, 'stato'] = mod_stato
                    msg_commit = f"Modificato movimento ID: {id_riga_selezionata}"
                else:
                    df_latest = df_latest.drop(id_riga_selezionata)
                    msg_commit = f"Eliminato movimento ID: {id_riga_selezionata}"
                    
                with st.spinner("Sincronizzazione in corso..."):
                    if save_to_github(df_latest, sha_latest, msg_commit):
                        st.success("Database allineato cloud!")
                        st.rerun()
else:
    st.caption("ℹ️ Nessuna riga selezionata. Fai clic su un elemento della tabella sopra per aprire il pannello di controllo rapido.")
