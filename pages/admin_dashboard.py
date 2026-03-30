import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
from utils.database import get_supabase_client, check_and_save_monats_abschluss
from utils.calculations import berechne_azk_kumuliert, get_monatsnamen, erstelle_zeitraum_auswertung

def show_admin_dashboard():
    # 1. Konfiguration & Sicherheit
    st.set_page_config(page_title="CrewBase Admin", layout="wide")
    supabase = get_supabase_client()
    heute = datetime.now()

    if not st.session_state.get('is_admin', False):
        st.error("Zugriff verweigert. Nur für Administratoren.")
        st.stop()

    st.title("🛡️ Admin-Zentrale - Steakhouse Piccolo")
    st.write(f"Status: Online | Angemeldet als: {st.session_state.get('username')}")

    # --- TABS FÜR DIE ÜBERSICHT ---
    tab1, tab2, tab3 = st.tabs(["📊 Zeiträume & Auswertung", "📤 Lohnscheine & Upload", "⚙️ Geräte & System"])

    # --- TAB 1: DETAILLIERTE ZEITAUSWERTUNG ---
    with tab1:
        st.header("📊 Arbeitszeitauswertung (Freie Zeiträume)")
        st.info("Hier generieren Sie Berichte mit Soll, Plan, Ist und Salden.")

        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Filter Start", value=date.today().replace(day=1))
        with col2:
            end_date = st.date_input("Filter Ende", value=date.today())
        with col3:
            # Mitarbeiter laden
            ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname").execute()
            ma_options = {f"{m['vorname']} {m['nachname']}": m['id'] for m in ma_res.data}
            selected_ma_name = st.selectbox("Mitarbeiter wählen", options=list(ma_options.keys()))
            selected_ma_id = ma_options[selected_ma_name]

        if st.button("🚀 Auswertung generieren"):
            # Diese Funktion nutzt die neue Logik in utils/calculations.py
            df = erstelle_zeitraum_auswertung(selected_ma_id, start_date, end_date, supabase)
            
            st.subheader(f"Bericht: {selected_ma_name}")
            
            # Die Tabelle mit den gewünschten Überschriften
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Soll Stunden": st.column_config.NumberColumn(format="%.2f h"),
                    "Ist": st.column_config.NumberColumn(format="%.2f h"),
                    "Saldo": st.column_config.NumberColumn(format="%.2f h"),
                    "laufender Saldo": st.column_config.NumberColumn(format="%.2f h")
                }
            )

            # Kumuliertes AZK (Bis heute)
            st.divider()
            try:
                gesamt_azk = berechne_azk_kumuliert(selected_ma_id, heute.month, heute.year, supabase)
                st.metric("Auflaufendes Arbeitszeitkonto (Gesamtstand)", f"{gesamt_azk:.2f} Std.")
            except:
                st.write("AZK-Gesamtstand konnte nicht berechnet werden.")

    # --- TAB 2: DOKUMENTEN-UPLOAD ---
    with tab2:
        st.header("📤 Lohnscheine bereitstellen")
        
        with st.form("upload_form", clear_on_submit=True):
            target_ma = st.selectbox("Empfänger", options=list(ma_options.keys()), key="doc_ma")
            doc_type = st.radio("Dokumententyp", ["Lohnschein", "Arbeitsvertrag"], horizontal=True)
            u_file = st.file_uploader("PDF auswählen", type=["pdf"])
            
            if st.form_submit_button("Datei für Mitarbeiter freigeben"):
                if u_file:
                    target_id = ma_options[target_ma]
                    bucket = "lohnscheine" if doc_type == "Lohnschein" else "arbeitesvertraege"
                    path = f"{target_id}/{heute.strftime('%Y%m')}_{u_file.name}"
                    
                    try:
                        # Upload zu Storage
                        supabase.storage.from_(bucket).upload(path, u_file.getvalue())
                        url = supabase.storage.from_(bucket).get_public_url(path).public_url
                        
                        # Eintrag in DB
                        supabase.table("mitarbeiter_dokumente").insert({
                            "mitarbeiter_id": target_id,
                            "name": u_file.name,
                            "typ": doc_type,
                            "file_url": url
                        }).execute()
                        st.success(f"Erfolgreich: {u_file.name} ist nun für {target_ma} sichtbar.")
                    except Exception as e:
                        st.error(f"Fehler beim Upload: {e}")

    # --- TAB 3: SYSTEM & MASTERGERÄTE ---
    with tab3:
        st.header("⚙️ Mastergeräte & Monatsabschluss")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("Gerät registrieren")
            with st.form("device_reg"):
                d_name = st.text_input("Name (z.B. Tablet Counter)")
                d_typ = st.selectbox("Typ", ["Kasse", "Terminal", "Mobil"])
                if st.form_submit_button("Gerät speichern"):
                    supabase.table("mastergeraete").insert({"name": d_name, "typ": d_typ, "aktiv": True}).execute()
                    st.success("Gerät erfolgreich registriert.")

        with col_b:
            st.subheader("Automatischer Abschluss")
            st.write("Berechnet die Differenzen (Ist-Soll) für den letzten Monat für alle Mitarbeiter.")
            if st.button("🚀 Monatsabschluss jetzt ausführen"):
                m = heute.month - 1 if heute.month > 1 else 12
                j = heute.year if heute.month > 1 else heute.year - 1
                for mid in ma_options.values():
                    check_and_save_monats_abschluss(mid, m, j)
                st.success(f"Abschluss für {get_monatsnamen(m)} erfolgreich gespeichert!")

if __name__ == "__main__":
    show_admin_dashboard()
