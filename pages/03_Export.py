import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Export Cloud", layout="wide")

st.title("📂 Esportazione Dati (Cloud)")

conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['data'] = pd.to_datetime(df['data'])
    anni = sorted(df['data'].dt.year.unique(), reverse=True)
    anno_fiscale = st.selectbox("Seleziona Anno Fiscale", anni)
    
    report = df[df['data'].dt.year == anno_fiscale].copy()
    report['data'] = report['data'].dt.strftime('%d/%m/%Y')
    
    st.dataframe(report, use_container_width=True)
    
    csv = report.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Scarica Bilancio CSV",
        data=csv,
        file_name=f"Bilancio_{anno_fiscale}.csv",
        mime='text/csv'
    )
