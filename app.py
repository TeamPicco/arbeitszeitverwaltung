"""
Arbeitszeitverwaltung - Hauptanwendung
DSGVO-konform & Nachweisgesetz-konform
"""

import streamlit as st
from dotenv import load_dotenv
import os
from datetime import datetime

# Lade Umgebungsvariablen
load_dotenv()

# Importiere Module
from utils.database import init_supabase_client, verify_credentials
from utils.session import init_session_state, check_session_timeout
from pages import admin_dashboard, mitarbeiter_dashboard

# Seiten-Konfiguration
st.set_page_config(
    page_title=os.getenv("APP_TITLE", "Arbeitszeitverwaltung"),
    page_icon=os.getenv("APP_ICON", "⏰"),
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS für besseres Design
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .info-box {
        background-color: #e7f3ff;
        border-left: 5px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #155a8a;
    }
</style>
""", unsafe_allow_html=True)


def login_page():
    """Zeigt die Login-Seite an"""
    
    st.markdown('<div class="main-header">🕐 Arbeitszeitverwaltung</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>Willkommen zur Arbeitszeitverwaltung</strong><br>
        Diese Anwendung erfüllt die Anforderungen des deutschen Arbeitsrechts und ist DSGVO-konform.
    </div>
    """, unsafe_allow_html=True)
    
    # Login-Formular
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Anmeldung")
        
        with st.form("login_form"):
            username = st.text_input("Benutzername", key="login_username")
            password = st.text_input("Passwort", type="password", key="login_password")
            submit = st.form_submit_button("Anmelden")
            
            if submit:
                if not username or not password:
                    st.error("Bitte geben Sie Benutzername und Passwort ein.")
                else:
                    # Verifiziere Anmeldedaten
                    user_data = verify_credentials(username, password)
                    
                    if user_data:
                        # Speichere Benutzerdaten in Session
                        st.session_state.authenticated = True
                        st.session_state.user_id = user_data['id']
                        st.session_state.username = user_data['username']
                        st.session_state.role = user_data['role']
                        st.session_state.login_time = datetime.now()
                        
                        # Aktualisiere letzten Login in Datenbank
                        from utils.database import update_last_login
                        update_last_login(user_data['id'])
                        
                        st.success(f"Willkommen, {username}!")
                        st.rerun()
                    else:
                        st.error("Ungültige Anmeldedaten. Bitte versuchen Sie es erneut.")
        
        # DSGVO-Hinweis
        st.markdown("""
        <div style="margin-top: 2rem; padding: 1rem; background-color: #f8f9fa; border-radius: 5px; font-size: 0.85rem;">
            <strong>Datenschutzhinweis:</strong><br>
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
