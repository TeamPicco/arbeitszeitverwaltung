"""
Session-Management für Streamlit
"""

import streamlit as st
from datetime import datetime, timedelta
import os


def init_session_state():
    """Initialisiert den Session State mit Standardwerten"""
    
    # Authentifizierung
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    if 'role' not in st.session_state:
        st.session_state.role = None
    
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None
    
    # Mitarbeiterdaten (Cache)
    if 'mitarbeiter_data' not in st.session_state:
        st.session_state.mitarbeiter_data = None


def check_session_timeout() -> bool:
    """
    Prüft, ob die Session abgelaufen ist
    
    Returns:
        bool: True wenn abgelaufen, sonst False
    """
    if not st.session_state.get('authenticated', False):
        return False
    
    if not st.session_state.get('login_time'):
        return True
    
    # Hole Timeout aus Umgebungsvariablen (Standard: 480 Minuten = 8 Stunden)
    timeout_minutes = int(os.getenv('SESSION_TIMEOUT_MINUTES', '480'))
    timeout_delta = timedelta(minutes=timeout_minutes)
    
    # Prüfe, ob Timeout überschritten
    if datetime.now() - st.session_state.login_time > timeout_delta:
        return True
    
    return False


def clear_session():
    """Löscht alle Session-Daten"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def is_admin() -> bool:
    """
    Prüft, ob der aktuelle Benutzer ein Administrator ist
    
    Returns:
        bool: True wenn Admin, sonst False
    """
    return st.session_state.get('role') == 'admin'


def is_mitarbeiter() -> bool:
    """
    Prüft, ob der aktuelle Benutzer ein Mitarbeiter ist
    
    Returns:
        bool: True wenn Mitarbeiter, sonst False
    """
    return st.session_state.get('role') == 'mitarbeiter'


def get_current_user_id() -> str:
    """
    Gibt die User-ID des aktuell angemeldeten Benutzers zurück
    
    Returns:
        str: User-ID
    """
    return st.session_state.get('user_id', '')


def get_current_username() -> str:
    """
    Gibt den Benutzernamen des aktuell angemeldeten Benutzers zurück
    
    Returns:
        str: Benutzername
    """
    return st.session_state.get('username', '')


def get_current_betrieb_id() -> int:
    """
    Gibt die Betrieb-ID des aktuell angemeldeten Benutzers zurück
    
    Returns:
        int: Betrieb-ID
    """
    return st.session_state.get('betrieb_id', None)
