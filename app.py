import streamlit as st
import pandas as pd
import base64
import requests
import io
import time
from datetime import datetime

st.set_page_config(page_title="AgriFinance Cloud", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"
BRANCH = "main"

# --- NUOVA COSTANTE AZIENDALE ---
COSTO_GIORNATA_EXTRA = 55.00  # Costo fisso per 8 ore fuori busta

def format_euro(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def estrai_giornate(descrizione, nome_target):
    try:
        if "|" in str(descrizione) and nome_target.lower() in str(descrizione).lower():
            parti = descrizione.split("|")
            info_tempo = parti[1].strip()
            if "gg" in info_tempo:
                return float(info_tempo.split(" gg")[0].strip())
    except:
        pass
    return 0.0

def get_github_file():
    timestamp = int(time.time())
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}?ref={BRANCH}&t={timestamp}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Cache-Control": "no-cache"
    }
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

tab1, tab2, tab3, tab4 = st.tabs(["🛒 Movimenti Standard", "👥 Giornate Operai", "💸 Extra & Buste Paga", "📦 Raccolta Rese"])

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

# --- TAB 2: OPERAI (DOPPIO BINARIO CON RECUPERO E DECIMALI) ---
with tab2:
    st.subheader("👥 Registro Manodopera (Gestione Doppio Binario)")
    with st.form("operaio_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            op_data = st.date_input("Data Registrazione", format="DD/MM/YYYY", key="op_data")
            ANAGRAFICA_DIPENDENTI = ["Iannone Felice", "--- Inserisci Altro Dipendente ---"]
            scelta_dip = st.selectbox("Seleziona Dipendente:", ANAGRAFICA_DIPENDENTI, key="dip_op")
            if scelta_dip == "--- Inserisci Altro Dipendente ---":
                op_nome = st.text_input("Scrivi Nome e Cognome esatti:", key="dip_op_txt")
            else:
                op_nome = scelta_dip
            op_nome = op_nome.strip() if op_nome else "Iannone Felice"
            
            st.markdown("---")
            op_reali = st.number_input("🔴 Giornate REALI lavorate (Totale Effettivo)", min_value=0.0, step=0.125, value=1.0, format="%.3f")
            
            # Legenda visiva per aiutare l'inserimento
            st.markdown("""
            <div style="font-size: 13px; color: #555; background-color: #e3f2fd; padding: 8px; border-radius: 5px; margin-top: -15px; margin-bottom: 10px;">
            ⏱️ <b>Convertitore Rapido Ore ➔ Decimali:</b><br>
            1 ora = <b>0.125</b> | 2 ore = <b>0.250</b> | 3 ore = <b>0.375</b> | 4 ore (Mezza) = <b>0.500</b><br>
            5 ore = <b>0.625</b> | 6 ore = <b>0.750</b> | 7 ore = <b>0.875</b> | 8 ore (Intera) = <b>1.000</b>
            </div>
            """, unsafe_allow_html=True)
            
            op_ufficiali = st.number_input("🟢 Di cui UFFICIALI (Da comunicare al Commercialista)", min_value=0.0, step=0.125, value=1.0, format="%.3f")
            st.markdown("---")
            
        with c2:
            op_tipo_paga = st.selectbox("Tipo di Pagamento", ["Nessuno (Attesa Busta Paga)", "Acconto", "Saldo Finale", "Paga Intera"])
            op_importo = st.number_input("Importo (€) - Lascia 0 se attendi busta paga", min_value=0.0, step=1.0, value=0.0)
            op_stato = st.selectbox("Stato del Costo", ["Saldato", "Impegnato (Da liquidare in futuro)"])
            op_note = st.text_area("Note Attività", placeholder="es. Raccolta Olive")
        
        if st.form_submit_button("Registra Giornate"):
            df, sha = get_github_file()
            stato_salvato = "Impegnato" if "Impegnato" in op_stato else "Saldato"
            righe_da_aggiungere = []
            
            # Riga 1: Ufficiale
            if op_ufficiali > 0:
                desc_uff = f"{op_nome} | {op_ufficiali} gg | {op_tipo_paga} | UFFICIALE: {op_note}"
                righe_da_aggiungere.append([op_data.strftime('%Y-%m-%d'), "Uscita", "Manodopera", desc_uff, float(op_importo), "Olive", stato_salvato])
            
            # Riga 2: Extra
            gg_extra = op_reali - op_ufficiali
            
            if gg_extra != 0:
                etichetta = "FUORI BUSTA" if gg_extra > 0 else "RECUPERO (Anticipo Ufficiale)"
                desc_extra = f"{op_nome} | {gg_extra} gg | {op_tipo_paga} | {etichetta}: {op_note}"
                righe_da_aggiungere.append([op_data.strftime('%Y-%m-%d'), "Uscita", "Manodopera Extra", desc_extra, 0.0, "Olive", stato_salvato])
            
            if righe_da_aggiungere:
                df_nuove = pd.DataFrame(righe_da_aggiungere, columns=df.columns)
                df = pd.concat([df, df_nuove], ignore_index=True)
                if save_to_github(df, sha, "Aggiunto Doppio Binario Manodopera"): 
                    st.success("Registrazione completata e Banca Ore aggiornata!")
                    st.rerun()

# --- TAB 3: CASSA, BUSTE PAGA E ESTRATTO CONTO IN EURO ---
with tab3:
    st.subheader("💸 Cassa, Buste Paga ed Estratto Conto (Dare/Avere)")
    ANAGRAFICA_DIPENDENTI = ["Iannone Felice", "--- Inserisci Altro Dipendente ---"]
    scelta_dip_ex = st.selectbox("Seleziona Dipendente per il Quadro Riassuntivo:", ANAGRAFICA_DIPENDENTI, key="dip_ex")
    if scelta_dip_ex == "--- Inserisci Altro Dipendente ---":
        dip_extra = st.text_input("Scrivi Nome e Cognome esatti:", key="dip_ex_txt")
    else:
        dip_extra = scelta_dip_ex
    dip_extra = dip_extra.strip() if dip_extra else "Iannone Felice"
    
    df_dash, _ = get_github_file()
    if not df_dash.empty:
        df_dash['data_dt'] = pd.to_datetime(df_dash['data'], errors='coerce')
        anno_corrente = datetime.today().year
        df_anno = df_dash[df_dash['data_dt'].dt.year == anno_corrente]
        
        df_dip = df_anno[df_anno['descrizione'].str.contains(dip_extra, case=False, na=False)]
        
        # 1. Totale Buste Paga (Solo info)
        tot_stipendi_ufficiali = df_dip[df_dip['descrizione'].str.contains('Saldo Busta Paga', case=False, na=False)]['importo'].sum()
        
        # 2. Denaro versato per i Saldi Extra
        tot_pagamenti_extra = df_dip[df_dip['categoria'] == 'Saldo Extra']['importo'].sum()
        
        # 3. Calcolo Trasparente delle Giornate
        # A) Somma lorda di tutti i mesi lavorati in extra (solo valori positivi)
        gg_extra_lorde = sum(estrai_giornate(row['descrizione'], dip_extra) for _, row in df_dip[df_dip['categoria'] == 'Manodopera Extra'].iterrows() if estrai_giornate(row['descrizione'], dip_extra) > 0)
        
        # B) Giornate recuperate (mesi in cui ha lavorato meno del dichiarato)
        gg_recuperate = sum(abs(estrai_giornate(row['descrizione'], dip_extra)) for _, row in df_dip[df_dip['categoria'] == 'Manodopera Extra'].iterrows() if estrai_giornate(row['descrizione'], dip_extra) < 0)
        
        # C) Giornate saldate/azzerate manualmente tramite pagamento
        gg_saldate_manualmente = sum(estrai_giornate(row['descrizione'], dip_extra) for _, row in df_dip[df_dip['categoria'] == 'Saldo Extra'].iterrows())
        
        # LA TUA DIFFERENZA
        gg_totali_sottratte = gg_recuperate + gg_saldate_manualmente
        gg_netto_residuo = gg_extra_lorde - gg_totali_sottratte
        
        valore_gg_extra = gg_netto_residuo * COSTO_GIORNATA_EXTRA
        
        # --- SALDO BILANCIATO ---
        saldo_in_euro = tot_pagamenti_extra - valore_gg_extra
        
        st.markdown(f"##### 📊 Resoconto Finanziario {anno_corrente}: **{dip_extra}**")
        
        if saldo_in_euro < 0:
            colore_saldo = "#D32F2F"
            etichetta_saldo = "DEBITO AZIENDA (Da pagare)"
            segno = ""
        elif saldo_in_euro > 0:
            colore_saldo = "#388E3C"
            etichetta_saldo = "CREDITO AZIENDA (Anticipo erogato)"
            segno = "+"
        else:
            colore_saldo = "#1A237E"
            etichetta_saldo = "CONTI IN PAREGGIO"
            segno = ""
            
        st.markdown(f"""<div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-top: 5px solid {colore_saldo}; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);">
<h4 style="margin-top:0; color:#333;">🏦 Estratto Conto Lavoratore (In Euro)</h4>
<table style="width:100%; font-size: 16px; border-collapse: collapse; color: #333;">
<tr>
<td style="padding: 5px 0; color: #555;">[ Info ] Totale Buste Paga Ufficiali versate:</td>
<td style="text-align: right; color: #555;">{format_euro(tot_stipendi_ufficiali)}</td>
</tr>
<tr style="border-top: 1px solid #ddd;">
<td style="padding: 5px 0; color: #1565C0;">[ Info ] Somma Giornate Extra Lavorate:</td>
<td style="text-align: right; color: #1565C0;">{gg_extra_lorde} gg</td>
</tr>
<tr>
<td style="padding: 5px 0; color: #1565C0;">[ Info ] Meno Differenza (Recuperi + Saldate):</td>
<td style="text-align: right; color: #1565C0;">- {gg_totali_sottratte} gg</td>
</tr>
<tr style="border-top: 1px dashed #ccc;">
<td style="padding: 5px 0;">[ - ] Valore Netto Giornate Extra Residue ({gg_netto_residuo} gg):</td>
<td style="text-align: right;">- {format_euro(valore_gg_extra)}</td>
</tr>
<tr style="border-top: 1px solid #ccc;">
<td style="padding: 5px 0;">[ + ] Pagamenti Fuori Busta (Euro) erogati:</td>
<td style="text-align: right; font-weight: bold;">{format_euro(tot_pagamenti_extra)}</td>
</tr>
<tr style="border-top: 1px solid #333;">
<td style="padding: 10px 0; font-size: 18px; color: {colore_saldo};"><b>SALDO FINALE: {etichetta_saldo}</b></td>
<td style="text-align: right; font-size: 22px; font-weight: bold; color: {colore_saldo}; padding: 10px 0;">{segno}{format_euro(saldo_in_euro)}</td>
</tr>
</table>
</div>""", unsafe_allow_html=True)
        
    st.divider()

    with st.form("extra_form", clear_on_submit=True):
        st.markdown(f"**Registra un Pagamento o un Azzeramento per {dip_extra}**")
        col1, col2 = st.columns(2)
        with col1:
            ex_data = st.date_input("Data Operazione", format="DD/MM/YYYY", key="ex_data")
            tipo_op = st.selectbox("Natura dell'Operazione", [
                "Pagamento Busta Paga Mensile (Non entra nel debito extra)",
                "Azzeramento Giornate Extra (Fuori Busta)",
                "Rimborso Spesa (effettuata dal dipendente)", 
                "Straordinario (Ore extra dipendente)", 
                "Spesa Extra Aziendale"
            ])
            ex_importo = st.number_input("Importo Erogato (€)", min_value=0.0, step=0.01, key="ex_importo")
            ex_stato = st.selectbox("Stato Pagamento", ["Saldato", "Impegnato"], key="ex_stato")
        with col2:
            ex_gg_azzerare = st.number_input("Giornate extra azzerate (Lascia 0 se paghi solo in €)", min_value=0.0, step=0.5, value=0.0)
            ex_titolo = st.text_input("Oggetto / Mese", placeholder="es. Saldo Busta Paga Luglio / Saldo Extra")
            ex_note = st.text_area("Dettagli aggiuntivi", key="ex_note")
            
        if st.form_submit_button("Registra Operazione"):
            df, sha = get_github_file()
            
            if "Busta Paga" in tipo_op:
                cat_salvataggio = "Manodopera"
                desc_salvataggio = f"{dip_extra} | 0 gg | Saldo Busta Paga | {ex_titolo} - {ex_note}"
            elif "Azzeramento" in tipo_op:
                cat_salvataggio = "Saldo Extra"
                desc_salvataggio = f"{dip_extra} | {ex_gg_azzerare} gg | Azzeramento Fuori Busta | {ex_titolo} - {ex_note}"
            elif "Straordinario" in tipo_op:
                cat_salvataggio = "Straordinari"
                desc_salvataggio = f"{dip_extra} | Straordinario | {ex_titolo} - {ex_note}"
            elif "Rimborso" in tipo_op:
                cat_salvataggio = "Rimborsi"
                desc_salvataggio = f"{dip_extra} | Rimborso Spesa | {ex_titolo} - {ex_note}"
            else:
                cat_salvataggio = "Altro"
                desc_salvataggio = f"EXTRA AZIENDA: {ex_titolo} - {ex_note}"
                
            new_row = pd.DataFrame([[ex_data.strftime('%Y-%m-%d'), "Uscita", cat_salvataggio, desc_salvataggio, ex_importo, "Olive", ex_stato]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            if save_to_github(df, sha, "Aggiunto Pagamento / Extra"): 
                st.success("Registrato!"); st.rerun()
# --- TAB 4: RACCOLTA E TABELLA INFERIORE (INVARIATE) ---
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
    
    selezione_griglia = st.dataframe(df_display, use_container_width=True, on_select="rerun", selection_mode="single-row")
    
    if selezione_griglia and selezione_griglia.get("selection", {}).get("rows"):
        indice_visualizzato = selezione_griglia["selection"]["rows"][0]
        id_riga_selezionata = df_filtrato.index[indice_visualizzato]

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
                categorie = ["Sementi", "Carburante", "Concimi", "Vendita", "Fatture Fornitori", "Attrezzature", "Manodopera", "Manodopera Extra", "Saldo Extra", "Straordinari", "Rimborsi", "Raccolta", "Altro"]
                idx_cat = categorie.index(riga_dati['categoria']) if riga_dati['categoria'] in categorie else len(categorie)-1
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
