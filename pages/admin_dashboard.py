import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from utils.database import get_supabase_client, upload_file_to_storage
from utils.calculations import erstelle_zeitraum_auswertung

def show_admin_dashboard():
    supabase = get_supabase_client()
    st.sidebar.title("🥩 Admin-Menü")
    choice = st.sidebar.radio("Navigation", ["👥 Stammdaten", "📅 Dienstplan & Urlaub", "🕒 Zeit-Korrektur", "📊 Export & Steuer"])

    # --- 1. STAMMDATEN ---
    if choice == "👥 Stammdaten":
        st.header("Personalstamm & Dokumente")
        res = supabase.table("mitarbeiter").select("*").execute()
        df = pd.DataFrame(res.data)
        st.dataframe(df[["vorname", "nachname", "soll_stunden_monat", "pin"]], use_container_width=True)
        
        with st.expander("Vertrag/Dokument hochladen"):
            sel_ma = st.selectbox("Mitarbeiter", df['id'].tolist(), format_func=lambda x: f"{df[df['id']==x]['vorname'].values[0]}")
            file = st.file_uploader("PDF wählen", type="pdf")
            if st.button("Hochladen") and file:
                upload_file_to_storage("stammdaten", f"vertrage/{sel_ma}_{file.name}", file.getvalue())
                st.success("Gespeichert!")

    # --- 2. DIENSTPLAN & URLAUB ---
    elif choice == "📅 Dienstplan & Urlaub":
        st.header("Planung (Dienste & Urlaub)")
        t1, t2 = st.tabs(["🗓️ Schichtplanung", "🏖️ Urlaubsübersicht"])
        
        with t1:
            st.subheader("Schichten per Klick setzen")
            ma_res = supabase.table("mitarbeiter").select("id, vorname").execute()
            ma_dict = {m['vorname']: m['id'] for m in ma_res.data}
            sel_n = st.selectbox("Mitarbeiter wählen", list(ma_dict.keys()))
            
            d_cols = st.columns(7)
            for i in range(7):
                d = date.today() + timedelta(days=i)
                if d_cols[i].button(f"{d.strftime('%a')}\n{d.day}.{d.month}."):
                    st.session_state['edit_d'] = d
            
            if 'edit_d' in st.session_state:
                with st.form("shift_form"):
                    st.write(f"Schicht für {sel_n} am {st.session_state['edit_d']}")
                    s, e = st.time_input("Start"), st.time_input("Ende")
                    if st.form_submit_button("Speichern"):
                        supabase.table("dienstplan").upsert({"mitarbeiter_id": ma_dict[sel_n], "datum": st.session_state['edit_d'].isoformat(), "start_zeit": s.strftime("%H:%M:%S"), "ende_zeit": e.strftime("%H:%M:%S")}).execute()
                        st.success("Plan aktualisiert!")

        with t2:
            st.subheader("Urlaubsplanung")
            u_res = supabase.table("urlaub").select("*, mitarbeiter(vorname)").execute()
            if u_res.data:
                u_df = pd.DataFrame(u_res.data)
                st.table(u_df[['mitarbeiter', 'von_datum', 'bis_datum', 'status']])
            
            # Download-Buttons für Pläne
            if st.button("📅 Gesamten Dienstplan als CSV laden"):
                all_p = supabase.table("dienstplan").select("*, mitarbeiter(vorname, nachname)").execute()
                p_df = pd.DataFrame(all_p.data)
                st.download_button("Datei speichern", p_df.to_csv().encode('utf-8'), "Gesamt_Dienstplan.csv")

    # --- 3. EXPORT & STEUERBERATER ---
    elif choice == "📊 Export & Steuer":
        st.header("Auswertungen für Mitarbeiter & Steuerberater")
        c1, c2 = st.columns(2)
        v, b = c1.date_input("Von"), c2.date_input("Bis")
        
        ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname").execute()
        for m in ma_res.data:
            with st.expander(f"Auswertung: {m['vorname']} {m['nachname']}"):
                data = erstelle_zeitraum_auswertung(m['id'], v, b, supabase)
                st.dataframe(data)
                csv = data.to_csv(index=False).encode('utf-8')
                st.download_button(f"📥 Download {m['vorname']}.csv", csv, f"Lohn_{m['vorname']}_{v}.csv", "text/csv")

    # --- 4. ZEIT-KORREKTUR ---
    elif choice == "🕒 Zeit-Korrektur":
        st.header("Manuelle Korrektur")
        tag = st.date_input("Datum wählen")
        entries = supabase.table("zeiterfassung").select("*, mitarbeiter(vorname)").eq("datum", tag.isoformat()).execute()
        for e in entries.data:
            with st.form(f"f_{e['id']}"):
                st.write(f"Eintrag für {e['mitarbeiter']['vorname']}")
                ns, ne = st.text_input("Start", e['start_zeit']), st.text_input("Ende", e['ende_zeit'])
                if st.form_submit_button("💾 Speichern"):
                    supabase.table("zeiterfassung").update({"start_zeit": ns, "ende_zeit": ne}).eq("id", e['id']).execute()
                    st.rerun()
