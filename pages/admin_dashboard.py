import streamlit as st
from datetime import datetime, date, timedelta
import calendar
from utils.database import get_supabase_client

def show_admin_dashboard():
    supabase = get_supabase_client()
    
    # --- STYLING (Edle Optik) ---
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #1e1e1e; border-radius: 10px 10px 0 0;
            padding: 10px 20px; color: white;
        }
        .stTabs [aria-selected="true"] { background-color: #8A2BE2 !important; }
        .shift-cell {
            border: 1px solid #333; padding: 5px; border-radius: 5px;
            text-align: center; cursor: pointer; min-height: 45px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🛡️ Admin-Zentrale - Piccolo")

    # TABS
    tab_planung, tab_auswertung, tab_personal = st.tabs(["📅 Monats-Dienstplan", "📊 Auswertung", "👥 Team"])

    with tab_planung:
        # Monats-Navigation
        c1, c2 = st.columns([2, 4])
        heute = datetime.now()
        gew_monat = c1.selectbox("Monat wählen", range(1, 13), index=heute.month-1)
        jahr = heute.year
        
        st.subheader(f"Dienstplan für {calendar.month_name[gew_monat]} {jahr}")

        # Mitarbeiter und Vorlagen laden
        ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname, bereich").execute()
        vorlagen_res = supabase.table("schicht_vorlagen").select("*").execute()
        vorlagen_namen = {v['anzeige_name']: v for v in vorlagen_res.data}

        # --- DAS GROSSE MONATS-GRID ---
        anzahl_tage = calendar.monthrange(jahr, gew_monat)[1]
        
        # Header-Zeile mit Tagen
        t_cols = st.columns([2] + [1] * anzahl_tage)
        t_cols[0].write("**Mitarbeiter**")
        for d in range(1, anzahl_tage + 1):
            t_cols[d].write(f"**{d}**")

        st.divider()

        # Zeilen pro Mitarbeiter
        for ma in ma_res.data:
            m_cols = st.columns([2] + [1] * anzahl_tage)
            m_cols[0].write(f"**{ma['vorname']}**")
            
            for d in range(1, anzahl_tage + 1):
                with m_cols[d]:
                    # Button als interaktive Kalenderzelle
                    if st.button("➕", key=f"cell_{ma['id']}_{d}", help=f"Schicht für {ma['vorname']} am {d}.{gew_monat}. setzen"):
                        st.session_state['edit_mode'] = {
                            "ma_id": ma['id'], 
                            "ma_name": ma['vorname'], 
                            "datum": date(jahr, gew_monat, d)
                        }

        # --- POPUP-FENSTER (SIDEBAR) ZUM EINTRAGEN ---
        if 'edit_mode' in st.session_state:
            edit = st.session_state['edit_mode']
            with st.sidebar:
                st.header(f"📝 Dienst setzen")
                st.write(f"**Mitarbeiter:** {edit['ma_name']}")
                st.write(f"**Datum:** {edit['datum'].strftime('%d.%m.%Y')}")
                
                # Wahl 1: Aus Vorlage
                auswahl = st.selectbox("Vorlage wählen", ["-"] + list(vorlagen_namen.keys()))
                
                st.divider()
                st.write("Oder manuell:")
                m_start = st.time_input("Start", value=datetime.strptime("17:00", "%H:%M").time())
                m_ende = st.time_input("Ende", value=datetime.strptime("22:00", "%H:%M").time())
                
                col_s, col_l = st.columns(2)
                if col_s.button("✅ Speichern", use_container_width=True):
                    final_start = vorlagen_namen[auswahl]['start_zeit'] if auswahl != "-" else m_start.strftime("%H:%M")
                    final_ende = vorlagen_namen[auswahl]['ende_zeit'] if auswahl != "-" else m_ende.strftime("%H:%M")
                    
                    supabase.table("dienstplan").upsert({
                        "mitarbeiter_id": edit['ma_id'],
                        "datum": edit['datum'].isoformat(),
                        "start_zeit": final_start,
                        "ende_zeit": final_ende,
                        "notiz": auswahl if auswahl != "-" else "Manuell"
                    }).execute()
                    st.success("Gespeichert!")
                    del st.session_state['edit_mode']
                    st.rerun()
                
                if col_l.button("🗑️ Löschen", use_container_width=True):
                    supabase.table("dienstplan").delete().eq("mitarbeiter_id", edit['ma_id']).eq("datum", edit['datum'].isoformat()).execute()
                    del st.session_state['edit_mode']
                    st.rerun()

    with tab_auswertung:
        st.header("Arbeitszeit-Berichte")
        # Hier kommt dein Zeitraum-Bericht rein (Soll, Plan, Ist, Saldo)            with st.expander(f"📌 {ma['vorname']} {ma['nachname']} ({ma['bereich']})", expanded=False):
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
