import streamlit as st
import pandas as pd
import requests
import base64
import json
import re
from io import StringIO
import time

# --- CONFIGURAZIONE INIZIALE ---
st.set_page_config(page_title="AgriFinance Cloud", layout="wide")
COSTO_GIORNATA_EXTRA = 55.0
# --- MANUALE OPERATIVO (Sidebar) ---
with st.sidebar:
    st.header("📚 Supporto")
    
    testo_manuale = """
    MANUALE OPERATIVO: AGRIFINANCE CLOUD
    ... (Versione: 2.0 (Architettura a Doppio Binario e Database Cloud)

🎯 Obiettivo del Sistema
Il software centralizza la gestione amministrativa, finanziaria e operativa dell'impresa agricola. Il cuore logico è la separazione netta tra i movimenti fisici (il lavoro sui campi in giornate da 6 ore) e i movimenti finanziari (cassa, fatture e bonifici).

Moduli Operativi (Le 6 Aree del Gestionale)
1. Tab 1: Home (Registro Generale / Editor Diviso)
Questo è il pannello di controllo diretto sul database. L'interfaccia è divisa in due colonne: 🟢 Entrate e 🔴 Uscite.

Come Analizzare: Clicca sull'intestazione di qualsiasi colonna (es. "Importo" o "Data") per ordinare i dati.

Come Modificare: Fai doppio clic su una cella qualsiasi per correggere un refuso (es. una categoria assegnata per sbaglio). Premi Invio per confermare la digitazione.

Come Eliminare: Seleziona la riga cliccando sul quadratino alla sua estrema sinistra e premi il tasto Canc (o clicca sull'icona a cestino in alto a destra).

⚠️ PASSAGGIO OBBLIGATORIO: Nessuna modifica è definitiva finché non clicchi il pulsante blu in basso "💾 SALVA MODIFICHE NEL DATABASE".

2. Tab 2: Manodopera (Gestione Ore e Forza Lavoro)
Modulo dedicato esclusivamente al tracciamento del tempo fisico speso sugli uliveti. Non movimenta Euro in questa fase.

Logica di Base: La giornata lavorativa standard è impostata rigidamente su 6 ore (1.000 = 6 ore).

Come Registrare:

Seleziona il lavoratore (es. Iannone Felice).

Inserisci il totale delle giornate REALI lavorate (es. 2.000 per 12 ore totali).

Inserisci la quota da dichiarare come UFFICIALE (es. 1.000).

Il sistema calcola automaticamente la differenza (1.000 gg Extra) e crea due registrazioni separate per mantenere in perfetto equilibrio il doppio binario (Busta Paga vs. Fuori Busta).

Nota Strategica: Usa il campo note per specificare l'attività (es. "Potatura uliveto", "Raccolta").

3. Tab 3: Cassa (Estratto Conto Dipendenti)
Questo modulo traduce il tempo lavorato (Tab 2) in valuta, incrociandolo con i pagamenti reali effettuati.

Indicatore Dare/Avere: Il sistema moltiplica le giornate totali estratte dalla Tab 2 per la tariffa fissa (55 €) e sottrae tutti i versamenti registrati.

Verde: L'azienda ha erogato più di quanto strettamente dovuto (Credito).

Rosso: Ci sono giornate lavorate ancora da saldare (Debito).

Registrazione: Usa il form in basso per inserire i bonifici o gli anticipi. Scegli se si tratta di "Busta Paga" o "Saldo Extra" per mantenere l'allineamento con la contabilità della manodopera.

4. Tab 4: Rese
Modulo attualmente in fase di predisposizione per incrociare i quintali raccolti con la resa in olio.

5. Tab 5: Bilancio e Controllo di Gestione
È il cruscotto direzionale. Filtra i dati per anno e restituisce 4 livelli di analisi finanziaria:

Sintesi Finanziaria: L'utile o la perdita reale calcolando tutte le Entrate contro tutte le Uscite (incluse fatture e stipendi).

Analisi dei Costi (Dove vanno i soldi): Divide le uscite in due categorie. Da una parte la Cassa Personale (quanto è costato il lavoratore), dall'altra i Costi Operativi puri (acquisto attrezzature, gasolio, ecc.).

Forza Lavoro: Un contatore che riassume l'impegno fisico (giornate totali) e mostra il debito potenziale generato dal lavoro ancor prima che venga pagato.

Grafico Andamento: Permette di visualizzare picchi di spesa in determinati mesi (es. picco di acquisti carburante durante la raccolta).

6. Tab 6: Fatture e Commercializzazione
Il modulo per la contabilità generale e le operazioni commerciali dell'azienda.

Flusso di lavoro:

Seleziona in alto se è un'Uscita o un'Entrata. Questa scelta è reattiva e modificherà le categorie disponibili nel passo successivo.

Compila Data, Fornitore (es. Consorzio Agrario) e Descrizione (es. "Acquisto Concime").

Assegna la categoria, inserisci l'importo e clicca su Registra. Questi dati andranno ad alimentare istantaneamente i grafici della Tab 5.

    """
   
    st.download_button(
        label="📥 Scarica Manuale Operativo",
        data=testo_manuale,
        file_name="Manuale_AgriFinance.txt",
        mime="text/plain",
        use_container_width=True
    )
    st.divider()
    st.info("Utilizza il manuale per orientarti nel flusso di cassa e nella gestione delle fatture.")


# --- FUNZIONI DI CONNESSIONE GITHUB ---
@st.cache_data(ttl=0) # Forza Streamlit a scaricare dati sempre freschissimi aggirando la cache
def get_github_file():
    """Scarica il database aggiornato da GitHub."""
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = "antonellomazzilli-bit/agri-finance"
        path = "database.csv"
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            df = pd.read_csv(StringIO(content))
            return df, data['sha']
        else:
            # Se il file non esiste ancora, crea le colonne base
            return pd.DataFrame(columns=['data', 'tipo', 'categoria', 'descrizione', 'importo', 'prodotto', 'stato']), ""
    except Exception as e:
        st.error(f"Errore di comunicazione in Lettura: {e}")
        return pd.DataFrame(columns=['data', 'tipo', 'categoria', 'descrizione', 'importo', 'prodotto', 'stato']), ""

def save_to_github(df, sha, message):
    """Salva i dati e restituisce True SOLO in caso di successo effettivo confermato dal server."""
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = "antonellomazzilli-bit/agri-finance"
        path = "database.csv"
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

        csv_data = df.to_csv(index=False)
        encoded_data = base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')

        payload = {
            "message": message,
            "content": encoded_data,
            "sha": sha
        }

        response = requests.put(url, headers=headers, data=json.dumps(payload))

        if response.status_code in [200, 201]:
            st.cache_data.clear() # Svuota la cache dopo il salvataggio
            return True
        else:
            st.error(f"❌ Errore Server GitHub: Impossibile salvare. Dettaglio: {response.text}")
            return False
    except Exception as e:
        st.error(f"❌ Errore di Sistema durante il salvataggio: {e}")
        return False

# --- FUNZIONI DI UTILITA' ---
def format_euro(valore):
    """Formatta i numeri in stile italiano: 1.000,50 €"""
    # 1. Formatta il numero in stile anglosassone (1,234.56)
    importo_str = f"{valore:,.2f}"
    
    # 2. Inverte punto e virgola tramite un carattere temporaneo (X)
    importo_str = importo_str.replace(",", "X").replace(".", ",").replace("X", ".")
    
    return f"€ {importo_str}"

def estrai_giornate(descrizione, dipendente):
    try:
        if dipendente in descrizione:
            parti = descrizione.split('|')
            for p in parti:
                if 'gg' in p:
                    return float(p.replace('gg', '').strip())
        return 0.0
    except: return 0.0


# --- INTERFACCIA PRINCIPALE (LE 6 TAB) ---
st.title("AgriFinance Cloud")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Home", "Manodopera", "Cassa", "Rese", "Bilancio", "Fatture"])

# ==========================================
# --- TAB 1: HOME (Editor Diviso) ---
# ==========================================

with tab1:
    st.header("🏠 Registro Generale (Editor Diviso)")
    st.markdown("💡 Fai doppio clic sulle celle per modificare e premi Canc per eliminare. Salva per confermare.")
    
    df, sha = get_github_file()
    
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df = df.sort_values(by='data', ascending=False)

        df_entrate = df[df['tipo'] == 'Entrata'].reset_index(drop=True)
        df_uscite = df[df['tipo'] == 'Uscita'].reset_index(drop=True)
        df_altri = df[(df['tipo'] != 'Entrata') & (df['tipo'] != 'Uscita')].reset_index(drop=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🟢 Entrate")
            df_entrate_mod = st.data_editor(
                df_entrate, 
                column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY")},
                num_rows="dynamic", use_container_width=True, key="editor_entrate"
            )
        with col2:
            st.subheader("🔴 Uscite")
            df_uscite_mod = st.data_editor(
                df_uscite, 
                column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY")},
                num_rows="dynamic", use_container_width=True, key="editor_uscite"
            )
            
        st.divider()
        if st.button("💾 SALVA MODIFICHE NEL DATABASE", type="primary", use_container_width=True):
            df_modificato = pd.concat([df_entrate_mod, df_uscite_mod, df_altri], ignore_index=True)
            df_modificato['data'] = pd.to_datetime(df_modificato['data'], errors='coerce')
            df_modificato = df_modificato.sort_values(by='data', ascending=False).reset_index(drop=True)
            df_modificato['data'] = df_modificato['data'].dt.strftime('%Y-%m-%d')
            
            if save_to_github(df_modificato, sha, "Modifica da Editor Diviso"):
                st.success("✅ Modifiche salvate!")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Nessun dato registrato al momento nel database.")

# ==========================================
# --- TAB 2: MANODOPERA (Standard 6 Ore) ---
# ==========================================
with tab2:
    st.subheader("👥 Registro Manodopera (Giornata standard: 6 ore)")
    with st.form("operaio_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            op_data = st.date_input("Data Registrazione", format="DD/MM/YYYY")
            op_nome = st.selectbox("Seleziona Dipendente:", ["Iannone Felice"])
            op_reali = st.number_input("🔴 Giornate REALI (6h = 1.000)", min_value=0.0, step=0.167, value=1.0, format="%.3f")
            op_ufficiali = st.number_input("🟢 Di cui UFFICIALI", min_value=0.0, step=0.167, value=1.0, format="%.3f")
        with c2:
            op_tipo_paga = st.selectbox("Tipo di Pagamento", ["Nessuno", "Acconto", "Saldo Finale"])
            op_note = st.text_area("Note Attività")
        
        if st.form_submit_button("Registra Giornate"):
            df, sha = get_github_file()
            
            righe_nuove = []
            if op_ufficiali > 0:
                desc_uff = f"{op_nome} | {op_ufficiali:.3f} gg | UFFICIALE: {op_note}"
                righe_nuove.append([op_data.strftime('%Y-%m-%d'), "Uscita", "Manodopera", desc_uff, 0.0, "Olive", "Impegnato"])
            
            gg_extra = op_reali - op_ufficiali
            if abs(gg_extra) > 0.001:
                desc_extra = f"{op_nome} | {gg_extra:.3f} gg | EXTRA: {op_note}"
                righe_nuove.append([op_data.strftime('%Y-%m-%d'), "Uscita", "Manodopera Extra", desc_extra, 0.0, "Olive", "Impegnato"])
            
            if righe_nuove:
                df_nuove = pd.DataFrame(righe_nuove, columns=df.columns)
                df = pd.concat([df, df_nuove], ignore_index=True)
                if save_to_github(df, sha, "Aggiornamento Manodopera (6h)"):
                    st.success("✅ Giornate lavorative registrate!")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# --- TAB 3: CASSA ---
# ==========================================
with tab3:
    st.subheader("💸 Cassa e Estratto Conto (Euro)")
    df, _ = get_github_file()
    
    if not df.empty:
        cat_pagamenti = ['Busta Paga', 'Saldo Extra', 'Straordinari', 'Rimborsi']
        tot_versato = df[df['categoria'].isin(cat_pagamenti)]['importo'].sum()
        gg_totali = sum(estrai_giornate(row['descrizione'], "Iannone Felice") for _, row in df[df['categoria'].isin(['Manodopera', 'Manodopera Extra'])].iterrows())
        valore_lavoro = gg_totali * COSTO_GIORNATA_EXTRA
        
        saldo = tot_versato - valore_lavoro
        st.metric("Saldo Dare/Avere Dipendente", format_euro(saldo), delta="Verde = in credito | Rosso = a debito", delta_color="normal" if saldo>=0 else "inverse")
        
        with st.form("cassa_form", clear_on_submit=True):
            st.write("Registra un pagamento al dipendente:")
            c1, c2 = st.columns(2)
            with c1:
                data_pag = st.date_input("Data Pagamento", format="DD/MM/YYYY")
                tipo_op = st.selectbox("Natura Operazione", ["Busta Paga", "Saldo Extra", "Rimborsi"])
            with c2:
                imp = st.number_input("Importo Erogato (€)", min_value=0.0, step=10.0, format="%.2f")
            
            if st.form_submit_button("Registra Pagamento"):
                if imp > 0:
                    nuova_riga = [data_pag.strftime('%Y-%m-%d'), "Uscita", tipo_op, f"Pagamento Iannone Felice | {tipo_op}", float(imp), "Azienda", "Saldato"]
                    df = pd.concat([df, pd.DataFrame([nuova_riga], columns=df.columns)], ignore_index=True)
                    if save_to_github(df, sha, f"Pagamento Cassa: {imp}€"):
                        st.success("✅ Pagamento registrato!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("L'importo deve essere maggiore di zero.")

# ==========================================
# --- TAB 4: SIMULATORE STRATEGICO E TARGET ---
# ==========================================
with tab4:
    st.title("🎯 Simulatore Strategico & Break-Even")
    st.markdown("Pianifica la campagna olearia: definisci il tuo **obiettivo di reddito** e scopri i volumi fisici (olive/olio) necessari in tempo reale.")
    st.divider()

    df_pareggio, _ = get_github_file()
    
    if not df_pareggio.empty:
        df_pareggio['data_dt'] = pd.to_datetime(df_pareggio['data'], errors='coerce')
        anni_disponibili = df_pareggio['data_dt'].dt.year.dropna().unique()
        
        if len(anni_disponibili) > 0:
            anno_sel = st.selectbox("📅 Basato sulle spese storiche dell'anno:", sorted(anni_disponibili, reverse=True), key="anno_target")
            uscite_totali = df_pareggio[(df_pareggio['data_dt'].dt.year == anno_sel) & (df_pareggio['tipo'] == 'Uscita')]['importo'].sum()
            
            # --- LAYOUT A SCHEDE (CARDS) ---
            col_fin, col_strat = st.columns([1, 1], gap="large")
            
            # SCHEDA 1: I SOLDI (Fabbisogno)
            with col_fin:
                with st.container(border=True):
                    st.subheader("💶 1. Fabbisogno Economico")
                    st.metric("🔴 Spese Vive (dal database)", format_euro(uscite_totali))
                    
                    utile_desiderato = st.number_input("🟢 Tuo Obiettivo di Guadagno Annuo (€)", min_value=0.0, step=1000.0, value=24000.0)
                    fabbisogno_totale = uscite_totali + utile_desiderato
                    
                    # Box HTML ad alto impatto visivo per il totale
                    st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; margin-top: 15px; border-left: 5px solid #0f52ba;">
                        <p style="margin: 0; font-size: 14px; color: #555; text-transform: uppercase;">Obiettivo Finanziario Totale</p>
                        <h2 style="margin: 0; color: #0f52ba; font-size: 32px;">{format_euro(fabbisogno_totale)}</h2>
                    </div>
                    """, unsafe_allow_html=True)

            # SCHEDA 2: LA STRATEGIA E IL MERCATO
            with col_strat:
                with st.container(border=True):
                    st.subheader("⚖️ 2. Scelta Strategica")
                    strategia = st.radio("Cosa decidi di vendere?", ["Olio (Molitura)", "Olive (Vendita Diretta)"], horizontal=True)
                    
                    st.markdown("---")
                    if "Olio" in strategia:
                        prezzo_attuale = st.number_input("📈 Prezzo di Vendita Olio (€ / Litro)", min_value=0.0, step=0.5, value=8.50)
                        resa_stimata = st.number_input("⚙️ Resa Frantoio (Litri per 100Kg di olive)", min_value=0.0, step=0.5, value=15.0)
                    else:
                        prezzo_attuale = st.number_input("📈 Prezzo Vendita Olive (€ / QUINTALE)", min_value=0.0, step=5.0, value=80.0)
                        resa_stimata = 1.0 # Variabile tecnica invisibile
            
            # --- PANNELLO DEI RISULTATI (Aggiornato in Tempo Reale) ---
            st.write("") # Spazio vuoto
            st.markdown("### 🏆 Traguardo Produttivo")
            
            if prezzo_attuale > 0:
                with st.container(border=True):
                    if "Olio" in strategia:
                        if resa_stimata > 0:
                            litri_necessari = fabbisogno_totale / prezzo_attuale
                            quintali_necessari = litri_necessari / resa_stimata
                            
                            rc1, rc2, rc3 = st.columns(3)
                            rc1.metric("🫒 Olive da Raccogliere", f"{quintali_necessari:,.0f} Quintali", "Materia Prima")
                            rc2.metric("🍾 Olio da Produrre", f"{litri_necessari:,.0f} Litri", "Prodotto Finito")
                            rc3.metric("📊 Fatturato Target", format_euro(fabbisogno_totale), "Copertura Raggiunta")
                            
                            st.info(f"💡 **Piano d'Azione:** Per garantirti uno stipendio di **{format_euro(utile_desiderato)}** pagando tutte le spese, devi raccogliere circa **{quintali_necessari:,.0f} quintali**. Con una resa di {resa_stimata} L/q, otterrai i {litri_necessari:,.0f} litri necessari per incassare il totale vendendoli a {prezzo_attuale} €/L.")
                        else:
                            st.error("⚠️ Inserisci una resa maggiore di zero.")
                            
                    else: # Scenario Olive
                        quintali_necessari = fabbisogno_totale / prezzo_attuale
                        
                        rc1, rc2, rc3 = st.columns(3)
                        rc1.metric("🫒 Olive da Vendere", f"{quintali_necessari:,.0f} Quintali")
                        rc2.metric("⚖️ Equivalente in Kg", f"{quintali_necessari * 100:,.0f} Kg")
                        rc3.metric("📊 Fatturato Target", format_euro(fabbisogno_totale), "Copertura Raggiunta")
                        
                        st.info(f"💡 **Piano d'Azione:** Per garantirti uno stipendio di **{format_euro(utile_desiderato)}** pagando tutte le spese, devi vendere ai commercianti almeno **{quintali_necessari:,.0f} quintali** di olive al prezzo di {prezzo_attuale} €/q.")
            else:
                st.warning("⚠️ Imposta un Prezzo di Mercato maggiore di zero per visualizzare i traguardi.")
                
    else:
        st.info("Nessun dato finanziario registrato nel database per attivare il simulatore.")


# ==========================================
# --- TAB 5: BILANCIO (SCHEMA IV DIRETTIVA CEE) ---
# ==========================================
with tab5:
    st.header("⚖️ Conto Economico CEE (Art. 2425 c.c.)")
    
    df_bilancio, _ = get_github_file()
    
    if not df_bilancio.empty:
        df_bilancio['data_dt'] = pd.to_datetime(df_bilancio['data'], errors='coerce')
        anni_disponibili = df_bilancio['data_dt'].dt.year.dropna().unique()
        
        if len(anni_disponibili) > 0:
            anno_sel = st.selectbox("Seleziona Esercizio Fiscale:", sorted(anni_disponibili, reverse=True), key="bilancio_anno")
            df_anno = df_bilancio[df_bilancio['data_dt'].dt.year == anno_sel].copy()

            # --- MOTORE DI TRADUZIONE CIVILISTICA (MAPPING CEE) ---
            def classifica_cee(row):
                cat = str(row['categoria']).upper()
                tipo = row['tipo']
                
                if tipo == 'Entrata':
                    if 'CONTRIBUT' in cat or 'AGEA' in cat or 'PAC' in cat:
                        return "A.5 - Altri ricavi e proventi (Contributi)"
                    else:
                        return "A.1 - Ricavi delle vendite e delle prestazioni"
                elif tipo == 'Uscita':
                    if 'MANODOPERA' in cat or 'BUSTA' in cat or 'SALDO' in cat:
                        return "B.9 - Costi per il personale"
                    elif 'ATTREZZATUR' in cat or 'AMMORTAMENT' in cat or 'MACCHINARI' in cat:
                        return "B.10 - Ammortamenti e svalutazioni"
                    elif 'SERVIZ' in cat or 'FRANTOIO' in cat or 'MOLITURA' in cat or 'TERZI' in cat or 'CONSULENZ' in cat:
                        return "B.7 - Costi per servizi"
                    elif 'CONCIM' in cat or 'MATERI' in cat or 'PIANTIN' in cat or 'CARBURANT' in cat or 'GASOLIO' in cat:
                        return "B.6 - Per materie prime, sussidiarie e di consumo"
                    elif 'AFFITT' in cat or 'LEASING' in cat:
                        return "B.8 - Per godimento di beni di terzi"
                    else:
                        return "B.14 - Oneri diversi di gestione"
                return "Non Classificato"

            df_anno['voce_cee'] = df_anno.apply(classifica_cee, axis=1)

            # --- CALCOLO AGGREGATI ---
            entrate = df_anno[df_anno['tipo'] == 'Entrata'].groupby('voce_cee')['importo'].sum().reset_index()
            uscite = df_anno[df_anno['tipo'] == 'Uscita'].groupby('voce_cee')['importo'].sum().reset_index()
            
            tot_a = entrate['importo'].sum() if not entrate.empty else 0.0
            tot_b = uscite['importo'].sum() if not uscite.empty else 0.0
            risultato_operativo = tot_a - tot_b

            # --- CREAZIONE SOTTO-SCHEDE ---
            sub_bil1, sub_bil2 = st.tabs(["💻 Visualizzazione Interattiva", "🖨️ Documento Stampabile (PDF)"])

            # --- SOTTO-SCHEDA 1: CRUSCOTTO VIDEO ---
            with sub_bil1:
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.subheader("🟢 A) VALORE DELLA PRODUZIONE")
                    if not entrate.empty:
                        for _, row in entrate.sort_values(by='voce_cee').iterrows():
                            st.markdown(f"**{row['voce_cee']}**")
                            st.markdown(f"<p style='text-align: right; color: #1b5e20; font-size: 18px;'>{format_euro(row['importo'])}</p>", unsafe_allow_html=True)
                    else:
                        st.write("Nessun ricavo registrato.")
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                    st.markdown(f"<h4 style='text-align: right;'>TOTALE A: {format_euro(tot_a)}</h4>", unsafe_allow_html=True)

                with col_b:
                    st.subheader("🔴 B) COSTI DELLA PRODUZIONE")
                    if not uscite.empty:
                        for _, row in uscite.sort_values(by='voce_cee').iterrows():
                            st.markdown(f"**{row['voce_cee']}**")
                            st.markdown(f"<p style='text-align: right; color: #b71c1c; font-size: 18px;'>{format_euro(row['importo'])}</p>", unsafe_allow_html=True)
                    else:
                        st.write("Nessun costo registrato.")
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                    st.markdown(f"<h4 style='text-align: right;'>TOTALE B: {format_euro(tot_b)}</h4>", unsafe_allow_html=True)

                st.divider()
                col_risultato1, col_risultato2, col_risultato3 = st.columns([1, 2, 1])
                with col_risultato2:
                    colore = "#1b5e20" if risultato_operativo >= 0 else "#b71c1c"
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid {colore};">
                        <h3 style="margin: 0; color: #333;">Differenza tra Valore e Costi della Produzione (A - B)</h3>
                        <h1 style="margin: 0; color: {colore};">{format_euro(risultato_operativo)}</h1>
                    </div>
                    """, unsafe_allow_html=True)

            # --- SOTTO-SCHEDA 2: STAMPA HTML CIVILISTICA ---
            with sub_bil2:
                # Costruzione stringhe per le tabelle HTML
                righe_entrate = "".join([f"<tr><td>{row['voce_cee']}</td><td class='right'>{format_euro(row['importo'])}</td></tr>" for _, row in entrate.sort_values(by='voce_cee').iterrows()])
                righe_uscite = "".join([f"<tr><td>{row['voce_cee']}</td><td class='right'>{format_euro(row['importo'])}</td></tr>" for _, row in uscite.sort_values(by='voce_cee').iterrows()])
                
                colore_risultato_stampa = "#1b5e20" if risultato_operativo >= 0 else "#b71c1c"

                html_bilancio = f"""
                <html>
                <head>
                <style>
                    body {{ font-family: 'Arial', sans-serif; background-color: #f4f4f9; padding: 20px; }}
                    .foglio-a4 {{ background-color: white; color: black; padding: 40px; max-width: 800px; margin: auto; box-shadow: 0 0 15px rgba(0,0,0,0.2); }}
                    h2, h3, h4 {{ text-align: center; margin: 5px 0; }}
                    .header-doc {{ border-bottom: 2px solid black; padding-bottom: 15px; margin-bottom: 25px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; page-break-inside: avoid; }}
                    th, td {{ border: 1px solid #000; padding: 8px; text-align: left; }}
                    th {{ background-color: #e9e9e9; font-weight: bold; }}
                    .right {{ text-align: right; }}
                    .bold {{ font-weight: bold; }}
                    .totale-box {{ margin-top: 30px; border: 2px solid black; padding: 15px; text-align: right; page-break-inside: avoid; }}
                    @media print {{
                        body {{ background-color: white; padding: 0; }}
                        .foglio-a4 {{ box-shadow: none; max-width: 100%; padding: 0; margin: 0; }}
                        button {{ display: none; }}
                    }}
                </style>
                </head>
                <body>
                    <div style="text-align: center; margin-bottom: 20px;">
                        <button onclick="window.print()" style="padding: 12px 24px; font-size: 16px; cursor: pointer; background-color: #1565c0; color: white; border: none; border-radius: 5px; font-weight: bold;">🖨️ Stampa Conto Economico PDF</button>
                    </div>
                    <div class="foglio-a4">
                        <div class="header-doc">
                            <h2>AZIENDA AGRICOLA ANTONELLO MAZZILLI</h2>
                            <h4>Produzione Olio ed Esercizio Agricolo</h4>
                            <h3>CONTO ECONOMICO ESERCIZIO {anno_sel}</h3>
                            <p style="text-align:center; font-size: 12px;">Redatto in conformità all'Art. 2425 c.c. (Schema IV Direttiva CEE)</p>
                        </div>
                        
                        <h4 style="text-align: left;">A) VALORE DELLA PRODUZIONE</h4>
                        <table>
                            <tr><th>Voce Bilancio (Ricavi)</th><th class="right">Importo</th></tr>
                            {righe_entrate if righe_entrate else "<tr><td colspan='2'>Nessun dato presente</td></tr>"}
                            <tr><td class="bold right" style="background-color: #e9e9e9;">TOTALE A</td><td class="bold right" style="background-color: #e9e9e9;">{format_euro(tot_a)}</td></tr>
                        </table>

                        <br>
                        
                        <h4 style="text-align: left;">B) COSTI DELLA PRODUZIONE</h4>
                        <table>
                            <tr><th>Voce Bilancio (Costi Operativi)</th><th class="right">Importo</th></tr>
                            {righe_uscite if righe_uscite else "<tr><td colspan='2'>Nessun dato presente</td></tr>"}
                            <tr><td class="bold right" style="background-color: #e9e9e9;">TOTALE B</td><td class="bold right" style="background-color: #e9e9e9;">{format_euro(tot_b)}</td></tr>
                        </table>

                        <div class="totale-box">
                            <h3>Differenza tra Valore e Costi della Produzione (A - B)</h3>
                            <h2 style="color: {colore_risultato_stampa};">{format_euro(risultato_operativo)}</h2>
                        </div>
                    </div>
                </body>
                </html>
                """
                import streamlit.components.v1 as components
                components.html(html_bilancio, height=850, scrolling=True)
                
    else:
        st.info("Nessun dato registrato nel database per generare il bilancio.")
# ==========================================
# --- TAB 6: FATTURE E COMMERCIALIZZAZIONE ---
# ==========================================
with tab6:
    st.header("🧾 Registrazione Fatture e Operazioni Commerciali")
    
    fat_tipo = st.radio("Seleziona la Natura dell'Operazione:", ["Uscita (Acquisto / Spesa)", "Entrata (Vendita / Ricavo)"], horizontal=True)
    
    if "Uscita" in fat_tipo:
        categorie_disponibili = ["Carburante e Mezzi", "Attrezzature", "Materiale Agricolo (Concimi/Piante)", "Manutenzione", "Consulenze/Tasse", "Oneri",  "Irrigazione","Altro"]
        tipo_db = "Uscita"
    else:
        categorie_disponibili = ["Vendita Olio", "Vendita Olive", "Contributi/Aiuti", "Altro"]
        tipo_db = "Entrata"
        
    st.divider()
    
    with st.form("form_fatture", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            fat_data = st.date_input("Data Operazione", format="DD/MM/YYYY")
            fat_soggetto = st.text_input("Fornitore / Cliente", placeholder="es. Consorzio Agrario")
            fat_descrizione = st.text_input("Descrizione e Numero Documento", placeholder="es. Fatt. 15/2026")
        with c2:
            fat_categoria = st.selectbox("Categoria Bilancio", categorie_disponibili)
            fat_importo = st.number_input("Importo Totale (€)", min_value=0.0, step=1.0, format="%.2f")
            fat_stato = st.selectbox("Stato Pagamento", ["Saldato", "Da Saldare"])
            
        if st.form_submit_button("Registra Operazione"):
            if fat_importo > 0 and fat_soggetto:
                df, sha = get_github_file()
                descrizione_completa = f"{fat_soggetto.strip()} | {fat_descrizione.strip()}"
                stato_db = "Saldato" if "Saldato" in fat_stato else "Impegnato"
                
                nuova_riga = [fat_data.strftime('%Y-%m-%d'), tipo_db, fat_categoria, descrizione_completa, float(fat_importo), "Azienda Generale", stato_db]
                
                if len(nuova_riga) != len(df.columns):
                    st.error(f"Errore Colonne: Il database ha {len(df.columns)} colonne, stiamo cercando di inserirne {len(nuova_riga)}.")
                else:
                    df = pd.concat([df, pd.DataFrame([nuova_riga], columns=df.columns)], ignore_index=True)
                    if save_to_github(df, sha, f"Registrata Fattura: {fat_soggetto}"): 
                        st.success(f"✅ Operazione registrata con successo!")
                        time.sleep(2)
                        st.rerun()
            else:
                st.warning("⚠️ Compila almeno Fornitore/Cliente e assicurati che l'importo sia maggiore di zero.")
