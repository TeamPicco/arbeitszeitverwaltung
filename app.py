import streamlit as st
import os
import time
from datetime import datetime, date
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login
from pages import admin_dashboard

# --- 1. KONFIGURATION ---
st.set_page_config(
    page_title="🥩 CrewBase Piccolo - Admin & Terminal",
    page_icon="🥩",
    layout="wide" # Wide Mode für bessere Tabellenübersicht
)

supabase = init_supabase_client()

# --- 2. HILFSFUNKTIONEN ---
def reset_to_pin_mask():
    if "terminal_pin_entry" in st.session_state:
        st.session_state["terminal_pin_entry"] = ""
    st.session_state["trigger_reset"] = True
    st.rerun()

# --- 3. HAUPTLOGIK ---
if not st.session_state.get('logged_in'):
    st.title("🥩 CrewBase Piccolo")
    
    tab_stempel, tab_admin_login = st.tabs(["🕒 Mitarbeiter Stempeluhr", "🔐 Admin Bereich"])
    
    with tab_stempel:
        # Reset-Logik
        if st.session_state.get("trigger_reset"):
            st.session_state["terminal_pin_entry"] = ""
            st.session_state["trigger_reset"] = False
            st.rerun()

        st.subheader("Schnell-Stempeln per PIN")
        pin_input = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        
        if len(pin_input) == 4:
            res = supabase.table("mitarbeiter").select("id, vorname, nachname").eq("pin", pin_input).execute()
            
            if res.data:
                ma = res.data[0]
                ma_id = ma['id']
                st.info(f"Mitarbeiter erkannt: **{ma['vorname']} {ma['nachname']}**")
                
                heute_str = date.today().isoformat()
                col1, col2 = st.columns(2)
                
                # --- KOMMEN ---
                if col1.button("🟢 KOMMEN", key=f"k_{ma_id}", use_container_width=True):
                    jetzt = datetime.now()
                    start_zeit = jetzt.strftime("%H:%M:%S")
                    # Schichtplan-Check
                    plan = supabase.table("dienstplan").select("start_zeit").eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    if plan.data and jetzt.strftime("%H:%M:%S") < plan.data[0]['start_zeit']:
                        start_zeit = plan.data[0]['start_zeit']
                        st.warning(f"Planzeit ({start_zeit[:5]}) übernommen.")

                    supabase.table("zeiterfassung").upsert({
                        "mitarbeiter_id": ma_id, "datum": heute_str,
                        "start_zeit": start_zeit, "monat": jetzt.month, "jahr": jetzt.year
                    }).execute()
                    st.success("Erfolgreich eingestempelt!")
                    time.sleep(1.5)
                    reset_to_pin_mask()

                # --- GEHEN ---
                if col2.button("🔴 GEHEN", key=f"g_{ma_id}", use_container_width=True):
                    supabase.table("zeiterfassung").update({
                        "ende_zeit": datetime.now().strftime("%H:%M:%S")
                    }).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    st.success("Schönen Feierabend!")
                    time.sleep(1.5)
                    reset_to_pin_mask()
            else:
                st.error("PIN ungültig.")

    with tab_admin_login:
        with st.form("admin_form"):
            st.subheader("Admin Anmeldung")
            b_nr = st.text_input("Betriebsnummer", value="20262204")
            u_name = st.text_input("Admin Benutzername")
            p_word = st.text_input("Passwort", type="password")
            if st.form_submit_button("Einloggen", use_container_width=True):
                user = verify_credentials_with_betrieb(b_nr, u_name, p_word)
                if user and user['role'] == 'admin':
                    st.session_state.update({
                        "logged_in": True, "is_admin": True, "user_id": user['id'],
                        "vorname": user.get('vorname', 'Admin')
                    })
                    update_last_login(user['id'])
                    st.rerun()
                else:
                    st.error("Zugriff verweigert. Nur für Admins.")

# --- 4. ADMIN DASHBOARD ANZEIGEN ---
else:
    admin_dashboard.show_admin_dashboard()
    
    if st.sidebar.button("Abmelden / Zum Terminal"):
        st.session_state.clear()
        st.rerun()
