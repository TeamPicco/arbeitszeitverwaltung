import streamlit as st
from datetime import datetime, date
from utils.database import get_supabase_client, check_and_save_monats_abschluss
from utils.calculations import erstelle_zeitraum_auswertung, berechne_azk_kumuliert

def show_admin_dashboard():
    st.set_page_config(page_title="Admin Zentrale", layout="wide")
    supabase = get_supabase_client()
    
    st.title("🛡️ Admin Bereich")
    
    # NEU: Zeitraum Auswertung
    st.header("📊 Zeitraum-Bericht")
    c1, c2, c3 = st.columns(3)
    start = c1.date_input("Von", value=date.today().replace(day=1))
    ende = c2.date_input("Bis", value=date.today())
    
    ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname").execute()
    ma_map = {f"{m['vorname']} {m['nachname']}": m['id'] for m in ma_res.data}
    sel_ma = c3.selectbox("Mitarbeiter", options=list(ma_map.keys()))

    if st.button("Auswertung laden"):
        ma_id = ma_map[sel_ma]
        from utils.calculations import erstelle_zeitraum_auswertung
        df = erstelle_zeitraum_auswertung(ma_id, start, ende, supabase)
        st.dataframe(df, use_container_width=True)
        
        # Kumuliertes AZK (TypeError Fix)
        heute = datetime.now()
        ges_saldo = berechne_azk_kumuliert(ma_id, heute.month, heute.year, supabase)
        st.metric("Gesamt-AZK Stand", f"{ges_saldo} Std.")

if __name__ == "__main__":
    show_admin_dashboard()
