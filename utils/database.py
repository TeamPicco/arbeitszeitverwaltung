"""
Datenbank-Utility-Funktionen für Supabase
"""

import streamlit as st
from supabase import create_client, Client
import bcrypt
import os
from datetime import datetime
from typing import Optional, Dict, Any, List


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
        response = supabase.table('mitarbeiter').select('*').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Mitarbeiterdaten: {str(e)}")
        return None


def get_all_mitarbeiter() -> List[Dict[str, Any]]:
    """
    Holt alle Mitarbeiter (nur für Admin)
    
    Returns:
        List[Dict]: Liste aller Mitarbeiter
    """
    try:
        supabase = get_supabase_client()
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
    try:
        supabase = get_supabase_client()
        
        # Prüfe, ob Benutzername bereits existiert
        existing = supabase.table('users').select('id').eq('username', username).execute()
        if existing.data and len(existing.data) > 0:
            st.error(f"Benutzername '{username}' existiert bereits.")
            return None
        
        # Erstelle Benutzer
        password_hash = hash_password(password)
        response = supabase.table('users').insert({
            'username': username,
            'password_hash': password_hash,
            'role': role,
            'is_active': True
        }).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
        return None
        
    except Exception as e:
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
    try:
        supabase = get_supabase_client()
        
        # Füge user_id hinzu
        mitarbeiter_data['user_id'] = user_id
        
        response = supabase.table('mitarbeiter').insert(mitarbeiter_data).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
        return None
        
    except Exception as e:
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
