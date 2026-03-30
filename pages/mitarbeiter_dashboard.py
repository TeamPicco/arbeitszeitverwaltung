import streamlit as st
from datetime import datetime, date
import pandas as pd
from utils.database import get_supabase_client
from utils.calculations import (
    berechne_arbeitsstunden, 
    berechne_azk_kumuliert, 
    get_monatsnamen, 
    format_stunden
)

def show_mitarbeiter_dashboard():
    """Hauptseite für Mitarbeiter"""
    st.set_page_config(page_title="CrewBase - Mein Bereich", layout="wide")
    supabase = get_supabase_client()
    heute = datetime.now()
    
    # Nutzer-ID aus der Session holen
    user_id = st.session_state.get('user_id')
    mitarbeiter_id = st.session_state.get('mitarbeiter_id')

    if not mitarbeiter_id:
        st.error("Mitarbeiter-Daten konnten nicht geladen werden. Bitte loggen Sie sich neu an.")
        st.stop()

    st.title(f"Moin {st.session_state.get('vorname', 'Mitarbeiter')}! 👋")
    
    # Navigation innerhalb des Dashboards
    tab1, tab2, tab3 = st.tabs(["🕒 Zeiterfassung", "📅 Mein Zeitkonto", "📄 Meine Dokumente"])

    # --- TAB 1: ZEITERFASSUNG (Stempeluhr) ---
    with tab1:
        st.header("🕒 Arbeitszeit erfassen")
        with st.expander("Heute stempeln", expanded=True):
            col1, col2 = st.columns(2)
            start_zeit = col1.time_input("Kommen", value=datetime.now().time())
            ende_zeit = col2.time_input("Gehen", value=datetime.now().time())
            pause = st.number_input("Pause (in Minuten)", min_value=0, value=30, step=15)
            
            if st.button("⏱️ Zeit speichern"):
                stunden = berechne_arbeitsstunden(start_zeit, ende_zeit, pause)
                data = {
                    "mitarbeiter_id": mitarbeiter_id,
                    "datum": heute.date().isoformat(),
                    "start_zeit": start_zeit.strftime("%H:%M:%S"),
                    "ende_zeit": ende_zeit.strftime("%H:%M:%S"),
                    "pause_minuten": pause,
                    "stunden": stunden,
                    "monat": heute.month,
                    "jahr": heute.year
                }
                supabase.table("zeiterfassung").insert(data).execute()
                st.success(f"Gespeichert: {stunden} Stunden erfasst!")

    # --- TAB 2: ARBEITSZEITKONTO (AZK) ---
    with tab2:
        st.header("📅 Mein Arbeitszeitkonto")
        
        try:
            # Live-Berechnung des Kontostands (Inkl. Monat und Jahr Fix)
            saldo = berechne_azk_kumuliert(
                mitarbeiter_id, 
                bis_monat=heute.month, 
                bis_jahr=heute.year,
                supabase_client=supabase
            )
            
            # Anzeige mit Farbindikator
            color = "normal" if saldo >= 0 else "inverse"
            st.metric(
                label="Aktueller Stand (kumuliert)", 
                value=f"{saldo:.2f} Std.", 
                delta=f"{saldo:.2f} Std.",
                delta_color=color
            )
            
            if saldo < 0:
                st.warning(f"Hinweis: Sie haben aktuell {abs(saldo):.2f} Minusstunden.")
            else:
                st.success(f"Super! Sie haben {saldo:.2f} Überstunden auf dem Konto.")
                
        except Exception as e:
            st.error(f"Fehler bei der Konto-Abfrage: {e}")

    # --- TAB 3: DOKUMENTE (Lohnscheine) ---
    with tab3:
        render_my_documents(mitarbeiter_id, supabase)

def render_my_documents(mitarbeiter_id, supabase):
    """
    Unterfunktion für den Dokumenten-Bereich.
    FIX: Korrekte Einrückung (4 Leerzeichen)
    """
    st.header("📄 Meine Dokumente")
    st.info("Hier finden Sie Ihre Lohnabrechnungen und Verträge.")

    # Dokumente nur für diesen Mitarbeiter laden
    res = supabase.table("mitarbeiter_dokumente")\
        .select("*")\
        .eq("mitarbeiter_id", mitarbeiter_id)\
        .order("erstellt_am", desc=True)\
        .execute()

    if not res.data:
        st.write("Noch keine Dokumente hinterlegt.")
    else:
        for doc in res.data:
            with st.container():
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{doc['name']}**")
                c1.caption(f"Typ: {doc['typ']} | Datum: {doc['erstellt_am'][:10]}")
                # Button zum direkten Download/Anschauen
                c2.link_button("👁️ Öffnen", doc['file_url'], use_container_width=True)
                st.divider()

# Start der Seite
if __name__ == "__main__":
    show_mitarbeiter_dashboard()
