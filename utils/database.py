import streamlit as st
from supabase import create_client, Client
import bcrypt
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any

def init_supabase_client() -> Client:
    """Initialisiert den Client für die app.py"""
    if 'supabase' not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase

def get_supabase_client() -> Client:
    return init_supabase_client()

def verify_credentials(username, password):
    """Prüft Login für die app.py"""
    supabase = get_supabase_client()
    res = supabase.table('users').select('*').eq('username', username).eq('is_active', True).execute()
    if res.data and bcrypt.checkpw(password.encode('utf-8'), res.data[0]['password_hash'].encode('utf-8')):
        return res.data[0]
    return None

def check_and_save_monats_abschluss(mitarbeiter_id, monat, jahr):
    supabase = get_supabase_client()
    ist_res = supabase.table("zeiterfassung").select("stunden").eq("mitarbeiter_id", mitarbeiter_id).eq("monat", monat).eq("jahr", jahr).execute()
    gesamt_ist = sum(item['stunden'] for item in ist_res.data) if ist_res.data else 0.0
    ma_res = supabase.table("mitarbeiter").select("soll_stunden_monat").eq("id", mitarbeiter_id).single().execute()
    soll = ma_res.data.get('soll_stunden_monat', 160.0)
    differenz = round(gesamt_ist - soll, 2)
    supabase.table("azk_historie").upsert({
        "mitarbeiter_id": mitarbeiter_id, "monat": monat, "jahr": jahr,
        "ist_stunden": gesamt_ist, "soll_stunden": soll, "differenz": differenz
    }, on_conflict="mitarbeiter_id, monat, jahr").execute()
    return differenz
