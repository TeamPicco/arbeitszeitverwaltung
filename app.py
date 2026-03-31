import streamlit as st
import time
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login
from utils.time_utils import format_datetime_de, now_berlin
from utils.zeit_events import EVENT_CLOCK_IN, EVENT_CLOCK_OUT, register_time_event
from pages import admin_dashboard

st.set_page_config(page_title="🥩 CrewBase Piccolo", page_icon="🥩", layout="wide")
supabase = init_supabase_client()

# --- RESET LOGIK ---
if st.session_state.get("trigger_reset"):
    st.session_state["terminal_pin_entry"] = ""
    st.session_state["trigger_reset"] = False

# --- HAUPTLOGIK ---
if not st.session_state.get('logged_in'):
    st.title("🥩 CrewBase Piccolo")
    tab_stempel, tab_admin = st.tabs(["🕒 Mitarbeiter Stempeluhr", "🔐 Admin Login"])
    
    with tab_stempel:
        pin = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        if len(pin) == 4:
            res = supabase.table("mitarbeiter").select("*").eq("pin", pin).execute()
            if res.data:
                ma = res.data[0]
                st.info(f"Hallo {ma['vorname']}! Schicht: {now_berlin().strftime('%d.%m.%Y')}")
                
                c1, c2 = st.columns(2)
                if c1.button("🟢 KOMMEN", key=f"k_{ma['id']}", use_container_width=True):
                    result = register_time_event(
                        supabase,
                        betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
                        mitarbeiter_id=ma["id"],
                        action=EVENT_CLOCK_IN,
                        source="terminal",
                        created_by=st.session_state.get("user_id"),
                    )
                    if not result.get("ok"):
                        st.error(result.get("error", "Einstempeln fehlgeschlagen."))
                    else:
                        st.success(f"Eingestempelt um {format_datetime_de(now_berlin())}")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5); st.rerun()

                if c2.button("🔴 GEHEN", key=f"g_{ma['id']}", use_container_width=True):
                    result = register_time_event(
                        supabase,
                        betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
                        mitarbeiter_id=ma["id"],
                        action=EVENT_CLOCK_OUT,
                        source="terminal",
                        created_by=st.session_state.get("user_id"),
                    )
                    if not result.get("ok"):
                        st.error(result.get("error", "Ausstempeln fehlgeschlagen."))
                    else:
                        st.success("Schönen Feierabend!")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5); st.rerun()
            else: st.error("PIN unbekannt.")

    with tab_admin:
        with st.form("login"):
            bnr = st.text_input("Betriebsnummer", value="20262204")
            usr = st.text_input("Admin")
            pwd = st.text_input("Passwort", type="password")
            if st.form_submit_button("Login"):
                user = verify_credentials_with_betrieb(bnr, usr, pwd)
                if user and user['role'] == 'admin':
                    st.session_state.update(
                        {
                            "logged_in": True,
                            "is_admin": True,
                            "user_id": user.get("id"),
                            "betrieb_id": user.get("betrieb_id"),
                            "betrieb_name": user.get("betrieb_name"),
                        }
                    )
                    update_last_login(str(user.get("id")))
                    st.rerun()
else:
    admin_dashboard.show_admin_dashboard()
    if st.sidebar.button("Abmelden"):
        st.session_state.clear(); st.rerun()
