import streamlit as st
import time
import base64
import mimetypes
from typing import Any, Dict, Optional
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
    initial_sidebar_state="collapsed",
)
@st.cache_resource(show_spinner=False)
def _get_supabase_client():
    return init_supabase_client()


supabase = _get_supabase_client()
apply_custom_css()


def _load_mitarbeiter_profile_for_user(user: Dict[str, Any], username: str) -> Optional[Dict[str, Any]]:
    """
    Lädt den Mitarbeiterdatensatz zum eingeloggten User.
    Primär über user_id, fallback über username/email für Legacy-Daten.
    """
    try:
        base_select = (
            "id, betrieb_id, user_id, personalnummer, vorname, nachname, email, telefon, "
            "strasse, plz, ort, geburtsdatum, eintrittsdatum, monatliche_soll_stunden, "
            "jahres_urlaubstage, resturlaub_vorjahr"
        )
        q = (
            supabase.table("mitarbeiter")
            .select(base_select)
            .eq("betrieb_id", user.get("betrieb_id"))
            .eq("user_id", user.get("id"))
            .limit(1)
            .execute()
        )
        if q.data:
            return q.data[0]
    except Exception:
        pass

    # Legacy-Fallback: Zuordnung über email=username
    try:
        q = (
            supabase.table("mitarbeiter")
            .select(base_select)
            .eq("betrieb_id", user.get("betrieb_id"))
            .eq("email", username)
            .limit(1)
            .execute()
        )
        if q.data:
            return q.data[0]
    except Exception:
        pass
    return None


def _find_mitarbeiter_by_pin(pin: str) -> Optional[Dict[str, Any]]:
    """
    Sucht Mitarbeiter per Terminal-PIN.
    Unterstützt sowohl neues Feld `stempel_pin` als auch Legacy-Feld `pin`.
    """
    select_cols = "id, vorname, nachname, betrieb_id"
    for pin_column in ("stempel_pin", "pin"):
        try:
            res = (
                supabase.table("mitarbeiter")
                .select(select_cols)
                .eq(pin_column, pin)
                .limit(1)
                .execute()
            )
            if res.data:
                return res.data[0]
        except Exception:
            continue
    return None


def _wrap_card_start() -> None:
    st.markdown("<div class='coreo-card'>", unsafe_allow_html=True)


def _wrap_card_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


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
        [data-testid="stMainBlockContainer"] > div.block-container {
            min-height: 92vh;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }
        .coreo-login-root {
            width: min(760px, 96vw);
            margin: 0 auto;
        }
        .coreo-logo-wrap {
            width: 100%;
            display: flex;
            justify-content: center;
            margin: 0 auto 1.25rem auto;
        }
        .coreo-logo-wrap img {
            width: min(92vw, 560px);
            max-width: 560px;
            height: auto;
            object-fit: contain;
            display: block;
        }
        div[data-testid="stTabs"] {
            max-width: 680px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stForm"] {
            border: 1px solid #2a2a2a !important;
            border-radius: 12px !important;
            background: #0b0b0b !important;
            padding: 1.2rem 1.2rem 0.6rem 1.2rem !important;
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.45) !important;
            max-width: 680px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stForm"] * {
            color: #ffffff !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            background: #0b0b0b !important;
            border-bottom: 1px solid #2a2a2a !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab"] {
            color: #ffffff !important;
            background: #121212 !important;
            border: 1px solid #2a2a2a !important;
            border-radius: 10px 10px 0 0 !important;
        }
        div[data-testid="stTabs"] [aria-selected="true"] {
            background: #2563eb !important;
            color: #ffffff !important;
            border-color: #2563eb !important;
        }
        div[data-testid="stTextInput"] input {
            min-height: 52px !important;
            font-size: 1rem !important;
            border-radius: 10px !important;
            padding: 0 0.85rem !important;
            background: #121212 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: 1px solid #2a2a2a !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 1px #2563eb !important;
            background: #000000 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        div[data-testid="stWidgetLabel"], label {
            color: #ffffff !important;
        }
        .coreo-topbar {
            position: sticky;
            top: 0;
            z-index: 50;
            background: #0b0b0b;
            border-bottom: 1px solid #2a2a2a;
            margin-bottom: 1rem;
            padding-top: 0.25rem;
            padding-bottom: 0.25rem;
        }
        .st-key-top_nav_main {
            margin-top: 0.35rem;
        }
        @media (max-width: 768px) {
            .coreo-login-root {
                max-width: 96vw;
            }
            .coreo-logo-wrap img {
                width: min(94vw, 460px);
                max-width: 460px;
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


@st.fragment
def _render_login_fragment() -> None:
    tab_stempel, tab_admin = st.tabs(["Mitarbeiter Stempeluhr", "Admin Login"])

    with tab_stempel:
        pin = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        if len(pin) == 4:
            ma = _find_mitarbeiter_by_pin(pin)
            if ma:
                st.info(f"Hallo {ma['vorname']}! Schicht: {now_berlin().strftime('%d.%m.%Y')}")
                state = get_event_state_for_day(
                    supabase,
                    mitarbeiter_id=ma["id"],
                    day=now_berlin().date(),
                )

                c1, c2 = st.columns(2)
                if c1.button("KOMMEN", key=f"k_{ma['id']}", use_container_width=True):
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

                if c2.button("GEHEN", key=f"g_{ma['id']}", use_container_width=True):
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
                    "PAUSE START",
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
                    "PAUSE ENDE",
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
            usr = st.text_input("Benutzername")
            pwd = st.text_input("Passwort", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                user = verify_credentials_with_betrieb(bnr, usr, pwd)
                if user and user['role'] == 'admin':
                    st.session_state.update(
                        {
                            "logged_in": True,
                            "is_admin": True,
                            "role": "admin",
                            "user_id": user.get("id"),
                            "betrieb_id": user.get("betrieb_id"),
                            "betrieb_name": user.get("betrieb_name"),
                            "mitarbeiter_id": None,
                        }
                    )
                    update_last_login(str(user.get("id")))
                    st.rerun()
                elif user and user.get("role") == "mitarbeiter":
                    ma = _load_mitarbeiter_profile_for_user(user, usr)
                    if not ma:
                        st.error("Mitarbeiter-Profil konnte nicht geladen werden. Bitte Admin informieren.")
                    else:
                        st.session_state.update(
                            {
                                "logged_in": True,
                                "is_admin": False,
                                "role": "mitarbeiter",
                                "user_id": user.get("id"),
                                "betrieb_id": user.get("betrieb_id"),
                                "betrieb_name": user.get("betrieb_name"),
                                "mitarbeiter_id": ma.get("id"),
                                "vorname": ma.get("vorname"),
                                "nachname": ma.get("nachname"),
                                "mitarbeiter_personalnummer": ma.get("personalnummer"),
                            }
                        )
                        update_last_login(str(user.get("id")))
                        st.rerun()
                else:
                    st.error("Login fehlgeschlagen. Bitte Zugangsdaten prüfen.")


# --- HAUPTLOGIK ---
if not st.session_state.get('logged_in'):
    _render_login_branding()
    _wrap_card_start()
    _render_login_fragment()
    _wrap_card_end()
else:
    st.markdown(
        """
        <style>
        .st-key-logout_fixed_wrap {
            position: fixed;
            top: 0.85rem;
            right: 1rem;
            z-index: 2000;
            width: 150px;
        }
        .st-key-logout_fixed_wrap button {
            width: 100% !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }
        @media (max-width: 768px) {
            .st-key-logout_fixed_wrap {
                top: 0.6rem;
                right: 0.6rem;
                width: 132px;
            }
            .st-key-logout_fixed_wrap button {
                min-height: 38px !important;
                font-size: 0.9rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="logout_fixed_wrap"):
        if st.button("Abmelden", key="logout_fixed_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    if st.session_state.get("is_admin"):
        from pages import admin_dashboard
        admin_dashboard.show_admin_dashboard()
    else:
        from pages import mitarbeiter_dashboard
        mitarbeiter_dashboard.show_mitarbeiter_dashboard()
