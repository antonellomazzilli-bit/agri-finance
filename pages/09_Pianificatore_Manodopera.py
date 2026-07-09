import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime

st.set_page_config(page_title="Pianificatore Manodopera", layout="wide")

# --- CONFIGURAZIONE E COLLEGAMENTO ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

# Pesi olivicoli standard (proporzione del lavoro nei vari mesi)
# Gen, Feb(Potatura), Mar(Potatura), Apr, Mag, Giu, Lug, Ago, Set, Ott(Inizio Raccolta), Nov(Raccolta), Dic
PESI_OLIVO = [5, 12, 12, 6, 6, 5, 4, 4, 6, 15, 20, 5]

MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

def load_github_data():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def estrai_giornate_operaio(descrizione, nome_target):
    """Cerca il nome esatto nella stringa e ne estrae le giornate."""
    try:
        if "|" in str(descrizione) and nome_target.lower() in str(descrizione).lower():
            parti = descrizione.split("|")
            info_tempo = parti[1].strip()
            return float(info_tempo.split(" gg")[0].strip())
    except:
        pass
    return 0.0

st.title("📅 Pianificatore Annuale Manodopera")
st.markdown("Imposta il tetto massimo di giornate e distribuiscile. Il sistema calcolerà le quote future adattandosi dinamicamente ai tuoi inserimenti.")

# --- IMPOSTAZIONI ---
col_set1, col_set2, col_set3 = st.columns(3)
with col_set1:
    anno_sel = st.selectbox("Anno di Pianificazione:", [2026, 2025, 2027])
with col_set2:
    dipendente_target = st.text_input("Dipendente sotto contratto:", value="Iannone Felice")
with col_set3:
    tetto_giornate = st.number_input("Target Giornate Annuali:", min_value=1.0, value=160.0, step=1.0)

st.divider()

with st.spinner("Sincronizzazione col database per leggere i consuntivi reali..."):
    df_git = load_github_data()
    
    # Inizializziamo l'array dei giorni effettivi (già fatti e registrati)
    giornate_effettive = [0.0] * 12
    
    if not df_git.empty:
        df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
        df_lavoro = df_git[(df_git['data_dt'].dt.year == anno_sel) & (df_git['categoria'] == 'Manodopera')]
        
        for _, row in df_lavoro.iterrows():
            gg_lavorate = estrai_giornate_operaio(row['descrizione'], dipendente_target)
            if gg_lavorate > 0 and pd.notna(row['data_dt']):
                mese_idx = row['data_dt'].month - 1
                giornate_effettive[mese_idx] += gg_lavorate

    # --- LOGICA DI RICALCOLO A CASCATA ---
    # Usiamo Session State per memorizzare le "forzature manuali" dell'utente sulla tabella
    if 'pianificazioni_manuali' not in st.session_state or st.session_state.get('anno_plan') != anno_sel:
        st.session_state.pianificazioni_manuali = {i: None for i in range(12)}
        st.session_state.anno_plan = anno_sel

    # Calcolo base
    giornate_pianificate = [0.0] * 12
    totale_consumato_finora = sum(giornate_effettive)
    giornate_da_spalmare = tetto_giornate - totale_consumato_finora

    # Assegnazione
    for i in range(12):
        # Se il mese è nel passato o ha già giornate effettive, la pianificazione futura è 0
        if giornate_effettive[i] > 0:
            giornate_pianificate[i] = 0.0
        else:
            # Se l'utente ha forzato un valore a mano per questo mese, usiamo quello
            if st.session_state.pianificazioni_manuali[i] is not None:
                valore_forzato = st.session_state.pianificazioni_manuali[i]
                giornate_pianificate[i] = valore_forzato
                giornate_da_spalmare -= valore_forzato
            else:
                # Altrimenti lasciamo il calcolo in sospeso per la spalmatura proporzionale
                giornate_pianificate[i] = -1.0 

    # Ripartizione proporzionale del "Resto" sui mesi non toccati
    mesi_da_calcolare = [i for i, val in enumerate(giornate_pianificate) if val == -1.0]
    somma_pesi_residui = sum([PESI_OLIVO[i] for i in mesi_da_calcolare])

    for i in mesi_da_calcolare:
        if somma_pesi_residui > 0 and giornate_da_spalmare > 0:
            quota = (PESI_OLIVO[i] / somma_pesi_residui) * giornate_da_spalmare
            giornate_pianificate[i] = round(quota, 1)
        else:
            giornate_pianificate[i] = 0.0

    # --- CREAZIONE DEL DATAFRAME INTERATTIVO ---
    dati_tabella = []
    for i in range(12):
        dati_tabella.append({
            "Mese": MESI[i],
            "Consuntivate (Da DB)": giornate_effettive[i],
            "Pianificate (Modificabili)": giornate_pianificate[i]
        })
        
    df_plan = pd.DataFrame(dati_tabella)
    df_plan["Totale Mese"] = df_plan["Consuntivate (Da DB)"] + df_plan["Pianificate (Modificabili)"]

    st.subheader("⚙️ Regolazione Dinamica")
    st.write("Modifica la colonna **'Pianificate'**. I mesi successivi si ricalcoleranno in automatico per farti raggiungere sempre l'obiettivo.")
    
    # Data Editor
    df_modificato = st.data_editor(
        df_plan,
        disabled=["Mese", "Consuntivate (Da DB)", "Totale Mese"],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Consuntivate (Da DB)": st.column_config.NumberColumn(format="%.1f gg"),
            "Pianificate (Modificabili)": st.column_config.NumberColumn(format="%.1f gg", min_value=0.0),
            "Totale Mese": st.column_config.NumberColumn(format="%.1f gg")
        }
    )
    
    # Intercettiamo le modifiche fatte dall'utente
    cambiamenti = False
    for i in range(12):
        vecchio_valore = giornate_pianificate[i]
        nuovo_valore = df_modificato.at[i, "Pianificate (Modificabili)"]
        
        # Se l'utente ha modificato la cella (con una tolleranza di arrotondamento)
        if abs(vecchio_valore - nuovo_valore) > 0.01:
            st.session_state.pianificazioni_manuali[i] = nuovo_valore
            cambiamenti = True
            
    if cambiamenti:
        st.rerun()

    # --- CONTROLLO FINALE E ALERT ---
    totale_generale = df_modificato["Totale Mese"].sum()
    
    st.divider()
    c_res1, c_res2 = st.columns(2)
    
    with c_res1:
        if totale_generale > tetto_giornate:
            st.error(f"⚠️ ATTENZIONE: Stai sforando il tetto! Totale calcolato: **{totale_generale:,.1f} gg** (Massimo consentito: {tetto_giornate})")
        elif totale_generale < tetto_giornate:
            st.warning(f"⚖️ Tetto non raggiunto. Totale calcolato: **{totale_generale:,.1f} gg** su {tetto_giornate}.")
        else:
            st.success(f"✅ Perfetto! L'allocazione raggiunge esattamente le **{tetto_giornate} giornate** contrattuali.")
            
    with c_res2:
        if st.button("🔄 Ripristina Curve di Default"):
            st.session_state.pianificazioni_manuali = {i: None for i in range(12)}
            st.rerun()

    # --- GRAFICO VISIVO ---
    st.subheader("📊 Andamento Annuale")
    df_chart = df_modificato.copy()
    df_chart = df_chart.set_index("Mese")
    st.bar_chart(df_chart[["Consuntivate (Da DB)", "Pianificate (Modificabili)"]], color=["#1A237E", "#4CAF50"])
