"""
Plauderecke - Interner Chat für alle Mitarbeiter und Admin
"""

from utils.database import get_supabase_client
from datetime import datetime


def get_chat_nachrichten(limit: int = 100, betrieb_id: int = None):
    """Holt die letzten Chat-Nachrichten"""
    try:
        supabase = get_supabase_client()
        
        # Basis-Query
        query = supabase.table('plauderecke').select(
            '*, users(username)'
        )
        
        # Filter nach Betrieb falls angegeben
        if betrieb_id:
            query = query.eq('betrieb_id', betrieb_id)
        
        result = query.order('erstellt_am', desc=False).limit(limit).execute()
        
        # Füge Mitarbeiter-Namen manuell hinzu
        if result.data:
            for nachricht in result.data:
                user_id = nachricht['user_id']
                mitarbeiter_result = supabase.table('mitarbeiter').select('vorname, nachname').eq('user_id', user_id).execute()
                if mitarbeiter_result.data:
                    nachricht['mitarbeiter'] = mitarbeiter_result.data[0]
                else:
                    nachricht['mitarbeiter'] = {'vorname': 'Unbekannt', 'nachname': ''}
        
        return result.data if result.data else []
    except Exception as e:
        import logging
        logging.error(f"Fehler beim Laden der Chat-Nachrichten: {e}")
        return []


def send_chat_nachricht(user_id: int, nachricht: str, betrieb_id: int = None):
    """Sendet eine neue Chat-Nachricht"""
    try:
        supabase = get_supabase_client()
        
        # Hole betrieb_id vom User falls nicht übergeben
        if betrieb_id is None:
            user_result = supabase.table('users').select('betrieb_id').eq('id', user_id).execute()
            if user_result.data:
                betrieb_id = user_result.data[0]['betrieb_id']
        
        result = supabase.table('plauderecke').insert({
            'user_id': user_id,
            'nachricht': nachricht,
            'betrieb_id': betrieb_id
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        import logging
        logging.error(f"Fehler beim Senden der Chat-Nachricht: {e}")
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
