import streamlit as st
import os
import time
from datetime import datetime, date
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login
from pages import admin_dashboard

st.set_page_config(page_title="🥩 CrewBase Piccolo", page_icon="🥩", layout="wide")
supabase = init_supabase_client()

# --- RESET LOGIK ---
if st.session_state.get("trigger_reset"):
    st.session_state["terminal_pin_entry"] = ""
    st.session_state["trigger_reset"] = False

# --- HAUPTLOGIK ---
if not st.session_state.get('logged_in'):
    st.title("🥩 CrewBase Piccolo")
    tab_stempel, tab_admin = st.tabs(["🕒 Mitarbeiter Stempeluhr", "🔐 Admin Login"])
    
    with tab_stempel:
        pin = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        if len(pin) == 4:
            res = supabase.table("mitarbeiter").select("*").eq("pin", pin).execute()
            if res.data:
                ma = res.data[0]
                heute = date.today().isoformat()
                st.info(f"Hallo {ma['vorname']}! Schicht: {heute}")
                
                c1, c2 = st.columns(2)
                if c1.button("🟢 KOMMEN", key=f"k_{ma['id']}", use_container_width=True):
                    plan = supabase.table("dienstplan").select("start_zeit").eq("mitarbeiter_id", ma['id']).eq("datum", heute).execute()
                    start = plan.data[0]['start_zeit'] if plan.data else datetime.now().strftime("%H:%M:%S")
                    supabase.table("zeiterfassung").upsert({"mitarbeiter_id": ma['id'], "datum": heute, "start_zeit": start, "monat": date.today().month, "jahr": date.today().year}).execute()
                    st.success(f"Eingestempelt (Plan: {start[:5]})")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5); st.rerun()

                if c2.button("🔴 GEHEN", key=f"g_{ma['id']}", use_container_width=True):
                    supabase.table("zeiterfassung").update({"ende_zeit": datetime.now().strftime("%H:%M:%S")}).eq("mitarbeiter_id", ma['id']).eq("datum", heute).execute()
                    st.success("Schönen Feierabend!"); st.session_state["trigger_reset"] = True
                    time.sleep(1.5); st.rerun()
            else: st.error("PIN unbekannt.")

    with tab_admin:
        with st.form("login"):
            bnr = st.text_input("Betriebsnummer", value="20262204")
            usr = st.text_input("Admin")
            pwd = st.text_input("Passwort", type="password")
            if st.form_submit_button("Login"):
                user = verify_credentials_with_betrieb(bnr, usr, pwd)
                if user and user['role'] == 'admin':
                    st.session_state.update({"logged_in": True, "is_admin": True})
                    st.rerun()
else:
    admin_dashboard.show_admin_dashboard()
    if st.sidebar.button("Abmelden"):
        st.session_state.clear(); st.rerun()
