import streamlit as st
from supabase import create_client, Client
import bcrypt
import os

def init_supabase_client() -> Client:
    """Wird von app.py aufgerufen"""
    if 'supabase' not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase

def get_supabase_client() -> Client:
    return init_supabase_client()

def verify_credentials(username, password):
    """Wird von app.py aufgerufen"""
    supabase = get_supabase_client()
    try:
        res = supabase.table('users').select('*').eq('username', username).eq('is_active', True).execute()
        if res.data:
            user = res.data[0]
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return user
    except Exception as e:
        st.error(f"Datenbankfehler: {e}")
    return None

def check_and_save_monats_abschluss(mitarbeiter_id, monat, jahr):
    """Speichert den Saldo fest in der Historie-Tabelle"""
    supabase = get_supabase_client()
    # Ist-Stunden des Monats
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
