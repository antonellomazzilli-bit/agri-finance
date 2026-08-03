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
                if save_to_github(df, sha, "Aggiornamento Manodopera (6h)"):
                    st.success("✅ Giornate lavorative registrate!")
                    time.sleep(1)
                    st.rerun()
            # ==========================================
        # --- SEZIONE: STAMPA E REPORT PRESENZE ---
        # ==========================================
        st.divider()
        st.subheader("🖨️ Stampa Riepilogo Presenze (Annuale e Mensile)")
        
        # 1. Filtri di ricerca
        c_filtro1, c_filtro2 = st.columns(2)
        with c_filtro1:
            sel_dipendente = st.selectbox("Seleziona Dipendente per il Report", ["Iannone Felice"])
        
        # Estraiamo gli anni disponibili dal database per il filtro
        df_lavoro = df[df['categoria'].isin(['Manodopera', 'Manodopera Extra'])].copy()
        df_lavoro['data_dt'] = pd.to_datetime(df_lavoro['data'], errors='coerce')
        df_lavoro = df_lavoro.dropna(subset=['data_dt'])
        
        anni_disp = df_lavoro['data_dt'].dt.year.unique().tolist()
        if not anni_disp:
            anni_disp = [datetime.now().year]
            
        with c_filtro2:
            sel_anno = st.selectbox("Seleziona Anno di Riferimento", sorted(anni_disp, reverse=True))

        if st.button("Genera Report Dettagliato", type="primary"):
            # 2. Motore di Estrazione Dati
            df_anno = df_lavoro[df_lavoro['data_dt'].dt.year == sel_anno]
            dati_puliti = []
            
            for idx, row in df_anno.iterrows():
                desc = str(row['descrizione'])
                if sel_dipendente in desc:
                    # Smontiamo la stringa per estrarre le giornate pure
                    parti = desc.split("|")
                    if len(parti) >= 2:
                        try:
                            giornate = float(parti[1].replace("gg", "").strip())
                            tipo = "Ufficiale" if "UFFICIALE:" in desc else ("Extra" if "EXTRA:" in desc else "Altro")
                            note = desc.split(":", 1)[1].strip() if ":" in desc else ""
                            
                            dati_puliti.append({
                                'Data': row['data_dt'],
                                'Mese_Num': row['data_dt'].month,
                                'Giornate': giornate,
                                'Tipo': tipo,
                                'Note': note
                            })
                        except:
                            pass
                            
            # 3. Impaginazione e Visualizzazione
            if not dati_puliti:
                st.warning(f"Nessuna presenza trovata per {sel_dipendente} nell'anno {sel_anno}.")
            else:
                df_report = pd.DataFrame(dati_puliti)
                
                # Calcolo Totali Annuali
                tot_uff = df_report[df_report['Tipo'] == 'Ufficiale']['Giornate'].sum()
                tot_ext = df_report[df_report['Tipo'] == 'Extra']['Giornate'].sum()
                
                st.success(f"### 🏆 Riepilogo Globale {sel_anno} - {sel_dipendente}\n"
                           f"**Totale Giornate Ufficiali:** {tot_uff:.2f} gg | **Totale Giornate Extra:** {tot_ext:.2f} gg")
                
                # Scomposizione Mese per Mese
                mesi_nomi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 
                             7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
                
                # Ciclo che crea una tabella per ogni mese lavorato
                for mese in sorted(df_report['Mese_Num'].unique()):
                    df_mese = df_report[df_report['Mese_Num'] == mese].sort_values(by='Data')
                    
                    mese_uff = df_mese[df_mese['Tipo'] == 'Ufficiale']['Giornate'].sum()
                    mese_ext = df_mese[df_mese['Tipo'] == 'Extra']['Giornate'].sum()
                    
                    # Intestazione del singolo mese
                    st.markdown(f"#### 📅 {mesi_nomi[mese]} {sel_anno} *(Ufficiali: {mese_uff:.2f} gg - Extra: {mese_ext:.2f} gg)*")
                    
                    # Preparazione estetica della tabella
                    df_display = df_mese[['Data', 'Tipo', 'Giornate', 'Note']].copy()
                    df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')
                    
                    # Mostra a schermo (con possibilità di download nativo)
                    st.dataframe(df_display, use_container_width=True, hide_index=True)

# ==========================================
# --- TAB 3: CASSA E CONTROLLO MESI ARRETRATI ---
# ==========================================
with tab3:
    st.subheader("💸 Cassa e Estratto Conto Mensile (Euro)")
    df, sha = get_github_file()
    
    if not df.empty:
        # 1. Blindatura numerica e conversione date
        df['importo'] = pd.to_numeric(df['importo'], errors='coerce').fillna(0.0)
        df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
        
        # 2. MOTORE DI CALCOLO DELLE PENDENZE MENSILI
        # Creiamo un dizionario per raccogliere i dati mese per mese
        dati_mensili = {}
        mesi_nomi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
        
        # Fase A: Raccogliamo tutto il lavoro effettuato (Tab 2)
        lavoro_df = df[df['categoria'].isin(['Manodopera', 'Manodopera Extra'])]
        for index, row in lavoro_df.iterrows():
            if pd.notna(row['data_dt']):
                mese_num = row['data_dt'].month
                anno_num = row['data_dt'].year
                chiave_mese = f"{mesi_nomi[mese_num]} {anno_num}"
                
                gg_lavorati = estrai_giornate(str(row['descrizione']), "Iannone Felice")
                valore_maturato = gg_lavorati * COSTO_GIORNATA_EXTRA
                
                if chiave_mese not in dati_mensili:
                    dati_mensili[chiave_mese] = {'Maturato': 0.0, 'Pagato': 0.0}
                dati_mensili[chiave_mese]['Maturato'] += valore_maturato

        # Fase B: Raccogliamo tutti i pagamenti effettuati (Tab 3) e li associamo al mese
        # N.B. D'ora in poi cerchiamo il mese nella descrizione del pagamento
        cat_pagamenti = ['Busta Paga', 'Saldo Extra', 'Rimborsi']
        pagamenti_df = df[df['categoria'].isin(cat_pagamenti)]
        
        for index, row in pagamenti_df.iterrows():
            importo_pagato = row['importo']
            descrizione = str(row['descrizione'])
            
            # Cerchiamo se c'è un "Mese Riferimento:" nella descrizione
            mese_trovato = False
            for chiave in dati_mensili.keys():
                if chiave in descrizione:
                    dati_mensili[chiave]['Pagato'] += importo_pagato
                    mese_trovato = True
                    break
            
            # Se è un pagamento vecchio (senza mese esplicito), lo mettiamo in un calderone generico
            if not mese_trovato:
                if "Pagamenti Pregressi/Non Allocati" not in dati_mensili:
                    dati_mensili["Pagamenti Pregressi/Non Allocati"] = {'Maturato': 0.0, 'Pagato': 0.0}
                dati_mensili["Pagamenti Pregressi/Non Allocati"]['Pagato'] += importo_pagato

       # 3. VISUALIZZAZIONE DELLE PENDENZE
        st.markdown("### 📊 Situazione Arretrati e Saldi per Mese")
        
        # MOTORE DI ORDINAMENTO CRONOLOGICO
        mesi_ordine = {'Gennaio': 1, 'Febbraio': 2, 'Marzo': 3, 'Aprile': 4, 'Maggio': 5, 'Giugno': 6, 'Luglio': 7, 'Agosto': 8, 'Settembre': 9, 'Ottobre': 10, 'Novembre': 11, 'Dicembre': 12}
        
        def ordina_mesi(chiave):
            if chiave == "Pagamenti Pregressi/Non Allocati":
                return (0, 0) # Mettiamo le voci non assegnate sempre in cima
            try:
                mese, anno = chiave.split()
                return (int(anno), mesi_ordine.get(mese, 0))
            except:
                return (9999, 99) # In caso di stringhe anomale le mette in fondo

        # Trasformiamo il dizionario in una tabella per la visualizzazione
        if dati_mensili:
            # Riordiniamo i dati matematicamente prima di mostrarli
            dati_mensili = dict(sorted(dati_mensili.items(), key=lambda item: ordina_mesi(item[0])))
            
            df_riepilogo = pd.DataFrame.from_dict(dati_mensili, orient='index')
            df_riepilogo['Stato Mensile'] = df_riepilogo['Pagato'] - df_riepilogo['Maturato']
            
            # Formattazione per la lettura
            df_display = df_riepilogo.copy()
            for col in df_display.columns:
                df_display[col] = df_display[col].apply(format_euro)
                
            st.dataframe(df_display, use_container_width=True)
            
            # Calcolo del totale Globale
            totale_maturato = df_riepilogo['Maturato'].sum()
            totale_pagato = df_riepilogo['Pagato'].sum()
            saldo_globale = totale_pagato - totale_maturato
            
            if saldo_globale < 0:
                st.error(f"⚠️ ATTENZIONE: Il dipendente risulta in credito totale (arretrati) per: **{format_euro(abs(saldo_globale))}**")
            else:
                st.success(f"✅ Situazione regolare. Saldo globale: **{format_euro(saldo_globale)}**")
        else:
            st.info("Nessun dato lavorativo o di pagamento registrato.")
            saldo_globale = 0.0
            
        st.divider()
        
        # 4. IL NUOVO FORM DI PAGAMENTO (Con ripartizione a cascata)
        with st.form("cassa_form", clear_on_submit=True):
             st.write("### ➕ Registra un pagamento al dipendente")
            
             c1, c2 = st.columns(2)
             with c1:
                data_pag = st.date_input("Data del Bonifico/Contanti", format="DD/MM/YYYY")
                tipo_op = st.selectbox("Natura Operazione", ["Busta Paga", "Saldo Extra", "Rimborsi"])
             with c2:
                # L'importo suggerito è già il totale degli arretrati globale
                importo_consigliato = abs(saldo_globale) if saldo_globale < 0 else 0.0
                imp = st.number_input("Importo Totale Erogato (€)", min_value=0.0, step=10.0, format="%.2f", value=importo_consigliato)
                
                # La checkbox "magica" (già attiva di default)
                st.markdown("<br>", unsafe_allow_html=True)
                saldo_automatico = st.checkbox("🪄 Spalma in automatico sui mesi scoperti", value=True)
            
            # Lista dei mesi per la modalità manuale
             mesi_da_pagare = []
             for mese, dati_mese in dati_mensili.items():
                if mese != "Pagamenti Pregressi/Non Allocati":
                    if (dati_mese['Maturato'] - dati_mese['Pagato']) > 0.01:
                        mesi_da_pagare.append(mese)
             if not mesi_da_pagare:
                mesi_da_pagare = ["Nessun arretrato"]
                
             mese_rif = st.selectbox("📌 Mese specifico (usato SOLO se togli la spunta sopra):", mesi_da_pagare)
            
             if st.form_submit_button("Registra Pagamento", type="primary"):
                if imp > 0:
                    data_f = data_pag.strftime('%Y-%m-%d')
                    righe_nuove = []
                    
                    if saldo_automatico:
                        importo_rimanente = float(imp)
                        
                        # Cicliamo i mesi in ordine cronologico
                        for mese, dati_mese in dati_mensili.items():
                            if mese != "Pagamenti Pregressi/Non Allocati" and importo_rimanente > 0:
                                debito_mese = dati_mese['Maturato'] - dati_mese['Pagato']
                                
                                if debito_mese > 0.01:
                                    # Diamo a questo mese il minimo tra quello che gli spetta e i soldi rimasti
                                    pagamento_mese = min(debito_mese, importo_rimanente)
                                    
                                    righe_nuove.append({
                                        'data': data_f, 'tipo': "Uscita", 'categoria': tipo_op, 
                                        'descrizione': f"Pagamento Iannone Felice | {tipo_op} | Rif: {mese}", 
                                        'importo': float(pagamento_mese), 'prodotto': "Azienda", 'stato': "Saldato", 
                                        'totale_fattura': float(pagamento_mese), 'importo_pagato': float(pagamento_mese), 
                                        'registro_pagamenti': f"{data_f}|{pagamento_mese}|Erogazione Diretta"
                                    })
                                    importo_rimanente -= pagamento_mese
                        
                        # Se ha pagato di più del debito totale, l'eccesso diventa un Anticipo
                        if importo_rimanente > 0.01:
                            righe_nuove.append({
                                'data': data_f, 'tipo': "Uscita", 'categoria': tipo_op, 
                                'descrizione': f"Pagamento Iannone Felice | {tipo_op} | Rif: Anticipo/Extra", 
                                'importo': float(importo_rimanente), 'prodotto': "Azienda", 'stato': "Saldato", 
                                'totale_fattura': float(importo_rimanente), 'importo_pagato': float(importo_rimanente), 
                                'registro_pagamenti': f"{data_f}|{importo_rimanente}|Erogazione Diretta"
                            })
                    else:
                        # Modalità manuale classica
                        righe_nuove.append({
                            'data': data_f, 'tipo': "Uscita", 'categoria': tipo_op, 
                            'descrizione': f"Pagamento Iannone Felice | {tipo_op} | Rif: {mese_rif}", 
                            'importo': float(imp), 'prodotto': "Azienda", 'stato': "Saldato", 
                            'totale_fattura': float(imp), 'importo_pagato': float(imp), 
                            'registro_pagamenti': f"{data_f}|{imp}|Erogazione Diretta"
                        })
                    
                    if righe_nuove:
                        df_nuove = pd.DataFrame(righe_nuove)
                        df = pd.concat([df, df_nuove], ignore_index=True)
                        if save_to_github(df, sha, f"Pagamento dipendente distribuito: {imp}€"):
                            st.success(f"✅ Pagamento di {format_euro(imp)} registrato con successo!")
                            time.sleep(1.5)
                            st.rerun()
                else:
                    st.warning("L'importo deve essere maggiore di zero.")

# ==========================================
# --- TAB 4: STAMPE E REPORT DIPENDENTI ---
# ==========================================
with tab4:
    st.subheader("🖨️ Stampa Foglio Presenze Dipendente")
    st.markdown("Seleziona il mese e l'anno per generare il riepilogo delle giornate lavorate.")
    
    df, _ = get_github_file()
    
    if not df.empty:
        # Assicuriamoci che le date siano leggibili
        df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
        df_valido = df.dropna(subset=['data_dt'])
        
        if not df_valido.empty:
            # Layout filtri in cima
            c1, c2, c3 = st.columns(3)
            with c1:
                dipendente_sel = st.selectbox("👤 Dipendente", ["Iannone Felice"])
            with c2:
                # Estrae i mesi e anni disponibili dal database per evitare selezioni vuote
                mesi_disp = sorted(df_valido['data_dt'].dt.month.unique())
                mese_sel = st.selectbox("📅 Mese", mesi_disp, index=len(mesi_disp)-1 if mesi_disp else 0)
            with c3:
                anni_disp = sorted(df_valido['data_dt'].dt.year.unique(), reverse=True)
                anno_sel = st.selectbox("📆 Anno", anni_disp)
                
            st.divider()
            
            # Filtriamo il database in base alle scelte dell'utente
            df_filtrato = df_valido[
                (df_valido['categoria'].isin(['Manodopera', 'Manodopera Extra'])) & 
                (df_valido['data_dt'].dt.month == mese_sel) & 
                (df_valido['data_dt'].dt.year == anno_sel) &
                (df_valido['descrizione'].str.contains(dipendente_sel, na=False))
            ].sort_values(by='data_dt') # Ordina dalla data più vecchia alla più recente
            
            if not df_filtrato.empty:
                st.markdown(f"### 📋 Riepilogo: {dipendente_sel} - Mese {mese_sel}/{anno_sel}")
                
                dettaglio_righe = []
                tot_ufficiali = 0.0
                tot_extra = 0.0
                
                # Analizziamo riga per riga per estrarre il valore esatto
                for _, row in df_filtrato.iterrows():
                    data_str = row['data_dt'].strftime('%d/%m/%Y')
                    cat = row['categoria']
                    desc = str(row['descrizione'])
                    
                    # Blindatura anti-errore: cerchiamo di estrarre le giornate dal testo
                    try:
                        parti = desc.split('|')
                        gg_str = parti[1].replace('gg', '').strip()
                        gg = float(gg_str)
                        note = parti[2].strip() if len(parti) > 2 else "Nessuna nota"
                    except:
                        gg = 0.0
                        note = f"⚠️ Errore lettura: {desc}"
                        
                    # Smistamento tra ufficiali ed extra
                    if "Extra" in cat:
                        tot_extra += gg
                        tipo_gg = "🔴 Extra"
                    else:
                        tot_ufficiali += gg
                        tipo_gg = "🟢 Ufficiale"
                        
                    dettaglio_righe.append({
                        "Data": data_str,
                        "Tipologia": tipo_gg,
                        "Giornate": gg,
                        "Note / Dettaglio": note
                    })
                    
                # Mostriamo la tabella a schermo
                df_stampa = pd.DataFrame(dettaglio_righe)
                st.dataframe(df_stampa, use_container_width=True, hide_index=True)
                
                # BOX RIASSUNTIVO FINALE
                st.markdown("---")
                c_tot1, c_tot2, c_tot3 = st.columns(3)
                c_tot1.metric(label="Giornate UFFICIALI", value=f"{tot_ufficiali:.3f}")
                c_tot2.metric(label="Giornate EXTRA", value=f"{tot_extra:.3f}")
                c_tot3.metric(label="TOTALE GENERALE", value=f"{tot_ufficiali + tot_extra:.3f} gg")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Funzione per convertire il file per il download
                @st.cache_data
                def convert_df_to_csv(df):
                    # Formattato per aprirsi perfettamente in Excel in italiano
                    return df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                    
                csv_data = convert_df_to_csv(df_stampa)
                
                c_btn1, c_btn2 = st.columns([1, 2])
                with c_btn1:
                    st.download_button(
                        label="📥 Scarica in Excel (CSV)",
                        data=csv_data,
                        file_name=f"Presenze_{dipendente_sel.replace(' ', '_')}_{mese_sel}_{anno_sel}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                with c_btn2:
                    st.info("💡 **Vuoi stamparlo su carta?** Usa la scorciatoia da tastiera **Ctrl + P** (o Cmd + P) per stampare direttamente questa schermata pulita.")
                    
            else:
                st.warning(f"Nessuna giornata registrata per {dipendente_sel} nel mese {mese_sel}/{anno_sel}.")
        else:
            st.warning("Il database non contiene date valide.")


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
