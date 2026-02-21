"""
Plauderecke - Interner Chat für alle Mitarbeiter und Admin
"""

from utils.database import get_supabase_client
from datetime import datetime


def get_chat_nachrichten(limit: int = 100):
    """Holt die letzten Chat-Nachrichten"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('plauderecke').select(
            '*, users(username), mitarbeiter!inner(vorname, nachname)'
        ).order('erstellt_am', desc=False).limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Fehler beim Laden der Chat-Nachrichten: {e}")
        return []


def send_chat_nachricht(user_id: int, nachricht: str):
    """Sendet eine neue Chat-Nachricht"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('plauderecke').insert({
            'user_id': user_id,
            'nachricht': nachricht
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Fehler beim Senden der Chat-Nachricht: {e}")
        return None


def delete_chat_nachricht(nachricht_id: int, user_id: int):
    """Löscht eine Chat-Nachricht (nur eigene Nachrichten)"""
    try:
        supabase = get_supabase_client()
        supabase.table('plauderecke').delete().eq('id', nachricht_id).eq('user_id', user_id).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Löschen der Chat-Nachricht: {e}")
        return False
