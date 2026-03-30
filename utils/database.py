import streamlit as st
from supabase import create_client, Client
import bcrypt
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any

def init_supabase_client() -> Client:
    """Initialisiert den Supabase-Client für die gesamte App."""
    if 'supabase' not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase

def get_supabase_client() -> Client:
    return init_supabase_client()

def verify_credentials_with_betrieb(betriebsnummer: str, username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifiziert die Anmeldung inkl. Betriebsnummer (Mandantenfähigkeit)."""
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
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                user['betrieb_name'] = betrieb['name']
                user['betrieb_id'] = betrieb['id']
                return user
        return None
    except Exception as e:
        st.error(f"Login-Fehler: {e}")
        return None

def check_and_save_monats_abschluss(mitarbeiter_id, monat, jahr):
    """Speichert den Saldo (Ist-Soll) fest in der Datenbank."""
    supabase = get_supabase_client()
    res = supabase.table("zeiterfassung").select("stunden").eq("mitarbeiter_id", mitarbeiter_id).eq("monat", monat).eq("jahr", jahr).execute()
    ist = sum(r['stunden'] for r in res.data) if res.data else 0.0
    ma = supabase.table("mitarbeiter").select("soll_stunden_monat").eq("id", mitarbeiter_id).single().execute()
    soll = ma.data.get('soll_stunden_monat', 160.0)
    diff = round(ist - soll, 2)
    supabase.table("azk_historie").upsert({
        "mitarbeiter_id": mitarbeiter_id, "monat": monat, "jahr": jahr,
        "ist_stunden": ist, "soll_stunden": soll, "differenz": diff
    }, on_conflict="mitarbeiter_id, monat, jahr").execute()
    return diff
