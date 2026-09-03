import streamlit as st
import pandas as pd
import requests
import base64
import json
from datetime import datetime
import time
import calendar

# Configurazione ottimizzata
st.set_page_config(page_title="Foglio Mensile", page_icon="🚜", layout="centered")

# --- CONNESSIONE GITHUB ---
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
        from io import StringIO
        return pd.read_csv(StringIO(content)), data['sha']
    else:
        colonne = ['timestamp', 'lavoratore', 'tipo', 'valore', 'note', 'stato']
        return pd.DataFrame(columns=colonne), None

def salva_richiesta(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_RICHIESTE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    csv_data = df.to_csv(index=False)
    encoded_data = base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')
    payload = {"message": "Invio foglio mensile", "content": encoded_data}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, data=json.dumps(payload))
    return r.status_code in [200, 201]

# --- INTERFACCIA APP ---
st.title("🚜 Foglio Presenze Mensile")

df_richieste, sha_attuale = get_richieste()
nome_dipendente = st.selectbox("👤 Chi sei?", ["Seleziona il tuo nome...", "Iannone Felice"])

if nome_dipendente != "Seleziona il tuo nome...":
    tab1, tab2 = st.tabs(["📝 Compila Mese", "🗂️ Storico Inviati"])
    
    # ==========================================
    # --- TAB 1: GRIGLIA MENSILE ---
    # ==========================================
    with tab1:
        st.info("💡 **Istruzioni:** Compila questa tabella alla fine del mese con tutti i giorni lavorati e clicca su Invia.")
        
        # Selezione Mese e Anno
        oggi = datetime.today()
        mesi_nomi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 
                     7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
        
        c1, c2 = st.columns(2)
        with c1:
            mese_sel = st.selectbox("Mese di Riferimento", list(mesi_nomi.values()), index=oggi.month-1)
        with c2:
            anno_sel = st.selectbox("Anno", [oggi.year, oggi.year-1], index=0)
            
        mese_num = list(mesi_nomi.keys())[list(mesi_nomi.values()).index(mese_sel)]
        giorni_nel_mese = calendar.monthrange(anno_sel, mese_num)[1]
        
        # Creazione della tabella vuota per quel mese
        if 'dati_griglia' not in st.session_state or st.session_state.get('mese_corrente') != f"{mese_sel}_{anno_sel}":
            df_vuoto = pd.DataFrame({
                "Giorno": range(1, giorni_nel_mese + 1),
                "Ore Lavoro": [0.0] * giorni_nel_mese,
                "Spese (€)": [0.0] * giorni_nel_mese,
                "Note (Lavori / Scontrini)": [""] * giorni_nel_mese
            })
            st.session_state.dati_griglia = df_vuoto
            st.session_state.mese_corrente = f"{mese_sel}_{anno_sel}"
            
        st.markdown("### ✍️ Tabella Giornaliera")
        
        # La griglia modificabile dal dipendente
        df_modificato = st.data_editor(
            st.session_state.dati_griglia, 
            disabled=["Giorno"], # Impedisce di cancellare i numeri dei giorni
            hide_index=True,
            use_container_width=True,
            column_config={
                "Ore Lavoro": st.column_config.NumberColumn("Ore Lavoro", min_value=0.0, max_value=24.0, step=0.5),
                "Spese (€)": st.column_config.NumberColumn("Spese (€)", min_value=0.0, step=1.0),
                "Note (Lavori / Scontrini)": st.column_config.TextColumn("Cosa hai fatto?")
            }
        )
        
        # Totali in tempo reale
        tot_ore = df_modificato['Ore Lavoro'].sum()
        tot_spese = df_modificato['Spese (€)'].sum()
        
        st.success(f"**Totale accumulato nel mese:** {tot_ore} Ore | {tot_spese} € Spese")
        
        # Tasto di invio
        if st.button("🚀 Invia Foglio Mensile all'Azienda", type="primary", use_container_width=True):
            # Filtriamo solo i giorni in cui ha scritto qualcosa
            giorni_compilati = df_modificato[(df_modificato['Ore Lavoro'] > 0) | (df_modificato['Spese (€)'] > 0)]
            
            if giorni_compilati.empty:
                st.warning("⚠️ La tabella è vuota! Inserisci le ore o le spese in almeno un giorno.")
            else:
                # Creiamo il riepilogo testuale per te
                dettaglio_note = f"Dettaglio giorni di {mese_sel} {anno_sel}:\n"
                for _, row in giorni_compilati.iterrows():
                    dettaglio_note += f"• Giorno {int(row['Giorno'])}: "
                    if row['Ore Lavoro'] > 0: dettaglio_note += f"{row['Ore Lavoro']} ore. "
                    if row['Spese (€)'] > 0: dettaglio_note += f"Spese: {row['Spese (€)']}€. "
                    if row['Note (Lavori / Scontrini)']: dettaglio_note += f"({row['Note (Lavori / Scontrini)']})"
                    dettaglio_note += "\n"
                    
                nuova_riga = {
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'lavoratore': nome_dipendente,
                    'tipo': f"Riepilogo Mensile - {mese_sel} {anno_sel}",
                    'valore': f"TOTALE: {tot_ore} Ore | {tot_spese} €",
                    'note': dettaglio_note,
                    'stato': "In Attesa"
                }
                
                df_richieste = pd.concat([df_richieste, pd.DataFrame([nuova_riga])], ignore_index=True)
                
                with st.spinner("Invio in corso..."):
                    if salva_richiesta(df_richieste, sha_attuale):
                        st.success(f"✅ Foglio di {mese_sel} inviato con successo!")
                        
                        # Resetta la tabella dopo l'invio per evitare doppi invii
                        st.session_state.dati_griglia = pd.DataFrame({
                            "Giorno": range(1, giorni_nel_mese + 1),
                            "Ore Lavoro": [0.0] * giorni_nel_mese,
                            "Spese (€)": [0.0] * giorni_nel_mese,
                            "Note (Lavori / Scontrini)": [""] * giorni_nel_mese
                        })
                        time.sleep(3)
                        st.rerun()
                    else:
                        st.error("❌ Errore di rete.")

    # ==========================================
    # --- TAB 2: STORICO INVII ---
    # ==========================================
    with tab2:
        st.markdown("### 🗂️ Storico Fogli Inviati")
        if not df_richieste.empty:
            df_mio = df_richieste[df_richieste['lavoratore'] == nome_dipendente].copy()
            if not df_mio.empty:
                df_display = df_mio[['tipo', 'valore', 'stato', 'timestamp']].copy()
                df_display.columns = ['Mese', 'Totali Dichiarati', 'Stato Azienda', 'Data Invio']
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.info("Nessun foglio mensile inviato finora.")
else:
    st.info("Seleziona il tuo nome in alto per sbloccare la tabella mensile.")
