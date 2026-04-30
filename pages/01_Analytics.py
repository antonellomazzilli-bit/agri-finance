import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# --- CONFIGURAZIONE DASHBOARD ---
st.set_page_config(page_title="AgriFinance Analytics", layout="wide")

DB_NAME = 'agri_finance.db'

# --- 1. RECUPERO DATI ---
def load_data():
    """Legge i dati dal DB e restituisce un DataFrame pulito."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            query = "SELECT * FROM transactions"
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                return df
            
            # --- 2. TRASFORMAZIONE ---
            # Conversione data e creazione raggruppamento temporale
            df['data'] = pd.to_datetime(df['data'])
            df['Mese-Anno'] = df['data'].dt.strftime('%Y-%m')
            return df
    except Exception as e:
        st.error(f"Errore nel caricamento dati: {e}")
        return pd.DataFrame()

# --- LOGICA DASHBOARD ---
def main():
    st.title("📊 Business Intelligence Agricola")
    st.markdown("Analisi delle performance finanziarie e dei costi colturali.")

    df = load_data()

    if df.empty:
        st.warning("Il database è vuoto o non esiste. Inserisci dei dati per visualizzare l'analisi.")
        return

    # --- 5. FILTRI (Sidebar) ---
    st.sidebar.header("Filtri di Analisi")
    
    # Lista unica di colture + opzione per vederle tutte
    colture_disponibili = ["Tutte"] + sorted(df['coltura_id'].unique().tolist())
    scelta_coltura = st.sidebar.selectbox("Seleziona Coltura", colture_disponibili)

    # Applicazione filtro
    if scelta_coltura != "Tutte":
        df_filtered = df[df['coltura_id'] == scelta_coltura]
    else:
        df_filtered = df

    # --- 3. VISUALIZZAZIONE CASH FLOW (Bar Chart) ---
    st.subheader(f"Flussi di Cassa: {scelta_coltura}")
    
    # Raggruppamento per Mese-Anno e Tipo
    cash_flow = df_filtered.groupby(['Mese-Anno', 'tipo'])['importo'].sum().reset_index()
    
    fig_bar = px.bar(
        cash_flow, 
        x='Mese-Anno', 
        y='importo', 
        color='tipo',
        barmode='group',
        color_discrete_map={'Entrata': '#2ECC71', 'Uscita': '#E74C3C'},
        labels={'importo': 'Totale (€)', 'Mese-Anno': 'Periodo'},
        title="Entrate vs Uscite Mensili"
    )
    fig_bar.update_layout(hovermode="x unified")
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- 4. VISUALIZZAZIONE COSTI (Pie Chart) ---
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Distribuzione dei Costi")
        df_uscite = df_filtered[df_filtered['tipo'] == 'Uscita']
        
        if not df_uscite.empty:
            fig_pie = px.pie(
                df_uscite, 
                values='importo', 
                names='categoria',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Reds_r,
                title="Scomposizione Uscite per Categoria"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Nessuna uscita registrata per questo filtro.")

    with col2:
        st.subheader("Riepilogo Numerico")
        tot_entrate = df_filtered[df_filtered['tipo'] == 'Entrata']['importo'].sum()
        tot_uscite = df_filtered[df_filtered['tipo'] == 'Uscita']['importo'].sum()
        margine = tot_entrate - tot_uscite
        
        st.metric("Totale Ricavi", f"{tot_entrate:,.2f} €")
        st.metric("Totale Costi", f"{tot_uscite:,.2f} €")
        st.metric("Margine Operativo", f"{margine:,.2f} €", delta=float(margine))

    # Tabella dettagliata
    with st.expander("Vedi i dettagli delle transazioni filtrate"):
        st.dataframe(df_filtered.sort_values(by='data', ascending=False), use_container_width=True)

if __name__ == "__main__":
    main()
