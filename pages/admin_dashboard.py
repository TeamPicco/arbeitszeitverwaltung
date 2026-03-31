import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
from utils.database import get_supabase_client
from utils.calculations import erstelle_zeitraum_auswertung

def show_admin_dashboard():
    st.set_page_config(page_title="Admin - CrewBase Piccolo", layout="wide")
    supabase = get_supabase_client()
    
    st.title("🛡️ Admin-Management - Piccolo")

    # Tabs für die Übersicht
    tab_planung, tab_auswertung, tab_einstellungen = st.tabs([
        "📅 Dienstplan (Vorlagen)", 
        "📊 Zeitauswertung", 
        "⚙️ System"
    ])

    # --- TAB 1: INTERAKTIVE DIENSTPLAN-ERSTELLUNG ---
    with tab_planung:
        st.header("Schichtplan per Klick")
        st.info("Wählen Sie einen Tag aus, um eine Vorlage (Service, Küche, Orga) zuzuweisen.")

        # Vorlagen aus der Datenbank laden
        vorlagen_res = supabase.table("schicht_vorlagen").select("*").execute()
        v_dict = {v['anzeige_name']: v for v in vorlagen_res.data}

        # Mitarbeiter laden
        ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname, bereich").execute()
        
        # Aktueller Monat
        heute = date.today()
        tage_im_monat = 31 # Vereinfacht für die Ansicht

        for ma in ma_res.data:
            with st.expander(f"📌 {ma['vorname']} {ma['nachname']} ({ma['bereich']})", expanded=False):
                # Erstelle ein Grid für die Tage
                cols = st.columns(10) # Wir zeigen die nächsten 10 Tage
                for i in range(10):
                    tag = heute + timedelta(days=i)
                    with cols[i]:
                        st.write(f"**{tag.strftime('%d.%m.')}**")
                        
                        # Dropdown mit Schichten (gefiltert nach Bereich oder Alle)
                        wahl = st.selectbox(
                            "Schicht", 
                            ["-"] + list(v_dict.keys()), 
                            key=f"plan_{ma['id']}_{tag}",
                            label_visibility="collapsed"
                        )
                        
                        if wahl != "-":
                            v = v_dict[wahl]
                            if st.button("OK", key=f"save_{ma['id']}_{tag}"):
                                supabase.table("dienstplan").upsert({
                                    "mitarbeiter_id": ma['id'],
                                    "datum": tag.isoformat(),
                                    "start_zeit": v['start_zeit'],
                                    "ende_zeit": v['ende_zeit'],
                                    "notiz": v['anzeige_name']
                                }).execute()
                                st.toast(f"Dienst für {ma['vorname']} gespeichert!")

    # --- TAB 2: ZEITAUSWERTUNG (Wie gewünscht) ---
    with tab_auswertung:
        st.header("Arbeitszeitauswertung")
        c1, c2, c3 = st.columns(3)
        start = c1.date_input("Von", value=heute.replace(day=1))
        ende = c2.date_input("Bis", value=heute)
        
        ma_namen = {f"{m['vorname']} {m['nachname']}": m['id'] for m in ma_res.data}
        sel_ma = c3.selectbox("Mitarbeiter wählen", options=list(ma_namen.keys()))
        
        if st.button("Auswertung laden"):
            df = erstelle_zeitraum_auswertung(ma_namen[sel_ma], start, ende, supabase)
            st.dataframe(df, use_container_width=True, hide_index=True)

# App-Start
if __name__ == "__main__":
    show_admin_dashboard()                        supabase.table("dienstplan").upsert({"mitarbeiter_id": ma['id'], "datum": d.isoformat(), "start_zeit": v['start_zeit'], "ende_zeit": v['ende_zeit']}).execute()

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
