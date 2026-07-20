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

# Testo del manuale incorporato nell'app
testo_manuale = """
📖 MANUALE OPERATIVO: AGRIFINANCE CLOUD
Versione: 2.0 (Architettura a Doppio Binario e Database Cloud)

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

# Bottone per il download immediato
st.download_button(
    label="📥 Scarica Manuale Operativo",
    data=testo_manuale,
    file_name="Manuale_AgriFinance.txt",
    mime="text/plain"
)
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
# --- TAB 4: RESE ---
# ==========================================
with tab4:
    st.header("🚜 Registro Rese e Produzione")
    st.info("Modulo di calcolo rese olive/olio in fase di sviluppo.")

# ==========================================
# --- TAB 5: BILANCIO E CONTROLLO ---
# ==========================================
with tab5:
    st.header("📊 Bilancio e Controllo di Gestione")
    df_dash, _ = get_github_file()
    
    if not df_dash.empty:
        df_dash['data_dt'] = pd.to_datetime(df_dash['data'], errors='coerce')
        anni_disponibili = df_dash['data_dt'].dt.year.dropna().unique()
        
        if len(anni_disponibili) > 0:
            anno_selezionato = st.selectbox("Seleziona Anno di Esercizio:", sorted(anni_disponibili, reverse=True))
            df_anno = df_dash[df_dash['data_dt'].dt.year == anno_selezionato].copy()
            
            # --- CREAZIONE SOTTO-SCHEDE ---
            sub_tab1, sub_tab2 = st.tabs(["📈 Cruscotto Interattivo", "🖨️ Fascicolo Debiti (Stampa Civile)"])
            
            # --- PRIMA SOTTO-SCHEDA: IL TUO VECCHIO CRUSCOTTO ---
            with sub_tab1:
                st.subheader("1. Sintesi Finanziaria (Cassa)")
                tot_entrate = df_anno[df_anno['tipo'] == 'Entrata']['importo'].sum()
                tot_uscite = df_anno[df_anno['tipo'] == 'Uscita']['importo'].sum()
                utile_netto = tot_entrate - tot_uscite
                
                c1, c2, c3 = st.columns(3)
                c1.metric("🟢 Totale Entrate", format_euro(tot_entrate))
                c2.metric("🔴 Totale Uscite", format_euro(tot_uscite))
                c3.metric("⚖️ Flusso di Cassa", format_euro(utile_netto), delta=f"{utile_netto:.2f} €", delta_color="normal")
                
                st.divider()
                st.subheader("2. Analisi dei Costi")
                cat_personale_cassa = ['Busta Paga', 'Saldo Extra', 'Straordinari', 'Rimborsi']
                df_uscite = df_anno[df_anno['tipo'] == 'Uscita'].copy()
                costo_personale = df_uscite[df_uscite['categoria'].isin(cat_personale_cassa)]['importo'].sum()
                costo_operativo = tot_uscite - costo_personale
                
                col_p, col_o = st.columns(2)
                with col_p:
                    st.info(f"**Cassa Personale:** {format_euro(costo_personale)}")
                    st.dataframe(df_uscite[df_uscite['categoria'].isin(cat_personale_cassa)].groupby('categoria')['importo'].sum().reset_index(), hide_index=True, use_container_width=True)
                with col_o:
                    st.warning(f"**Costi Operativi:** {format_euro(costo_operativo)}")
                    st.dataframe(df_uscite[~df_uscite['categoria'].isin(cat_personale_cassa) & ~df_uscite['categoria'].str.contains('Manodopera')].groupby('categoria')['importo'].sum().reset_index().sort_values(by='importo', ascending=False), hide_index=True, use_container_width=True)

                st.divider()
                st.subheader("3. Statistiche Forza Lavoro")
                df_lavoro = df_anno[df_anno['categoria'].isin(['Manodopera', 'Manodopera Extra'])]
                gg_ufficiali, gg_extra = 0.0, 0.0
                
                for _, row in df_lavoro.iterrows():
                    match = re.search(r'([\d\.]+)\s*gg', str(row['descrizione']))
                    if match:
                        valore = float(match.group(1))
                        if row['categoria'] == 'Manodopera':
                            gg_ufficiali += valore
                        else:
                            gg_extra += valore
                            
                valore_generato = (gg_ufficiali + gg_extra) * COSTO_GIORNATA_EXTRA
                c_lav1, c_lav2, c_lav3 = st.columns(3)
                c_lav1.metric("🚜 Giornate Ufficiali", f"{gg_ufficiali:.3f} gg")
                c_lav2.metric("⏱️ Giornate Fuori Busta", f"{gg_extra:.3f} gg")
                c_lav3.metric("💸 Valore Lavoro Generato", format_euro(valore_generato))
                
                st.divider()
                st.subheader("4. Andamento Uscite Mensili")
                df_uscite['mese'] = df_uscite['data_dt'].dt.month
                df_uscite_grafico = df_uscite[~df_uscite['categoria'].str.contains('Manodopera')]
                if not df_uscite_grafico.empty:
                    st.bar_chart(df_uscite_grafico.groupby(['mese', 'categoria'])['importo'].sum().unstack().fillna(0))
                    
            # --- SECONDA SOTTO-SCHEDA: DOCUMENTO STAMPABILE ---
            with sub_tab2:
                st.subheader("Fascicolo Civile: Debiti e Spese Impegnate")
                st.markdown("Isolamento e impaginazione automatica delle fatture e degli stipendi con stato **'Impegnato'** o **'Da Saldare'**.")
                
                # Filtro rigoroso: solo spese in uscita non saldate
                df_impegnate = df_anno[(df_anno['stato'] == 'Impegnato') & (df_anno['tipo'] == 'Uscita')].sort_values(by='data_dt')
                
                if not df_impegnate.empty:
                    totale_debito = df_impegnate['importo'].sum()
                    
                    # Costruzione delle righe del documento HTML
                    righe_html = ""
                    for _, row in df_impegnate.iterrows():
                        data_f = row['data_dt'].strftime('%d/%m/%Y')
                        imp_f = format_euro(row['importo'])
                        righe_html += f"<tr><td>{data_f}</td><td>{row['descrizione']}</td><td>{row['categoria']}</td><td class='right'>{imp_f}</td></tr>"
                    
                    # Template A4 Isolato
                    html_template = f"""
                    <html>
                    <head>
                    <style>
                        body {{ font-family: 'Arial', sans-serif; background-color: #f4f4f9; padding: 20px; }}
                        .foglio-a4 {{ background-color: white; color: black; padding: 40px; max-width: 800px; margin: auto; box-shadow: 0 0 15px rgba(0,0,0,0.2); }}
                        h2, h3, h4 {{ text-align: center; margin: 5px 0; }}
                        .header-doc {{ border-bottom: 2px solid black; padding-bottom: 15px; margin-bottom: 25px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
                        th, td {{ border: 1px solid #000; padding: 10px; text-align: left; }}
                        th {{ background-color: #e9e9e9; font-weight: bold; }}
                        .right {{ text-align: right; }}
                        .bold {{ font-weight: bold; }}
                        @media print {{
                            body {{ background-color: white; padding: 0; }}
                            .foglio-a4 {{ box-shadow: none; max-width: 100%; padding: 0; margin: 0; }}
                            button {{ display: none; }}
                        }}
                    </style>
                    </head>
                    <body>
                        <div style="text-align: center; margin-bottom: 20px;">
                            <button onclick="window.print()" style="padding: 12px 24px; font-size: 16px; cursor: pointer; background-color: #008CBA; color: white; border: none; border-radius: 5px; font-weight: bold;">🖨️ Stampa PDF Formale</button>
                        </div>
                        <div class="foglio-a4">
                            <div class="header-doc">
                                <h2>AZIENDA AGRICOLA ANTONELLO MAZZILLI</h2>
                                <h4>Produzione Olio ed Esercizio Agricolo</h4>
                                <h3>ALLEGATO BILANCIO: PROSPETTO DEBITI E SPESE IMPEGNATE</h3>
                                <p style="text-align:center; font-size: 12px;">Esercizio Fiscale: {anno_selezionato} | Redatto ai sensi dell'Art. 2424 c.c. (Passivo, Sez. D)</p>
                            </div>
                            <table>
                                <tr>
                                    <th>Data</th>
                                    <th>Creditore / Descrizione</th>
                                    <th>Natura Spesa</th>
                                    <th class="right">Importo</th>
                                </tr>
                                {righe_html}
                                <tr>
                                    <td colspan="3" class="bold right" style="background-color: #e9e9e9;">TOTALE DEBITI VERSO FORNITORI E PERSONALE</td>
                                    <td class="bold right" style="background-color: #e9e9e9;">{format_euro(totale_debito)}</td>
                                </tr>
                            </table>
                        </div>
                    </body>
                    </html>
                    """
                    import streamlit.components.v1 as components
                    # Incapsuliamo il documento in un riquadro visuale
                    components.html(html_template, height=800, scrolling=True)
                else:
                    st.success("✅ Nessuna spesa impegnata o debito in sospeso per questo esercizio. Situazione contabile pulita!")
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
