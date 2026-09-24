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

def estrai_giornate(descrizione, nome_operatore):
    if not isinstance(descrizione, str):
        return 0.0
    # Controlla se la riga appartiene all'operatore giusto
    if nome_operatore.lower() not in descrizione.lower():
        return 0.0
    
    # Usa le espressioni regolari (regex) per trovare qualsiasi numero prima di "gg"
    import re
    # Cerca un numero (anche con virgola o punto) seguito opzionalmente da spazi e poi "gg" o "giornate"
    match = re.search(r'(\d+(?:[\.,]\d+)?)\s*(?:gg|giornate)', descrizione.lower())
    if match:
        # Estrae il numero, trasforma eventuale virgola in punto e lo converte
        numero_str = match.group(1).replace(',', '.')
        return float(numero_str)
    
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
    
    # ==================================================
    # --- MODULO METEO & GESTIONE POZZO PREPAGATO ---
    # ==================================================
    st.divider()

    # 1. LETTURA STORICO IRRIGAZIONE E CALCOLO CREDITO ORE
    df_meteo_db, sha_meteo_db = get_github_file()
    
    ultima_irrigazione_str = "Mai registrata"
    giorni_trascorsi = 999
    
    ore_ricaricate = 0.0
    ore_consumate = 0.0
    ultima_data_dt = None
    
    # Inizializziamo un dataframe vuoto per evitare errori successivi
    df_irrigazione = pd.DataFrame()

    if not df_meteo_db.empty:
        df_irrigazione = df_meteo_db[df_meteo_db['categoria'].str.contains('Irrigazione', case=False, na=False)].copy()
        
        if not df_irrigazione.empty:
            df_irrigazione['data_dt'] = pd.to_datetime(df_irrigazione['data'], errors='coerce')
            
            for _, row in df_irrigazione.iterrows():
                desc = str(row['descrizione']).lower()
                
                # Estraiamo il numero di ore dalla descrizione
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*ore', desc)
                ore_riga = float(match.group(1)) if match else 0.0
                
                # Calcolo del credito e consumi
                if "ricarica" in desc:
                    ore_ricaricate += ore_riga
                elif "turno" in desc:
                    ore_consumate += ore_riga
                    # Aggiorna la data per il semaforo
                    d = row['data_dt']
                    if pd.notna(d):
                        if ultima_data_dt is None or d > ultima_data_dt:
                            ultima_data_dt = d
                            
            if ultima_data_dt is not None:
                giorni_trascorsi = (datetime.now() - ultima_data_dt).days
                ultima_irrigazione_str = ultima_data_dt.strftime('%d/%m/%Y')
                
    # Calcolo finale della variabile che generava l'errore
    credito_ore = ore_ricaricate - ore_consumate

    st.subheader("🌦️ Previsioni Meteo & Gestione Pozzo (Prepagato)")
    st.markdown("Gestione intelligente del credito acqua e dei turni di irrigazione reali.")

    col_meteo, col_irrig = st.columns([2, 1], gap="large")

    # --- COLONNA DESTRA: PORTAFOGLIO POZZO ---
    with col_irrig:
        with st.container(border=True):
            st.markdown("### 💧 Portafoglio Pozzo")
            
            # Display del monte ore (ora la variabile credito_ore è sempre definita)
            if credito_ore >= 0:
                st.success(f"🔋 **Credito Residuo:** {credito_ore:.1f} Ore")
            else:
                st.error(f"⚠️ **Credito Esaurito (Sofferto):** {credito_ore:.1f} Ore")
                
            if giorni_trascorsi < 999:
                st.info(f"**Ultimo Turno:** {ultima_irrigazione_str} ({giorni_trascorsi} gg fa)")
            
            # Tasto 1: RICARICA SCHEDA (Genera Costo)
            with st.expander("💳 1. Ricarica Scheda", expanded=False):
                with st.form("form_ricarica", clear_on_submit=True):
                    st.write("Acquista nuove ore (Crea uscita a bilancio):")
                    data_ricarica = st.date_input("Data", format="DD/MM/YYYY")
                    ore_da_comprare = st.number_input("Ore (Costo: 20€/h)", min_value=1.0, step=1.0, value=24.0)
                    stato_pag = st.radio("Pagamento", ["Saldato", "Da Saldare"], horizontal=True)
                    
                    if st.form_submit_button("Aggiungi Credito", type="primary"):
                        costo = ore_da_comprare * 20.0
                        stato_db = "Saldato" if "Saldato" in stato_pag else "Impegnato"
                        nuova_riga = {
                            'data': data_ricarica.strftime('%Y-%m-%d'), 'tipo': 'Uscita', 'categoria': 'Irrigazione',
                            'descrizione': f"Ricarica Pozzo | {ore_da_comprare} ore",
                            'importo': costo, 'prodotto': '', 'stato': stato_db,
                            'totale_fattura': costo, 'importo_pagato': costo if stato_db == "Saldato" else 0.0,
                            'registro_pagamenti': ''
                        }
                        df_meteo_db = pd.concat([df_meteo_db, pd.DataFrame([nuova_riga])], ignore_index=True)
                        if save_to_github(df_meteo_db, sha_meteo_db, f"Ricarica pozzo {ore_da_comprare} ore"):
                            st.success(f"✅ Ricarica di {costo}€ effettuata. +{ore_da_comprare} ore!")
                            time.sleep(1.5); st.rerun()
            
            # Tasto 2: REGISTRA TURNO (Costo Zero)
            with st.expander("💧 2. Registra Turno", expanded=False):
                with st.form("form_consumo", clear_on_submit=True):
                    st.write("Scala ore dal credito (Costo zero a bilancio):")
                    data_turno = st.date_input("Data Irrigazione", format="DD/MM/YYYY")
                    ore_da_usare = st.number_input("Ore consumate", min_value=0.5, step=0.5, value=18.0)
                    note_turno = st.text_input("Note opzionali")
                    
                    if st.form_submit_button("Registra Turno", type="primary"):
                        nuova_riga = {
                            'data': data_turno.strftime('%Y-%m-%d'), 'tipo': 'Uscita', 'categoria': 'Irrigazione',
                            'descrizione': f"Turno Irrigazione | {ore_da_usare} ore | {note_turno}".strip(' |'),
                            'importo': 0.0, 'prodotto': '', 'stato': 'Saldato',
                            'totale_fattura': 0.0, 'importo_pagato': 0.0, 'registro_pagamenti': ''
                        }
                        df_meteo_db = pd.concat([df_meteo_db, pd.DataFrame([nuova_riga])], ignore_index=True)
                        if save_to_github(df_meteo_db, sha_meteo_db, f"Consumo irrigazione {ore_da_usare} ore"):
                            st.success(f"✅ Turno registrato. -{ore_da_usare} ore.")
                            time.sleep(1.5); st.rerun()

            # --- NUOVO REGISTRO CRONOLOGICO TURNI ---
            st.divider()
            st.markdown("#### 📜 Cronologia Turni")
            if not df_irrigazione.empty:
                df_storico_turni = df_irrigazione[
                    (df_irrigazione['importo'] == 0) | 
                    (df_irrigazione['descrizione'].str.contains('Turno', case=False, na=False))
                ].copy()
                
                if not df_storico_turni.empty:
                    df_storico_turni = df_storico_turni.sort_values(by='data', ascending=False)
                    st.dataframe(
                        df_storico_turni[['data', 'descrizione']], 
                        use_container_width=True, 
                        hide_index=True
                    )
                else:
                    st.info("Nessun turno registrato.")
            else:
                st.info("Nessun dato idrico trovato.")

   # --- FUNZIONE CACHE PER IL METEO (Evita l'errore 429) ---
    @st.cache_data(ttl=10800) # Il sistema ricorderà i dati per 3 ore (10800 secondi) senza richiederli al server
    def scarica_meteo_in_cache():
        url_meteo = "https://api.open-meteo.com/v1/forecast"
        parametri_meteo = {
            "latitude": 41.1535,
            "longitude": 16.4132,
            "daily": "temperature_2m_max,precipitation_sum",
            "timezone": "Europe/Rome",
            "past_days": 30,
            "forecast_days": 4
        }
        try:
            resp = requests.get(url_meteo, params=parametri_meteo, timeout=10)
            return resp.json(), resp.status_code
        except Exception:
            return None, 0

    # --- COLONNA SINISTRA: METEO E SEMAFORO AGRONOMICO ---
    with col_meteo:
        st.subheader("🌦️ Previsioni e Ciclo Fenologico")
        
        # --- 0. RECUPERO DATA ULTIMA IRRIGAZIONE DAL DATABASE ---
        ultima_data_dt = None
        giorni_trascorsi = 0
        try:
            df_meteo, _ = get_github_file()
            df_irr = df_meteo[df_meteo['categoria'] == 'Irrigazione'].copy()
            if not df_irr.empty:
                df_irr['data_dt'] = pd.to_datetime(df_irr['data'], errors='coerce')
                ultima_data_dt = df_irr['data_dt'].max()
                if pd.notna(ultima_data_dt):
                    giorni_trascorsi = max(0, (datetime.now() - ultima_data_dt).days)
        except Exception:
            pass

        # 1. MOTORE AGRONOMICO: Calcolo della Fase Fenologica attuale
        mese_oggi = datetime.now().month
        
        if mese_oggi in [3, 4]:
            fase = "🌱 Risveglio / Mignolatura"
            fabbisogno = "Basso"
            soglia_temp = 32.0  
            giorni_allarme = 15
            msg_fase = "Fase di preparazione alla fioritura. Irrigare solo in caso di siccità prolungata."
        elif mese_oggi == 5:
            fase = "🌼 Fioritura"
            fabbisogno = "Moderato"
            soglia_temp = 31.0
            giorni_allarme = 12
            msg_fase = "Fioritura in corso. Evitare stress idrici severi per non compromettere l'allegagione."
        elif mese_oggi == 6:
            fase = "🟢 Allegagione (Formazione Frutto)"
            fabbisogno = "Alto"
            soglia_temp = 31.0
            giorni_allarme = 10
            msg_fase = "I fiori diventano frutti (Allegagione). Lo stress idrico ora causa la cascola delle olivine."
        elif mese_oggi in [7, 8]:
            fase = "🫒 Indurimento Nocciolo / Accrescimento"
            fabbisogno = "CRITICO (Massima esigenza idrica)"
            soglia_temp = 30.0  
            giorni_allarme = 7
            msg_fase = "Fase decisiva. L'acqua è vitale per ingrossare la polpa ed evitare frutti piccoli e raggrinziti."
        elif mese_oggi == 9:
            fase = "💧 Inoliazione (Accumulo Olio)"
            fabbisogno = "Alto (Decisivo per la resa)"
            soglia_temp = 30.0
            giorni_allarme = 10
            msg_fase = "La polpa si riempie d'olio. L'acqua serve ad aumentare i quintali e la resa al frantoio."
        elif mese_oggi == 10:
            fase = "🟣 Invaiatura (Cambio Colore)"
            fabbisogno = "Basso (Pericolo diluizione)"
            soglia_temp = 33.0
            giorni_allarme = 20
            msg_fase = "Sospendere gradualmente l'acqua per concentrare i polifenoli, i profumi e la qualità dell'olio."
        else:
            fase = "❄️ Riposo Invernale / Raccolta"
            fabbisogno = "Nullo"
            soglia_temp = 35.0
            giorni_allarme = 999
            msg_fase = "L'albero è in riposo vegetativo o in fase di raccolta. Nessuna irrigazione richiesta."

        st.info(f"**Fase Attuale:** {fase}\n\n**Esigenza Idrica:** {fabbisogno}\n\n*{msg_fase}*")

        # 2. SCARICAMENTO DATI METEO (TRAMITE CACHE)
        m_data, status_code = scarica_meteo_in_cache()
        
        if status_code == 200 and m_data:
            daily = m_data.get("daily", {})
            dates = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            rain_sums = daily.get("precipitation_sum", [])
            
            if dates and max_temps:
                oggi_str = datetime.now().strftime('%Y-%m-%d')
                indice_oggi = dates.index(oggi_str) if oggi_str in dates else 30
                
                forecast_list = []
                for i in range(indice_oggi, min(indice_oggi + 4, len(dates))):
                    forecast_list.append({
                        "Giorno": dates[i],
                        "Temp Mass (°C)": max_temps[i],
                        "Pioggia (mm)": rain_sums[i] if i < len(rain_sums) else 0.0
                    })
                st.dataframe(pd.DataFrame(forecast_list), use_container_width=True, hide_index=True)
                
                temp_oggi = max_temps[indice_oggi]
                pioggia_oggi = rain_sums[indice_oggi]
                
                # 3. CALCOLO STRESS E ALGORITMO ORE POZZO
                giorni_stress_caldo = 0
                pioggia_accumulata = 0.0
                ore_consigliate = 0
                
                if ultima_data_dt is not None and pd.notna(ultima_data_dt):
                    giorni_da_controllare = min(giorni_trascorsi, 30)
                    start_idx = max(0, indice_oggi - giorni_da_controllare)
                    
                    for i in range(start_idx, indice_oggi):
                        if max_temps[i] >= soglia_temp: 
                            giorni_stress_caldo += 1
                        pioggia_accumulata += rain_sums[i]
                        
                    # --- CALCOLO ORE CONSIGLIATE ---
                    giorni_sconto_pioggia = (pioggia_accumulata / 10.0) * 3.5
                    giorni_debito = max(0.0, giorni_trascorsi - giorni_sconto_pioggia)
                    
                    if mese_oggi in [7, 8]:
                        moltiplicatore = 1.8
                    elif mese_oggi == 9:
                        moltiplicatore = 1.5
                    elif mese_oggi in [5, 6, 10]:
                        moltiplicatore = 1.0
                    else:
                        moltiplicatore = 0.0
                        
                    ore_consigliate = int(round(giorni_debito * moltiplicatore))
                
                st.markdown("### 🚦 Semaforo Dinamico Intelligente")
                
                if ultima_data_dt is not None and pd.notna(ultima_data_dt):
                    st.caption(f"Dall'ultimo turno ({ultima_data_dt.strftime('%d/%m/%Y')}): **{giorni_stress_caldo} gg** oltre i {soglia_temp}°C | Pioggia accumulata: **{pioggia_accumulata:.1f} mm**")
                else:
                    st.caption("Nessuna irrigazione registrata di recente nel database.")
                
                # 4. LOGICA DECISIONALE
                if mese_oggi in [11, 12, 1, 2]:
                    st.success("❄️ **Pausa Invernale:** L'impianto di irrigazione dovrebbe essere spento o svuotato per evitare gelate.")
                elif pioggia_oggi > 2.0:
                    st.success(f"🌧️ **Pioggia in arrivo ({pioggia_oggi} mm):** Impianto spento. Lascia fare alla natura.")
                elif pioggia_accumulata > 15.0 and giorni_trascorsi < 12:
                    st.success(f"✅ **Terreno Bagnato:** Sono caduti {pioggia_accumulata:.1f} mm di pioggia di recente. Le radici hanno scorte sufficienti.")
                elif giorni_trascorsi <= (giorni_allarme / 2):
                    st.success(f"✅ **Pianta Idratata:** Hai irrigato {giorni_trascorsi} giorni fa. La fase di {fase.split()[1]} procede bene.")
                elif giorni_stress_caldo >= giorni_allarme:
                    st.error(f"🔥 **Allarme Stress Idrico:** Sono passati {giorni_trascorsi} gg con troppi giorni sopra i {soglia_temp}°C! Intervenire per proteggere la {fase.split()[1]}.\n\n🎯 **Turno consigliato: {ore_consigliate} ore**")
                elif giorni_trascorsi >= giorni_allarme and giorni_stress_caldo >= 3:
                    st.warning(f"⚠️ **Fabbisogno Crescente:** Nessuna pioggia utile da {giorni_trascorsi} giorni. Il terreno si sta asciugando.\n\n🎯 **Turno consigliato: {ore_consigliate} ore**")
                else:
                    st.info(f"🆗 **Clima Mite:** Temperature sotto controllo dall'ultimo turno. La pianta sopporta bene, risparmia il credito ore del pozzo.")
        elif status_code == 429:
            st.warning("⚠️ Troppe richieste inviate (Errore 429). Il server Open-Meteo ha attivato il blocco di sicurezza temporaneo sul tuo IP. Riprova tra circa un'ora per permettere lo sblocco automatico.")
        else:
            st.warning(f"Impossibile leggere i dati meteo (Codice Errore API: {status_code}).")
    
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
        # --- CORREZIONE CRITICA: SALVATAGGIO DELLE VIRGOLE ITALIANE ---
        # Rimuove simboli euro, spazi e trasforma le virgole in punti prima di calcolare
        df_spesa['importo'] = df_spesa['importo'].astype(str).str.replace('€', '').str.replace(' ', '').str.replace(',', '.')
        df_spesa['importo'] = pd.to_numeric(df_spesa['importo'], errors='coerce').fillna(0)
        
        # Filtro mirato: Nasconde gli 0.00 € SOLO per l'Irrigazione.
        df_validi = df_spesa[
            (df_spesa['stato'].isin(['Saldato', 'Impegnato'])) & 
            ~((df_spesa['importo'] == 0) & (df_spesa['categoria'] == 'Irrigazione'))
        ].copy()
        
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
        df_spese = df_spesa[
            (df_spesa['stato'].isin(['Saldato', 'Impegnato'])) & 
            ~((df_spesa['importo'] == 0) & (df_spesa['categoria'] == 'Irrigazione'))
        ].copy()
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
    st.markdown("Genera un documento PDF ufficiale con il riepilogo e il dettaglio analitico di tutte le operazioni.")

    df_spesa_pdf, _ = get_github_file()

    if not df_spesa_pdf.empty:
        # --- CORREZIONE VIRGOLE ANCHE NEL PDF ---
        df_spesa_pdf['importo'] = df_spesa_pdf['importo'].astype(str).str.replace('€', '').str.replace(' ', '').str.replace(',', '.')
        df_spesa_pdf['importo'] = pd.to_numeric(df_spesa_pdf['importo'], errors='coerce').fillna(0)
        
        df_validi_pdf = df_spesa_pdf[
            (df_spesa_pdf['stato'].isin(['Saldato', 'Impegnato'])) & 
            ~((df_spesa_pdf['importo'] == 0) & (df_spesa_pdf['categoria'] == 'Irrigazione'))
        ].copy()
        
        df_validi_pdf = df_validi_pdf.sort_values(by=['tipo', 'categoria', 'data'])
        df_pdf_data = df_validi_pdf.groupby(['tipo', 'categoria'])['importo'].sum().reset_index()
        
        if not df_pdf_data.empty:
            pdf = FPDF()
            
            # PAGINA 1: RIEPILOGO GENERALE
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, txt="AgriFinance Cloud - Bilancio Aziendale", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            pdf.cell(190, 10, txt=f"Data generazione: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(40, 10, "Tipo", 1, 0, 'C', fill=True)
            pdf.cell(100, 10, "Categoria", 1, 0, 'C', fill=True)
            pdf.cell(50, 10, "Totale (EUR)", 1, 1, 'C', fill=True)
            
            pdf.set_font("Arial", size=9)
            totale_entrate = 0.0
            totale_uscite = 0.0
            
            for _, row in df_pdf_data.iterrows():
                tipo_op = str(row['tipo'])
                cat_op = str(row['categoria'])[:30]
                imp_op = float(row['importo'])
                
                if tipo_op == "Entrata":
                    totale_entrate += imp_op
                else:
                    totale_uscite += imp_op
                
                pdf.cell(40, 8, tipo_op, 1, 0, 'L')
                pdf.cell(100, 8, cat_op, 1, 0, 'L')
                pdf.cell(50, 8, f"{imp_op:,.2f} EUR", 1, 1, 'R')
            
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 11)
            utile_esercizio = totale_entrate - totale_uscite
            pdf.cell(140, 10, "Totale Ricavi / Entrate:", 1, 0, 'L')
            pdf.cell(50, 10, f"{totale_entrate:,.2f} EUR", 1, 1, 'R')
            
            pdf.cell(140, 10, "Totale Costi / Uscite:", 1, 0, 'L')
            pdf.cell(50, 10, f"{totale_uscite:,.2f} EUR", 1, 1, 'R')
            
            if utile_esercizio >= 0:
                pdf.set_text_color(40, 167, 69)
            else:
                pdf.set_text_color(220, 53, 69)
                
            pdf.cell(140, 10, "Risultato d'Esercizio (Utile / Perdita):", 1, 0, 'L')
            pdf.cell(50, 10, f"{utile_esercizio:,.2f} EUR", 1, 1, 'R')
            pdf.set_text_color(0, 0, 0)
            
            # PAGINA 2: DETTAGLIO ANALITICO CON TOTALI
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(190, 10, txt="Dettaglio Analitico delle Operazioni", ln=True, align='C')
            pdf.ln(5)
            
            categorie_uniche = df_validi_pdf['categoria'].unique()
            
            for cat in sorted(categorie_uniche):
                df_cat = df_validi_pdf[df_validi_pdf['categoria'] == cat]
                totale_categoria = df_cat['importo'].sum() 
                
                pdf.set_font("Arial", 'B', 11)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(190, 8, f"Categoria: {cat}", 1, 1, 'L', fill=True)
                
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(30, 8, "Data", 1, 0, 'C')
                pdf.cell(100, 8, "Descrizione", 1, 0, 'C')
                pdf.cell(30, 8, "Stato", 1, 0, 'C')
                pdf.cell(30, 8, "Importo", 1, 1, 'C')
                
                pdf.set_font("Arial", size=8)
                for _, riga in df_cat.iterrows():
                    data_op = str(riga['data'])
                    desc_op = str(riga['descrizione'])[:50] 
                    stato_op = str(riga['stato'])
                    imp_op = float(riga['importo'])
                    
                    pdf.cell(30, 6, data_op, 1, 0, 'C')
                    pdf.cell(100, 6, desc_op, 1, 0, 'L')
                    pdf.cell(30, 6, stato_op, 1, 0, 'C')
                    pdf.cell(30, 6, f"{imp_op:,.2f} EUR", 1, 1, 'R')
                
                pdf.set_font("Arial", 'B', 9)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(160, 6, f"TOTALE {cat.upper()}", 1, 0, 'R', fill=True)
                pdf.cell(30, 6, f"{totale_categoria:,.2f} EUR", 1, 1, 'R', fill=True)
                
                pdf.ln(6) 

            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            
            st.success("✅ Documento PDF completo di dettagli generato con successo!")
            st.download_button(
                label="📄 Clicca qui per Scaricare il Bilancio Dettagliato in PDF",
                data=pdf_bytes,
                file_name=f'Bilancio_Analitico_{datetime.now().strftime("%Y_%m_%d")}.pdf',
                mime='application/pdf',
                type="primary",
                use_container_width=True
            )
        else:
            st.info("Nessun dato sufficiente per generare il PDF.")
    else:
        st.warning("Il database è vuoto.")
    

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
