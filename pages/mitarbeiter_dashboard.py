import streamlit as st
from datetime import datetime
import pandas as pd
from utils.database import get_supabase_client, check_and_save_monats_abschluss
from utils.calculations import berechne_azk_kumuliert, get_monatsnamen, format_waehrung

def show_admin_dashboard():
    # 1. Projekt-Setup & Sicherheit
    st.set_page_config(page_title="TeamPicco Admin", layout="wide")
    supabase = get_supabase_client()
    heute = datetime.now()

    # Prüfung, ob Nutzer Admin ist (Sicherheits-Check)
    if not st.session_state.get('is_admin', False):
        st.error("Zugriff verweigert. Diese Seite ist nur für Administratoren.")
        st.stop()

    st.title("🛡️ Admin-Zentrale - Steakhouse Piccolo")
    st.write(f"Willkommen zurück! Heute ist der {heute.strftime('%d.%m.%Y')}")

    # --- TAB NAVIGATION ---
    tab1, tab2, tab3 = st.tabs(["📄 Dokumente & Lohn", "⏳ Arbeitszeitkonten", "⚙️ System-Check"])

    # --- TAB 1: DOKUMENTEN-UPLOAD & LOHN ---
    with tab1:
        st.header("📤 Dokumenten-Management")
        st.info("Hier laden Sie Lohnscheine oder Arbeitsverträge für Mitarbeiter hoch.")
        
        # Mitarbeiterliste für Selectbox laden
        ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname").execute()
        if ma_res.data:
            ma_options = {f"{m['vorname']} {m['nachname']}": m['id'] for m in ma_res.data}
            
            with st.form("upload_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    selected_ma_name = st.selectbox("Mitarbeiter wählen", options=list(ma_options.keys()))
                    selected_ma_id = ma_options[selected_ma_name]
                
                with col2:
                    doc_type = st.radio("Dokumenten-Typ", ["Lohnschein", "Arbeitsvertrag"], horizontal=True)
                
                u_file = st.file_uploader("PDF-Datei auswählen", type=["pdf"])
                submit_upload = st.form_submit_button("Dokument jetzt freigeben")

                if submit_upload and u_file:
                    bucket = "lohnscheine" if doc_type == "Lohnschein" else "arbeitesvertraege"
                    file_path = f"{selected_ma_id}/{heute.strftime('%Y%m%d')}_{u_file.name}"
                    
                    try:
                        # 1. Upload in Storage
                        supabase.storage.from_(bucket).upload(file_path, u_file.getvalue())
                        
                        # 2. URL generieren
                        url_data = supabase.storage.from_(bucket).get_public_url(file_path)
                        public_url = url_data.public_url

                        # 3. Datenbank-Eintrag erstellen
                        supabase.table("mitarbeiter_dokumente").insert({
                            "mitarbeiter_id": selected_ma_id,
                            "name": u_file.name,
                            "typ": doc_type,
                            "bucket": bucket,
                            "file_url": public_url
                        }).execute()
                        
                        st.success(f"✅ {doc_type} erfolgreich für {selected_ma_name} bereitgestellt!")
                    except Exception as e:
                        st.error(f"Fehler beim Upload: {e}")

    # --- TAB 2: ARBEITSZEITKONTEN (AZK) ---
    with tab2:
        st.header("⏳ Team-Übersicht Arbeitszeitkonten")
        
        # Sammel-Button für alle (Der Autopilot)
        if st.button("🚀 Monatsabschluss für alle Mitarbeiter berechnen (Letzter Monat)"):
            with st.spinner("Berechne Salden und prüfe auf Minusstunden..."):
                # Bestimme den letzten Monat (Februar, wenn wir im März sind)
                m = heute.month - 1 if heute.month > 1 else 12
                j = heute.year if heute.month > 1 else heute.year - 1
                
                for name, m_id in ma_options.items():
                    check_and_save_monats_abschluss(m_id, m, j)
                st.success(f"Abschluss für {get_monatsnamen(m)} {j} erfolgreich für das ganze Team gespeichert!")

        st.divider()

        # Einzel-Abfrage (Fix für den TypeError)
        st.subheader("Einzelabfrage & Details")
        sel_ma_azk = st.selectbox("Mitarbeiter für Details wählen", options=list(ma_options.keys()), key="sel_azk")
        sel_id_azk = ma_options[sel_ma_azk]

        try:
            # Aufruf mit korrekten Parametern (Monat & Jahr)
            saldo = berechne_azk_kumuliert(
                sel_id_azk, 
                bis_monat=heute.month, 
                bis_jahr=heute.year
            )
            
            # Anzeige des Kontostands
            # Falls Saldo negativ (Minusstunden), wird es rot angezeigt
            delta_val = saldo
            st.metric(
                label=f"Aktuelles Zeitkonto: {sel_ma_azk}", 
                value=f"{saldo:.2f} Std.", 
                delta=f"{delta_val:.2f} Std. Differenz",
                delta_color="normal" if saldo >= 0 else "inverse"
            )
            
            if saldo < 0:
                st.warning(f"⚠️ {sel_ma_azk} befindet sich aktuell mit {abs(saldo):.2f} Stunden im Minus.")
        
        except Exception as e:
            st.error(f"Fehler bei der Live-Berechnung: {e}")

    # --- TAB 3: SYSTEM-CHECK & MASTERGERÄTE ---
    with tab3:
        st.header("⚙️ Mastergeräte-Verwaltung")
        st.write("Hier können Sie neue Geräte registrieren. Dank der neuen RLS-Regeln ist dies nur Admins gestattet.")
        
        with st.form("geraet_form"):
            g_name = st.text_input("Name des Geräts (z.B. iPad Küche)")
            g_typ = st.selectbox("Typ", ["Kasse", "Tablet", "Terminal"])
            submit_g = st.form_submit_button("Gerät registrieren")
            
            if submit_g and g_name:
                try:
                    supabase.table("mastergeraete").insert({
                        "name": g_name,
                        "typ": g_typ,
                        "aktiv": True
                    }).execute()
                    st.success(f"Gerät '{g_name}' wurde erfolgreich im System hinterlegt!")
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e} (Prüfen Sie Ihre RLS-Policies in Supabase)")

# App-Start
if __name__ == "__main__":
    show_admin_dashboard()
    import streamlit as st
from datetime import datetime
from utils.database import get_supabase_client
from utils.calculations import erstelle_zeitraum_auswertung, berechne_azk_kumuliert

def show_admin_dashboard():
    supabase = get_supabase_client()
    heute = datetime.now()
    
    st.title("Arbeitszeitauswertung")
    
    col1, col2, col3 = st.columns(3)
    start = col1.date_input("Von", value=datetime.now().replace(day=1))
    ende = col2.date_input("Bis")
    
    ma_res = supabase.table("mitarbeiter").select("id, vorname, nachname").execute()
    ma_map = {f"{m['vorname']} {m['nachname']}": m['id'] for m in ma_res.data}
    sel_ma = col3.selectbox("Mitarbeiter", options=list(ma_map.keys()))
    
    if st.button("Auswertung anzeigen"):
        ma_id = ma_map[sel_ma]
        df = erstelle_zeitraum_auswertung(ma_id, start, ende, supabase)
        
        # FIX: TypeError behoben durch Übergabe von Monat und Jahr
        gesamt_azk = berechne_azk_kumuliert(ma_id, bis_monat=heute.month, bis_jahr=heute.year, supabase_client=supabase)
        
        st.subheader(f"Ergebnisse für {sel_ma}")
        st.dataframe(df, hide_index=True)
        
        st.metric("auflaufendes Arbeitszeitkonto (bis heute)", f"{gesamt_azk} Std.")

# --- WICHTIG: Korrektur für Silke im Mitarbeiter Dashboard ---
# In pages/mitarbeiter_dashboard.py muss die Zeile 1146 eingerückt werden:
# def render_my_documents():
#     st.header("📄 Meine Dokumente")  # <--- HIER 4 LEERZEICHEN DAVOR!
