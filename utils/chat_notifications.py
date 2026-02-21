"""
Chat-Benachrichtigungen - Zählt ungelesene Nachrichten
"""

from utils.database import get_supabase_client
from datetime import datetime


def get_unread_chat_count(user_id: int, betrieb_id: int, last_read: datetime = None):
    """
    Zählt ungelesene Chat-Nachrichten seit letztem Besuch
    
    Args:
        user_id: ID des aktuellen Users
        betrieb_id: ID des Betriebs
        last_read: Zeitpunkt des letzten Besuchs (optional)
        
    Returns:
        int: Anzahl ungelesener Nachrichten
    """
    try:
        supabase = get_supabase_client()
        
        # Basis-Query: Alle Nachrichten außer eigene
        query = supabase.table('plauderecke').select('id', count='exact').eq('betrieb_id', betrieb_id).neq('user_id', user_id)
        
        # Filter nach Zeitpunkt falls angegeben
        if last_read:
            query = query.gt('erstellt_am', last_read.isoformat())
        
        result = query.execute()
        return result.count if result.count else 0
        
    except Exception as e:
        import logging
        logging.error(f"Fehler beim Zählen ungelesener Chat-Nachrichten: {e}")
        return 0


def mark_chat_as_read(user_id: int):
    """
    Markiert Chat als gelesen (speichert Zeitstempel in Session)
    
    Args:
        user_id: ID des Users
    """
    import streamlit as st
    st.session_state.chat_last_read = datetime.now()
