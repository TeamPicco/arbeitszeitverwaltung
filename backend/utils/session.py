"""
Session-Management für Streamlit
"""

import streamlit as st
from datetime import datetime, timedelta, timezone
import os


def init_session_state():
    """Initialisiert den Session State mit Standardwerten."""
    defaults = {
        "authenticated": False,
        "logged_in": False,
        "is_admin": False,
        "user_id": None,
        "username": None,
        "role": None,
        "betrieb_id": None,
        "betrieb_name": None,
        "login_time": None,
        "mitarbeiter_data": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
    if datetime.now(timezone.utc) - st.session_state.login_time > timeout_delta:
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


def set_login_session(user: dict) -> None:
    """
    Setzt alle Session-Felder nach erfolgreichem Login.
    Einzige Stelle wo Login-State gesetzt werden darf.
    """
    st.session_state.update({
        "authenticated": True,
        "logged_in": True,
        "is_admin": user.get("role") == "admin",
        "user_id": user.get("id"),
        "username": user.get("username"),
        "role": user.get("role"),
        "betrieb_id": user.get("betrieb_id"),
        "betrieb_name": user.get("betrieb_name"),
        "login_time": datetime.now(),
    })


def clear_login_session() -> None:
    """
    Löscht alle Login-relevanten Session-Felder.
    Einzige Stelle wo Logout durchgeführt werden darf.
    """
    login_keys = [
        "authenticated", "logged_in", "is_admin",
        "user_id", "username", "role",
        "betrieb_id", "betrieb_name", "login_time",
        "mitarbeiter_data", "supabase",
    ]
    for key in login_keys:
        st.session_state.pop(key, None)


def require_betrieb_id() -> int:
    """
    Holt die betrieb_id aus der Session und wirft einen sauberen Fehler falls sie fehlt.
    NIEMALS auf einen Default-Wert zurückfallen - das würde Multi-Tenancy-Isolation brechen.

    Returns:
        int: Die betrieb_id des eingeloggten Users

    Raises:
        st.error + st.stop: Bei fehlender oder ungültiger betrieb_id
    """
    import streamlit as st

    betrieb_id = st.session_state.get("betrieb_id")

    if betrieb_id is None:
        st.error(
            "🔒 Sicherheitshinweis: Deine Sitzung ist nicht vollständig initialisiert. "
            "Bitte melde dich erneut an."
        )
        # Session aufräumen damit kein halbgarer Zustand bleibt
        for key in ("user_id", "user_role", "betrieb_id", "user_email"):
            if key in st.session_state:
                del st.session_state[key]
        st.stop()

    try:
        betrieb_id_int = int(betrieb_id)
        if betrieb_id_int <= 0:
            raise ValueError("betrieb_id muss positiv sein")
        return betrieb_id_int
    except (ValueError, TypeError):
        st.error(
            "🔒 Sicherheitshinweis: Ungültige Betriebs-Kennung in der Sitzung. "
            "Bitte melde dich erneut an."
        )
        st.stop()
