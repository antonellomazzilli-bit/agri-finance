import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="AgriFinance Cloud", layout="wide")

# --- FUNZIONI DI SERVIZIO ---
def format_euro(val):
    try:
        return f"€ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "€ 0,00"

st.title("🚜 Gestione Agricola Cloud")
st.info("I dati vengono salvati direttamente su Google Sheets.")

# --- CONNESSIONE ---
# Creiamo la connessione
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FORM DI INSERIMENTO ---
with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data Operazione", format="DD/MM/YYYY")
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.01, format="%.2f")
    with col2:
        cat = st.selectbox("Categoria", ["Sementi", "Carburante", "Concimi", "Manodopera", "Vendita", "Altro"])
        coltura = st.text_input("Coltura (es. Olivo, Grano)")
        desc = st.text_area("Note / Descrizione")
    
    submit = st.form_submit_button("Registra Movimento")

if submit:
    try:
        # 1. Leggi i dati esistenti (ttl=0 forza il refresh immediato dal cloud)
        existing_data = conn.read(ttl=0)
        
        # 2. Prepara la nuova riga come DataFrame
        new_row = pd.DataFrame([{
            "data": data.strftime('%Y-%m-%d'),
            "tipo": tipo,
            "categoria": cat,
            "descrizione": desc,
            "importo": float(importo),
            "coltura_id": coltura
        }])
        
        # 3. Combina i dati vecchi con i nuovi
        # Se il foglio è vuoto, il nuovo dataframe sarà solo la nuova riga
        if existing_data is not None and not existing_data.empty:
            updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        else:
            updated_df = new_row

        # 4. AGGIORNA IL FOGLIO GOOGLE
        conn.update(data=updated_df)
        
        st.success(f"✅ Movimento registrato: {format_euro(importo)}")
        st.balloons()
        
    except Exception as e:
        st.error("❌ Errore durante il salvataggio!")
        st.error(f"Dettaglio: {e}")
        st.warning("Verifica che il tuo Foglio Google sia condiviso con 'Chiunque abbia il link' come EDITOR.")

# --- ANTEPRIMA DATI ---
st.divider()
st.subheader("Ultimi 5 inserimenti nel Cloud")
try:
    # Rileggiamo per mostrare i dati aggiornati
    df_preview = conn.read(ttl=0)
    if df_preview is not None and not df_preview.empty:
        # Formattiamo solo per la visualizzazione
        df_display = df_preview.tail(5).copy()
        df_display['importo'] = df_display['importo'].apply(format_euro)
        st.table(df_display)
    else:
        st.write("Il foglio è attualmente vuoto.")
except:
    st.write("In attesa del primo inserimento...")
