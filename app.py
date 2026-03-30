import streamlit as st
import os
from datetime import datetime
from utils.database import init_supabase_client, verify_credentials_with_betrieb
from pages import admin_dashboard, mitarbeiter_dashboard

# Konfiguration
st.set_page_config(page_title="CrewBase Piccolo - Terminal", page_icon="⏰", layout="centered")

# CSS für große Kiosk-Buttons
st.markdown("""
    <style>
    div.stButton > button {
        height: 80px;
        font-size: 20px !important;
        font-weight: bold;
        border-radius: 15px;
        margin-bottom: 10px;
    }
    .st-key-kommen_btn button { background-color: #28a745 !important; color: white !important; }
    .st-key-gehen_btn button { background-color: #dc3545 !important; color: white !important; }
    .st-key-pause_btn button { background-color: #ffc107 !important; color: black !important; }
    </style>
    """, unsafe_allow_html=True)

supabase = init_supabase_client()

if not st.session_state.get('logged_in'):
    st.title("🇮🇹 CrewBase Piccolo")
    
    tab_stempel, tab_login = st.tabs(["🕒 Stempeluhr (PIN)", "🔐 Management"])
    
    with tab_stempel:
        st.write("Bitte PIN eingeben:")
        pin_input = st.text_input("PIN", type="password", max_chars=4, label_visibility="collapsed", key="pinfeld")
        
        if len(pin_input) == 4:
            res = supabase.table("mitarbeiter").select("id, vorname, nachname").eq("pin", pin_input).execute()
            if res.data:
                ma = res.data[0]
                st.success(f"Angemeldet: {ma['vorname']} {ma['nachname']}")
                
                heute = datetime.now().date().isoformat()
                
                c1, c2 = st.columns(2)
                if c1.button("🟢 KOMMEN", key="kommen_btn", use_container_width=True):
                    supabase.table("zeiterfassung").insert({
                        "mitarbeiter_id": ma['id'], "datum": heute,
                        "start_zeit": datetime.now().strftime("%H:%M:%S"),
                        "monat": datetime.now().month, "jahr": datetime.now().year
                    }).execute()
                    st.toast("Einstempeln erfolgreich!")

                if c2.button("🔴 GEHEN", key="gehen_btn", use_container_width=True):
                    supabase.table("zeiterfassung").update({
                        "ende_zeit": datetime.now().strftime("%H:%M:%S")
                    }).eq("mitarbeiter_id", ma['id']).eq("datum", heute).execute()
                    st.toast("Feierabend erfasst!")
                
                if st.button("☕ PAUSE (Start/Stopp)", key="pause_btn", use_container_width=True):
                    st.info("Pausenfunktion wird synchronisiert...")
            else:
                st.error("Falsche PIN")

    with tab_login:
        with st.form("admin_login"):
            st.subheader("Büro-Anmeldung")
            bnr = st.text_input("Betriebsnummer", value="20262204")
            usr = st.text_input("Benutzername")
            pwd = st.text_input("Passwort", type="password")
            if st.form_submit_button("Einloggen"):
                user = verify_credentials_with_betrieb(bnr, usr, pwd)
                if user:
                    st.session_state.update({"logged_in": True, "role": user['role'], "is_admin": (user['role'] == 'admin')})
                    st.rerun()
                else:
                    st.error("Login fehlgeschlagen")

else:
    if st.session_state.get('is_admin'):
        admin_dashboard.show_admin_dashboard()
    else:
        mitarbeiter_dashboard.show_mitarbeiter_dashboard()
