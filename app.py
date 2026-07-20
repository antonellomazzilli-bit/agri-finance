import streamlit as st
import pandas as pd
from datetime import datetime
import os
# Assicurati di avere installato le librerie necessarie (github, ecc. se le usavi prima)

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AgriFinance Cloud", layout="wide")
COSTO_GIORNATA_EXTRA = 55.0

# --- FUNZIONI DI SISTEMA (GitHub & Helpers) ---
# Queste sono le funzioni che mancavano e che fanno parlare l'app con il cloud
def get_github_file():
    # Inserisci qui il tuo codice esistente per leggere da GitHub
    # Se hai dei token o configurazioni specifiche, devono stare qui
    # Esempio semplificato:
    try:
        return pd.read_csv("database.csv"), "sha_mock" 
    except:
        return pd.DataFrame(columns=['data', 'tipo', 'categoria', 'descrizione', 'importo', 'prodotto', 'stato']), "new"

def save_to_github(df, sha, message):
    # Inserisci qui il tuo codice esistente per salvare su GitHub
    df.to_csv("database.csv", index=False)
    return True

def format_euro(valore):
    return f"€ {valore:,.2f}"

def estrai_giornate(descrizione, dipendente):
    try:
        if dipendente in descrizione:
            parti = descrizione.split('|')
            for p in parti:
                if 'gg' in p:
                    return float(p.replace('gg', '').strip())
        return 0.0
    except: return 0.0

# --- INTERFACCIA PRINCIPALE ---
st.title("AgriFinance Cloud")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Home", "Manodopera", "Cassa", "Rese", "Bilancio", "Fatture"])

# --- TAB 1: HOME E REGISTRO GENERALE MODIFICABILE ---
with tab1:
    st.header("🏠 Registro Generale (Editor Diviso)")
    st.markdown("💡 Le operazioni sono separate. Fai doppio clic sulle celle per modificare e premi Canc per eliminare una riga.")
    
    df, sha = get_github_file()
    
    if not df.empty:
        # 1. Preparazione della Data come Oggetto Calendario
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df = df.sort_values(by='data', ascending=False)

        # 2. Separazione chirurgica dei dati
        # Creiamo due dataframe separati in base alla colonna "tipo"
        df_entrate = df[df['tipo'] == 'Entrata'].reset_index(drop=True)
        df_uscite = df[df['tipo'] == 'Uscita'].reset_index(drop=True)
        
        # Paracadute: salviamo in memoria eventuali righe anomale per non perderle
        df_altri = df[(df['tipo'] != 'Entrata') & (df['tipo'] != 'Uscita')].reset_index(drop=True)

        # 3. Creazione delle Colonne Visive
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🟢 Entrate")
            df_entrate_mod = st.data_editor(
                df_entrate, 
                column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY")},
                num_rows="dynamic", 
                use_container_width=True, 
                key="editor_entrate"
            )

        with col2:
            st.subheader("🔴 Uscite")
            df_uscite_mod = st.data_editor(
                df_uscite, 
                column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY")},
                num_rows="dynamic", 
                use_container_width=True, 
                key="editor_uscite"
            )
            
        st.divider()
        
        # 4. Pulsante di Salvataggio e Fusione dei Dati
        if st.button("💾 SALVA MODIFICHE NEL DATABASE", type="primary", use_container_width=True):
            
            # Ricuciamo le tabelle modificate insieme al paracadute delle righe anomale
            df_modificato = pd.concat([df_entrate_mod, df_uscite_mod, df_altri], ignore_index=True)
            
            # Formattiamo e riordiniamo per il salvataggio sicuro
            df_modificato['data'] = pd.to_datetime(df_modificato['data'], errors='coerce')
            df_modificato = df_modificato.sort_values(by='data', ascending=False).reset_index(drop=True)
            df_modificato['data'] = df_modificato['data'].dt.strftime('%Y-%m-%d')
            
            if save_to_github(df_modificato, sha, "Modifica da Editor Diviso (Tab 1)"):
                st.success("✅ Modifiche salvate con successo!")
                st.rerun()
    else:
        st.info("Nessun dato registrato al momento.")
        
# --- TAB 2: MANODOPERA (6h Day) ---
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
            if op_ufficiali > 0:
                desc_uff = f"{op_nome} | {op_ufficiali:.3f} gg | UFFICIALE: {op_note}"
                df = pd.concat([df, pd.DataFrame([[op_data, "Uscita", "Manodopera", desc_uff, 0.0, "Olive", "Impegnato"]], columns=df.columns)])
            gg_extra = op_reali - op_ufficiali
            if abs(gg_extra) > 0.001:
                desc_extra = f"{op_nome} | {gg_extra:.3f} gg | EXTRA: {op_note}"
                df = pd.concat([df, pd.DataFrame([[op_data, "Uscita", "Manodopera Extra", desc_extra, 0.0, "Olive", "Impegnato"]], columns=df.columns)])
            save_to_github(df, sha, "Aggiornamento Manodopera")
            st.rerun()

# --- TAB 3: CASSA ---
with tab3:
    st.subheader("💸 Cassa e Estratto Conto (Euro)")
    df, _ = get_github_file()
    cat_pagamenti = ['Busta Paga', 'Saldo Extra', 'Straordinari', 'Rimborsi']
    tot_versato = df[df['categoria'].isin(cat_pagamenti)]['importo'].sum()
    gg_totali = sum(estrai_giornate(row['descrizione'], "Iannone Felice") for _, row in df[df['categoria'].isin(['Manodopera', 'Manodopera Extra'])].iterrows())
    valore_lavoro = gg_totali * COSTO_GIORNATA_EXTRA
    
    saldo = tot_versato - valore_lavoro
    st.metric("Saldo Dare/Avere", format_euro(saldo))
    
    with st.form("cassa_form"):
        tipo_op = st.selectbox("Natura Operazione", ["Busta Paga", "Saldo Extra"])
        imp = st.number_input("Importo (€)", min_value=0.0)
        if st.form_submit_button("Registra"):
            # Aggiungi riga logica di salvataggio
            st.rerun()

# --- TAB 4: RESE ---
with tab4:
    st.header("Registro Rese")

# --- TAB 5: BILANCIO E CONTROLLO DI GESTIONE (DETTAGLIATO) ---
with tab5:
    st.header("📊 Bilancio e Controllo di Gestione")
    st.markdown("Visione d'insieme sulle performance finanziarie e sui costi operativi dell'azienda.")
    
    df_dash, _ = get_github_file()
    if not df_dash.empty:
        df_dash['data_dt'] = pd.to_datetime(df_dash['data'], errors='coerce')
        anni_disponibili = df_dash['data_dt'].dt.year.dropna().unique()
        
        if len(anni_disponibili) > 0:
            anno_selezionato = st.selectbox("Seleziona Anno di Esercizio:", sorted(anni_disponibili, reverse=True))
            df_anno = df_dash[df_dash['data_dt'].dt.year == anno_selezionato].copy()
            
            # --- 1. SINTESI FINANZIARIA (FLUSSO DI CASSA) ---
            st.subheader("1. Sintesi Finanziaria (Cassa)")
            tot_entrate = df_anno[df_anno['tipo'] == 'Entrata']['importo'].sum()
            tot_uscite = df_anno[df_anno['tipo'] == 'Uscita']['importo'].sum()
            utile_netto = tot_entrate - tot_uscite
            
            c1, c2, c3 = st.columns(3)
            c1.metric("🟢 Totale Entrate (Vendite/Altro)", format_euro(tot_entrate))
            c2.metric("🔴 Totale Uscite (Costi Totali)", format_euro(tot_uscite))
            c3.metric("⚖️ Flusso di Cassa", format_euro(utile_netto), delta=f"{utile_netto:.2f} €", delta_color="normal")
            
            st.divider()
            
            # --- 2. SCOMPOSIZIONE DELLE USCITE (Personale vs Azienda) ---
            st.subheader("2. Analisi dei Costi (Dove vanno i soldi?)")
            
            # Identifichiamo le categorie puramente finanziarie (pagamenti)
            cat_personale_cassa = ['Busta Paga', 'Saldo Extra', 'Straordinari', 'Rimborsi']
            df_uscite = df_anno[df_anno['tipo'] == 'Uscita'].copy()
            
            costo_personale = df_uscite[df_uscite['categoria'].isin(cat_personale_cassa)]['importo'].sum()
            costo_operativo = tot_uscite - costo_personale
            
            col_p, col_o = st.columns(2)
            with col_p:
                st.info(f"**Cassa Personale:** {format_euro(costo_personale)}")
                st.write("*Dettaglio Erogazioni ai Lavoratori:*")
                dettaglio_pers = df_uscite[df_uscite['categoria'].isin(cat_personale_cassa)].groupby('categoria')['importo'].sum().reset_index()
                st.dataframe(dettaglio_pers, hide_index=True, use_container_width=True)
            
            with col_o:
                st.warning(f"**Costi Operativi (Azienda/Olive):** {format_euro(costo_operativo)}")
                st.write("*Dettaglio Spese (Carburante, Materiali, ecc.):*")
                dettaglio_op = df_uscite[~df_uscite['categoria'].isin(cat_personale_cassa) & ~df_uscite['categoria'].str.contains('Manodopera')].groupby('categoria')['importo'].sum().reset_index()
                st.dataframe(dettaglio_op.sort_values(by='importo', ascending=False), hide_index=True, use_container_width=True)

            st.divider()
            
            # --- 3. FOCUS MANODOPERA E FORZA LAVORO ---
            st.subheader("3. Statistiche Forza Lavoro (Impegno Fisico)")
            st.markdown("Analisi basata sui giorni di lavoro registrati (*1 Giornata = 6 Ore*).")
            
            # Sommiamo tutte le giornate fisiche estraendole dal testo
            cat_lavoro = ['Manodopera', 'Manodopera Extra']
            df_lavoro = df_anno[df_anno['categoria'].isin(cat_lavoro)]
            
            gg_ufficiali = 0.0
            gg_extra = 0.0
            
            import re
            for _, row in df_lavoro.iterrows():
                # Cerca un numero (anche con decimali) seguito da "gg" nella descrizione
                match = re.search(r'([\d\.]+)\s*gg', row['descrizione'])
                if match:
                    valore = float(match.group(1))
                    if row['categoria'] == 'Manodopera':
                        gg_ufficiali += valore
                    else:
                        gg_extra += valore
                        
            gg_totali = gg_ufficiali + gg_extra
            valore_economico_generato = gg_totali * COSTO_GIORNATA_EXTRA
            
            c_lav1, c_lav2, c_lav3 = st.columns(3)
            c_lav1.metric("🚜 Giornate Ufficiali", f"{gg_ufficiali:.3f} gg")
            c_lav2.metric("⏱️ Giornate Fuori Busta", f"{gg_extra:.3f} gg")
            c_lav3.metric("💸 Valore Lavoro Generato", format_euro(valore_economico_generato))
            
            st.divider()
            
            # --- 4. ANDAMENTO MENSILE DELLE SPESE ---
            st.subheader("4. Andamento Uscite Mensili")
            df_uscite['mese'] = df_uscite['data_dt'].dt.month
            
            # Creiamo una tabella pivot per il grafico escludendo le righe di pura registrazione giorni
            df_uscite_grafico = df_uscite[~df_uscite['categoria'].str.contains('Manodopera')]
            
            if not df_uscite_grafico.empty:
                andamento = df_uscite_grafico.groupby(['mese', 'categoria'])['importo'].sum().unstack().fillna(0)
                st.bar_chart(andamento)
            else:
                st.write("Nessun movimento finanziario registrato per alimentare il grafico.")
                
        else:
            st.info("Nessuna data valida trovata per generare il bilancio.")
    else:
        st.info("Nessun dato registrato al momento nel database.")

# --- TAB 6: REGISTRAZIONE FATTURE E SPESE OPERATIVE ---
with tab6:
    st.header("🧾 Registrazione Fatture e Operazioni Commerciali")
    
    # 1. SCELTA REATTIVA FUORI DAL FORM
    # Scegliendo qui, la pagina si aggiorna all'istante
    fat_tipo = st.radio("Seleziona la Natura dell'Operazione:", 
                        ["Uscita (Acquisto / Spesa)", "Entrata (Vendita / Ricavo)"], 
                        horizontal=True)
    
    # 2. FILTRAGGIO DINAMICO DELLE CATEGORIE
    if "Uscita" in fat_tipo:
        categorie_disponibili = ["Carburante e Mezzi", "Attrezzature", "Materiale Agricolo (Concimi/Piante)", "Manutenzione", "Consulenze/Tasse", "Altro"]
        tipo_db = "Uscita"
    else:
        categorie_disponibili = ["Vendita Olio", "Vendita Olive", "Contributi/Aiuti", "Altro"]
        tipo_db = "Entrata"
        
    st.divider()
    
    # 3. MODULO DI INSERIMENTO PROTETTO
    with st.form("form_fatture", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        with c1:
            fat_data = st.date_input("Data Fattura / Operazione", format="DD/MM/YYYY")
            fat_soggetto = st.text_input("Fornitore / Cliente", placeholder="es. Consorzio Agrario")
            fat_descrizione = st.text_input("Descrizione e Numero Fattura", placeholder="es. Fatt. 15/2026 - Acquisto Concime")
            
        with c2:
            # Qui il menu a tendina riceve solo la lista filtrata
            fat_categoria = st.selectbox("Categoria Bilancio (Filtrata automaticamente)", categorie_disponibili)
            fat_importo = st.number_input("Importo Totale (€)", min_value=0.0, step=1.0, format="%.2f")
            fat_stato = st.selectbox("Stato Pagamento", ["Saldato", "Da Saldare (A credito/debito)"])
            
        if st.form_submit_button("Registra Operazione nel Database"):
            df, sha = get_github_file()
            
            # Formattazione per il database
            descrizione_completa = f"{fat_soggetto.strip()} | {fat_descrizione.strip()}"
            stato_db = "Saldato" if "Saldato" in fat_stato else "Impegnato"
            
            # Creazione della riga
            nuova_riga = [
                fat_data.strftime('%Y-%m-%d'), 
                tipo_db, 
                fat_categoria, 
                descrizione_completa, 
                float(fat_importo), 
                "Azienda Generale", 
                stato_db
            ]
            
            df_nuova = pd.DataFrame([nuova_riga], columns=df.columns)
            df = pd.concat([df, df_nuova], ignore_index=True)
            
            if save_to_github(df, sha, f"Registrata Fattura: {fat_soggetto}"): 
                st.success(f"✅ Operazione da {fat_importo} € registrata con successo!")
                st.rerun()
