import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar

def show_admin_dashboard():
    supabase = st.session_state.supabase
    st.sidebar.title("🥩 Admin Zentrale")
    choice = st.sidebar.radio("Navigation", ["📅 Dienstplan & Vorlagen", "🏖️ Abwesenheiten (Krank/Urlaub)", "👥 Stammdaten", "📊 Lohn-Export"])

    # --- SEKTION: DIENSTPLAN ---
    if choice == "📅 Dienstplan & Vorlagen":
        st.header("Schichtplanung")
        # Vorlagen-Editor
        with st.expander("⚙️ Schichtvorlagen verwalten"):
            v_name = st.text_input("Name (z.B. Abend)")
            v_s = st.time_input("Start")
            v_e = st.time_input("Ende")
            if st.button("Vorlage speichern"):
                supabase.table("schicht_vorlagen").upsert({"name": v_name, "start_zeit": v_s.strftime("%H:%M:%S"), "ende_zeit": v_e.strftime("%H:%M:%S")}).execute()
                st.rerun()

        # Tabellen-Editor
        res_v = supabase.table("schicht_vorlagen").select("*").execute()
        v_namen = ["-- Frei --"] + [v['name'] for v in res_v.data]
        v_map = {v['name']: v for v in res_v.data}
        
        ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname").execute()
        for ma in ma_res.data:
            with st.expander(f"Plan für {ma['vorname']}"):
                cols = st.columns(7)
                for i in range(7):
                    d = date.today() + timedelta(days=i)
                    sel = cols[i].selectbox(f"{d.day}.{d.month}", v_namen, key=f"p_{ma['id']}_{i}")
                    if sel != "-- Frei --":
                        v = v_map[sel]
                        supabase.table("dienstplan").upsert({"mitarbeiter_id": ma['id'], "datum": d.isoformat(), "start_zeit": v['start_zeit'], "ende_zeit": v['ende_zeit']}).execute()

    # --- SEKTION: ABWESENHEITEN ---
    elif choice == "🏖️ Abwesenheiten (Krank/Urlaub)":
        st.header("Urlaub & Krankheit eintragen")
        with st.form("abw_form"):
            ma_id = st.selectbox("Mitarbeiter", options=[m['id'] for m in ma_res.data], format_func=lambda x: next(m['vorname'] for m in ma_res.data if m['id']==x))
            typ = st.selectbox("Typ", ["Urlaub", "Krankheit", "Feiertag"])
            von = st.date_input("Von")
            bis = st.date_input("Bis")
            
            if st.form_submit_button("Eintragen"):
                curr = von
                # Soll-Stunden pro Tag holen (Lohnfortzahlung)
                ma_data = supabase.table("mitarbeiter").select("soll_stunden_monat").eq("id", ma_id).single().execute()
                soll_tag = ma_data.data['soll_stunden_monat'] / 30
                
                while curr <= bis:
                    supabase.table("abwesenheiten").upsert({"mitarbeiter_id": ma_id, "datum": curr.isoformat(), "typ": typ, "stunden_gutschrift": soll_tag}).execute()
                    # Zeitgleich in Zeiterfassung spiegeln für AZK
                    supabase.table("zeiterfassung").upsert({"mitarbeiter_id": ma_id, "datum": curr.isoformat(), "stunden": soll_tag, "bemerkung": typ, "monat": curr.month, "jahr": curr.year}).execute()
                    curr += timedelta(days=1)
                st.success("Abwesenheit verbucht. Stunden wurden dem AZK gutgeschrieben.")

    # --- SEKTION: EXPORT ---
    elif choice == "📊 Lohn-Export":
        st.header("Monatsauswertung & Steuerberater")
        sel_ma = st.selectbox("Mitarbeiter", options=[m['id'] for m in ma_res.data], format_func=lambda x: next(m['vorname'] for m in ma_res.data if m['id']==x))
        m, j = st.columns(2)
        mon = m.number_input("Monat", 1, 12, date.today().month)
        jah = j.number_input("Jahr", 2024, 2030, date.today().year)
        
        data = supabase.table("zeiterfassung").select("*").eq("mitarbeiter_id", sel_ma).eq("monat", mon).eq("jahr", jah).execute()
        df = pd.DataFrame(data.data)
        if not df.empty:
            st.dataframe(df[["datum", "start_zeit", "ende_zeit", "stunden", "bemerkung"]])
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 CSV Export (Steuerberater)", csv, f"Lohn_{sel_ma}_{mon}_{jah}.csv")
