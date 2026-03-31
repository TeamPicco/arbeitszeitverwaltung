import streamlit as st
import os
import time
from datetime import datetime, date
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login
from pages import admin_dashboard

# --- 1. KONFIGURATION ---
st.set_page_config(
    page_title="🥩 CrewBase Piccolo - Admin & Terminal",
    page_icon="🥩",
    layout="wide"
)

supabase = init_supabase_client()

# --- 2. RESET-LOGIK (Muss VOR dem Widget stehen) ---
if "trigger_reset" in st.session_state and st.session_state["trigger_reset"]:
    st.session_state["terminal_pin_entry"] = ""
    st.session_state["trigger_reset"] = False

# --- 3. HILFSFUNKTIONEN ---
def berechne_pause_minuten(start_iso):
    """Berechnet Minuten von start_iso bis jetzt"""
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        t1 = datetime.strptime(start_iso.split("+")[0], fmt)
        t2 = datetime.now()
        diff = t2 - t1
        return round(max(0, diff.total_seconds() / 60))
    except:
        return 0

# --- 4. HAUPTLOGIK ---
if not st.session_state.get('logged_in'):
    st.title("🥩 CrewBase Piccolo")
    
    tab_stempel, tab_admin_login = st.tabs(["🕒 Mitarbeiter Stempeluhr", "🔐 Admin Bereich"])
    
    with tab_stempel:
        st.subheader("Schnell-Stempeln per PIN")
        pin_input = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        
        if len(pin_input) == 4:
            res = supabase.table("mitarbeiter").select("id, vorname, nachname").eq("pin", pin_input).execute()
            
            if res.data:
                ma = res.data[0]
                ma_id = ma['id']
                st.info(f"Mitarbeiter: **{ma['vorname']} {ma['nachname']}**")
                
                heute_str = date.today().isoformat()
                
                # Bestehenden Eintrag für heute laden
                entry_res = supabase.table("zeiterfassung").select("*").eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                entry = entry_res.data[0] if entry_res.data else None

                col1, col2 = st.columns(2)
                
                # --- KOMMEN ---
                if col1.button("🟢 KOMMEN", key=f"k_{ma_id}", use_container_width=True):
                    jetzt = datetime.now()
                    start_zeit = jetzt.strftime("%H:%M:%S")
                    # Schichtplan-Check
                    plan = supabase.table("dienstplan").select("start_zeit").eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    if plan.data and jetzt.strftime("%H:%M:%S") < plan.data[0]['start_zeit']:
                        start_zeit = plan.data[0]['start_zeit']
                    
                    supabase.table("zeiterfassung").upsert({
                        "mitarbeiter_id": ma_id, "datum": heute_str,
                        "start_zeit": start_zeit, "monat": jetzt.month, "jahr": jetzt.year
                    }).execute()
                    st.success("Eingestempelt!")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5)
                    st.rerun()

                # --- GEHEN ---
                if col2.button("🔴 GEHEN", key=f"g_{ma_id}", use_container_width=True):
                    supabase.table("zeiterfassung").update({
                        "ende_zeit": datetime.now().strftime("%H:%M:%S")
                    }).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    st.success("Schönen Feierabend!")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1.5)
                    st.rerun()

                st.divider()
                st.write("**Pausen-Kontrolle**")
                c3, c4 = st.columns(2)

                # --- PAUSE START ---
                if c3.button("☕ PAUSE START", key=f"ps_{ma_id}", use_container_width=True):
                    supabase.table("zeiterfassung").update({
                        "pause_start": datetime.now().isoformat()
                    }).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    st.warning("Pause gestartet!")
                    st.session_state["trigger_reset"] = True
                    time.sleep(1)
                    st.rerun()

                # --- PAUSE ENDE ---
                if c4.button("🔄 PAUSE ENDE", key=f"pe_{ma_id}", use_container_width=True):
                    if entry and entry.get('pause_start'):
                        minuten = berechne_pause_minuten(entry['pause_start'])
                        supabase.table("zeiterfassung").update({
                            "pause_ende": datetime.now().isoformat(),
                            "pause_minuten": minuten
                        }).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                        st.success(f"Pause beendet: {minuten} Min. erfasst.")
                        st.session_state["trigger_reset"] = True
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Keine laufende Pause gefunden!")
            else:
                st.error("PIN ungültig.")

    with tab_admin_login:
        with st.form("admin_form"):
            st.subheader("Admin Anmeldung")
            b_nr = st.text_input("Betriebsnummer", value="20262204")
            u_name = st.text_input("Admin Benutzername")
            p_word = st.text_input("Passwort", type="password")
            if st.form_submit_button("Einloggen", use_container_width=True):
                user = verify_credentials_with_betrieb(b_nr, u_name, p_word)
                if user and user['role'] == 'admin':
                    st.session_state.update({"logged_in": True, "is_admin": True, "user_id": user['id']})
                    update_last_login(user['id'])
                    st.rerun()
                else:
                    st.error("Zugriff verweigert.")

else:
    admin_dashboard.show_admin_dashboard()
    if st.sidebar.button("Abmelden / Zum Terminal"):
        st.session_state.clear()
        st.rerun()
