import streamlit as st
import os
import time
from datetime import datetime, date
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login
from pages import admin_dashboard, mitarbeiter_dashboard

# --- 1. SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="CrewBase Piccolo - Terminal",
    page_icon="⏰",
    layout="centered"
)

# Initialisierung des Datenbank-Clients
supabase = init_supabase_client()

# --- 2. HILFSFUNKTIONEN ---
def berechne_pause_minuten(start_iso, ende_iso):
    """Berechnet die Differenz zwischen zwei Zeitstempeln in Minuten."""
    fmt = "%Y-%m-%dT%H:%M:%S.%f"
    try:
        t1 = datetime.strptime(start_iso.split("+")[0], fmt)
        t2 = datetime.strptime(ende_iso.split("+")[0], fmt)
        diff = t2 - t1
        return round(max(0, diff.total_seconds() / 60))
    except Exception:
        return 0

# --- 3. HAUPTLOGIK ---
if not st.session_state.get('logged_in'):
   (" 🥩Crew Piccolo")
    
    tab_stempel, tab_login = st.tabs(["🕒 Schnell-Stempeln (PIN)", "🔐 Management Login"])
    
    with tab_stempel:
        st.subheader("Mitarbeiter-Terminal")
        
        # FIX: Wir prüfen, ob wir einen Reset brauchen
        if st.session_state.get("trigger_reset"):
            st.session_state["terminal_pin_entry"] = ""
            st.session_state["trigger_reset"] = False
            st.rerun()

        # PIN-Eingabe
        pin_input = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        
        if len(pin_input) == 4:
            res = supabase.table("mitarbeiter").select("id, vorname, nachname").eq("pin", pin_input).execute()
            
            if res.data:
                ma = res.data[0]
                ma_id = ma['id']
                st.info(f"Angemeldet: **{ma['vorname']} {ma['nachname']}**")
                
                heute_str = date.today().isoformat()
                
                # Daten für heute laden
                entry_res = supabase.table("zeiterfassung").select("*").eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                aktuelle_daten = entry_res.data[0] if entry_res.data else {}

                col1, col2 = st.columns(2)
                
                # --- KOMMEN ---
                if col1.button("🟢 KOMMEN", key=f"btn_kom_{ma_id}", use_container_width=True):
                    jetzt = datetime.now()
                    start_zeit_final = jetzt.strftime("%H:%M:%S")
                    
                    # Dienstplan-Check
                    plan_res = supabase.table("dienstplan").select("start_zeit").eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    if plan_res.data:
                        plan_start = plan_res.data[0]['start_zeit']
                        if jetzt.strftime("%H:%M:%S") < plan_start:
                            start_zeit_final = plan_start
                            st.warning(f"Zu früh! Startzeit auf Plan ({plan_start[:5]}) gesetzt.")

                    supabase.table("zeiterfassung").upsert({
                        "mitarbeiter_id": ma_id, "datum": heute_str,
                        "start_zeit": start_zeit_final, "monat": jetzt.month, "jahr": jetzt.year
                    }).execute()
                    st.success("✅ Erfasst! System setzt zurück...")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5)
                    st.rerun()

                # --- GEHEN ---
                if col2.button("🔴 GEHEN", key=f"btn_geh_{ma_id}", use_container_width=True):
                    supabase.table("zeiterfassung").update({
                        "ende_zeit": datetime.now().strftime("%H:%M:%S")
                    }).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    st.success("👋 Feierabend! System setzt zurück...")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5)
                    st.rerun()

                st.divider()
                c3, c4 = st.columns(2)

                # --- PAUSE START ---
                if c3.button("☕ PAUSE START", key=f"btn_ps_{ma_id}", use_container_width=True):
                    supabase.table("zeiterfassung").update({"pause_start": datetime.now().isoformat()}).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    st.session_state["trigger_reset"] = True
                    st.rerun()

                # --- PAUSE ENDE ---
                if c4.button("🔄 PAUSE ENDE", key=f"btn_pe_{ma_id}", use_container_width=True):
                    if aktuelle_daten.get('pause_start'):
                        minuten = berechne_pause_minuten(aktuelle_daten['pause_start'], datetime.now().isoformat())
                        supabase.table("zeiterfassung").update({"pause_ende": datetime.now().isoformat(), "pause_minuten": minuten}).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                        st.success(f"✅ Pause beendet ({minuten} Min.)")
                        st.session_state["trigger_reset"] = True
                        time.sleep(1.5)
                        st.rerun()
            else:
                st.error("❌ PIN ungültig.")

    with tab_login:
        st.subheader("Büro-Anmeldung")
        with st.form("admin_login_form"):
            b_nr = st.text_input("Betriebsnummer", value="20262204")
            u_name = st.text_input("Benutzername")
            p_word = st.text_input("Passwort", type="password")
            if st.form_submit_button("Anmelden", use_container_width=True):
                user = verify_credentials_with_betrieb(b_nr, u_name, p_word)
                if user:
                    st.session_state.update({
                        "logged_in": True, "user_id": user['id'], "role": user['role'],
                        "vorname": user.get('vorname', u_name), "is_admin": user['role'] == 'admin'
                    })
                    update_last_login(user['id'])
                    st.rerun()
                else:
                    st.error("❌ Login fehlgeschlagen.")

else:
    if st.session_state.is_admin:
        admin_dashboard.show_admin_dashboard()
    else:
        mitarbeiter_dashboard.show_mitarbeiter_dashboard()
