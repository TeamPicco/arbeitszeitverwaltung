import streamlit as st
from datetime import datetime
from utils.database import get_supabase_client
from utils.calculations import berechne_azk_kumuliert

def show_mitarbeiter_dashboard():
    st.set_page_config(page_title="Mein Bereich", layout="wide")
    supabase = get_supabase_client()
    m_id = st.session_state.get('mitarbeiter_id')

    st.title(f"Hallo {st.session_state.get('vorname')}! 👋")
    
    t1, t2, t3 = st.tabs(["🕒 Stempeln", "📅 Zeitkonto", "📄 Dokumente"])

    with t1:
        st.header("Zeiterfassung")
        # Hier deine Stempel-Logik...
        st.info("Nutzen Sie die Kiosk-Stempeluhr oder geben Sie Zeiten manuell ein.")

    with t2:
        st.header("Arbeitszeitkonto")
        heute = datetime.now()
        saldo = berechne_azk_kumuliert(m_id, heute.month, heute.year, supabase)
        st.metric("Dein Kontostand", f"{saldo} Std.", delta=saldo)

    with t3:
        render_my_documents(m_id, supabase)

def render_my_documents(m_id, supabase):
    # Wichtig: Die Einrückung hier löst den IndentationError!
    st.header("📄 Meine Dokumente")
    docs = supabase.table("mitarbeiter_dokumente").select("*").eq("mitarbeiter_id", m_id).execute()
    if not docs.data:
        st.write("Keine Dokumente gefunden.")
    for d in docs.data:
        col1, col2 = st.columns([3,1])
        col1.write(f"**{d['name']}** ({d['typ']})")
        col2.link_button("Öffnen", d['file_url'])
