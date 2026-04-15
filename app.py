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
    [data-testid="stAppViewContainer"]{background:#0a0a0a!important}
    [data-testid="stHeader"]{background:#0a0a0a!important;display:none}
    .block-container{padding:0!important;max-width:100%!important}
    [data-testid="stMainBlockContainer"]{padding:0 0 2rem 0!important}
    section[data-testid="stSidebar"]{display:none!important}
    div[data-testid="stTabs"] [data-baseweb="tab-list"]{background:#111!important;border-bottom:1px solid #222!important;gap:4px}
    div[data-testid="stTabs"] [data-baseweb="tab"]{color:#666!important;font-size:13px!important;padding:10px 20px!important;border-radius:0!important}
    div[data-testid="stTabs"] [aria-selected="true"]{color:#F97316!important;border-bottom:2px solid #F97316!important;background:transparent!important}
    div[data-testid="stTextInput"] label{color:#888!important;font-size:12px!important;font-weight:500!important;letter-spacing:0.5px!important}
    div[data-testid="stTextInput"] input{background:#1a1a1a!important;border:1px solid #222!important;color:#fff!important;-webkit-text-fill-color:#fff!important;border-radius:8px!important;font-size:14px!important;padding:10px 14px!important}
    div[data-testid="stTextInput"] input:focus{border-color:#F97316!important}
    div[data-testid="stForm"]{border:none!important;background:transparent!important;padding:0!important;box-shadow:none!important}
    div[data-testid="stFormSubmitButton"] button{background:#F97316!important;color:#fff!important;border:none!important;border-radius:8px!important;font-weight:600!important;font-size:14px!important;padding:10px!important;width:100%!important;margin-top:4px!important}
    div[data-testid="stFormSubmitButton"] button:hover{background:#EA6C0A!important}
    div[data-testid="stButton"] button{border:1px solid #222!important;color:#888!important;background:transparent!important;border-radius:8px!important}
    div[data-testid="stAlert"]{background:#1a1a1a!important;border:1px solid #222!important;color:#888!important}
    </style>
    <div style="background:#0a0a0a;border-bottom:1px solid #1a1a1a;padding:16px 32px;display:flex;justify-content:space-between;align-items:center">
        <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:-0.5px">Complio<span style="color:#F97316">.</span></div>
        <div style="font-size:10px;color:#333;letter-spacing:2px;text-transform:uppercase">Rechtssicher · Organisiert · Geschützt</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;min-height:calc(100vh - 60px)">
        <div style="background:#0a0a0a;padding:48px;border-right:1px solid #1a1a1a;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:11px;font-weight:600;color:#F97316;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px">HR & COMPLIANCE SOFTWARE</div>
            <h1 style="font-size:36px;font-weight:700;color:#fff;line-height:1.2;letter-spacing:-0.5px;margin-bottom:16px">Dein Betrieb.<br><span style="color:#F97316">Rechtssicher.</span><br>Organisiert.</h1>
            <p style="font-size:14px;color:#555;line-height:1.7;margin-bottom:32px">Dienstplanung, Personalakte und Arbeitssicherheit in einer Plattform. Automatisch. Rechtssicher.</p>
            <div style="display:flex;flex-direction:column;gap:14px;margin-bottom:32px">
                <div style="display:flex;align-items:flex-start;gap:12px">
                    <div style="width:32px;height:32px;min-width:32px;background:#1a1a1a;border:1px solid #222;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#F97316;font-weight:700;font-size:13px">!</div>
                    <div><div style="font-size:13px;font-weight:600;color:#ccc">Bis zu 30.000€ Bußgeld vermeiden</div><div style="font-size:12px;color:#444;margin-top:2px">Gefährdungsbeurteilung automatisch mit KI</div></div>
                </div>
                <div style="display:flex;align-items:flex-start;gap:12px">
                    <div style="width:32px;height:32px;min-width:32px;background:#1a1a1a;border:1px solid #222;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#F97316;font-weight:700;font-size:13px">T</div>
                    <div><div style="font-size:13px;font-weight:600;color:#ccc">Dienstplanung mit Kostenberechnung</div><div style="font-size:12px;color:#444;margin-top:2px">Automatische Stundenberechnung ab Dienstbeginn</div></div>
                </div>
                <div style="display:flex;align-items:flex-start;gap:12px">
                    <div style="width:32px;height:32px;min-width:32px;background:#1a1a1a;border:1px solid #222;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#F97316;font-weight:700;font-size:13px">P</div>
                    <div><div style="font-size:13px;font-weight:600;color:#ccc">Personalakte DSGVO-konform</div><div style="font-size:12px;color:#444;margin-top:2px">Alle Dokumente sicher und rechtssicher verwalten</div></div>
                </div>
            </div>
            <div style="padding-top:24px;border-top:1px solid #1a1a1a;display:flex;gap:20px">
                <div style="font-size:11px;color:#333"><span style="color:#F97316;margin-right:4px">✓</span>DSGVO-konform</div>
                <div style="font-size:11px;color:#333"><span style="color:#F97316;margin-right:4px">✓</span>SSL verschlüsselt</div>
                <div style="font-size:11px;color:#333"><span style="color:#F97316;margin-right:4px">✓</span>§5 ArbSchG</div>
            </div>
        </div>
        <div style="background:#111;padding:0" id="login-right-panel">
        </div>
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
    _render_login_branding()
    st.markdown("""
    <style>
    #login-form-container{padding:48px}
    </style>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])
    with col2:
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
