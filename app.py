import streamlit as st
from datetime import date
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


@st.cache_data(ttl=120, show_spinner=False)
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


@st.cache_data(ttl=10, show_spinner=False)
def _get_event_state_cached(mitarbeiter_id: int, day_iso: str) -> Dict[str, Any]:
    """Kurzzeit-Cache für Terminal-Status, reduziert DB-Last bei Reruns."""
    return get_event_state_for_day(
        supabase,
        mitarbeiter_id=mitarbeiter_id,
        day=date.fromisoformat(day_iso),
    )


def _refresh_after_terminal_event() -> None:
    """Leichtgewichtiger Refresh nach Event-Schreiben."""
    _get_event_state_cached.clear()
    st.session_state["trigger_reset"] = True
    st.rerun()


def _get_terminal_betrieb_id(mitarbeiter: Dict[str, Any]) -> Optional[int]:
    """
    Ermittelt den Betriebskontext für Terminal-Buchungen.
    Kein Fallback auf eine beliebige betrieb_id – schützt vor Cross-Tenant-Buchungen.
    """
    candidates = (
        mitarbeiter.get("betrieb_id"),
        st.session_state.get("betrieb_id"),
    )
    for value in candidates:
        if value is None:
            continue
        try:
            parsed = int(value)
        except (ValueError, TypeError):
            continue
        if parsed > 0:
            return parsed
    return None


def _submit_terminal_event(
    mitarbeiter: Dict[str, Any],
    *,
    action: str,
    success_message: str,
    error_message: str,
) -> None:
    betrieb_id = _get_terminal_betrieb_id(mitarbeiter)
    if betrieb_id is None:
        st.error(
            "🔒 Terminal konnte keinen Betriebskontext ermitteln. "
            "Bitte Mitarbeiterdaten oder Admin-Kontakt prüfen."
        )
        return

    result = register_time_event(
        supabase,
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter["id"],
        action=action,
        source="terminal",
        created_by=st.session_state.get("user_id"),
    )
    if not result.get("ok"):
        st.error(result.get("error", error_message))
    else:
        st.success(success_message)
    _refresh_after_terminal_event()


def _render_login_footer() -> None:
    st.markdown("""
        <div style="padding:14px 8px;border-top:1px solid #1a1a1a;background:#0a0a0a;margin-top:12px">
            <div style="font-size:10px;color:#2a2a2a;text-align:center">
                © 2026 Complio &nbsp;·&nbsp; DSGVO-konform &nbsp;·&nbsp; SSL &nbsp;·&nbsp; §5 ArbSchG
            </div>
        </div>
    """, unsafe_allow_html=True)


def _render_login_branding() -> None:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"]{background:#0a0a0a!important}
    [data-testid="stHeader"]{display:none!important}
    [data-testid="stMainBlockContainer"]{padding-top:0!important;max-width:480px!important;margin:0 auto!important}
    .block-container{padding-top:0!important;padding-bottom:2rem!important;max-width:480px!important;margin:0 auto!important}
    section[data-testid="stSidebar"]{display:none!important}
    [data-testid="stDecoration"]{display:none!important}
    div[data-testid="stTabs"] [data-baseweb="tab-list"]{background:#111!important;border:1px solid #1a1a1a!important;border-radius:7px!important;padding:3px!important;gap:0!important}
    div[data-testid="stTabs"] [data-baseweb="tab"]{color:#555!important;font-size:12px!important;padding:7px 8px!important;border-radius:5px!important;border:none!important;flex:1!important;text-align:center!important}
    div[data-testid="stTabs"] [aria-selected="true"]{background:#1a1a1a!important;color:#fff!important}
    div[data-testid="stTextInput"] label{font-size:10px!important;color:#555!important;font-weight:600!important;letter-spacing:0.5px!important;text-transform:uppercase!important}
    div[data-testid="stTextInput"] input{background:#111!important;border:1px solid #1a1a1a!important;color:#fff!important;-webkit-text-fill-color:#fff!important;border-radius:7px!important;font-size:14px!important;min-height:42px!important}
    div[data-testid="stTextInput"] input:focus{border-color:#F97316!important;box-shadow:none!important}
    div[data-testid="stTextInput"] input::placeholder{color:#333!important;-webkit-text-fill-color:#333!important}
    div[data-testid="stForm"]{border:none!important;background:transparent!important;padding:0!important;box-shadow:none!important}
    div[data-testid="stFormSubmitButton"] button{background:#F97316!important;color:#fff!important;border:none!important;border-radius:7px!important;font-weight:600!important;font-size:14px!important;width:100%!important;padding:12px!important;margin-top:4px!important}
    div[data-testid="stFormSubmitButton"] button:hover{background:#EA6C0A!important}
    div[data-testid="stButton"] button{color:#888!important;background:transparent!important;border:1px solid #1a1a1a!important;border-radius:7px!important;font-size:13px!important;width:100%!important}
    div[data-testid="stAlert"]{background:#1a1a1a!important;border:1px solid #222!important;border-radius:7px!important}
    div[data-testid="stAlert"] p{color:#888!important;font-size:13px!important}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#0a0a0a;padding:16px 0 20px 0;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1a1a1a;margin-bottom:28px">
        <div style="font-size:20px;font-weight:700;color:#fff;letter-spacing:-0.5px">Complio<span style="color:#F97316">.</span></div>
        <div style="font-size:9px;color:#333;letter-spacing:1.5px;text-transform:uppercase">Rechtssicher · Organisiert · Geschützt</div>
    </div>
    <div style="margin-bottom:20px">
        <div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:4px">Anmelden</div>
        <div style="font-size:13px;color:#444">Noch kein Konto? <a href="https://getcomplio.de" style="color:#F97316;text-decoration:none;font-weight:500">30 Tage kostenlos starten</a></div>
    </div>
    """, unsafe_allow_html=True)
    
# --- RESET LOGIK ---
if st.session_state.get("trigger_reset"):
    st.session_state["terminal_pin_entry"] = ""
    st.session_state["trigger_reset"] = False


@st.fragment
def _render_login_fragment() -> None:
    tab_stempel, tab_admin, tab_registrierung = st.tabs([
        "🕒 Stempeluhr",
        "🔐 Admin Login", 
        "🏢 Registrieren"
    ])

    with tab_stempel:
        import time as _time
        _PIN_FAIL_KEY = "pin_fail_count"
        _PIN_LOCK_KEY = "pin_locked_until"
        locked_until = st.session_state.get(_PIN_LOCK_KEY, 0)
        if _time.time() < locked_until:
            remaining = int(locked_until - _time.time())
            st.warning(f"Zu viele Fehlversuche. Bitte {remaining}s warten.")
        else:
            pin = st.text_input("PIN eingeben", type="password", max_chars=6, key="terminal_pin_entry")
            ma = None
            if len(pin) >= 4:
                ma = _find_mitarbeiter_by_pin(pin)
                if ma:
                    st.session_state[_PIN_FAIL_KEY] = 0
                else:
                    fails = st.session_state.get(_PIN_FAIL_KEY, 0) + 1
                    st.session_state[_PIN_FAIL_KEY] = fails
                    if fails >= 5:
                        st.session_state[_PIN_LOCK_KEY] = _time.time() + 60
                        st.session_state[_PIN_FAIL_KEY] = 0
            if ma:
                st.info(f"Hallo {ma['vorname']}! Schicht: {now_berlin().strftime('%d.%m.%Y')}")
                state = _get_event_state_cached(
                    ma["id"],
                    now_berlin().date().isoformat(),
                )

                c1, c2 = st.columns(2)
                if c1.button("KOMMEN", key=f"k_{ma['id']}", use_container_width=True):
                    _submit_terminal_event(
                        ma,
                        action=EVENT_CLOCK_IN,
                        success_message=f"Eingestempelt um {format_datetime_de(now_berlin())}",
                        error_message="Einstempeln fehlgeschlagen.",
                    )

                if c2.button("GEHEN", key=f"g_{ma['id']}", use_container_width=True):
                    _submit_terminal_event(
                        ma,
                        action=EVENT_CLOCK_OUT,
                        success_message="Schönen Feierabend!",
                        error_message="Ausstempeln fehlgeschlagen.",
                    )

                c3, c4 = st.columns(2)
                if c3.button(
                    "PAUSE START",
                    key=f"bs_{ma['id']}",
                    use_container_width=True,
                    disabled=(not state["eingestempelt"] or state["pause_aktiv"]),
                ):
                    _submit_terminal_event(
                        ma,
                        action=EVENT_BREAK_START,
                        success_message="Pause gestartet.",
                        error_message="Pausenstart fehlgeschlagen.",
                    )

                if c4.button(
                    "PAUSE ENDE",
                    key=f"be_{ma['id']}",
                    use_container_width=True,
                    disabled=(not state["eingestempelt"] or not state["pause_aktiv"]),
                ):
                    _submit_terminal_event(
                        ma,
                        action=EVENT_BREAK_END,
                        success_message="Pause beendet.",
                        error_message="Pausenende fehlgeschlagen.",
                    )
            else:
                st.error("PIN unbekannt.")

    with tab_admin:
        with st.form("login"):
            bnr = st.text_input("Betriebsnummer")
            usr = st.text_input("Benutzername")
            pwd = st.text_input("Passwort", type="password")
            if st.form_submit_button("Anmelden", use_container_width=True):
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

    with tab_registrierung:
        from modules.onboarding.onboarding_ui import show_registrierung
        show_registrierung()


# --- HAUPTLOGIK ---
# Landing Page temporär deaktiviert
if not st.session_state.get('logged_in'):
    _render_login_branding()
    _render_login_fragment()
    _render_login_footer()
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
    # Willkommens-Dialog nach Erstregistrierung
    if st.session_state.get("_neu_registriert"):
        bnr = st.session_state.get("_betriebsnummer", "")
        pwd = st.session_state.get("_admin_passwort", "")
        st.success(
            f"🎉 **Willkommen bei Complio!** Dein Betrieb wurde erfolgreich angelegt.\n\n"
            f"**Betriebsnummer:** `{bnr}`  \n"
            f"**Passwort:** `{pwd}`  \n\n"
            f"Deine Zugangsdaten wurden per E-Mail verschickt. "
            f"Du kannst das Passwort jederzeit im Admin-Bereich ändern."
        )
        st.session_state.pop("_neu_registriert", None)
        st.session_state.pop("_admin_passwort", None)

    if st.session_state.get("is_admin"):
        from modules.onboarding.onboarding_ui import show_testphase_banner
        show_testphase_banner(st.session_state.get("betrieb_id"))
        from pages import admin_dashboard
        admin_dashboard.show_admin_dashboard()
    else:
        from pages import mitarbeiter_dashboard
        mitarbeiter_dashboard.show_mitarbeiter_dashboard()
