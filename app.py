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
    pass


def _wrap_card_end() -> None:
    pass


def _render_login_branding() -> tuple:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:#0a0a0a!important}
    .block-container{padding-top:0!important;padding-bottom:0!important;max-width:100%!important}
    [data-testid="stMainBlockContainer"]{padding:0!important}
    section[data-testid="stSidebar"]{display:none}
    div[data-testid="column"]:first-child{background:#0a0a0a;border-right:1px solid #1a1a1a;padding:2rem!important}
    div[data-testid="column"]:last-child{background:#111;padding:2rem!important}
    div[data-testid="stTabs"] [data-baseweb="tab-list"]{background:#0a0a0a!important;border-bottom:1px solid #222!important}
    div[data-testid="stTabs"] [data-baseweb="tab"]{color:#888!important;background:transparent!important;border:none!important;font-size:13px!important;padding:8px 16px!important}
    div[data-testid="stTabs"] [aria-selected="true"]{color:#F97316!important;border-bottom:2px solid #F97316!important}
    div[data-testid="stTextInput"] input{background:#0a0a0a!important;border:1px solid #222!important;color:#fff!important;-webkit-text-fill-color:#fff!important;border-radius:8px!important;min-height:44px!important}
    div[data-testid="stTextInput"] input:focus{border-color:#F97316!important;box-shadow:0 0 0 1px #F97316!important}
    div[data-testid="stForm"]{border:none!important;background:transparent!important;padding:0!important}
    div[data-testid="stFormSubmitButton"] button{background:#F97316!important;color:#fff!important;border:none!important;border-radius:8px!important;font-weight:600!important;min-height:44px!important;width:100%!important}
    div[data-testid="stFormSubmitButton"] button:hover{background:#EA6C0A!important}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#0a0a0a;border-bottom:1px solid #1a1a1a;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;margin-bottom:0">
        <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:-0.5px">Complio<span style="color:#F97316">.</span></div>
        <div style="font-size:10px;color:#444;letter-spacing:2px;text-transform:uppercase">Rechtssicher · Organisiert · Geschützt</div>
    </div>
    """, unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1], gap="small")
    with col_left:
        st.markdown("""
        <div style="padding:1rem 0">
        <h2 style="font-size:24px;font-weight:700;color:#fff;line-height:1.3;margin-bottom:12px">
            Dein Betrieb.<br>
            <span style="color:#F97316">Rechtssicher.</span>
        </h2>
        <p style="font-size:13px;color:#555;line-height:1.7;margin-bottom:24px">
            Dienstplanung, Personalakte und Arbeitssicherheit in einer Plattform.
            Nie wieder Bußgelder wegen fehlender Dokumentation.
        </p>
        <div style="display:flex;flex-direction:column;gap:10px">
            <div style="display:flex;align-items:center;gap:10px">
                <div style="min-width:30px;height:30px;background:#1a1a1a;border:1px solid #222;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:13px">🛡️</div>
                <div style="font-size:12px;color:#555">Bis zu <strong style="color:#aaa">30.000€ Bußgeld</strong> vermeiden</div>
            </div>
            <div style="display:flex;align-items:center;gap:10px">
                <div style="min-width:30px;height:30px;background:#1a1a1a;border:1px solid #222;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:13px">📅</div>
                <div style="font-size:12px;color:#555"><strong style="color:#aaa">Dienstplanung</strong> mit Kostenberechnung</div>
            </div>
            <div style="display:flex;align-items:center;gap:10px">
                <div style="min-width:30px;height:30px;background:#1a1a1a;border:1px solid #222;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:13px">⏰</div>
                <div style="font-size:12px;color:#555"><strong style="color:#aaa">ArbZG-Verstöße</strong> in Echtzeit erkennen</div>
            </div>
            <div style="display:flex;align-items:center;gap:10px">
                <div style="min-width:30px;height:30px;background:#1a1a1a;border:1px solid #222;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:13px">👥</div>
                <div style="font-size:12px;color:#555"><strong style="color:#aaa">Personalakte</strong> DSGVO-konform</div>
            </div>
        </div>
        <div style="margin-top:2rem;padding-top:1.5rem;border-top:1px solid #1a1a1a">
            <div style="font-size:11px;color:#333;display:flex;gap:16px">
                <span><span style="color:#F97316">✓</span> DSGVO-konform</span>
                <span><span style="color:#F97316">✓</span> SSL</span>
                <span><span style="color:#F97316">✓</span> §5 ArbSchG</span>
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
    return col_right

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
            bnr = st.text_input("Betriebsnummer")
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

    with tab_registrierung:
        from modules.onboarding.onboarding_ui import show_registrierung
        show_registrierung()


# --- HAUPTLOGIK ---
# Landing Page temporär deaktiviert
if not st.session_state.get('logged_in'):
    col_right = _render_login_branding()
    with col_right:
        _render_login_fragment()
    st.markdown("""
    <div class="login-footer">
        <div class="footer-text">© 2026 Complio · support@complio.de</div>
        <div class="trust-badges">
            <div class="trust-badge"><span>✓</span> DSGVO-konform</div>
            <div class="trust-badge"><span>✓</span> SSL verschlüsselt</div>
            <div class="trust-badge"><span>✓</span> §5 ArbSchG konform</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
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
