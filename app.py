import streamlit as st
import pandas as pd
import requests
import base64
import json
import re
from io import StringIO
import time
from fpdf import FPDF
from datetime import datetime

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
@st.cache_data(ttl=0) 
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
            return pd.DataFrame(columns=['data', 'tipo', 'categoria', 'descrizione', 'importo', 'prodotto', 'stato', 'totale_fattura', 'importo_pagato', 'registro_pagamenti']), ""
    except Exception as e:
        st.error(f"Errore di comunicazione in Lettura: {e}")
        return pd.DataFrame(columns=['data', 'tipo', 'categoria', 'descrizione', 'importo', 'prodotto', 'stato', 'totale_fattura', 'importo_pagato', 'registro_pagamenti']), ""

def save_to_github(df, sha, message):
    """Salva i dati e restituisce True SOLO in caso di successo effettivo."""
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
            st.cache_data.clear() 
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
    # BLINDATURA: Se il valore non è un numero, forzalo a zero.
    try:
        valore = float(valore)
    except (ValueError, TypeError):
        valore = 0.0
        
    # 1. Formatta il numero in stile anglosassone (1,234.56)
    importo_str = f"{valore:,.2f}"
    
    # 2. Inverte punto e virgola tramite un carattere temporaneo (X)
    importo_str = importo_str.replace(",", "X").replace(".", ",").replace("X", ".")
    
    return f"€ {importo_str}"

def estrai_giornate(descrizione, dipendente):
    """Estrae il numero di giornate (gg) dalla descrizione testuale"""
    try:
        if dipendente in descrizione:
            parti = descrizione.split('|')
            for p in parti:
                if 'gg' in p:
                    return float(p.replace('gg', '').strip())
        return 0.0
    except: 
        return 0.0


# --- INTERFACCIA PRINCIPALE (LE 6 TAB) ---
st.title("AgriFinance Cloud")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Home", "Manodopera", "Cassa", "Rese", "Bilancio", "Fatture"])


# ==========================================
# --- TAB 1: HOME (CON TRACCIAMENTO TRANCHE DI PAGAMENTO) ---
# ==========================================
with tab1:
    st.header("🏠 Database Unificato")
    
    df, sha = get_github_file()
    
    if not df.empty:
        # 1. AUTO-AGGIORNAMENTO STRUTTURALE DEL DATABASE (MIGRAZIONE SILENZIOSA)
        colonne_modificate = False
        
        if 'totale_fattura' not in df.columns:
            df['totale_fattura'] = df['importo']
            colonne_modificate = True
        
        if 'importo_pagato' not in df.columns:
            df['importo_pagato'] = df.apply(lambda row: row['importo'] if row['stato'] == 'Saldato' else 0.0, axis=1)
            colonne_modificate = True
            
        if 'registro_pagamenti' not in df.columns:
            def crea_storico(row):
                if row['stato'] == 'Saldato':
                    return f"{row['data']}|{row['importo']}"
                return ""
            df['registro_pagamenti'] = df.apply(crea_storico, axis=1)
            colonne_modificate = True
            
        if colonne_modificate:
            save_to_github(df, sha, "Auto-Aggiornamento Struttura Database ERP")
            st.rerun()

        # 2. CALCOLO DINAMICO DEL RESIDUO
        df['Residuo (€)'] = df['totale_fattura'] - df['importo_pagato']
        
        df_display = df.copy()
        colonne_da_mostrare = ['data', 'categoria', 'descrizione', 'totale_fattura', 'importo_pagato', 'Residuo (€)', 'stato']
        df_display = df_display[[c for c in colonne_da_mostrare if c in df_display.columns]]

        st.subheader("📋 Storico Movimenti e Situazione Fatture")
        st.markdown("Seleziona una riga per registrare un nuovo pagamento o modificare la fattura.")

        evento = st.dataframe(
            df_display.reset_index(drop=True),
            use_container_width=True,
            selection_mode="single-row",
            on_select="rerun",
            hide_index=False
        )

        righe_selezionate = evento.selection.rows
        
        if len(righe_selezionate) > 0:
            indice_visualizzato = righe_selezionate[0]
            indice_reale = df.index[indice_visualizzato]
            riga_sel = df.loc[indice_reale]

            st.divider()
            
            with st.container(border=True):
                st.subheader(f"💼 Gestione Fattura/Documento: {riga_sel['categoria']}")
                
                # Layout a due colonne: A sinistra la fattura base, a destra i pagamenti
                col_dati, col_rate = st.columns([1.2, 1])
                
                with col_dati:
                    st.write("### 📝 Dati Documento")
                    with st.form("form_modifica_fattura"):
                        mod_cat = st.text_input("Categoria", value=str(riga_sel['categoria']))
                        mod_desc = st.text_input("Descrizione Documento", value=str(riga_sel['descrizione']))
                        
                        c_imp1, c_imp2 = st.columns(2)
                        # Qui modifichi il costo della fattura (se c'era stato un errore)
                        tot_fat_attuale = float(riga_sel['totale_fattura'])
                        mod_totale = c_imp1.number_input("Totale Fattura (€)", value=tot_fat_attuale, step=10.0)
                        
                        mod_stato = c_imp2.selectbox(
                            "Stato Generale", 
                            ["Saldato", "Pagamento Parziale", "Da Saldare", "Da Incassare"], 
                            index=["Saldato", "Pagamento Parziale", "Da Saldare", "Da Incassare"].index(riga_sel['stato']) if riga_sel['stato'] in ["Saldato", "Pagamento Parziale", "Da Saldare", "Da Incassare"] else 0
                        )

                        # Impaginazione dei due bottoni (Salva e Elimina)
                        st.markdown("<br>", unsafe_allow_html=True)
                        c_btn1, c_btn2 = st.columns(2)
                        salva_fattura = c_btn1.form_submit_button("💾 Salva Modifiche", type="primary")
                        elimina_fattura = c_btn2.form_submit_button("🗑️ Elimina Registrazione", type="secondary")
                        
                        if salva_fattura:
                            df.at[indice_reale, 'categoria'] = mod_cat
                            df.at[indice_reale, 'descrizione'] = mod_desc
                            df.at[indice_reale, 'totale_fattura'] = mod_totale
                            df.at[indice_reale, 'importo'] = mod_totale # per retrocompatibilità
                            df.at[indice_reale, 'stato'] = mod_stato
                            
                            if save_to_github(df, sha, f"Modificati dati riga {indice_reale}"):
                                st.success("✅ Dati aggiornati!")
                                time.sleep(1)
                                st.rerun()
                                
                        if elimina_fattura:
                            # Logica di eliminazione della riga dal database
                            df = df.drop(index=indice_reale).reset_index(drop=True)
                            
                            if save_to_github(df, sha, f"Eliminata registrazione: {riga_sel['descrizione']}"):
                                st.error("🗑️ Registrazione eliminata con successo dal database!")
                                time.sleep(1.5)
                                st.rerun()

                with col_rate:
                    totale = float(riga_sel['totale_fattura'])
                    pagato = float(riga_sel['importo_pagato'])
                    residuo = totale - pagato
                    
                    st.write("### 💶 Stato Pagamenti")
                    c_fin1, c_fin2 = st.columns(2)
                    c_fin1.metric("Totale Pagato", format_euro(pagato))
                    c_fin2.metric("Debito Residuo", format_euro(residuo), delta=f"{residuo:.2f} €", delta_color="inverse")
                    
                    storico_txt = str(riga_sel.get('registro_pagamenti', ''))
                    if storico_txt and storico_txt != 'nan':
                        st.write("**Storico Rate Versate:**")
                        rate = storico_txt.split(';')
                        for rata in rate:
                            parti = rata.split('|')
                            if len(parti) >= 2:
                                r_data = parti[0]
                                r_imp = format_euro(float(parti[1]))
                                r_nota = f" *(Note: {parti[2]})*" if len(parti) == 3 and parti[2].strip() else ""
                                st.markdown(f"- 📅 {r_data}: **{r_imp}**{r_nota}")
                    else:
                        st.info("Nessun pagamento registrato finora.")

                    st.divider()
                    
                    with st.form("form_aggiungi_rata"):
                        st.write("**➕ Registra Nuovo Versamento (Tranche)**")
                        r_col1, r_col2 = st.columns(2)
                        
                        import datetime
                        nuova_data = r_col1.date_input("Data Versamento", value=datetime.date.today())
                        importo_rata = r_col2.number_input("Importo Rata (€)", value=residuo if residuo > 0 else 0.0, step=10.0, min_value=0.0)
                        
                        nota_rata = st.text_input("Metodo / Note (es. Bonifico n.456, Contanti)", placeholder="Facoltativo...")
                        
                        aggiungi_rata = st.form_submit_button("Aggiungi Rata 💸", type="secondary")
                        
                        if aggiungi_rata and importo_rata > 0:
                            nota_pulita = nota_rata.replace("|", "-").replace(";", ",")
                            nuova_stringa_rata = f"{nuova_data.strftime('%Y-%m-%d')}|{importo_rata}|{nota_pulita}"
                            
                            storico_attuale = str(df.at[indice_reale, 'registro_pagamenti'])
                            if storico_attuale and storico_attuale != 'nan' and storico_attuale != '':
                                df.at[indice_reale, 'registro_pagamenti'] = f"{storico_attuale};{nuova_stringa_rata}"
                            else:
                                df.at[indice_reale, 'registro_pagamenti'] = nuova_stringa_rata
                            
                            nuovo_totale_pagato = pagato + importo_rata
                            df.at[indice_reale, 'importo_pagato'] = nuovo_totale_pagato
                            
                            if nuovo_totale_pagato >= totale:
                                df.at[indice_reale, 'stato'] = "Saldato"
                            elif nuovo_totale_pagato > 0:
                                df.at[indice_reale, 'stato'] = "Pagamento Parziale"
                                
                            if save_to_github(df, sha, f"Aggiunta tranche di {importo_rata} su riga {indice_reale}"):
                                st.success("✅ Rata registrata correttamente!")
                                time.sleep(1)
                                st.rerun()


# ==========================================
# --- TAB 2: MANODOPERA (CON RIEPILOGO MATEMATICO) ---
# ==========================================
with tab2:
    st.header("🚜 Gestione Manodopera")
    df, sha = get_github_file()
    
    with st.form("form_registrazione_manodopera", clear_on_submit=True):
        st.subheader("📝 Registra Nuova Giornata")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            op_nome = st.selectbox("Operatore", ["Iannone Felice"])
            op_data = st.date_input("Data Lavoro", format="DD/MM/YYYY")
        with c2:
            op_ufficiali = st.number_input("Giornate Ufficiali", min_value=0.0, step=0.5, format="%.2f")
        with c3:
            op_reali = st.number_input("Giornate Reali Effettuate", min_value=0.0, step=0.5, format="%.2f")
            
        op_note = st.text_input("Note (Lavoro svolto)")
        inviato = st.form_submit_button("Registra Giornate", type="primary")
        
    if inviato:
        righe_nuove = []
        if op_ufficiali > 0:
            desc_uff = f"{op_nome} | {op_ufficiali:.3f} gg | UFFICIALE: {op_note}"
            righe_nuove.append({
                'data': op_data.strftime('%Y-%m-%d'), 'tipo': "Uscita", 'categoria': "Manodopera", 
                'descrizione': desc_uff, 'importo': 0.0, 'prodotto': "Olive", 'stato': "Impegnato", 
                'totale_fattura': 0.0, 'importo_pagato': 0.0, 'registro_pagamenti': ""
            })
        
        gg_extra = op_reali - op_ufficiali
        if abs(gg_extra) > 0.001:
            desc_extra = f"{op_nome} | {gg_extra:.3f} gg | EXTRA: {op_note}"
            righe_nuove.append({
                'data': op_data.strftime('%Y-%m-%d'), 'tipo': "Uscita", 'categoria': "Manodopera Extra", 
                'descrizione': desc_extra, 'importo': 0.0, 'prodotto': "Olive", 'stato': "Impegnato", 
                'totale_fattura': 0.0, 'importo_pagato': 0.0, 'registro_pagamenti': ""
            })
        
        if righe_nuove:
            df_nuove = pd.DataFrame(righe_nuove)
            df = pd.concat([df, df_nuove], ignore_index=True)
            
            if save_to_github(df, sha, "Aggiornamento Manodopera"):
                st.success("✅ Giornate lavorative registrate con successo!")
                import time
                time.sleep(1)
                st.rerun()
        else:
            st.warning("Nessun dato valido inserito (Giornate a zero).")

    # --- NUOVO SCHERMO: RIEPILOGO TAB 2 ---
    st.divider()
    st.subheader("📊 Riepilogo Giornate Lavorate (Totali vs Extra)")
    
    df_lav = df[df['categoria'].isin(['Manodopera', 'Manodopera Extra'])].copy()
    if not df_lav.empty:
        df_lav['data_dt'] = pd.to_datetime(df_lav['data'], errors='coerce')
        mesi_nomi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
        
        riepilogo = {}
        for _, row in df_lav.iterrows():
            if pd.notna(row['data_dt']):
                chiave = f"{mesi_nomi[row['data_dt'].month]} {row['data_dt'].year}"
                gg = estrai_giornate(str(row['descrizione']), "Iannone Felice")
                
                if chiave not in riepilogo:
                    riepilogo[chiave] = {'Giornate TOTALI': 0.0, 'Giornate EXTRA': 0.0, 'Giornate UFFICIALI': 0.0}
                    
                riepilogo[chiave]['Giornate TOTALI'] += gg
                if row['categoria'] == 'Manodopera Extra':
                    riepilogo[chiave]['Giornate EXTRA'] += gg
                elif row['categoria'] == 'Manodopera':
                    riepilogo[chiave]['Giornate UFFICIALI'] += gg

        if riepilogo:
            df_riep = pd.DataFrame.from_dict(riepilogo, orient='index')
            st.dataframe(df_riep, use_container_width=True)
        else:
            st.info("Nessuna giornata registrata finora.")


# ==========================================
# --- TAB 3: CASSA E CONTROLLO MESI ARRETRATI ---
# ==========================================
with tab3:
    st.subheader("💸 Cassa e Estratto Conto Mensile")
    df, sha = get_github_file()
    
    if not df.empty:
        # 1. Preparazione Dati
        df['importo'] = pd.to_numeric(df['importo'], errors='coerce').fillna(0.0)
        df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
        
        dati_mensili = {}
        mesi_nomi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
        mesi_nomi_inv = {v: k for k, v in mesi_nomi.items()}
        
        # 2. Inizializzazione Mesi e Calcolo Extra (SEPARATO)
        tutto_lavoro = df[df['categoria'].isin(['Manodopera', 'Manodopera Extra'])]
        
        for index, row in tutto_lavoro.iterrows():
            if pd.notna(row['data_dt']):
                mese_num = row['data_dt'].month
                anno_num = row['data_dt'].year
                chiave_mese = f"{mesi_nomi[mese_num]} {anno_num}"
                
                if chiave_mese not in dati_mensili:
                    dati_mensili[chiave_mese] = {'Extra Maturato (Debito)': 0.0, 'Extra Pagato': 0.0, 'Busta Paga Versata': 0.0}
                
                if row['categoria'] == 'Manodopera Extra':
                    gg_lavorati = estrai_giornate(str(row['descrizione']), "Iannone Felice")
                    
                    # --- SCUDO MATEMATICO ANTI-ERRORE ---
                    # Se le giornate extra inserite per sbaglio sono negative, le forza a 0
                    if gg_lavorati < 0:
                        gg_lavorati = 0.0
                        
                    dati_mensili[chiave_mese]['Extra Maturato (Debito)'] += gg_lavorati * 55.0

        # 3. Associazione Pagamenti (SEPARATA)
        pagamenti_df = df[df['categoria'].isin(['Busta Paga', 'Saldo Extra', 'Rimborsi'])]
        
        for index, row in pagamenti_df.iterrows():
            importo_pagato = row['importo']
            desc_str = str(row['descrizione'])
            cat = row['categoria']
            
            mese_trovato = False
            for chiave in dati_mensili.keys():
                if chiave in desc_str:
                    if cat == 'Saldo Extra' or cat == 'Rimborsi':
                        dati_mensili[chiave]['Extra Pagato'] += importo_pagato
                    elif cat == 'Busta Paga':
                        dati_mensili[chiave]['Busta Paga Versata'] += importo_pagato
                    mese_trovato = True
                    break
            
            if not mese_trovato:
                chiave_na = "Pagamenti Pregressi/Non Allocati"
                if chiave_na not in dati_mensili:
                    dati_mensili[chiave_na] = {'Extra Maturato (Debito)': 0.0, 'Extra Pagato': 0.0, 'Busta Paga Versata': 0.0}
                
                if cat == 'Saldo Extra' or cat == 'Rimborsi':
                    dati_mensili[chiave_na]['Extra Pagato'] += importo_pagato
                elif cat == 'Busta Paga':
                    dati_mensili[chiave_na]['Busta Paga Versata'] += importo_pagato

        # 4. Visualizzazione e Tabella Trasparente
        st.markdown("### 📊 Situazione Arretrati e Compensazione Lavoro")
        saldo_globale = 0.0
        
        if dati_mensili:
            def chiave_ordinamento(item):
                chiave = item[0]
                if chiave == "Pagamenti Pregressi/Non Allocati": return (0, 0)
                try:
                    mese_testo, anno_testo = chiave.split()
                    return (int(anno_testo), mesi_nomi_inv.get(mese_testo, 0))
                except:
                    return (9999, 99) 
                    
            dati_mensili = dict(sorted(dati_mensili.items(), key=chiave_ordinamento))
            df_riepilogo = pd.DataFrame.from_dict(dati_mensili, orient='index')
            
            # --- LA MATEMATICA E' STATA INVERTITA IN SOTTRAZIONE COME RICHIESTO ---
            df_riepilogo['Saldo Arretrati (Extra)'] = df_riepilogo['Extra Pagato'] - df_riepilogo['Extra Maturato (Debito)']
            df_riepilogo['Differenza (Busta - Extra)'] = df_riepilogo['Busta Paga Versata'] - df_riepilogo['Extra Maturato (Debito)']
            
            totale_maturato_ex = df_riepilogo['Extra Maturato (Debito)'].sum()
            totale_pagato_ex = df_riepilogo['Extra Pagato'].sum()
            saldo_globale = totale_pagato_ex - totale_maturato_ex
            
            df_display = df_riepilogo.copy()
            for col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: f"{x:,.2f} €")
                
            st.dataframe(df_display, use_container_width=True)
            
            # --- MOTORE DI DISEGNO DEL PDF AGGIORNATO ---
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, txt="Estratto Conto Lavoro - Iannone Felice", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            from datetime import datetime
            pdf.cell(190, 10, txt=f"Generato il: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
            pdf.ln(5)
            
            # Intestazioni PDF ridimensionate per far spazio alla parola "Differenza"
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(32, 10, "Mese", 1, 0, 'C')
            pdf.cell(28, 10, "Debito Ext", 1, 0, 'C')
            pdf.cell(28, 10, "Pagato Ext", 1, 0, 'C')
            pdf.cell(32, 10, "Busta Paga", 1, 0, 'C')
            pdf.cell(30, 10, "Arretrati", 1, 0, 'C')
            pdf.cell(40, 10, "Diff (Busta-Ext)", 1, 1, 'C')
            
            pdf.set_font("Arial", size=9)
            for mese, row in df_riepilogo.iterrows():
                m_str = str(mese)[:12]
                pdf.cell(32, 10, m_str, 1, 0, 'L')
                pdf.cell(28, 10, f"{row['Extra Maturato (Debito)']:,.2f} E", 1, 0, 'R')
                pdf.cell(28, 10, f"{row['Extra Pagato']:,.2f} E", 1, 0, 'R')
                pdf.cell(32, 10, f"{row['Busta Paga Versata']:,.2f} E", 1, 0, 'R')
                
                # Colore Arretrati (Rosso o Verde)
                pdf.set_text_color(220, 53, 69) if row['Saldo Arretrati (Extra)'] < 0 else pdf.set_text_color(40, 167, 69)
                pdf.cell(30, 10, f"{row['Saldo Arretrati (Extra)']:,.2f} E", 1, 0, 'R')
                pdf.set_text_color(0, 0, 0)
                
                # Inserimento della Differenza calcolata
                pdf.cell(40, 10, f"{row['Differenza (Busta - Extra)']:,.2f} E", 1, 1, 'R')
                
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 12)
            if saldo_globale < 0:
                pdf.set_text_color(220, 53, 69)
                pdf.cell(190, 10, txt=f"ATTENZIONE: Arretrati (Extra) da pagare per {abs(saldo_globale):,.2f} Euro", ln=True)
            else:
                pdf.set_text_color(40, 167, 69)
                pdf.cell(190, 10, txt=f"Situazione Extra regolare. Saldo finale: {saldo_globale:,.2f} Euro", ln=True)
                
            pdf.set_text_color(0, 0, 0)
            
            # --- PULSANTE PDF ---
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            st.download_button(
                label="📄 Scarica Tabella Aggiornata (PDF)",
                data=pdf_bytes,
                file_name=f'Conto_Lavoro_Iannone_{datetime.now().strftime("%Y_%m")}.pdf',
                mime='application/pdf',
                type="primary"
            )
            
            if saldo_globale < 0:
                st.error(f"⚠️ ATTENZIONE: Il dipendente risulta in credito (arretrati Extra) per: **{abs(saldo_globale):,.2f} €**")
            else:
                st.success(f"✅ Situazione Extra regolare. Saldo arretrati globale: **{saldo_globale:,.2f} €**")
        else:
            st.info("Nessun dato lavorativo o di pagamento registrato.")
            
        st.divider()
        
        # 5. Modulo di Pagamento Cassa CON AUTO-SALDATO
        with st.form("cassa_form", clear_on_submit=True):
            st.write("### ➕ Registra un pagamento al dipendente")
            
            c1, c2, c3 = st.columns([1, 1, 1.5])
            with c1:
                data_pag = st.date_input("Data del Bonifico/Contanti", format="DD/MM/YYYY")
            with c2:
                imp = st.number_input("Importo Erogato (€)", min_value=0.0, step=10.0, format="%.2f", value=float(abs(saldo_globale) if saldo_globale < 0 else 0.0))
            with c3:
                tipo_op = st.selectbox("Natura Operazione", ["Busta Paga", "Saldo Extra", "Rimborsi"])
                
                presenze_mesi = df[df['categoria'].isin(['Manodopera', 'Manodopera Extra'])]['data_dt'].dt.strftime('%B %Y').dropna().unique()
                import datetime
                mesi_tradotti = []
                for m in presenze_mesi:
                    for num, nome in mesi_nomi.items():
                        if m.startswith(datetime.datetime.strptime(str(num), "%m").strftime("%B")):
                            mesi_tradotti.append(f"{nome} {m.split(' ')[1]}")
                
                if not mesi_tradotti: mesi_tradotti = ["Nessun mese registrato (Versamento Generico)"]
                mese_rif = st.selectbox("Mese di Riferimento del Pagamento", set(mesi_tradotti))
            
            if st.form_submit_button("Registra Pagamento e Copri il Mese", type="primary"):
                if imp > 0:
                    data_f = data_pag.strftime('%Y-%m-%d')
                    descrizione_estesa = f"Pagamento Iannone Felice | {tipo_op} | Rif: {mese_rif}"
                    
                    nuova_riga = {
                        'data': data_f, 'tipo': "Uscita", 'categoria': tipo_op, 
                        'descrizione': descrizione_estesa, 'importo': float(imp), 
                        'prodotto': "Azienda", 'stato': "Saldato", 
                        'totale_fattura': float(imp), 'importo_pagato': float(imp), 
                        'registro_pagamenti': f"{data_f}|{imp}|Erogazione Diretta"
                    }
                    df = pd.concat([df, pd.DataFrame([nuova_riga])], ignore_index=True)
                    
                    # --- MAGIA AUTO-SALDATO ---
                    try:
                        if mese_rif != "Nessun mese registrato (Versamento Generico)":
                            nome_mese, anno_str = mese_rif.split()
                            m_num = mesi_nomi_inv[nome_mese]
                            y_num = int(anno_str)
                            
                            cat_target = "Manodopera" if tipo_op == "Busta Paga" else ("Manodopera Extra" if tipo_op == "Saldo Extra" else None)
                            
                            if cat_target:
                                df['data_temp'] = pd.to_datetime(df['data'], errors='coerce')
                                maschera = (df['categoria'] == cat_target) & (df['stato'] != 'Saldato') & (df['data_temp'].dt.month == m_num) & (df['data_temp'].dt.year == y_num)
                                df.loc[maschera, 'stato'] = 'Saldato'
                                df = df.drop(columns=['data_temp'])
                    except Exception:
                        pass
                    
                    if save_to_github(df, sha, f"Pagato: {imp}€ per {mese_rif} e aggiornato stato giornate"):
                        st.success(f"✅ Pagamento di {imp}€ registrato! Le giornate in Tab 1 sono state chiuse in automatico.")
                        import time
                        time.sleep(2)
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
        # ---> AGGIUNTA SALVAVITA: Forziamo la colonna importo in numeri puri
        df_pareggio['importo'] = pd.to_numeric(df_pareggio['importo'], errors='coerce').fillna(0.0)
        
        df_pareggio['data_dt'] = pd.to_datetime(df_pareggio['data'], errors='coerce')
        anni_disponibili = df_pareggio['data_dt'].dt.year.dropna().unique()
        
        if len(anni_disponibili) > 0:
            anno_sel = st.selectbox("📅 Basato sulle spese storiche dell'anno:", sorted(anni_disponibili, reverse=True), key="anno_target")
            
            # Ora questa somma matematica funzionerà perfettamente (Solo Uscite)
            uscite_totali = df_pareggio[(df_pareggio['data_dt'].dt.year == anno_sel) & (df_pareggio['tipo'] == 'Uscita')]['importo'].sum()
            
            col_fin, col_strat = st.columns([1, 1], gap="large")
            
            with col_fin:
                with st.container(border=True):
                    st.subheader("💶 1. Fabbisogno Economico")
                    st.metric("🔴 Spese Vive (dal database)", format_euro(uscite_totali))
                    
                    utile_desiderato = st.number_input("🟢 Tuo Obiettivo di Guadagno Annuo (€)", min_value=0.0, step=1000.0, value=24000.0)
                    fabbisogno_totale = uscite_totali + utile_desiderato
                    
                    st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; margin-top: 15px; border-left: 5px solid #0f52ba;">
                        <p style="margin: 0; font-size: 14px; color: #555; text-transform: uppercase;">Obiettivo Finanziario Totale</p>
                        <h2 style="margin: 0; color: #0f52ba; font-size: 32px;">{format_euro(fabbisogno_totale)}</h2>
                    </div>
                    """, unsafe_allow_html=True)

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
                        resa_stimata = 1.0
            
            st.write("")
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
                            
                    else:
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
# --- TAB 5: BILANCIO (SCHEMA CEE COMPARATO N vs N-1) ---
# ==========================================
with tab5:
    st.header("⚖️ Conto Economico CEE Comparato")
    st.markdown("Riclassificazione civilistica (Art. 2425 c.c.) con affiancamento automatico dell'anno precedente.")

    df_bilancio, _ = get_github_file()
    
    if not df_bilancio.empty:
        # ---> AGGIUNTA SALVAVITA: Forziamo la colonna importo in numeri puri anche nel Bilancio
        df_bilancio['importo'] = pd.to_numeric(df_bilancio['importo'], errors='coerce').fillna(0.0)
        
        df_bilancio['data_dt'] = pd.to_datetime(df_bilancio['data'], errors='coerce')
        df_bilancio = df_bilancio.dropna(subset=['data_dt'])
        anni_disponibili = sorted(df_bilancio['data_dt'].dt.year.unique(), reverse=True)
        
        if len(anni_disponibili) > 0:
            anno_sel = st.selectbox("Seleziona Esercizio Fiscale (N):", anni_disponibili, key="bilancio_anno")
            anno_prec = anno_sel - 1
            
            def classifica_cee(row):
                cat = str(row['categoria']).upper()
                tipo = row['tipo']
                if tipo == 'Entrata':
                    if 'CONTRIBUT' in cat or 'AGEA' in cat or 'PAC' in cat: return "A.5 - Altri ricavi e proventi (Contributi)"
                    else: return "A.1 - Ricavi delle vendite e prestazioni"
                elif tipo == 'Uscita':
                    if 'MANODOPERA' in cat or 'BUSTA' in cat or 'SALDO' in cat: return "B.9 - Costi per il personale"
                    elif 'ATTREZZATUR' in cat or 'AMMORTAMENT' in cat or 'MACCHINARI' in cat: return "B.10 - Ammortamenti e svalutazioni"
                    elif 'SERVIZ' in cat or 'FRANTOIO' in cat or 'MOLITURA' in cat or 'TERZI' in cat or 'CONSULENZ' in cat: return "B.7 - Costi per servizi"
                    elif 'CONCIM' in cat or 'MATERI' in cat or 'PIANTIN' in cat or 'CARBURANT' in cat or 'GASOLIO' in cat: return "B.6 - Per materie prime, sussidiarie, di consumo"
                    elif 'AFFITT' in cat or 'LEASING' in cat: return "B.8 - Per godimento di beni di terzi"
                    else: return "B.14 - Oneri diversi di gestione"
                return "Non Classificato"

            df_bilancio['voce_cee'] = df_bilancio.apply(classifica_cee, axis=1)

            df_n = df_bilancio[df_bilancio['data_dt'].dt.year == anno_sel]
            entrate_n = df_n[df_n['tipo'] == 'Entrata'].groupby('voce_cee')['importo'].sum()
            uscite_n = df_n[df_n['tipo'] == 'Uscita'].groupby('voce_cee')['importo'].sum()
            
            df_n1 = df_bilancio[df_bilancio['data_dt'].dt.year == anno_prec]
            entrate_n1 = df_n1[df_n1['tipo'] == 'Entrata'].groupby('voce_cee')['importo'].sum()
            uscite_n1 = df_n1[df_n1['tipo'] == 'Uscita'].groupby('voce_cee')['importo'].sum()

            voci_a = sorted(list(set(entrate_n.index).union(set(entrate_n1.index))))
            voci_b = sorted(list(set(uscite_n.index).union(set(uscite_n1.index))))

            tot_a_n, tot_a_n1 = entrate_n.sum(), entrate_n1.sum()
            tot_b_n, tot_b_n1 = uscite_n.sum(), uscite_n1.sum()
            ris_operativo_n = tot_a_n - tot_b_n
            ris_operativo_n1 = tot_a_n1 - tot_b_n1

            mappatura_categorie = {
                "A.1 - Ricavi delle vendite e prestazioni": "Vendita Olio, Vendita Olive, ecc.",
                "A.5 - Altri ricavi e proventi (Contributi)": "Contributi AGEA, PAC, ecc.",
                "B.6 - Per materie prime, sussidiarie, di consumo": "Gasolio, Concimi, Piantine, Materie varie",
                "B.7 - Costi per servizi": "Frantoio, Molitura, Consulenze, Lavori conto terzi",
                "B.8 - Per godimento di beni di terzi": "Affitti terreni, Leasing",
                "B.9 - Costi per il personale": "Manodopera, Buste Paga",
                "B.10 - Ammortamenti e svalutazioni": "Attrezzature, Macchinari",
                "B.14 - Oneri diversi di gestione": "Tutte le altre uscite non classificate"
            }

            sub_bil1, sub_bil2 = st.tabs(["💻 Visualizzazione Interattiva (N vs N-1)", "🖨️ Documento Stampabile (PDF Comparato)"])

            with sub_bil1:
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.subheader(f"🟢 A) VALORE PRODUZIONE")
                    for v in voci_a:
                        val_n = entrate_n.get(v, 0.0)
                        val_n1 = entrate_n1.get(v, 0.0)
                        spiegazione = mappatura_categorie.get(v, "")
                        
                        st.markdown(f"**{v}**")
                        if spiegazione:
                            st.markdown(f"<p style='color: gray; font-size: 12px; margin-top: -15px; margin-bottom: 5px;'>Da DB: {spiegazione}</p>", unsafe_allow_html=True)
                        
                        c1, c2 = st.columns(2)
                        c1.metric(f"Anno {anno_sel}", format_euro(val_n))
                        c2.metric(f"Anno {anno_prec}", format_euro(val_n1), delta=f"{val_n - val_n1:.2f} €", delta_color="normal")
                    st.divider()
                    st.markdown(f"<h4 style='color: #1b5e20;'>TOTALE A ({anno_sel}): {format_euro(tot_a_n)}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color: gray;'>TOTALE A ({anno_prec}): {format_euro(tot_a_n1)}</p>", unsafe_allow_html=True)

                with col_b:
                    st.subheader(f"🔴 B) COSTI PRODUZIONE")
                    for v in voci_b:
                        val_n = uscite_n.get(v, 0.0)
                        val_n1 = uscite_n1.get(v, 0.0)
                        spiegazione = mappatura_categorie.get(v, "")
                        
                        st.markdown(f"**{v}**")
                        if spiegazione:
                            st.markdown(f"<p style='color: gray; font-size: 12px; margin-top: -15px; margin-bottom: 5px;'>Da DB: {spiegazione}</p>", unsafe_allow_html=True)
                            
                        c1, c2 = st.columns(2)
                        c1.metric(f"Anno {anno_sel}", format_euro(val_n))
                        c2.metric(f"Anno {anno_prec}", format_euro(val_n1), delta=f"{val_n - val_n1:.2f} €", delta_color="inverse")
                    st.divider()
                    st.markdown(f"<h4 style='color: #b71c1c;'>TOTALE B ({anno_sel}): {format_euro(tot_b_n)}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color: gray;'>TOTALE B ({anno_prec}): {format_euro(tot_b_n1)}</p>", unsafe_allow_html=True)

                st.divider()
                st.subheader("⚖️ RISULTATO D'ESERCIZIO")
                c_ris1, c_ris2, c_ris3 = st.columns(3)
                c_ris1.metric(f"Utile/Perdita {anno_prec}", format_euro(ris_operativo_n1))
                c_ris2.metric(f"Utile/Perdita {anno_sel}", format_euro(ris_operativo_n), delta=f"{ris_operativo_n - ris_operativo_n1:.2f} €")

            with sub_bil2:
                html_righe_a = ""
                for v in voci_a:
                    html_righe_a += f"<tr><td>{v}</td><td class='right bold'>{format_euro(entrate_n.get(v, 0.0))}</td><td class='right' style='color: #555;'>{format_euro(entrate_n1.get(v, 0.0))}</td></tr>"
                
                html_righe_b = ""
                for v in voci_b:
                    html_righe_b += f"<tr><td>{v}</td><td class='right bold'>{format_euro(uscite_n.get(v, 0.0))}</td><td class='right' style='color: #555;'>{format_euro(uscite_n1.get(v, 0.0))}</td></tr>"

                colore_ris = "#1b5e20" if ris_operativo_n >= 0 else "#b71c1c"

                html_bilancio_comparato = f"""
                <html>
                <head>
                <style>
                    body {{ font-family: 'Arial', sans-serif; background-color: #f4f4f9; padding: 20px; }}
                    .foglio-a4 {{ background-color: white; color: black; padding: 40px; max-width: 800px; margin: auto; box-shadow: 0 0 15px rgba(0,0,0,0.2); }}
                    h2, h3, h4 {{ text-align: center; margin: 5px 0; }}
                    .header-doc {{ border-bottom: 2px solid black; padding-bottom: 15px; margin-bottom: 25px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; page-break-inside: avoid; }}
                    th, td {{ border: 1px solid #000; padding: 8px; text-align: left; }}
                    th {{ background-color: #e9e9e9; font-weight: bold; text-align: center; }}
                    .right {{ text-align: right; }}
                    .bold {{ font-weight: bold; }}
                    .totale-riga td {{ background-color: #e9e9e9; font-weight: bold; }}
                    .totale-box {{ margin-top: 30px; border: 2px solid black; padding: 15px; page-break-inside: avoid; }}
                    .box-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }}
                    @media print {{
                        body {{ background-color: white; padding: 0; }}
                        .foglio-a4 {{ box-shadow: none; max-width: 100%; padding: 0; margin: 0; }}
                        button {{ display: none; }}
                    }}
                </style>
                </head>
                <body>
                    <div style="text-align: center; margin-bottom: 20px;">
                        <button onclick="window.print()" style="padding: 12px 24px; font-size: 16px; cursor: pointer; background-color: #1565c0; color: white; border: none; border-radius: 5px; font-weight: bold;">🖨️ Stampa Bilancio Comparato PDF</button>
                    </div>
                    <div class="foglio-a4">
                        <div class="header-doc">
                            <h2>AZIENDA AGRICOLA ANTONELLO MAZZILLI</h2>
                            <h4>Produzione Olio ed Esercizio Agricolo</h4>
                            <h3>CONTO ECONOMICO COMPARATO: ESERCIZIO {anno_sel} vs {anno_prec}</h3>
                            <p style="text-align:center; font-size: 12px;">Redatto in conformità all'Art. 2425 c.c. (Schema IV Direttiva CEE)</p>
                        </div>
                        
                        <h4 style="text-align: left;">A) VALORE DELLA PRODUZIONE</h4>
                        <table>
                            <tr><th>Voce Bilancio</th><th style="width: 20%;">Anno {anno_sel}</th><th style="width: 20%;">Anno {anno_prec}</th></tr>
                            {html_righe_a if html_righe_a else "<tr><td colspan='3'>Nessun dato presente</td></tr>"}
                            <tr class="totale-riga"><td>TOTALE A</td><td class="right">{format_euro(tot_a_n)}</td><td class="right">{format_euro(tot_a_n1)}</td></tr>
                        </table>

                        <br>
                        <h4 style="text-align: left;">B) COSTI DELLA PRODUZIONE</h4>
                        <table>
                            <tr><th>Voce Bilancio</th><th style="width: 20%;">Anno {anno_sel}</th><th style="width: 20%;">Anno {anno_prec}</th></tr>
                            {html_righe_b if html_righe_b else "<tr><td colspan='3'>Nessun dato presente</td></tr>"}
                            <tr class="totale-riga"><td>TOTALE B</td><td class="right">{format_euro(tot_b_n)}</td><td class="right">{format_euro(tot_b_n1)}</td></tr>
                        </table>

                        <div class="totale-box">
                            <h3 style="text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 10px;">DIFFERENZA TRA VALORE E COSTI DELLA PRODUZIONE (A - B)</h3>
                            <div class="box-row">
                                <span style="font-size: 18px;">Risultato d'Esercizio {anno_prec}:</span>
                                <span style="font-size: 18px; color: #555;">{format_euro(ris_operativo_n1)}</span>
                            </div>
                            <div class="box-row">
                                <span style="font-size: 22px; font-weight: bold;">Risultato d'Esercizio {anno_sel}:</span>
                                <span style="font-size: 24px; font-weight: bold; color: {colore_ris};">{format_euro(ris_operativo_n)}</span>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                import streamlit.components.v1 as components
                components.html(html_bilancio_comparato, height=900, scrolling=True)
                
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
                
                data_formattata = fat_data.strftime('%Y-%m-%d')
                descrizione_completa = f"{fat_soggetto.strip()} | {fat_descrizione.strip()}"
                stato_db = "Saldato" if "Saldato" in fat_stato else "Impegnato"
                
               # 1. Calcoliamo i valori per le nuove colonne ERP (Rate)
                totale_fat = fat_importo
                imp_pagato = fat_importo if stato_db == "Saldato" else 0.0
                storico_iniziale = f"{data_formattata}|{fat_importo}|Registrazione iniziale" if stato_db == "Saldato" else ""

                # 2. Creiamo la riga come DIZIONARIO (Metodo Infallibile)
                nuova_riga = {
                    'data': data_formattata,
                    'tipo': tipo_db,
                    'categoria': fat_categoria,
                    'descrizione': descrizione_completa,
                    'importo': fat_importo,
                    'prodotto': "",
                    'stato': stato_db,
                    'totale_fattura': totale_fat,
                    'importo_pagato': imp_pagato,
                    'registro_pagamenti': storico_iniziale
                }

                # 3. Salvataggio intelligente (Senza più contare le colonne!)
                df = pd.concat([df, pd.DataFrame([nuova_riga])], ignore_index=True)
                
                if save_to_github(df, sha, f"Registrata Fattura: {fat_soggetto}"): 
                    st.success("✅ Operazione registrata con successo!")
                    time.sleep(2)
                    st.rerun()
            else:
                st.warning("⚠️ Compila almeno Fornitore/Cliente e assicurati che l'importo sia maggiore di zero.")
