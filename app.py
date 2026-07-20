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
        return pd.read_csv("data.csv"), "sha_mock" 
    except:
        return pd.DataFrame(columns=['data', 'tipo', 'categoria', 'descrizione', 'importo', 'prodotto', 'stato']), "new"

def save_to_github(df, sha, message):
    # Inserisci qui il tuo codice esistente per salvare su GitHub
    df.to_csv("data.csv", index=False)
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Home", "Manodopera", "Cassa", "Rese", "Bilancio"])

# --- TAB 1: HOME E REGISTRO GENERALE MODIFICABILE ---
with tab1:
    st.header("🏠 Registro Generale (Editor)")
    st.markdown("Fai **doppio clic** su una cella per modificarla (es. per aggiornare una categoria). Premi Invio per confermare la cella e poi usa il tasto verde qui sotto per salvare le modifiche nel database.")
    
    # Recuperiamo il file e il suo codice di sicurezza (sha)
    df, sha = get_github_file()
    
    if not df.empty:
        # Mostra il dataframe in modalità editor (stile Excel)
        df_modificato = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor_database")
        
        # Tasto di salvataggio
        st.divider()
        if st.button("💾 SALVA MODIFICHE NEL DATABASE", type="primary"):
            # Salviamo il nuovo dataframe sovrascrivendo quello vecchio
            if save_to_github(df_modificato, sha, "Correzione manuale dati storici dalla Tab 1"):
                st.success("✅ Modifiche storiche salvate con successo!")
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

# --- TAB 5: BILANCIO ---
with tab5:
    st.header("⚖️ Bilancio Semplificato")
    df, _ = get_github_file()
    tot_entrate = df[df['tipo'] == 'Entrata']['importo'].sum()
    tot_uscite = df[df['tipo'] == 'Uscita']['importo'].sum()
    st.metric("Risultato Netto", format_euro(tot_entrate - tot_uscite))
