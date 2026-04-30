import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Gestione Cloud", layout="wide")

def format_it(val):
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("✏️ Gestione e Modifica (Cloud)")

conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

if not df.empty:
    df['display_label'] = df['data'].astype(str) + " | " + df['categoria'] + " | " + df['importo'].astype(str) + " €"
    
    scelta = st.selectbox("Seleziona il movimento da gestire:", df['display_label'].tolist())
    index_riga = df[df['display_label'] == scelta].index[0]
    riga = df.iloc[index_riga]

    with st.form("edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_data = st.date_input("Data", value=pd.to_datetime(riga['data']))
            n_imp = st.number_input("Importo (€)", value=float(riga['importo']), format="%.2f")
            n_tipo = st.selectbox("Tipo", ["Uscita", "Entrata"], index=0 if riga['tipo']=="Uscita" else 1)
        with col2:
            n_cat = st.text_input("Categoria", value=riga['categoria'])
            n_colt = st.text_input("Coltura", value=riga['coltura_id'])
            n_desc = st.text_area("Note", value=riga['descrizione'])
        
        if st.form_submit_button("💾 Salva Modifiche"):
            df.at[index_riga, 'data'] = n_data.strftime('%Y-%m-%d')
            df.at[index_riga, 'importo'] = n_imp
            df.at[index_riga, 'tipo'] = n_tipo
            df.at[index_riga, 'categoria'] = n_cat
            df.at[index_riga, 'coltura_id'] = n_colt
            df.at[index_riga, 'descrizione'] = n_desc
            
            conn.update(data=df)
            st.success("Dato aggiornato sul foglio Google!")
            st.rerun()

    if st.button("🗑️ Elimina Movimento"):
        df = df.drop(index_riga)
        conn.update(data=df)
        st.warning("Movimento eliminato dal cloud.")
        st.rerun()
