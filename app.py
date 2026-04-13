import streamlit as st
import time
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login, set_betrieb_session
from utils.session import init_session_state, set_login_session, clear_login_session
from utils.time_utils import format_datetime_de, now_berlin
from utils.branding import BRAND_APP_NAME, BRAND_LOGO_IMAGE, BRAND_TAGLINE
from modules.onboarding.onboarding_ui import show_registrierung
from utils.zeit_events import (
    EVENT_BREAK_END,
    EVENT_BREAK_START,
    EVENT_CLOCK_IN,
    EVENT_CLOCK_OUT,
    get_event_state_for_day,
    register_time_event,
)

st.set_page_config(
    page_title=BRAND_APP_NAME,
    page_icon=BRAND_LOGO_IMAGE,
    layout="wide",
)
@st.cache_resource(show_spinner=False)
def _get_supabase_client():
    return init_supabase_client()


supabase = _get_supabase_client()

# --- RESET LOGIK ---
if st.session_state.get("trigger_reset"):
    st.session_state["terminal_pin_entry"] = ""
    st.session_state["trigger_reset"] = False

# --- HAUPTLOGIK ---
if not st.session_state.get('logged_in'):
    brand_col, title_col = st.columns([1, 3], vertical_alignment="center")
    with brand_col:
        if BRAND_LOGO_IMAGE:
            st.image(BRAND_LOGO_IMAGE, width=150)
    with title_col:
        st.markdown(f"## {BRAND_APP_NAME}")
    tab_stempel, tab_admin, tab_registrierung = st.tabs([
        "🕒 Mitarbeiter Stempeluhr",
        "🔐 Admin Login",
        "🏢 Neu registrieren"
    ])
    
    with tab_stempel:
        pin = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        if len(pin) == 4:
            res = supabase.table("mitarbeiter").select("*").eq("pin", pin).execute()
            if res.data:
                ma = res.data[0]
                st.info(f"Hallo {ma['vorname']}! Schicht: {now_berlin().strftime('%d.%m.%Y')}")
                state = get_event_state_for_day(
                    supabase,
                    mitarbeiter_id=ma["id"],
                    day=now_berlin().date(),
                )
                
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("🟢 KOMMEN", key=f"k_{ma['id']}", use_container_width=True):
                    _bid = ma.get("betrieb_id") or st.session_state.get("betrieb_id")
                    if not _bid:
                        st.error("Fehler: Betrieb nicht erkannt. Bitte neu einloggen.")
                        st.stop()
                    result = register_time_event(
                        supabase,
                        betrieb_id=_bid,
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
                    _bid = ma.get("betrieb_id") or st.session_state.get("betrieb_id")
                    if not _bid:
                        st.error("Fehler: Betrieb nicht erkannt. Bitte neu einloggen.")
                        st.stop()
                    result = register_time_event(
                        supabase,
                        betrieb_id=_bid,
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

                if c3.button(
                    "⏸️ PAUSE START",
                    key=f"bs_{ma['id']}",
                    use_container_width=True,
                    disabled=(not state["eingestempelt"] or state["pause_aktiv"]),
                ):
                    _bid = ma.get("betrieb_id") or st.session_state.get("betrieb_id")
                    if not _bid:
                        st.error("Fehler: Betrieb nicht erkannt. Bitte neu einloggen.")
                        st.stop()
                    result = register_time_event(
                        supabase,
                        betrieb_id=_bid,
                        mitarbeiter_id=ma["id"],
                        action=EVENT_BREAK_START,
                        source="terminal",
                        created_by=st.session_state.get("user_id"),
                    )
                    if not result.get("ok"):
                        st.error(result.get("error", "Pausenstart fehlgeschlagen."))
                    else:
                        st.success("Pause gestartet.")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5); st.rerun()

                if c4.button(
                    "▶️ PAUSE ENDE",
                    key=f"be_{ma['id']}",
                    use_container_width=True,
                    disabled=(not state["eingestempelt"] or not state["pause_aktiv"]),
                ):
                    _bid = ma.get("betrieb_id") or st.session_state.get("betrieb_id")
                    if not _bid:
                        st.error("Fehler: Betrieb nicht erkannt. Bitte neu einloggen.")
                        st.stop()
                    result = register_time_event(
                        supabase,
                        betrieb_id=_bid,
                        mitarbeiter_id=ma["id"],
                        action=EVENT_BREAK_END,
                        source="terminal",
                        created_by=st.session_state.get("user_id"),
                    )
                    if not result.get("ok"):
                        st.error(result.get("error", "Pausenende fehlgeschlagen."))
                    else:
                        st.success("Pause beendet.")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5); st.rerun()
            else: st.error("PIN unbekannt.")

    with tab_admin:
        with st.form("login"):
            bnr = st.text_input("Betriebsnummer")
            usr = st.text_input("Admin")
            pwd = st.text_input("Passwort", type="password")
            if st.form_submit_button("Login"):
                user = verify_credentials_with_betrieb(bnr, usr, pwd)
                if user and user['role'] == 'admin':
                    set_login_session(user)
                    set_betrieb_session(
                        init_supabase_client(),
                        user.get("betrieb_id")
                    )
                    update_last_login(str(user.get("id")))
                    st.rerun()

    with tab_registrierung:
        show_registrierung()
else:
    if BRAND_LOGO_IMAGE:
        st.sidebar.image(BRAND_LOGO_IMAGE, use_container_width=True)
    from pages import admin_dashboard
    admin_dashboard.show_admin_dashboard()
    if st.sidebar.button("Abmelden"):
        clear_login_session()
        st.rerun()
