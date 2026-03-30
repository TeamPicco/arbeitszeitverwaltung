import streamlit as st
from supabase import create_client, Client
import os
import requests
from datetime import datetime

def get_supabase_client() -> Client:
    if 'supabase' not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase

def check_and_save_monats_abschluss(mitarbeiter_id, monat, jahr):
    supabase = get_supabase_client()
    # IST-Stunden
    ist_res = supabase.table("zeiterfassung").select("stunden").eq("mitarbeiter_id", mitarbeiter_id).eq("monat", monat).eq("jahr", jahr).execute()
    gesamt_ist = sum(item['stunden'] for item in ist_res.data) if ist_res.data else 0.0
    # SOLL-Stunden
    ma_res = supabase.table("mitarbeiter").select("soll_stunden_monat").eq("id", mitarbeiter_id).single().execute()
    soll = ma_res.data.get('soll_stunden_monat', 160.0)
    
    differenz = round(gesamt_ist - soll, 2)
    supabase.table("azk_historie").upsert({
        "mitarbeiter_id": mitarbeiter_id, "monat": monat, "jahr": jahr,
        "ist_stunden": gesamt_ist, "soll_stunden": soll, "differenz": differenz
    }, on_conflict="mitarbeiter_id, monat, jahr").execute()
    return differenz

def upload_file_to_storage(bucket_name: str, file_path: str, file_data: bytes):
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'x-upsert': 'true'
    }
    upload_url = f"{url}/storage/v1/object/{bucket_name}/{file_path}"
    # FIX: Hier war der SyntaxError aus dem PDF behoben (Klammern korrekt geschlossen)
    response = requests.post(upload_url, headers=headers, data=file_data, timeout=30)
    return response.status_code in [200, 201]
