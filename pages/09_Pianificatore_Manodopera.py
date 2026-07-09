import streamlit as st
import pandas as pd
import requests
import base64
import io
import calendar
import math
from datetime import datetime, date

st.set_page_config(page_title="Pianificatore Manodopera", layout="wide")

# --- CONFIGURAZIONE E COLLEGAMENTO ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

# Pesi olivicoli standard (proporzione del lavoro nei vari mesi)
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
    try:
        if "|" in str(descrizione) and nome_target.lower() in str(descrizione).lower():
            parti = descrizione.split("|")
            info_tempo = parti[1].strip()
            return float(info_tempo.split(" gg")[0].strip())
    except:
        pass
    return 0.0

def is_festivo_italiano(d):
    """Rileva fine settimana e festività fisse/mobili italiane."""
    if d.weekday() in [5, 6]: # Sabato e Domenica
        return True
    festivita_fisse = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    if (d.month, d.day) in festivita_fisse:
        return True
    # Pasquette per gli anni di riferimento
    if d.year == 2025 and d.month == 4 and d.day == 21: return True
    if d.year == 2026 and d.month == 4 and d.day == 6: return True
    if d.year == 2027 and d.month == 3 and d.day == 29: return True
    return False

def calcola_giorni_lavorativi(anno, mese):
    """Conta i giorni fertili del mese escludendo festivi."""
    _, num_giorni = calendar.monthrange(anno, mese)
    lavorativi = 0
    for g in range(1, num_giorni + 1):
        if not is_festivo_italiano(date(anno, mese, g)):
            lavorativi += 1
    return lavorativi

st.title("📅 Pianificatore Annuale Manodopera")
st.markdown("Imposta il tetto e distribuisci. Il sistema ripartirà i giorni interi rispettando la capienza massima feriale di ogni mese.")

# --- IMPOSTAZIONI ---
col_set1, col_set2, col_set3 = st.columns(3)
with col_set1:
    anno_sel = st.selectbox("Anno di Pianificazione:", [2026, 2025, 2027])
with col_set2:
    dipendente_target = st.text_input("Dipendente sotto contratto:", value="Iannone Felice")
with col_set3:
    tetto_giornate = st.number_input("Target Giornate Annuali:", min_value=1, value=160, step=1)

st.divider()

with st.spinner("Sincronizzazione calendario e lettura database..."):
    df_git = load_github_data()
    giornate_effettive = [0.0] * 12
    
    if not df_git.empty:
        df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
        df_lavoro = df_git[(df_git['data_dt'].dt.year == anno_sel) & (df_git['categoria'] == 'Manodopera')]
        
        for _, row in df_lavoro.iterrows():
            gg_lavorate = estrai_giornate_operaio(row['descrizione'], dipendente_target)
            if gg_lavorate > 0 and pd.notna(row['data_dt']):
                mese_idx = row['data_dt'].month - 1
                giornate_effettive[mese_idx] += gg_lavorate

    if 'pianificazioni_manuali' not in st.session_state or st.session_state.get('anno_plan') != anno_sel:
        st.session_state.pianificazioni_manuali = {i: None for i in range(12)}
        st.session_state.anno_plan = anno_sel

    # --- CALCOLO CAPIENZE MENSILI ---
    capacita_libera = [0] * 12
    giorni_max_calendario = [0] * 12
    for i in range(12):
        lavorativi = calcola_giorni_lavorativi(anno_sel, i + 1)
        giorni_max_calendario[i] = lavorativi
        capacita_libera[i] = max(0, lavorativi - int(math.ceil(giornate_effettive[i])))

    giornate_pianificate = [0] * 12
    totale_consumato_finora = sum(giornate_effettive)
    giornate_da_spalmare = int(round(tetto_giornate - totale_consumato_finora))

    mesi_da_calcolare = []

    # 1. Assegnazione Consuntivi e Forzature
    for i in range(12):
        if giornate_effettive[i] > 0:
            giornate_pianificate[i] = 0
        else:
            if st.session_state.pianificazioni_manuali[i] is not None:
                valore_forzato = int(st.session_state.pianificazioni_manuali[i])
                # Muro di gomma: non permette di forzare più giorni di quanti ne ha il calendario
                valore_forzato = min(valore_forzato, capacita_libera[i])
                
                giornate_pianificate[i] = valore_forzato
                giornate_da_spalmare -= valore_forzato
                capacita_libera[i] -= valore_forzato
            else:
                giornate_pianificate[i] = -1
                mesi_da_calcolare.append(i)

    # 2. Inizializziamo a zero i mesi da calcolare
    for i in mesi_da_calcolare:
        giornate_pianificate[i] = 0

    # 3. Spalmatura Algoritmica per Numeri Interi
    # Assegna 1 giorno alla volta al mese con il rapporto più basso rispetto al suo "peso",
    # fermandosi immediatamente se il mese raggiunge la sua capienza massima lavorativa.
    while giornate_da_spalmare > 0 and sum([capacita_libera[i] for i in mesi_da_calcolare]) > 0:
        best_month = None
        lowest_ratio = float('inf')
        
        for i in mesi_da_calcolare:
            if capacita_libera[i] > 0:
                peso = PESI_OLIVO[i] if PESI_OLIVO[i] > 0 else 0.1
                ratio = giornate_pianificate[i] / peso
                if ratio < lowest_ratio:
                    lowest_ratio = ratio
                    best_month = i
                    
        if best_month is not None:
            giornate_pianificate[best_month] += 1
            capacita_libera[best_month] -= 1
            giornate_da_spalmare -= 1
        else:
            break

    # --- TABELLA INTERATTIVA ---
    dati_tabella = []
    for i in range(12):
        dati_tabella.append({
            "Mese": MESI[i],
            "Capienza Calendario": giorni_max_calendario[i],
            "Consuntivate (Da DB)": giornate_effettive[i],
            "Pianificate (Modificabili)": int(giornate_pianificate[i])
        })
        
    df_plan = pd.DataFrame(dati_tabella)
    df_plan["Totale Mese"] = df_plan["Consuntivate (Da DB)"] + df_plan["Pianificate (Modificabili)"]

    st.subheader("⚙️ Regolazione Dinamica a Numeri Interi")
    
    df_modificato = st.data_editor(
        df_plan,
        disabled=["Mese", "Capienza Calendario", "Consuntivate (Da DB)", "Totale Mese"],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Capienza Calendario": st.column_config.NumberColumn(format="%d gg lavorativi"),
            "Consuntivate (Da DB)": st.column_config.NumberColumn(format="%.1f gg"),
            "Pianificate (Modificabili)": st.column_config.NumberColumn(format="%d gg", min_value=0, step=1),
            "Totale Mese": st.column_config.NumberColumn(format="%.1f gg")
        }
    )
    
    cambiamenti = False
    for i in range(12):
        vecchio_valore = int(giornate_pianificate[i])
        nuovo_valore = int(df_modificato.at[i, "Pianificate (Modificabili)"])
        
        if vecchio_valore != nuovo_valore:
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
            if giornate_da_spalmare > 0:
                st.warning(f"⚖️ Tetto non raggiunto ({totale_generale:,.1f} gg). **Il calendario feriale è completamente saturo!** Non ci sono più giorni utili nell'anno per spalmare il resto.")
            else:
                st.warning(f"⚖️ Tetto non raggiunto. Totale calcolato: **{totale_generale:,.1f} gg** su {tetto_giornate}.")
        else:
            st.success(f"✅ Perfetto! L'allocazione intera raggiunge esattamente le **{tetto_giornate} giornate** contrattuali.")
            
    with c_res2:
        if st.button("🔄 Ripristina Curve di Default"):
            st.session_state.pianificazioni_manuali = {i: None for i in range(12)}
            st.rerun()

    # --- GRAFICO VISIVO ---
    st.subheader("📊 Andamento Annuale")
    df_chart = df_modificato.copy()
    df_chart = df_chart.set_index("Mese")
    st.bar_chart(df_chart[["Consuntivate (Da DB)", "Pianificate (Modificabili)"]], color=["#1A237E", "#4CAF50"])
