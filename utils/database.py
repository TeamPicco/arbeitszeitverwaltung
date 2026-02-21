"""
Datenbank-Utility-Funktionen für Supabase
"""

import streamlit as st
from supabase import create_client, Client
import bcrypt
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# Konfiguriere Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def init_supabase_client() -> Client:
    """
    Initialisiert den Supabase-Client und speichert ihn im Session State
    
    Returns:
        Client: Supabase-Client-Instanz
    """
    if 'supabase' not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            st.error("Supabase-Konfiguration fehlt. Bitte .env-Datei prüfen.")
            st.stop()
        
        st.session_state.supabase = create_client(url, key)
    
    return st.session_state.supabase


def get_supabase_client() -> Client:
    """
    Gibt den Supabase-Client aus dem Session State zurück
    
    Returns:
        Client: Supabase-Client-Instanz
    """
    if 'supabase' not in st.session_state:
        return init_supabase_client()
    return st.session_state.supabase


def hash_password(password: str) -> str:
    """
    Hasht ein Passwort mit bcrypt
    
    Args:
        password: Klartext-Passwort
        
    Returns:
        str: Gehashtes Passwort
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verifiziert ein Passwort gegen einen Hash
    
    Args:
        password: Klartext-Passwort
        password_hash: Gespeicherter Hash
        
    Returns:
        bool: True wenn Passwort korrekt, sonst False
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def verify_credentials(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verifiziert Benutzername und Passwort
    
    Args:
        username: Benutzername
        password: Passwort
        
    Returns:
        Optional[Dict]: Benutzerdaten wenn erfolgreich, sonst None
    """
    try:
        supabase = get_supabase_client()
        
        # Hole Benutzerdaten
        response = supabase.table('users').select('*').eq('username', username).eq('is_active', True).execute()
        
        if not response.data or len(response.data) == 0:
            return None
        
        user = response.data[0]
        
        # Verifiziere Passwort
        if verify_password(password, user['password_hash']):
            return user
        
        return None
        
    except Exception as e:
        st.error(f"Fehler bei der Authentifizierung: {str(e)}")
        return None


def verify_credentials_with_betrieb(betriebsnummer: str, username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verifiziert Betriebsnummer, Benutzername und Passwort (Multi-Tenancy)
    
    Args:
        betriebsnummer: Betriebsnummer
        username: Benutzername
        password: Passwort
        
    Returns:
        Optional[Dict]: Benutzerdaten inkl. Betriebsinfo wenn erfolgreich, sonst None
    """
    try:
        supabase = get_supabase_client()
        
        # Prüfe Betrieb
        betrieb_response = supabase.table('betriebe').select('*').eq('betriebsnummer', betriebsnummer).eq('aktiv', True).execute()
        
        if not betrieb_response.data or len(betrieb_response.data) == 0:
            logger.error(f"DEBUG: Betrieb mit Nummer {betriebsnummer} nicht gefunden")
            return None
        
        betrieb = betrieb_response.data[0]
        betrieb_id = betrieb['id']
        logger.info(f"DEBUG: Betrieb gefunden - ID: {betrieb_id}, Name: {betrieb['name']}")
        
        # Hole Benutzerdaten für diesen Betrieb
        user_response = supabase.table('users').select('*').eq('username', username).eq('betrieb_id', betrieb_id).eq('is_active', True).execute()
        
        if not user_response.data or len(user_response.data) == 0:
            logger.error(f"DEBUG: User {username} nicht gefunden oder nicht aktiv für Betrieb {betrieb_id}")
            return None
        
        user = user_response.data[0]
        logger.info(f"DEBUG: User gefunden - ID: {user['id']}, Username: {user['username']}")
        logger.info(f"DEBUG: Password Hash: {user['password_hash'][:20]}...")
        
        # Verifiziere Passwort
        password_valid = verify_password(password, user['password_hash'])
        logger.info(f"DEBUG: Passwort gültig: {password_valid}")
        
        if password_valid:
            # Füge Betriebsinfo hinzu
            user['betrieb_id'] = betrieb_id
            user['betrieb_name'] = betrieb['name']
            user['betrieb_logo'] = betrieb.get('logo_url')
            logger.info(f"DEBUG: Login erfolgreich für {username}")
            return user
        
        logger.error(f"DEBUG: Passwort ungültig für {username}")
        return None
        
    except Exception as e:
        logger.error(f"DEBUG ERROR: {str(e)}")
        import traceback
        logger.error(f"DEBUG TRACEBACK: {traceback.format_exc()}")
        st.error(f"Fehler bei der Authentifizierung: {str(e)}")
        return None


def update_last_login(user_id: str) -> bool:
    """
    Aktualisiert den letzten Login-Zeitstempel
    
    Args:
        user_id: Benutzer-ID
        
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        supabase = get_supabase_client()
        supabase.table('users').update({
            'last_login': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        return True
    except Exception:
        return False


def get_mitarbeiter_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Holt Mitarbeiterdaten anhand der User-ID
    
    Args:
        user_id: Benutzer-ID
        
    Returns:
        Optional[Dict]: Mitarbeiterdaten wenn gefunden
    """
    try:
        supabase = get_supabase_client()
        
        # Versuche mit betrieb_id-Filter
        try:
            from utils.session import get_current_betrieb_id
            betrieb_id = get_current_betrieb_id()
            
            if betrieb_id is not None:
                response = supabase.table('mitarbeiter').select('*').eq('user_id', user_id).eq('betrieb_id', betrieb_id).execute()
            else:
                # Fallback: ohne betrieb_id
                response = supabase.table('mitarbeiter').select('*').eq('user_id', user_id).execute()
        except Exception:
            # Fallback: betrieb_id-Spalte existiert nicht
            response = supabase.table('mitarbeiter').select('*').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Mitarbeiterdaten: {str(e)}")
        return None


def get_all_mitarbeiter(betrieb_id: int = None) -> List[Dict[str, Any]]:
    """
    Holt alle Mitarbeiter (nur für Admin)
    
    Args:
        betrieb_id: Betrieb-ID für Multi-Tenancy (optional, aus Session wenn None)
    
    Returns:
        List[Dict]: Liste aller Mitarbeiter des Betriebs
    """
    try:
        supabase = get_supabase_client()
        
        # Versuche mit betrieb_id-Filter
        try:
            # Hole betrieb_id aus Session wenn nicht übergeben
            if betrieb_id is None:
                from utils.session import get_current_betrieb_id
                betrieb_id = get_current_betrieb_id()
            
            if betrieb_id is not None:
                response = supabase.table('mitarbeiter').select('*').eq('betrieb_id', betrieb_id).order('eintrittsdatum', desc=False).execute()
            else:
                # Fallback: ohne betrieb_id
                response = supabase.table('mitarbeiter').select('*').order('eintrittsdatum', desc=False).execute()
        except Exception:
            # Fallback: betrieb_id-Spalte existiert nicht
            response = supabase.table('mitarbeiter').select('*').order('eintrittsdatum', desc=False).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Mitarbeiter: {str(e)}")
        return []


def create_user(username: str, password: str, role: str) -> Optional[str]:
    """
    Erstellt einen neuen Benutzer
    
    Args:
        username: Benutzername
        password: Passwort (wird gehasht)
        role: Rolle ('admin' oder 'mitarbeiter')
        
    Returns:
        Optional[str]: User-ID wenn erfolgreich, sonst None
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        supabase = get_supabase_client()
        
        logger.info(f"DEBUG: Versuche Benutzer '{username}' anzulegen...")
        
        # Prüfe, ob Benutzername bereits existiert
        existing = supabase.table('users').select('id').eq('username', username).execute()
        if existing.data and len(existing.data) > 0:
            logger.warning(f"DEBUG: Benutzername '{username}' existiert bereits")
            st.error(f"Benutzername '{username}' existiert bereits.")
            return None
        
        # Erstelle Benutzer
        from utils.session import get_current_betrieb_id
        password_hash = hash_password(password)
        
        betrieb_id = get_current_betrieb_id()
        logger.info(f"DEBUG: Betrieb-ID: {betrieb_id}")
        
        user_data = {
            'username': username,
            'password_hash': password_hash,
            'role': role,
            'is_active': True
        }
        
        # Füge betrieb_id hinzu
        if betrieb_id:
            user_data['betrieb_id'] = betrieb_id
        else:
            logger.error("DEBUG: Keine Betrieb-ID gefunden!")
            st.error("Fehler: Keine Betrieb-ID gefunden. Bitte melden Sie sich neu an.")
            return None
        
        logger.info(f"DEBUG: Erstelle User mit Daten: {user_data}")
        response = supabase.table('users').insert(user_data).execute()
        
        if response.data and len(response.data) > 0:
            user_id = response.data[0]['id']
            logger.info(f"DEBUG: User erfolgreich erstellt mit ID: {user_id}")
            return user_id
        else:
            logger.error(f"DEBUG: Keine Daten in Response: {response}")
            return None
        
    except Exception as e:
        logger.error(f"DEBUG ERROR beim Erstellen des Benutzers: {e}", exc_info=True)
        st.error(f"Fehler beim Erstellen des Benutzers: {str(e)}")
        return None


def create_mitarbeiter(user_id: str, mitarbeiter_data: Dict[str, Any]) -> Optional[str]:
    """
    Erstellt einen neuen Mitarbeiter
    
    Args:
        user_id: Benutzer-ID
        mitarbeiter_data: Mitarbeiterdaten
        
    Returns:
        Optional[str]: Mitarbeiter-ID wenn erfolgreich
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from utils.session import get_current_betrieb_id
        supabase = get_supabase_client()
        
        logger.info(f"DEBUG: Erstelle Mitarbeiter für User-ID: {user_id}")
        
        # Füge user_id und betrieb_id hinzu
        mitarbeiter_data['user_id'] = user_id
        betrieb_id = get_current_betrieb_id()
        
        if betrieb_id:
            mitarbeiter_data['betrieb_id'] = betrieb_id
            logger.info(f"DEBUG: Betrieb-ID: {betrieb_id}")
        else:
            logger.error("DEBUG: Keine Betrieb-ID gefunden!")
            st.error("Fehler: Keine Betrieb-ID gefunden.")
            return None
        
        logger.info(f"DEBUG: Mitarbeiter-Daten: {mitarbeiter_data}")
        response = supabase.table('mitarbeiter').insert(mitarbeiter_data).execute()
        
        if response.data and len(response.data) > 0:
            mitarbeiter_id = response.data[0]['id']
            logger.info(f"DEBUG: Mitarbeiter erfolgreich erstellt mit ID: {mitarbeiter_id}")
            return mitarbeiter_id
        else:
            logger.error(f"DEBUG: Keine Daten in Response: {response}")
            return None
        
    except Exception as e:
        logger.error(f"DEBUG ERROR beim Erstellen des Mitarbeiters: {e}", exc_info=True)
        st.error(f"Fehler beim Erstellen des Mitarbeiters: {str(e)}")
        return None


def update_mitarbeiter(mitarbeiter_id: str, mitarbeiter_data: Dict[str, Any]) -> bool:
    """
    Aktualisiert Mitarbeiterdaten
    
    Args:
        mitarbeiter_id: Mitarbeiter-ID
        mitarbeiter_data: Zu aktualisierende Daten
        
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        supabase = get_supabase_client()
        supabase.table('mitarbeiter').update(mitarbeiter_data).eq('id', mitarbeiter_id).execute()
        return True
        
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren des Mitarbeiters: {str(e)}")
        return False


def change_password(user_id: str, new_password: str) -> bool:
    """
    Ändert das Passwort eines Benutzers
    
    Args:
        user_id: Benutzer-ID
        new_password: Neues Passwort
        
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        supabase = get_supabase_client()
        password_hash = hash_password(new_password)
        
        supabase.table('users').update({
            'password_hash': password_hash
        }).eq('id', user_id).execute()
        
        return True
        
    except Exception as e:
        st.error(f"Fehler beim Ändern des Passworts: {str(e)}")
        return False


def upload_file_to_storage(bucket_name: str, file_path: str, file_data: bytes) -> Optional[str]:
    """
    Lädt eine Datei in Supabase Storage hoch
    
    Args:
        bucket_name: Name des Buckets
        file_path: Pfad innerhalb des Buckets
        file_data: Datei-Bytes
        
    Returns:
        Optional[str]: Öffentlicher Pfad wenn erfolgreich
    """
    try:
        supabase = get_supabase_client()
        
        # Lösche existierende Datei falls vorhanden
        try:
            supabase.storage.from_(bucket_name).remove([file_path])
        except:
            pass
        
        # Lade neue Datei hoch
        response = supabase.storage.from_(bucket_name).upload(file_path, file_data)
        
        if response:
            return file_path
        return None
        
    except Exception as e:
        st.error(f"Fehler beim Hochladen der Datei: {str(e)}")
        return None


def download_file_from_storage(bucket_name: str, file_path: str) -> Optional[bytes]:
    """
    Lädt eine Datei aus Supabase Storage herunter
    
    Args:
        bucket_name: Name des Buckets
        file_path: Pfad innerhalb des Buckets
        
    Returns:
        Optional[bytes]: Datei-Bytes wenn erfolgreich
    """
    try:
        supabase = get_supabase_client()
        response = supabase.storage.from_(bucket_name).download(file_path)
        return response
        
    except Exception as e:
        st.error(f"Fehler beim Herunterladen der Datei: {str(e)}")
        return None


def get_public_url(bucket_name: str, file_path: str) -> Optional[str]:
    """
    Generiert eine öffentliche URL für eine Datei (funktioniert nur bei öffentlichen Buckets)
    
    Args:
        bucket_name: Name des Buckets
        file_path: Pfad innerhalb des Buckets
        
    Returns:
        Optional[str]: Öffentliche URL
    """
    try:
        supabase = get_supabase_client()
        response = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return response
        
    except Exception as e:
        return None
