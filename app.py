import streamlit as st
import time
import base64
import mimetypes
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login
from utils.time_utils import format_datetime_de, now_berlin
from utils.branding import BRAND_APP_NAME, BRAND_LOGO_IMAGE
from utils.styles import apply_custom_css
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
apply_custom_css()


def _render_login_branding() -> None:
    def _logo_data_uri(path: str) -> str:
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
            mime = mimetypes.guess_type(path)[0] or "image/png"
            encoded = base64.b64encode(raw).decode("ascii")
            return f"data:{mime};base64,{encoded}"
        except Exception:
            return ""

    st.markdown(
        """
        <style>
        .coreo-login-root {
            max-width: 620px;
            margin: 0 auto 0.6rem auto;
        }
        .coreo-logo-wrap {
            width: 100%;
            display: flex;
            justify-content: center;
            margin: 0.1rem auto 0.9rem auto;
        }
        .coreo-logo-wrap img {
            width: min(78vw, 430px);
            max-width: 430px;
            height: auto;
            object-fit: contain;
            display: block;
        }
        div[data-testid="stTabs"] {
            max-width: 620px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stForm"] {
            border: 1px solid #1f2937 !important;
            border-radius: 14px !important;
            background: #050505 !important;
            padding: 1rem 1rem 0.4rem 1rem !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.35) !important;
            max-width: 620px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stTextInput"] input {
            min-height: 46px !important;
            font-size: 1rem !important;
            border-radius: 10px !important;
        }
        @media (max-width: 768px) {
            .coreo-login-root {
                max-width: 96vw;
            }
            .coreo-logo-wrap img {
                width: min(92vw, 340px);
                max-width: 340px;
            }
            div[data-testid="stTabs"],
            div[data-testid="stForm"] {
                max-width: 96vw !important;
            }
            div[data-testid="stTabs"] [data-baseweb="tab"] {
                font-size: 0.9rem !important;
                padding: 0.5rem 0.4rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    data_uri = _logo_data_uri(BRAND_LOGO_IMAGE) if BRAND_LOGO_IMAGE else ""
    if data_uri:
        st.markdown(
            f"<div class='coreo-login-root'><div class='coreo-logo-wrap'><img src='{data_uri}' alt='Logo'></div></div>",
            unsafe_allow_html=True,
        )
    elif BRAND_LOGO_IMAGE:
        _, center, _ = st.columns([1, 2, 1])
        with center:
            st.image(BRAND_LOGO_IMAGE, use_container_width=True)

# --- RESET LOGIK ---
if st.session_state.get("trigger_reset"):
    st.session_state["terminal_pin_entry"] = ""
    st.session_state["trigger_reset"] = False

# --- HAUPTLOGIK ---
if not st.session_state.get('logged_in'):
    _render_login_branding()
    tab_stempel, tab_admin = st.tabs(["🕒 Mitarbeiter Stempeluhr", "🔐 Admin Login"])

    with tab_stempel:
        pin = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        if len(pin) == 4:
            res = supabase.table("mitarbeiter").select("id, vorname, betrieb_id").eq("pin", pin).limit(1).execute()
            if res.data:
                ma = res.data[0]
                st.info(f"Hallo {ma['vorname']}! Schicht: {now_berlin().strftime('%d.%m.%Y')}")
                state = get_event_state_for_day(
                    supabase,
                    mitarbeiter_id=ma["id"],
                    day=now_berlin().date(),
                )

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

                c3, c4 = st.columns(2)
                if c3.button(
                    "⏸️ PAUSE START",
                    key=f"bs_{ma['id']}",
                    use_container_width=True,
                    disabled=(not state["eingestempelt"] or state["pause_aktiv"]),
                ):
                    result = register_time_event(
                        supabase,
                        betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
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
                    result = register_time_event(
                        supabase,
                        betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
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
            else:
                st.error("PIN unbekannt.")

    with tab_admin:
        with st.form("login"):
            bnr = st.text_input("Betriebsnummer", value="20262204")
            usr = st.text_input("Admin")
            pwd = st.text_input("Passwort", type="password")
            if st.form_submit_button("Login", use_container_width=True):
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
    if BRAND_LOGO_IMAGE:
        st.sidebar.image(BRAND_LOGO_IMAGE, use_container_width=True)
    from pages import admin_dashboard
    admin_dashboard.show_admin_dashboard()
    if st.sidebar.button("Abmelden"):
        st.session_state.clear(); st.rerun()
