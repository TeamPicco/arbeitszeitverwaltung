"""
Arbeitszeitverwaltung - Hauptanwendung
DSGVO-konform & Nachweisgesetz-konform
"""

import streamlit as st
from dotenv import load_dotenv
import os
from datetime import datetime
import base64

# Lade Umgebungsvariablen
load_dotenv()

# Importiere Module
from utils.database import init_supabase_client, verify_credentials
from utils.session import init_session_state, check_session_timeout
from pages import admin_dashboard, mitarbeiter_dashboard

# Seiten-Konfiguration
favicon_path = os.path.join(os.path.dirname(__file__), "assets", "favicon.ico")
st.set_page_config(
    page_title="CrewBase - Arbeitszeitverwaltung",
    page_icon=favicon_path if os.path.exists(favicon_path) else "⏰",
    layout="wide",
    initial_sidebar_state="collapsed"
)


def get_base64_image(image_path):
    """Konvertiert ein Bild zu Base64"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None


# CSS für besseres Design
def inject_pwa_headers():
    """Fügt PWA-Meta-Tags und Manifest ein"""
    st.markdown("""
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#1f77b4">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="CrewBase">
    <link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
    <script>
        // Service Worker registrieren
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/sw.js')
                    .then(reg => console.log('Service Worker registriert:', reg))
                    .catch(err => console.log('Service Worker Fehler:', err));
            });
        }
    </script>
    """, unsafe_allow_html=True)


def apply_custom_css(hide_sidebar: bool = False):
    """Wendet benutzerdefiniertes CSS an"""
    
    sidebar_css = """
    /* Verstecke Seitenleiste komplett auf Login-Seite */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    """ if hide_sidebar else ""
    
    st.markdown(f"""
    <style>
        {sidebar_css}
        
        /* Verstecke Streamlit-Menü und Footer */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        .main-header {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            padding: 1rem 0;
        }}
        
        .logo-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 2rem auto;
            max-width: 600px;
        }}
        
        .logo-container img {{
            max-width: 100%;
            height: auto;
        }}
        
        .login-container {{
            max-width: 500px;
            margin: 0 auto;
            padding: 2rem;
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .info-box {{
            background-color: #e7f3ff;
            border-left: 5px solid #1f77b4;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 5px;
        }}
        
        .warning-box {{
            background-color: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 5px;
        }}
        
        .success-box {{
            background-color: #d4edda;
            border-left: 5px solid #28a745;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 5px;
        }}
        
        .error-box {{
            background-color: #f8d7da;
            border-left: 5px solid #dc3545;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 5px;
        }}
        
        .stButton>button {{
            width: 100%;
            background-color: #1f77b4;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            border: none;
        }}
        
        .stButton>button:hover {{
            background-color: #155a8a;
        }}
        
        .privacy-notice {{
            margin-top: 2rem;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
            font-size: 0.85rem;
            text-align: center;
        }}
    </style>
    """, unsafe_allow_html=True)


def login_page():
    """Zeigt die Login-Seite an"""
    
    # PWA-Headers einfügen
    inject_pwa_headers()
    
    # Wende CSS an mit versteckter Seitenleiste
    apply_custom_css(hide_sidebar=True)
    
    # Zentriertes Logo
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # CrewBase Logo anzeigen (optimiert und zentriert)
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "crewbase_logo_optimized.png")
        
        if os.path.exists(logo_path):
            # Zentriere Logo mit fester Breite
            col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
            with col_logo2:
                st.image(logo_path, use_container_width=True)
        else:
            # Fallback
            st.markdown('<div class="main-header">CrewBase</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Hinweistext in weißem Kasten
        st.markdown('<div style="background-color: #ffffff; padding: 1rem; border-radius: 8px; text-align: center; margin-bottom: 1.5rem; border: 1px solid #dee2e6;"><span style="color: #000000; font-size: 1.1rem;">Bitte gib deine Login-Daten ein:</span></div>', unsafe_allow_html=True)
        
        # Login-Formular (ohne extra Container)
        
        with st.form("login_form"):
            betriebsnummer = st.text_input("Betriebsnummer", key="login_betriebsnummer", placeholder="Ihre Betriebsnummer")
            username = st.text_input("Benutzername", key="login_username")
            password = st.text_input("Passwort", type="password", key="login_password")
            submit = st.form_submit_button("🔑 Anmelden", use_container_width=True)
            
            if submit:
                if not betriebsnummer or not username or not password:
                    st.error("⚠️ Bitte geben Sie Betriebsnummer, Benutzername und Passwort ein.")
                else:
                    # Verifiziere Anmeldedaten mit Betriebsnummer
                    from utils.database import verify_credentials_with_betrieb
                    user_data = verify_credentials_with_betrieb(betriebsnummer, username, password)
                    
                    if user_data:
                        # Speichere Benutzerdaten in Session
                        st.session_state.authenticated = True
                        st.session_state.user_id = user_data['id']
                        st.session_state.username = user_data['username']
                        st.session_state.role = user_data['role']
                        st.session_state.betrieb_id = user_data['betrieb_id']
                        st.session_state.betrieb_name = user_data['betrieb_name']
                        st.session_state.login_time = datetime.now()
                        
                        # Aktualisiere letzten Login in Datenbank
                        from utils.database import update_last_login
                        update_last_login(user_data['id'])
                        
                        st.success(f"✅ Willkommen, {username}!")
                        st.rerun()
                    else:
                        st.error("❌ Ungültige Anmeldedaten. Bitte prüfen Sie Betriebsnummer, Benutzername und Passwort.")
        
        # Datenschutzhinweis mit besserer Lesbarkeit
        st.markdown("""
        <div style="margin-top: 2rem; padding: 1.5rem; background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; color: #000000; font-size: 0.9rem; line-height: 1.6;">
            <strong style="color: #000000;">Datenschutzhinweis:</strong><br>
            Ihre Daten werden verschlüsselt übertragen und gemäß DSGVO verarbeitet. 
            Die Zeiterfassung erfolgt nach den Vorgaben des EuGH-Urteils zur Arbeitszeiterfassung.
        </div>
        """, unsafe_allow_html=True)


def logout():
    """Meldet den Benutzer ab"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def main():
    """Hauptfunktion der Anwendung"""
    
    # Initialisiere Supabase-Client
    init_supabase_client()
    
    # Initialisiere Session State
    init_session_state()
    
    # Prüfe, ob Benutzer authentifiziert ist
    if not st.session_state.get('authenticated', False):
        login_page()
        return
    
    # Nach Login: Zeige Seitenleiste
    apply_custom_css(hide_sidebar=False)
    
    # Prüfe Session-Timeout
    if check_session_timeout():
        st.warning("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
        logout()
        return
    
    # Sidebar mit Benutzerinformationen
    with st.sidebar:
        st.markdown(f"### Angemeldet als")
        st.markdown(f"**{st.session_state.username}**")
        st.markdown(f"Rolle: **{st.session_state.role.capitalize()}**")
        st.markdown("---")
        
        if st.button("Abmelden", key="logout_button"):
            logout()
    
    # Zeige entsprechendes Dashboard basierend auf Rolle
    if st.session_state.role == 'admin':
        admin_dashboard.show()
    elif st.session_state.role == 'mitarbeiter':
        mitarbeiter_dashboard.show()
    else:
        st.error("Ungültige Benutzerrolle.")


if __name__ == "__main__":
    main()
