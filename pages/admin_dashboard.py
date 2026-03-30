import streamlit as st
from datetime import datetime, date
from utils.database import get_supabase_client, check_and_save_monats_abschluss
from utils.calculations import erstelle_zeitraum_auswertung, berechne_azk_kumuliert, get_monatsnamen

def show_admin_dashboard():
    supabase = get_supabase_client()
    heute = datetime.now()
    
    st.title("🛡️ CrewBase Admin")
    
    tab1, tab2 = st.tabs(["📊 Zeiträume", "🚀 Monatsabschluss"])
    
    with tab1:
        st.header("Zeitraum-Auswertung")
        c1, c2, c3 = st.columns(3)
        start = c1.date_input("Start", value=date.today().replace(day=1))
        ende = c2.date_input("Ende")
        
        ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname").execute()
        ma_map = {f"{m['vorname']} {m['nachname']}": m['id'] for m in ma_res.data}
        sel_ma = c3.selectbox("Mitarbeiter", options=list(ma_map.keys()))

        if st.button("Bericht generieren"):
            ma_id = ma_map[sel_ma]
            df = erstelle_zeitraum_auswertung(ma_id, start, ende, supabase)
            st.dataframe(df, use_container_width=True)
            
            saldo = berechne_azk_kumuliert(ma_id, heute.month, heute.year, supabase)
            st.metric(f"AZK Stand {sel_ma}", f"{saldo} Std.", delta=saldo)

    with tab2:
        if st.button("Abschluss für alle Mitarbeiter (Letzter Monat)"):
            m = heute.month - 1 if heute.month > 1 else 12
            j = heute.year if heute.month > 1 else heute.year - 1
            for mid in ma_map.values():
                check_and_save_monats_abschluss(mid, m, j)
            st.success("Erfolgreich abgeschlossen!")
