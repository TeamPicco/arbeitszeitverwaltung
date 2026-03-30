"""
Datenbank-Utility-Funktionen für Supabase & Steakhouse Piccolo
Überarbeitete Version inkl. AZK-Abschluss-Logik
"""

import streamlit as st
from supabase import create_client, Client
import bcrypt
import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

# Konfiguriere Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CLIENT INITIALISIERUNG ---

def init_supabase_client() -> Client:
    """Initialisiert den Supabase-Client und speichert ihn im Session State."""
    if 'supabase' not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            st.error("Supabase-Konfiguration fehlt. Bitte .env-Datei prüfen.")
            st.stop()
        
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase

def get_supabase_client() -> Client:
    """Gibt den Supabase-Client aus dem Session State zurück."""
    if 'supabase' not in st.session_state:
        return init_supabase_client()
    return st.session_state.supabase

def get_service_role_client() -> Client:
    """Gibt einen Client mit Service-Role-Key zurück (umgeht RLS für Admin-Uploads)."""
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, service_key)

# --- AUTHENTIFIZIERUNG & PASSWORT ---

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

def verify_credentials_with_betrieb(betriebsnummer: str, username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifiziert Login-Daten inkl. Multi-Tenancy Check."""
    try:
        supabase = get_supabase_client()
        
        # Betrieb prüfen
        betrieb_res = supabase.table('betriebe').select('*').eq('betriebsnummer', betriebsnummer).eq('aktiv', True).execute()
        if not betrieb_res.data:
            return None
        
        betrieb = betrieb_res.data[0]
        
        # User prüfen
        user_res = supabase.table('users').select('*').eq('username', username).eq('betrieb_id', betrieb['id']).eq('is_active', True).execute()
        if not user_res.data:
            return None
        
        user = user_res.data[0]
        if verify_password(password, user['password_hash']):
            user['betrieb_name'] = betrieb['name']
            return user
        return None
    except Exception as e:
        logger.error(f"Login Fehler: {e}")
        return None

def update_last_login(user_id: str):
    try:
        supabase = get_supabase_client()
        supabase.table('users').update({'last_login': datetime.now().isoformat()}).eq('id', user_id).execute()
    except Exception:
        pass

# --- MITARBEITER-VERWALTUNG ---

def get_mitarbeiter_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        supabase = get_supabase_client()
        res = supabase.table('mitarbeiter').select('*').eq('user_id', user_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return None

def get_all_mitarbeiter() -> List[Dict[str, Any]]:
    try:
        supabase = get_supabase_client()
        res = supabase.table('mitarbeiter').select('*').order('nachname').execute()
        return res.data if res.data else []
    except Exception as e:
        st.error(f"Fehler: {e}")
        return []

# --- ARBEITSZEITKONTO (AZK) ABSCHLUSS-LOGIK ---

def check_and_save_monats_abschluss(mitarbeiter_id, monat, jahr):
    """
    Berechnet den Monats-Saldo (Ist vs. Soll) und speichert ihn in azk_historie.
    Ermöglicht das korrekte Erfassen von Minusstunden.
    """
    try:
        supabase = get_supabase_client()

        # 1. Ist-Stunden summieren
        ist_res = supabase.table("zeiterfassung") \
            .select("stunden") \
            .eq("mitarbeiter_id", mitarbeiter_id) \
            .eq("monat", monat) \
            .eq("jahr", jahr) \
            .execute()
        
        gesamt_ist = sum(item['stunden'] for item in ist_res.data) if ist_res.data else 0.0

        # 2. Soll-Stunden holen
        ma_res = supabase.table("mitarbeiter") \
            .select("soll_stunden_monat") \
            .eq("id", mitarbeiter_id) \
            .single().execute()
        
        soll_stunden = ma_res.data.get('soll_stunden_monat', 160.0)

        # 3. Differenz berechnen (Minusstunden entstehen hier!)
        differenz = round(gesamt_ist - soll_stunden, 2)

        # 4. Speichern (Upsert verhindert Duplikate)
        historie_data = {
            "mitarbeiter_id": mitarbeiter_id,
            "monat": monat,
            "jahr": jahr,
            "ist_stunden": gesamt_ist,
            "soll_stunden": soll_stunden,
            "differenz": differenz
        }

        supabase.table("azk_historie").upsert(historie_data, on_conflict="mitarbeiter_id, monat, jahr").execute()
        return differenz
    except Exception as e:
        logger.error(f"Fehler beim Monatsabschluss: {e}")
        return 0.0

# --- STORAGE & DATEI-MANAGEMENT ---

def upload_file_to_storage(bucket_name: str, file_path: str, file_data: bytes) -> Optional[str]:
    """Lädt Dateien sicher über die REST-API hoch (vermeidet RLS-Probleme)."""
    try:
        url = os.getenv("SUPABASE_URL")
        # Nutzt Service Key für volle Berechtigung
        service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        
        headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/pdf',
            'x-upsert': 'true',
        }
        
        upload_url = f"{url}/storage/v1/object/{bucket_name}/{file_path}"
        response = requests.post(upload_url, headers=headers, data=file_data, timeout=
