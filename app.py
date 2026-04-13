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
    from utils.styles import apply_login_css
    apply_login_css()

    st.markdown("""
    <div class="login-topbar">
        <div class="login-logo">Complio<span>.</span></div>
        <div class="login-tagline">Rechtssicher · Organisiert · Geschützt</div>
    </div>
    <div class="login-grid">
        <div class="login-left">
            <h1>Dein Betrieb.<br><em>Rechtssicher.</em><br>Organisiert.</h1>
            <p>Dienstplanung, Personalakte und Arbeitssicherheit –
            alles in einer Plattform. Nie wieder Bußgelder wegen 
            fehlender Dokumentation.</p>
            <div class="login-stat">
                <div class="login-stat-icon">🛡️</div>
                <div class="login-stat-text">
                    Bis zu <strong>30.000 € Bußgeld</strong> 
                    automatisch vermeiden
                </div>
            </div>
            <div class="login-stat">
                <div class="login-stat-icon">📅</div>
                <div class="login-stat-text">
                    <strong>Dienstplanung</strong> mit 
                    automatischer Kostenberechnung
                </div>
            </div>
            <div class="login-stat">
                <div class="login-stat-icon">⏰</div>
                <div class="login-stat-text">
                    <strong>ArbZG-Verstöße</strong> 
                    in Echtzeit erkennen
                </div>
            </div>
            <div class="login-stat">
                <div class="login-stat-icon">👥</div>
                <div class="login-stat-text">
                    <strong>Personalakte</strong> 
                    DSGVO-konform verwalten
                </div>
            </div>
        </div>
        <div class="login-right">
    """, unsafe_allow_html=True)

    tab_stempel, tab_admin, tab_registrierung = st.tabs([
        "🕒 Stempeluhr",
        "🔐 Admin Login",
        "🏢 Registrieren"
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

    st.markdown("""
        <div class="register-hint">
            Noch kein Konto? 
            <a href="#">30 Tage kostenlos starten</a>
        </div>
        </div>
    </div>
    <div class="login-footer">
        <div class="login-footer-text">
            © 2026 Complio · support@complio.de
        </div>
        <div class="login-trust">
            <div class="login-trust-item">
                <span>✓</span> DSGVO-konform
            </div>
            <div class="login-trust-item">
                <span>✓</span> SSL verschlüsselt
            </div>
            <div class="login-trust-item">
                <span>✓</span> §5 ArbSchG konform
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    if BRAND_LOGO_IMAGE:
        st.sidebar.image(BRAND_LOGO_IMAGE, use_container_width=True)
    from pages import admin_dashboard
    admin_dashboard.show_admin_dashboard()
    if st.sidebar.button("Abmelden"):
        clear_login_session()
        st.rerun()
