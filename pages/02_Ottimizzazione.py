import streamlit as st
import pandas as pd
import requests
import base64
import io

st.set_page_config(page_title="Analisi Margini e KPI", layout="wide")

# --- CONFIGURAZIONE ARCHITETTURALE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "antonellomazzilli-bit/agri-finance"
FILE_PATH = "database.csv"

def format_euro(val):
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def load_github_data():
    """Scarica il database centrale cloud."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return pd.read_csv(io.StringIO(content))
    return pd.DataFrame()

def parse_descrizione_operaio(descrizione):
    """Estrae le giornate e le ore lavorate dalla stringa dell'app."""
    try:
        if "|" in str(descrizione):
            parti = descrizione.split("|")
            info_tempo = parti[1].strip()
            giornate = float(info_tempo.split(" gg")[0].strip())
            ore = float(info_tempo.split("(")[1].split(" ore")[0].strip()) if "(" in info_tempo else 0.0
            return giornate, ore
    except:
        pass
    return 0.0, 0.0

st.title("📈 Cruscotto di Ottimizzazione e KPI")
st.markdown("Analisi finanziaria per annata agricola. I dati sono calcolati in tempo reale esclusivamente dal database Cloud unificato.")

df_git = load_github_data()

if not df_git.empty:
    # --- PRE-PROCESSING DATI ---
    df_git['data_dt'] = pd.to_datetime(df_git['data'], errors='coerce')
    df_git = df_git.dropna(subset=['data_dt'])
    df_git['Anno'] = df_git['data_dt'].dt.year
    df_git['importo'] = pd.to_numeric(df_git['importo'], errors='coerce').fillna(0.0)

    # Gestione di sicurezza: se 'coltura_id' non esiste, creiamo una colonna fittizia
    if 'coltura_id' not in df_git.columns:
        df_git['coltura_id'] = 'Generica'

    # --- SELEZIONE ANNATA E COLTURA ---
    anni_disponibili = sorted(df_git['Anno'].unique(), reverse=True)
    colture_disponibili = df_git['coltura_id'].unique().tolist()
    
    c_filtro1, c_filtro2 = st.columns(2)
    with c_filtro1:
        anno_sel = st.selectbox("📅 Seleziona l'Annata Agraria:", anni_disponibili)
    with c_filtro2:
        idx_olive = colture_disponibili.index('Olive') if 'Olive' in colture_disponibili else 0
        coltura_sel = st.selectbox("🌱 Seleziona la Coltura:", colture_disponibili, index=idx_olive)

    st.divider()

    # Filtriamo il database per la selezione corrente
    df_anno = df_git[(df_git['Anno'] == anno_sel) & (df_git['coltura_id'] == coltura_sel)]

    if df_anno.empty:
        st.info(f"Nessun dato finanziario registrato per la coltura '{coltura_sel}' nell'anno {anno_sel}.")
    else:
        # --- CALCOLI AGGREGATI TOTALI ---
        df_uscite = df_anno[df_anno['tipo'] == 'Uscita']
        df_entrate = df_anno[df_anno['tipo'] == 'Entrata']
        df_rese = df_anno[df_anno['tipo'] == 'Resa']

        costi_totali = df_uscite['importo'].sum()
        ricavi_totali = df_entrate['importo'].sum()
        margine = ricavi_totali - costi_totali
        kg_raccolti = df_rese['importo'].sum()

        # --- ESTRAZIONE DATI MANODOPERA CORRETTA ---
        # 1. Costi Reali (Buste, Extra, F24, Oneri)
        cat_costi_lavoro = ['Busta Paga', 'Saldo Extra', 'Oneri', 'F24', 'Contributi']
        costo_manodopera = df_uscite[df_uscite['categoria'].isin(cat_costi_lavoro)]['importo'].sum()
        
        # 2. Giornate e Ore Lavorate (Pesca sia ufficiali che extra)
        df_presenze = df_anno[df_anno['categoria'].isin(['Manodopera', 'Manodopera Extra'])]
        giornate_totali = 0.0
        ore_totali = 0.0
        
        for _, row in df_presenze.iterrows():
            gg, ore = parse_descrizione_operaio(row['descrizione'])
            giornate_totali += gg
            # Se nel database non ci sono scritte le ore, calcoliamo in automatico 6 ore per ogni giornata
            if ore == 0.0 and gg > 0:
                ore_totali += gg * 6.0
            else:
                ore_totali += ore

        # --- LAYOUT: SINTESI FINANZIARIA ---
        st.subheader(f"📊 Sintesi Economica Globale ({anno_sel})")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("🔴 Costi Totali", format_euro(costi_totali))
        k2.metric("🟢 Ricavi Totali", format_euro(ricavi_totali))
        k3.metric("💶 Margine Operativo", format_euro(margine), delta=f"{margine:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        k4.metric("📦 Resa Totale", f"{kg_raccolti:,.0f} Kg".replace(",", "."))

        st.divider()

        # --- LAYOUT: METRICHE DI EFFICIENZA (KPI) ---
        st.subheader("⚙️ Indici di Ottimizzazione Agricola")
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        
        with c_kpi1:
            costo_kg = (costi_totali / kg_raccolti) if kg_raccolti > 0 else 0.0
            st.metric("🎯 Costo di Produzione", f"{costo_kg:,.2f} €/Kg".replace(".", ","), help="Indica quanto ti costa produrre 1 Kg di prodotto (Uscite totali / Resa totale).")
            
        with c_kpi2:
            incidenza_mano = (costo_manodopera / costi_totali * 100) if costi_totali > 0 else 0.0
            st.metric("🧑‍🌾 Incidenza Costo Lavoro", f"{incidenza_mano:,.1f} %".replace(".", ","), help="Percentuale assorbita dai costi della manodopera rispetto al totale delle uscite.")
            
        with c_kpi3:
            costo_ora = (costo_manodopera / ore_totali) if ore_totali > 0 else 0.0
            st.metric("⏱️ Costo Orario Medio Lavoro", format_euro(costo_ora), help="Rapporto tra l'importo totale pagato agli operai (buste, extra, oneri) e le ore stimate/lavorate.")

        # --- LAYOUT: RIPARTIZIONE DEI COSTI ---
        st.divider()
        st.subheader("🥧 Distribuzione e Analisi delle Uscite")
        if not df_uscite.empty:
            costi_per_cat = df_uscite.groupby('categoria')['importo'].sum().reset_index()
            costi_per_cat = costi_per_cat.sort_values(by='importo', ascending=False)
            costi_per_cat = costi_per_cat.rename(columns={'categoria': 'Categoria', 'importo': 'Importo (€)'})
            
            col_chart, col_data = st.columns([2, 1])
            with col_chart:
                st.bar_chart(costi_per_cat.set_index('Categoria'), color="#B71C1C", height=350)
            with col_data:
                df_view = costi_per_cat.copy()
                df_view['Importo (€)'] = df_view['Importo (€)'].apply(lambda x: format_euro(x))
                st.dataframe(df_view, use_container_width=True, hide_index=True)
            
            st.info(f"💡 **Insight Forza Lavoro:** Nel corso dell'annata {anno_sel}, sono state rilevate **{giornate_totali:,.1f} giornate** lavorative, equivalenti a **{ore_totali:,.1f} ore** di impiego per la coltura selezionata.")
        else:
            st.write("Nessuna uscita registrata per i filtri selezionati.")

else:
    st.warning("Il database è vuoto. Inizia a registrare movimenti e rese per attivare il motore di ottimizzazione.")
