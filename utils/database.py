import streamlit as st
from supabase import create_client, Client
import bcrypt
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any

def init_supabase_client() -> Client:
    """Initialisiert den Supabase-Client."""
    if 'supabase' not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            st.error("Supabase-Konfiguration fehlt!")
            st.stop()
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase

def get_supabase_client() -> Client:
    return init_supabase_client()

def verify_credentials_with_betrieb(betriebsnummer: str, username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifiziert die Anmeldung inkl. Betriebsnummer."""
    try:
        supabase = get_supabase_client()
        # 1. Betrieb prüfen
        b_res = supabase.table('betriebe').select('*').eq('betriebsnummer', betriebsnummer).eq('aktiv', True).execute()
        if not b_res.data:
            return None
        betrieb = b_res.data[0]

        # 2. User für diesen Betrieb prüfen
        u_res = supabase.table('users').select('*').eq('username', username).eq('betrieb_id', betrieb['id']).eq('is_active', True).execute()
        if u_res.data:
            user = u_res.data[0]
            # Passwort prüfen
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                user['betrieb_name'] = betrieb['name']
                user['betrieb_id'] = betrieb['id']
                return user
        return None
    except Exception as e:
        st.error(f"Datenbankfehler: {e}")
        return None

def update_last_login(user_id: str):
    """Aktualisiert den Zeitstempel des letzten Logins."""
    try:
        supabase = get_supabase_client()
        supabase.table('users').update({
            'last_login': datetime.now().isoformat()
        }).eq('id', user_id).execute()
    except Exception:
        pass

def upload_file_to_storage(bucket_name: str, file_path: str, file_data: bytes):
    """Sicherer Upload via REST API (verhindert Syntaxfehler bei Storage-Methoden)."""
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'x-upsert': 'true'
    }
    upload_url = f"{url}/storage/v1/object/{bucket_name}/{file_path}"
    response = requests.post(upload_url, headers=headers, data=file_data, timeout=30)
    return response.status_code in [200, 201]        return None            user = u_res.data[0]
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                user['betrieb_name'] = betrieb['name']
                user['betrieb_id'] = betrieb['id']
                return user
        return None
    except Exception as e:
        st.error(f"Login-Fehler: {e}")
        return None

def update_last_login(user_id: str):
    """Aktualisiert den Zeitstempel des letzten Logins (Wird von app.py gesucht)"""
    try:
        supabase = get_supabase_client()
        supabase.table('users').update({
            'last_login': datetime.now().isoformat()
        }).eq('id', user_id).execute()
    except Exception:
        pass

def check_and_save_monats_abschluss(mitarbeiter_id, monat, jahr):
    """Speichert den Saldo fest in der azk_historie Tabelle"""
    supabase = get_supabase_client()
    # Ist-Stunden
    res = supabase.table("zeiterfassung").select("stunden").eq("mitarbeiter_id", mitarbeiter_id).eq("monat", monat).eq("jahr", jahr).execute()
    ist = sum(r['stunden'] for r in res.data) if res.data else 0.0
    # Soll-Stunden
    ma = supabase.table("mitarbeiter").select("soll_stunden_monat").eq("id", mitarbeiter_id).single().execute()
    soll = ma.data.get('soll_stunden_monat', 160.0)
    
    diff = round(ist - soll, 2)
    supabase.table("azk_historie").upsert({
        "mitarbeiter_id": mitarbeiter_id, "monat": monat, "jahr": jahr,
        "ist_stunden": ist, "soll_stunden": soll, "differenz": diff
    }, on_conflict="mitarbeiter_id, monat, jahr").execute()
    return diff

def upload_file_to_storage(bucket_name: str, file_path: str, file_data: bytes):
    """Sicherer Upload via REST API"""
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'x-upsert': 'true'
    }
    upload_url = f"{url}/storage/v1/object/{bucket_name}/{file_path}"
    response = requests.post(upload_url, headers=headers, data=file_data, timeout=30)
    return response.status_code in [200, 201]
