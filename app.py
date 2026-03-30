import streamlit as st
import os
from datetime import datetime, date
from utils.database import init_supabase_client, verify_credentials_with_betrieb, update_last_login
from pages import admin_dashboard, mitarbeiter_dashboard

# --- 1. PROJEKT-KONFIGURATION ---
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
        # Entferne Zeitzonen-Suffix für einfaches Parsing
        t1 = datetime.strptime(start_iso.split("+")[0], fmt)
        t2 = datetime.strptime(ende_iso.split("+")[0], fmt)
        diff = t2 - t1
        return round(max(0, diff.total_seconds() / 60))
    except Exception:
        return 0

# --- 3. HAUPTLOGIK: LOGIN ODER DASHBOARD ---
if not st.session_state.get('logged_in'):
    st.title("🇮🇹 CrewBase Piccolo")
    
    # Tabs für die Trennung von Stempeluhr und Admin-Bereich
    tab_stempel, tab_login = st.tabs(["🕒 Schnell-Stempeln (PIN)", "🔐 Management Login"])
    
    # --- TAB: STEMPELUHR ---
    with tab_stempel:
        st.subheader("Mitarbeiter-Terminal")
        pin_input = st.text_input("PIN eingeben", type="password", max_chars=4, key="terminal_pin_entry")
        
        if len(pin_input) == 4:
            # Mitarbeiter anhand der PIN suchen
            res = supabase.table("mitarbeiter").select("id, vorname, nachname").eq("pin", pin_input).execute()
            
            if res.data:
                ma = res.data[0]
                ma_id = ma['id']
                st.success(f"Hallo {ma['vorname']}! 👋")
                
                heute_str = date.today().isoformat()
                
                # Prüfen, ob für heute bereits ein Eintrag existiert
                entry_res = supabase.table("zeiterfassung").select("*").eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                exists = len(entry_res.data) > 0
                aktuelle_daten = entry_res.data[0] if exists else {}

                col1, col2 = st.columns(2)
                
                # --- BUTTON: KOMMEN ---
                # Key ist dynamisch mit Mitarbeiter-ID, um DuplicateKeyError zu vermeiden
                if col1.button("🟢 KOMMEN", key=f"btn_kom_{ma_id}", use_container_width=True):
                    jetzt = datetime.now()
                    start_zeit_final = jetzt.strftime("%H:%M:%S")
                    
                    # Dienstplan-Check: Darf der Mitarbeiter schon anfangen?
                    plan_res = supabase.table("dienstplan").select("start_zeit").eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    
                    if plan_res.data:
                        plan_start = plan_res.data[0]['start_zeit']
                        # Wenn echtes Stempeln VOR Plan-Start: Setze Plan-Zeit als Arbeitsbeginn
                        if jetzt.strftime("%H:%M:%S") < plan_start:
                            start_zeit_final = plan_start
                            st.info(f"Hinweis: Früheres Einloggen ignoriert. Startzeit auf {plan_start[:5]} gesetzt.")

                    supabase.table("zeiterfassung").upsert({
                        "mitarbeiter_id": ma_id,
                        "datum": heute_str,
                        "start_zeit": start_zeit_final,
                        "monat": jetzt.month,
                        "jahr": jetzt.year
                    }).execute()
                    st.success(f"Eingestempelt: {start_zeit_final[:5]} Uhr")

                # --- BUTTON: GEHEN ---
                if col2.button("🔴 GEHEN", key=f"btn_geh_{ma_id}", use_container_width=True):
                    supabase.table("zeiterfassung").update({
                        "ende_zeit": datetime.now().strftime("%H:%M:%S")
                    }).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    st.toast("Schönen Feierabend! 🍷")

                st.divider()
                st.write("**Pausen-Management**")
                c3, c4 = st.columns(2)

                # --- BUTTON: PAUSE START ---
                if c3.button("☕ PAUSE START", key=f"btn_p_s_{ma_id}", use_container_width=True):
                    supabase.table("zeiterfassung").update({
                        "pause_start": datetime.now().isoformat()
                    }).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                    st.warning("Pause wurde gestartet.")

                # --- BUTTON: PAUSE ENDE ---
                if c4.button("🔄 PAUSE ENDE", key=f"btn_p_e_{ma_id}", use_container_width=True):
                    if exists and aktuelle_daten.get('pause_start'):
                        p_start = aktuelle_daten['pause_start']
                        p_ende = datetime.now().isoformat()
                        # Berechne Dauer und addiere zu pause_minuten
                        minuten = berechne_pause_minuten(p_start, p_ende)
                        
                        supabase.table("zeiterfassung").update({
                            "pause_ende": p_ende,
                            "pause_minuten": minuten
                        }).eq("mitarbeiter_id", ma_id).eq("datum", heute_str).execute()
                        st.success(f"Pause beendet: {minuten} Min. erfasst.")
                    else:
                        st.error("Keine laufende Pause gefunden.")
            else:
                st.error("❌ PIN ungültig.")

    # --- TAB: ADMIN LOGIN ---
    with tab_login:
        st.subheader("Büro-Anmeldung")
        with st.form("management_login_form"):
            b_nr = st.text_input("Betriebsnummer", value="20262204")
            u_name = st.text_input("Benutzername")
            p_word = st.text_input("Passwort", type="password")
            
            if st.form_submit_button("Anmelden", use_container_width=True):
                user = verify_credentials_with_betrieb(b_nr, u_name, p_word)
                if user:
                    st.session_state.update({
                        "logged_in": True,
                        "user_id": user['id'],
                        "role": user['role'],
                        "vorname": user.get('vorname', u_name),
                        "is_admin": user['role'] == 'admin',
                        "betrieb_id": user.get('betrieb_id')
                    })
                    update_last_login(user['id'])
                    st.rerun()
                else:
                    st.error("❌ Login-Daten nicht korrekt.")

# --- 4. ROUTING NACH ERFOLGREICHEM LOGIN ---
else:
    if st.session_state.get('is_admin'):
        admin_dashboard.show_admin_dashboard()
    else:
        mitarbeiter_dashboard.show_mitarbeiter_dashboard()

    # Logout-Button in der Sidebar
    if st.sidebar.button("Abmelden"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
