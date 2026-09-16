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
    (Versione: Architettura a Doppio Binario e Database Cloud)

    🎯 Obiettivo del Sistema
    Il software centralizza la gestione amministrativa, finanziaria e operativa dell'impresa agricola. Il cuore logico è la separazione netta tra i movimenti fisici (il lavoro sui campi in giornate da 6 ore) e i movimenti finanziari (cassa, fatture e bonifici).
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
    try:
        valore = float(valore)
    except (ValueError, TypeError):
        valore = 0.0
        
    importo_str = f"{valore:,.2f}"
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
st.title("AgriFinance")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Home", "Manodopera", "Cassa", "Rese", "Bilancio", "Fatture"])

# ==========================================
# --- TAB 1: HOME, NOTIFICHE E METEO ---
# ==========================================
with tab1:
    st.header("🏠 Cruscotto Generale e Notifiche")
    
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = "antonellomazzilli-bit/agri-finance"
    FILE_RICHIESTE = "richieste_sospese.csv"
    
    def get_richieste():
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE_RICHIESTE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            return pd.read_csv(StringIO(content)), data['sha']
        return pd.DataFrame(), None

    def update_richieste(df, sha, messaggio_commit="Archiviata richiesta dipendente"):
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE_RICHIESTE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        csv_data = df.to_csv(index=False)
        payload = {
            "message": messaggio_commit, 
            "content": base64.b64encode(csv_data.encode('utf-8')).decode('utf-8'),
            "sha": sha
        }
        r = requests.put(url, headers=headers, data=json.dumps(payload))
        return r.status_code in [200, 201]
        
    df_richieste, sha_richieste = get_richieste()
    
    if not df_richieste.empty:
        richieste_attive = df_richieste[df_richieste['stato'] == 'In Attesa']
        if not richieste_attive.empty:
            st.error(f"🔔 **ATTENZIONE: Hai {len(richieste_attive)} nuova/e comunicazione/i dal personale!**")
            for idx, row in richieste_attive.iterrows():
                with st.expander(f"📩 {row['tipo']} da {row['lavoratore']} - {row['timestamp']}", expanded=True):
                    st.markdown(f"**Valore globale:** {row['valore']}")
                    st.text(row['note']) 
                    col_ok, col_ko = st.columns(2)
                    with col_ok:
                        if st.button("✅ Approva e Archivia", key=f"archivia_{idx}", use_container_width=True):
                            df_richieste.at[idx, 'stato'] = 'Approvata'
                            if update_richieste(df_richieste, sha_richieste, "Approvata richiesta dipendente"):
                                st.success("Richiesta archiviata!")
                                time.sleep(1.5)
                                st.rerun()
                    with col_ko:
                        if st.button("🗑️ Rifiuta ed Elimina", key=f"cestina_{idx}", type="primary", use_container_width=True):
                            df_richieste.at[idx, 'stato'] = 'Rifiutata (Cancellata)'
                            if update_richieste(df_richieste, sha_richieste, "Rifiutata/Eliminata richiesta"):
                                st.warning("Notifica rifiutata e rimossa.")
                                time.sleep(1.5)
                                st.rerun()
        else:
            st.info("📭 Nessuna nuova comunicazione dal personale.")
    else:
        st.info("📭 Sistema di comunicazione col personale in attesa del primo messaggio.")
        
    st.divider()
    
    # Modulo Meteo Integrato
    st.subheader("🌦️ Previsioni Meteo & Semaforo Irriguo (Corato)")
    st.markdown("Dati climatici aggiornati in automatico via satellite per l'area di Corato / Agro di Andria.")
    url_meteo = "https://api.open-meteo.com/v1/forecast?latitude=41.1535&longitude=16.4132&daily=temperature_2m_max,precipitation_sum&timezone=Europe/Rome"

    try:
        resp_meteo = requests.get(url_meteo, timeout=5)
        if resp_meteo.status_code == 200:
            m_data = resp_meteo.json()
            daily = m_data.get("daily", {})
            dates = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            rain_sums = daily.get("precipitation_sum", [])
            
            if dates and max_temps:
                forecast_list = []
                for i in range(min(5, len(dates))):
                    forecast_list.append({
                        "Giorno": dates[i],
                        "Temp Massima (°C)": max_temps[i],
                        "Pioggia Prevista (mm)": rain_sums[i] if i < len(rain_sums) else 0.0
                    })
                st.dataframe(pd.DataFrame(forecast_list), use_container_width=True, hide_index=True)
                
                temp_oggi = max_temps[0]
                pioggia_oggi = rain_sums[0] if rain_sums else 0.0
                
                st.markdown("### 🚦 Semaforo Irriguo Automatico (Oggi)")
                if pioggia_oggi > 1.5:
                    st.success(f"🌧️ **Pioggia in arrivo ({pioggia_oggi} mm):** Ottime notizie! **Non attivare l'irrigazione**.")
                elif temp_oggi >= 35.0:
                    st.error(f"🔥 **Caldo Estremo ({temp_oggi}°C):** Rischio stress idrico severo per la Coratina.")
                elif temp_oggi >= 32.0:
                    st.warning(f"⚠️ **Caldo Intenso ({temp_oggi}°C):** Condizione limite. Valuta se rimandare.")
                else:
                    st.success(f"✅ **Temperatura mite ({temp_oggi}°C):** La pianta non è in sofferenza termica. **Blocca l'acqua!**")
        else:
            st.warning("Impossibile leggere i dati meteo giornalieri.")
    except Exception:
        st.info("Connessione al meteo non disponibile in questo momento.")

    st.divider()
    
    # Database Generale
    st.subheader("🗄️ Database Generale Aziendale")
    df, sha = get_github_file()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.divider()
        
        st.subheader("✏️ Modifica o Elimina Registrazione")
        df_reversed = df.iloc[::-1].copy()
        opzioni_riga = [f"Riga {i} | {r['data']} | {r['categoria']} | {r['descrizione']} | {r['stato']}" for i, r in df_reversed.iterrows()]
        
        riga_selezionata = st.selectbox("Seleziona la registrazione da gestire:", opzioni_riga)
        if riga_selezionata:
            indice_reale = int(riga_selezionata.split(" | ")[0].replace("Riga ", ""))
            riga_dati = df.loc[indice_reale]
            
            with st.form("form_modifica_riga"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nuova_data = st.text_input("Data (YYYY-MM-DD)", value=str(riga_dati['data']))
                with c2:
                    stati_possibili = ["Impegnato", "Saldato", "Annullato"]
                    indice_stato = stati_possibili.index(riga_dati['stato']) if riga_dati['stato'] in stati_possibili else 0
                    nuovo_stato = st.selectbox("Stato Generale", stati_possibili, index=indice_stato)
                with c3:
                    importo_attuale = float(riga_dati['importo']) if pd.notna(riga_dati['importo']) and str(riga_dati['importo']).replace('.','',1).isdigit() else 0.0
                    nuovo_importo = st.number_input("Totale Fattura / Importo (€)", value=importo_attuale, format="%.2f")
                
                nuova_desc = st.text_input("Descrizione Documento", value=str(riga_dati['descrizione']))
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    salva_modifiche = st.form_submit_button("💾 Salva Modifiche", type="primary", use_container_width=True)
                with col_btn2:
                    elimina_riga = st.form_submit_button("🗑️ Elimina Registrazione", use_container_width=True)
            
            if salva_modifiche:
                df.at[indice_reale, 'data'] = nuova_data
                df.at[indice_reale, 'stato'] = nuovo_stato
                df.at[indice_reale, 'importo'] = float(nuovo_importo)
                df.at[indice_reale, 'totale_fattura'] = float(nuovo_importo)
                df.at[indice_reale, 'importo_pagato'] = float(nuovo_importo)
                df.at[indice_reale, 'descrizione'] = nuova_desc
                
                if save_to_github(df, sha, f"Modifica manuale riga {indice_reale}"):
                    st.success("✅ Modifiche salvate con successo!")
                    time.sleep(1.5)
                    st.rerun()
                    
            if elimina_riga:
                df = df.drop(index=indice_reale).reset_index(drop=True)
                if save_to_github(df, sha, f"Eliminata riga {indice_reale}"):
                    st.warning("🗑️ Registrazione eliminata definitivamente!")
                    time.sleep(1.5)
                    st.rerun()
    else:
        st.warning("Il database principale è attualmente vuoto o non raggiungibile.")

# ==========================================
# --- TAB 2: MANODOPERA ---
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
            op_ufficiali = st.number_input("Giornate Ufficiali (In Busta)", min_value=0.0, step=0.5, format="%.2f")
        with c3:
            op_extra = st.number_input("Giornate EXTRA (Fuori Busta)", min_value=0.0, step=0.5, format="%.2f")
            
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
        if op_extra > 0:
            desc_extra = f"{op_nome} | {op_extra:.3f} gg | EXTRA: {op_note}"
            righe_nuove.append({
                'data': op_data.strftime('%Y-%m-%d'), 'tipo': "Uscita", 'categoria': "Manodopera Extra", 
                'descrizione': desc_extra, 'importo': 0.0, 'prodotto': "Olive", 'stato': "Impegnato", 
                'totale_fattura': 0.0, 'importo_pagato': 0.0, 'registro_pagamenti': ""
            })
        if righe_nuove:
            df = pd.concat([df, pd.DataFrame(righe_nuove)], ignore_index=True)
            if save_to_github(df, sha, "Aggiornamento Manodopera Semplificata"):
                st.success("✅ Giornate lavorative registrate con successo!")
                time.sleep(1)
                st.rerun()

    st.divider()
    st.subheader("📊 Riepilogo Giornate Lavorate")
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
                    riepilogo[chiave] = {'Giornate EXTRA': 0.0, 'Giornate UFFICIALI': 0.0, 'TOTALE Giornate': 0.0}
                if row['categoria'] == 'Manodopera Extra':
                    riepilogo[chiave]['Giornate EXTRA'] += abs(gg)
                elif row['categoria'] == 'Manodopera':
                    riepilogo[chiave]['Giornate UFFICIALI'] += abs(gg)
                riepilogo[chiave]['TOTALE Giornate'] = riepilogo[chiave]['Giornate UFFICIALI'] + riepilogo[chiave]['Giornate EXTRA']

        if riepilogo:
            st.dataframe(pd.DataFrame.from_dict(riepilogo, orient='index'), use_container_width=True)

# ==========================================
# --- TAB 3: CASSA E ESTRATTO CONTO ---
# ==========================================
with tab3:
    st.subheader("💸 Cassa e Estratto Conto Mensile")
    df, sha = get_github_file()
    
    if not df.empty:
        df['importo'] = pd.to_numeric(df['importo'], errors='coerce').fillna(0.0)
        df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
        
        dati_mensili = {}
        mesi_nomi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
        mesi_nomi_inv = {v: k for k, v in mesi_nomi.items()}
        
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
                    importo_forzato = abs(float(row['importo']))
                    valore_maturato = importo_forzato if importo_forzato > 0 else abs(gg_lavorati) * 55.0
                    dati_mensili[chiave_mese]['Extra Maturato (Debito)'] += valore_maturato

        pagamenti_df = df[df['categoria'].isin(['Busta Paga', 'Saldo Extra', 'Rimborsi'])]
        for index, row in pagamenti_df.iterrows():
            importo_pagato = row['importo']
            desc_str = str(row['descrizione'])
            cat = row['categoria']
            
            mese_trovato = False
            for chiave in dati_mensili.keys():
                if chiave in desc_str:
                    if cat in ['Saldo Extra', 'Rimborsi']:
                        dati_mensili[chiave]['Extra Pagato'] += importo_pagato
                    elif cat == 'Busta Paga':
                        dati_mensili[chiave]['Busta Paga Versata'] += importo_pagato
                    mese_trovato = True
                    break
            
            if not mese_trovato:
                chiave_na = "Pagamenti Pregressi/Non Allocati"
                if chiave_na not in dati_mensili:
                    dati_mensili[chiave_na] = {'Extra Maturato (Debito)': 0.0, 'Extra Pagato': 0.0, 'Busta Paga Versata': 0.0}
                if cat in ['Saldo Extra', 'Rimborsi']:
                    dati_mensili[chiave_na]['Extra Pagato'] += importo_pagato
                elif cat == 'Busta Paga':
                    dati_mensili[chiave_na]['Busta Paga Versata'] += importo_pagato

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
            
            df_riepilogo['Saldo Arretrati (Extra)'] = df_riepilogo['Extra Pagato'] - df_riepilogo['Extra Maturato (Debito)']
            df_riepilogo['Differenza (Busta - Extra)'] = df_riepilogo['Busta Paga Versata'] - df_riepilogo['Extra Maturato (Debito)']
            saldo_globale = df_riepilogo['Differenza (Busta - Extra)'].sum()
            
            df_display = df_riepilogo.copy()
            for col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: f"{x:,.2f} €")
                
            st.dataframe(df_display, use_container_width=True)
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, txt="Estratto Conto Lavoro - Iannone Felice", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            pdf.cell(190, 10, txt=f"Generato il: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
            pdf.ln(5)
            
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
                
                if row['Saldo Arretrati (Extra)'] < 0:
                    pdf.set_text_color(220, 53, 69)
                else:
                    pdf.set_text_color(40, 167, 69)
                pdf.cell(30, 10, f"{row['Saldo Arretrati (Extra)']:,.2f} E", 1, 0, 'R')
                pdf.set_text_color(0, 0, 0)
                pdf.cell(40, 10, f"{row['Differenza (Busta - Extra)']:,.2f} E", 1, 1, 'R')
                
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 12)
            if saldo_globale < 0:
                pdf.set_text_color(220, 53, 69)
                pdf.cell(190, 10, txt=f"ATTENZIONE: Differenza totale negativa per {abs(saldo_globale):,.2f} Euro", ln=True)
            else:
                pdf.set_text_color(40, 167, 69)
                pdf.cell(190, 10, txt=f"Situazione Regolare. Differenza totale: {saldo_globale:,.2f} Euro", ln=True)
            pdf.set_text_color(0, 0, 0)
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            st.download_button(
                label="📄 Scarica Tabella Aggiornata (PDF)",
                data=pdf_bytes,
                file_name=f'Conto_Lavoro_Iannone_{datetime.now().strftime("%Y_%m")}.pdf',
                mime='application/pdf',
                type="primary"
            )
            
            if saldo_globale < 0:
                st.error(f"⚠️ ATTENZIONE: La differenza totale è negativa per: **{abs(saldo_globale):,.2f} €**")
            else:
                st.success(f"✅ Situazione regolare. La differenza totale è: **{saldo_globale:,.2f} €**")
        
        st.divider()
        with st.form("cassa_form", clear_on_submit=True):
            st.write("### ➕ Registra un pagamento al dipendente")
            c1, c2, c3 = st.columns([1, 1, 1.5])
            with c1:
                data_pag = st.date_input("Data del Bonifico/Contanti", format="DD/MM/YYYY")
            with c2:
                imp = st.number_input("Importo Erogato (€)", min_value=0.0, step=10.0, format="%.2f", value=0.0)
            with c3:
                tipo_op = st.selectbox("Natura Operazione", ["Busta Paga", "Saldo Extra", "Rimborsi"])
                presenze_mesi = df[df['categoria'].isin(['Manodopera', 'Manodopera Extra'])]['data_dt'].dt.strftime('%B %Y').dropna().unique()
                mesi_tradotti = []
                for m in presenze_mesi:
                    for num, nome in mesi_nomi.items():
                        if m.startswith(datetime.strptime(str(num), "%m").strftime("%B")):
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
                    
                    if save_to_github(df, sha, f"Pagato: {imp}€ per {mese_rif}"):
                        st.success(f"✅ Pagamento di {imp}€ registrato!")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.warning("L'importo deve essere maggiore di zero.")

# ==========================================
# --- TAB 4: SIMULATORE STRATEGICO & TARGET ---
# ==========================================
with tab4:
    st.title("🎯 Simulatore Strategico & Break-Even")
    st.markdown("Pianifica la campagna olearia: definisci il tuo **obiettivo di reddito** e scopri i volumi fisici necessari in tempo reale.")
    st.divider()

    df_pareggio, _ = get_github_file()
    if not df_pareggio.empty:
        df_pareggio['importo'] = pd.to_numeric(df_pareggio['importo'], errors='coerce').fillna(0.0)
        df_pareggio['data_dt'] = pd.to_datetime(df_pareggio['data'], errors='coerce')
        anni_disponibili = df_pareggio['data_dt'].dt.year.dropna().unique()
        
        if len(anni_disponibili) > 0:
            anno_sel = st.selectbox("📅 Basato sulle spese storiche dell'anno:", sorted(anni_disponibili, reverse=True), key="anno_target")
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
                    else:
                        quintali_necessari = fabbisogno_totale / prezzo_attuale
                        rc1, rc2, rc3 = st.columns(3)
                        rc1.metric("🫒 Olive da Vendere", f"{quintali_necessari:,.0f} Quintali")
                        rc2.metric("⚖️ Equivalente in Kg", f"{quintali_necessari * 100:,.0f} Kg")
                        rc3.metric("📊 Fatturato Target", format_euro(fabbisogno_totale), "Copertura Raggiunta")

# ==========================================
# --- TAB 5: BILANCIO E SPENDING REVIEW ---
# ==========================================
with tab5:
    st.header("📊 Conto Economico & Analitico per Categoria")
    st.markdown("Clicca sulla freccia di qualsiasi categoria per esplorare l'elenco esatto delle spese o dei ricavi registrati.")

    df_spesa, _ = get_github_file()
    
    if not df_spesa.empty:
        df_spesa['importo'] = pd.to_numeric(df_spesa['importo'], errors='coerce').fillna(0)
        df_validi = df_spesa[df_spesa['stato'].isin(['Saldato', 'Impegnato'])].copy()
        
        # Estraiamo dinamicamente tutte le categorie reali presenti nel database
        categorie_uniche = df_validi['categoria'].dropna().unique()
        
        if len(categorie_uniche) > 0:
            for cat in sorted(categorie_uniche):
                df_dettaglio = df_validi[df_validi['categoria'] == cat].copy()
                totale_cat = df_dettaglio['importo'].sum()
                
                tipo_op = df_dettaglio['tipo'].iloc[0] if 'tipo' in df_dettaglio.columns and not df_dettaglio.empty else "Uscita"
                icona = "🟢" if tipo_op == "Entrata" else "🔴"
                
                with st.expander(f"{icona} **{cat}** — Totale: **{totale_cat:,.2f} €**"):
                    if not df_dettaglio.empty:
                        st.dataframe(
                            df_dettaglio[['data', 'tipo', 'descrizione', 'importo', 'stato']], 
                            use_container_width=True, 
                            hide_index=True
                        )
                        st.caption(f"Numero movimenti registrati: {len(df_dettaglio)}")
                    else:
                        st.info("Nessun movimento registrato per questa categoria.")
        else:
            st.info("Nessuna categoria trovata nel database.")
            
    st.divider()
    st.header("📉 Radiografia dei Costi e Spending Review")
    st.markdown("Usa questo pannello per identificare esattamente dove stai perdendo marginalità.")
    
    if not df_spesa.empty:
        df_spese = df_spesa[df_spesa['stato'].isin(['Saldato', 'Impegnato'])].copy()
        df_spese['importo_assoluto'] = df_spese['importo'].abs()
        
        escluse = ['Vendita Olio', 'Vendita Olive', 'Contributi/Aiuti', 'Rimborso Spese']
        df_costi_vivi = df_spese[~df_spese['categoria'].isin(escluse)].copy()
        
        spese_per_categoria = df_costi_vivi.groupby('categoria')['importo_assoluto'].sum().reset_index()
        spese_per_categoria = spese_per_categoria.sort_values(by='importo_assoluto', ascending=False)
        totale_uscite = spese_per_categoria['importo_assoluto'].sum()
        
        st.subheader("🚨 Sintesi Critica Costi Operativi")
        c1, c2, c3 = st.columns(3)
        c1.metric("💸 Totale Costi Vivi", f"{totale_uscite:.2f} €")
        
        if not spese_per_categoria.empty:
            peggiore_categoria = spese_per_categoria.iloc[0]['categoria']
            peggiore_importo = spese_per_categoria.iloc[0]['importo_assoluto']
            incidenza = (peggiore_importo / totale_uscite) * 100 if totale_uscite > 0 else 0
            
            c2.metric("⚠️ Buco Nero (Voce peggiore)", peggiore_categoria)
            c3.metric("📊 Peso sul totale", f"{incidenza:.1f} %")
            
            st.divider()
            st.markdown("### 📊 Distribuzione dei Costi")
            st.bar_chart(spese_per_categoria.set_index('categoria')['importo_assoluto'])

    st.divider()
    st.subheader("📄 Esportazione e Stampa Bilancio")
    st.markdown("Genera un documento PDF ufficiale con il riepilogo di tutte le categorie e i totali del periodo.")

    

# ==========================================
# --- TAB 6: FATTURE E COMMERCIALIZZAZIONE ---
# ==========================================
with tab6:
    st.header("🧾 Registrazione Fatture e Operazioni Commerciali")
    fat_tipo = st.radio("Seleziona la Natura dell'Operazione:", ["Uscita (Acquisto / Spesa)", "Entrata (Vendita / Ricavo)"], horizontal=True)
    
    if "Uscita" in fat_tipo:
        categorie_disponibili = ["Carburante e Mezzi", "Attrezzature", "Materiale Agricolo (Concimi/Piante)", "Manutenzione", "Consulenze/Tasse", "Oneri", "Irrigazione", "Altro"]
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
                
                totale_fat = fat_importo
                imp_pagato = fat_importo if stato_db == "Saldato" else 0.0
                storico_iniziale = f"{data_formattata}|{fat_importo}|Registrazione iniziale" if stato_db == "Saldato" else ""

                nuova_riga = {
                    'data': data_formattata, 'tipo': tipo_db, 'categoria': fat_categoria,
                    'descrizione': descrizione_completa, 'importo': fat_importo, 'prodotto': "",
                    'stato': stato_db, 'totale_fattura': totale_fat, 'importo_pagato': imp_pagato,
                    'registro_pagamenti': storico_iniziale
                }

                df = pd.concat([df, pd.DataFrame([nuova_riga])], ignore_index=True)
                if save_to_github(df, sha, f"Registrata Fattura: {fat_soggetto}"): 
                    st.success("✅ Operazione registrata con successo!")
                    time.sleep(2)
                    st.rerun()
            else:
                st.warning("⚠️ Compila almeno Fornitore/Cliente e assicurati che l'importo sia maggiore di zero.")
