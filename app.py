import streamlit as st
import os
import time
from datetime import datetime, date
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login
from pages import admin_dashboard

st.set_page_config(page_title="🥩 CrewBase Piccolo", page_icon="🥩", layout="wide")
supabase = init_supabase_client()

def reset_to_pin_mask():
    st.session_state["terminal_pin_entry"] = ""
    st.session_state["trigger_reset"] = True
    st.rerun()

if not st.session_state.get('logged_in'):
    st.title("🥩 CrewBase Piccolo")
    tab_stempel, tab_admin = st.tabs(["🕒 Mitarbeiter Stempeluhr", "🔐 Admin Login"])
    
    with tab_stempel:
        if st.session_state.get("trigger_reset"):
            st.session_state["terminal_pin_entry"] = ""
            st.session_state["trigger_reset"] = False
            st.rerun()

        pin_input = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        if len(pin_input) == 4:
            res = supabase.table("mitarbeiter").select("id, vorname, nachname").eq("pin", pin_input).execute()
            if res.data:
                ma = res.data[0]
                st.info(f"Mitarbeiter: **{ma['vorname']} {ma['nachname']}**")
                heute = date.today().isoformat()
                c1, c2 = st.columns(2)
                
                if c1.button("🟢 KOMMEN", key=f"k_{ma['id']}", use_container_width=True):
                    jetzt = datetime.now()
                    start = jetzt.strftime("%H:%M:%S")
                    plan = supabase.table("dienstplan").select("start_zeit").eq("mitarbeiter_id", ma['id']).eq("datum", heute).execute()
                    if plan.data and jetzt.strftime("%H:%M:%S") < plan.data[0]['start_zeit']:
                        start = plan.data[0]['start_zeit']
                    supabase.table("zeiterfassung").upsert({"mitarbeiter_id": ma['id'], "datum": heute, "start_zeit": start, "monat": jetzt.month, "jahr": jetzt.year}).execute()
                    st.success("Eingestempelt!")
                    time.sleep(1.5); reset_to_pin_mask()

                if c2.button("🔴 GEHEN", key=f"g_{ma['id']}", use_container_width=True):
                    supabase.table("zeiterfassung").update({"ende_zeit": datetime.now().strftime("%H:%M:%S")}).eq("mitarbeiter_id", ma['id']).eq("datum", heute).execute()
                    st.success("Feierabend!"); time.sleep(1.5); reset_to_pin_mask()
            else: st.error("PIN falsch.")

    with tab_admin:
        with st.form("admin_login"):
            bnr = st.text_input("Betriebsnummer", value="20262204")
            usr = st.text_input("Admin-User")
            pwd = st.text_input("Passwort", type="password")
            if st.form_submit_button("Einloggen", use_container_width=True):
                user = verify_credentials_with_betrieb(bnr, usr, pwd)
                if user and user['role'] == 'admin':
                    st.session_state.update({"logged_in": True, "is_admin": True, "user_id": user['id']})
                    st.rerun()

else:
    admin_dashboard.show_admin_dashboard()
    if st.sidebar.button("Abmelden"):
        st.session_state.clear(); st.rerun()
