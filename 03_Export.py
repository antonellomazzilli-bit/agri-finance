import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Export Bilancio", layout="wide")
DB_NAME = 'agri_finance.db'

def load_data_export():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql_query("SELECT * FROM transactions", conn)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data'], errors='coerce')
                df = df.dropna(subset=['data'])
                df['anno'] = df['data'].dt.year.astype(int)
            return df
    except:
        return pd.DataFrame()

def main():
    st.title("📂 Esportazione Dati per il Commercialista")
    df = load_data_export()

    if df.empty:
        st.warning("Nessun dato da esportare.")
        return

    # --- FILTRO ANNO ---
    anni = sorted(df['anno'].unique(), reverse=True)
    anno_fiscale = st.selectbox("Seleziona l'anno fiscale da esportare", anni)
    
    df_fiscale = df[df['anno'] == anno_fiscale].copy()
    
    # Pulizia colonne per il commercialista
    report = df_fiscale[['data', 'tipo', 'categoria', 'descrizione', 'importo', 'coltura_id']]
    report.columns = ['DATA', 'TIPO', 'CATEGORIA', 'DESCRIZIONE', 'IMPORTO (€)', 'COLTURA']

    # --- RIEPILOGO ---
    c1, c2, c3 = st.columns(3)
    entrate = report[report['TIPO'] == 'Entrata']['IMPORTO (€)'].sum()
    uscite = report[report['TIPO'] == 'Uscita']['IMPORTO (€)'].sum()
    
    c1.metric("Totale Ricavi", f"{entrate:,.2f} €")
    c2.metric("Totale Costi", f"{uscite:,.2f} €")
    c3.metric("Utile Lordo", f"{entrate - uscite:,.2f} €")

    st.divider()

    # --- DOWNLOAD ---
    csv = report.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Scarica Bilancio (CSV/Excel)",
        data=csv,
        file_name=f"Bilancio_Agricolo_{anno_fiscale}.csv",
        mime='text/csv'
    )

    st.subheader("Dettaglio Movimenti")
    st.dataframe(report, use_container_width=True)

if __name__ == "__main__":
    main()