"""
Kiosk-Modus Stempeluhr
======================
Dauerhaft eingeloggter Kiosk-Modus für Mitarbeiter-Zeiterfassung.
Authentifizierung per 4-stelligem PIN.
Keine sensiblen Daten (Lohn, Stunden-Summen) sichtbar.
"""

import streamlit as st
from supabase import create_client
import os
from datetime import datetime, timezone
import time
import json

# ─── Supabase-Verbindung ────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jehomjeanbmkoptknutx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImplaG9tamVhbmJta29wdGtudXR4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDkxMzYwOSwiZXhwIjoyMDg2NDg5NjA5fQ.-gssE1hce_BldpSTry-ehFMXZQzmIQDpWFWTXPy61t8")

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── CSS-Styling ─────────────────────────────────────────────────────────────
KIOSK_CSS = """
<style>
/* Kiosk-Vollbild-Layout */
.kiosk-header {
    text-align: center;
    padding: 20px 0 10px 0;
    border-bottom: 2px solid #e0e0e0;
    margin-bottom: 20px;
}
.kiosk-uhr {
    font-size: 3.5rem;
    font-weight: 700;
    color: #1a1a2e;
    text-align: center;
    letter-spacing: 3px;
    margin: 10px 0;
}
.kiosk-datum {
    font-size: 1.3rem;
    color: #555;
    text-align: center;
    margin-bottom: 20px;
}
.pin-display {
    font-size: 2.5rem;
    letter-spacing: 12px;
    text-align: center;
    background: #f0f4ff;
    border: 2px solid #4a90d9;
    border-radius: 12px;
    padding: 15px 30px;
    margin: 15px auto;
    max-width: 300px;
    min-height: 75px;
    color: #1a1a2e;
    font-family: monospace;
}
.pin-hint {
    text-align: center;
    color: #888;
    font-size: 1rem;
    margin-bottom: 15px;
}
/* PIN-Tasten */
.stButton > button {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    height: 70px !important;
    border-radius: 10px !important;
    border: 2px solid #ddd !important;
    background: white !important;
    color: #1a1a2e !important;
    width: 100% !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #e8f0fe !important;
    border-color: #4a90d9 !important;
    transform: scale(1.03) !important;
}
.stButton > button:active {
    transform: scale(0.97) !important;
}
/* Kommen/Gehen Buttons */
.btn-kommen > button {
    background: #2e7d32 !important;
    color: white !important;
    font-size: 1.8rem !important;
    height: 120px !important;
    border-radius: 16px !important;
    border: none !important;
}
.btn-kommen > button:hover {
    background: #1b5e20 !important;
}
.btn-gehen > button {
    background: #c62828 !important;
    color: white !important;
    font-size: 1.8rem !important;
    height: 120px !important;
    border-radius: 16px !important;
    border: none !important;
}
.btn-gehen > button:hover {
    background: #b71c1c !important;
}
.btn-loeschen > button {
    background: #ff6f00 !important;
    color: white !important;
    font-size: 1.4rem !important;
    height: 70px !important;
    border-radius: 10px !important;
    border: none !important;
}
.btn-loeschen > button:hover {
    background: #e65100 !important;
}
.btn-reset > button {
    background: #546e7a !important;
    color: white !important;
    font-size: 1.4rem !important;
    height: 70px !important;
    border-radius: 10px !important;
    border: none !important;
}
/* Erfolgs-/Fehlermeldungen */
.success-box {
    background: #e8f5e9;
    border: 2px solid #2e7d32;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    font-size: 1.4rem;
    color: #1b5e20;
    margin: 20px 0;
}
.error-box {
    background: #ffebee;
    border: 2px solid #c62828;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    font-size: 1.4rem;
    color: #b71c1c;
    margin: 20px 0;
}
.mitarbeiter-name {
    font-size: 2rem;
    font-weight: 700;
    text-align: center;
    color: #1a1a2e;
    margin: 10px 0;
}
.offline-badge {
    background: #ff6f00;
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}
.online-badge {
    background: #2e7d32;
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}
</style>
"""

# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def get_jetzt_berlin():
    """Aktuelle Zeit in Europe/Berlin."""
    from datetime import timezone, timedelta
    # Einfache Näherung: UTC+1 (Winter) / UTC+2 (Sommer)
    # Für Produktion: pytz oder zoneinfo verwenden
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        return datetime.now(tz)
    except Exception:
        # Fallback: UTC+1
        return datetime.now(timezone(timedelta(hours=1)))


def format_uhrzeit(dt):
    return dt.strftime("%H:%M:%S")


def format_datum(dt):
    WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return f"{WOCHENTAGE[dt.weekday()]}, {dt.day}. {MONATE[dt.month - 1]} {dt.year}"


def mitarbeiter_per_pin(betrieb_id: int, pin: str):
    """Mitarbeiter anhand PIN suchen."""
    try:
        supabase = get_supabase()
        result = supabase.table("mitarbeiter").select(
            "id, vorname, nachname, stempel_pin"
        ).eq("betrieb_id", betrieb_id).eq("stempel_pin", pin).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        st.session_state["kiosk_offline"] = True
    return None


def letzter_eintrag(betrieb_id: int, mitarbeiter_id: int):
    """Letzten Zeiterfassungs-Eintrag des Mitarbeiters heute abrufen."""
    try:
        supabase = get_supabase()
        heute = get_jetzt_berlin().date().isoformat()
        # zeiterfassung hat datum + start_zeit/ende_zeit Schema
        result = supabase.table("zeiterfassung").select(
            "id, datum, start_zeit, ende_zeit"
        ).eq("betrieb_id", betrieb_id).eq("mitarbeiter_id", mitarbeiter_id).eq(
            "datum", heute
        ).order("created_at", desc=True).limit(1).execute()
        if result.data:
            return result.data[0]
    except Exception:
        pass
    return None


def stempel_buchen(betrieb_id: int, mitarbeiter_id: int, typ: str, geraet_id: str = None):
    """
    Kommen/Gehen in zeiterfassung buchen.
    
    Das bestehende Schema nutzt:
    - datum (DATE)
    - start_zeit (TIME) für 'kommen'
    - ende_zeit (TIME) für 'gehen'
    
    Logik:
    - 'kommen': Neuen Eintrag mit start_zeit anlegen
    - 'gehen': Letzten offenen Eintrag (ohne ende_zeit) aktualisieren
    """
    jetzt = get_jetzt_berlin()
    heute = jetzt.date().isoformat()
    uhrzeit = jetzt.strftime("%H:%M:%S")

    try:
        supabase = get_supabase()
        
        if typ == "kommen":
            # Neuen Eintrag anlegen
            eintrag = {
                "betrieb_id": betrieb_id,
                "mitarbeiter_id": mitarbeiter_id,
                "datum": heute,
                "start_zeit": uhrzeit,
            }
            supabase.table("zeiterfassung").insert(eintrag).execute()
        else:  # gehen
            # Letzten offenen Eintrag (start_zeit gesetzt, ende_zeit NULL) aktualisieren
            offene = supabase.table("zeiterfassung").select("id").eq(
                "betrieb_id", betrieb_id
            ).eq("mitarbeiter_id", mitarbeiter_id).eq(
                "datum", heute
            ).is_("ende_zeit", "null").order("created_at", desc=True).limit(1).execute()
            
            if offene.data:
                eintrag_id = offene.data[0]["id"]
                supabase.table("zeiterfassung").update({
                    "ende_zeit": uhrzeit
                }).eq("id", eintrag_id).execute()
            else:
                # Kein offener Eintrag - trotzdem Eintrag mit ende_zeit anlegen
                eintrag = {
                    "betrieb_id": betrieb_id,
                    "mitarbeiter_id": mitarbeiter_id,
                    "datum": heute,
                    "ende_zeit": uhrzeit,
                }
                supabase.table("zeiterfassung").insert(eintrag).execute()
        
        st.session_state["kiosk_offline"] = False
        return True, jetzt
    except Exception as e:
        # Offline-Puffer in Session State
        _offline_puffer_hinzufuegen(betrieb_id, mitarbeiter_id, typ, jetzt.isoformat(), geraet_id)
        return False, jetzt


def _offline_puffer_hinzufuegen(betrieb_id, mitarbeiter_id, typ, zeitstempel, geraet_id):
    """Eintrag in lokalen Offline-Puffer schreiben."""
    if "offline_puffer" not in st.session_state:
        st.session_state["offline_puffer"] = []
    st.session_state["offline_puffer"].append({
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "typ": typ,
        "zeitstempel": zeitstempel,
        "geraet_id": geraet_id,
    })
    st.session_state["kiosk_offline"] = True


def offline_puffer_synchronisieren(betrieb_id: int):
    """Offline-gepufferte Einträge mit Supabase synchronisieren."""
    puffer = st.session_state.get("offline_puffer", [])
    if not puffer:
        return 0

    supabase = get_supabase()
    synchronisiert = 0
    verbleibend = []

    for eintrag in puffer:
        if eintrag.get("betrieb_id") != betrieb_id:
            verbleibend.append(eintrag)
            continue
        try:
            from datetime import datetime as dt
            ts = dt.fromisoformat(eintrag["zeitstempel"])
            heute = ts.date().isoformat()
            uhrzeit = ts.strftime("%H:%M:%S")
            typ = eintrag["typ"]
            
            if typ == "kommen":
                db_eintrag = {
                    "betrieb_id": eintrag["betrieb_id"],
                    "mitarbeiter_id": eintrag["mitarbeiter_id"],
                    "datum": heute,
                    "start_zeit": uhrzeit,
                }
                supabase.table("zeiterfassung").insert(db_eintrag).execute()
            else:
                offene = supabase.table("zeiterfassung").select("id").eq(
                    "betrieb_id", eintrag["betrieb_id"]
                ).eq("mitarbeiter_id", eintrag["mitarbeiter_id"]).eq(
                    "datum", heute
                ).is_("ende_zeit", "null").order("created_at", desc=True).limit(1).execute()
                if offene.data:
                    supabase.table("zeiterfassung").update({"ende_zeit": uhrzeit}).eq("id", offene.data[0]["id"]).execute()
                else:
                    db_eintrag = {
                        "betrieb_id": eintrag["betrieb_id"],
                        "mitarbeiter_id": eintrag["mitarbeiter_id"],
                        "datum": heute,
                        "ende_zeit": uhrzeit,
                    }
                    supabase.table("zeiterfassung").insert(db_eintrag).execute()
            synchronisiert += 1
        except Exception:
            verbleibend.append(eintrag)

    st.session_state["offline_puffer"] = verbleibend
    if not verbleibend:
        st.session_state["kiosk_offline"] = False
    return synchronisiert


# ─── Haupt-Kiosk-Funktion ────────────────────────────────────────────────────

def zeige_kiosk(betrieb_id: int, geraet_name: str = "Kiosk"):
    """Haupt-Einstiegspunkt für den Kiosk-Modus."""
    st.markdown(KIOSK_CSS, unsafe_allow_html=True)

    # Session-State initialisieren
    if "kiosk_pin" not in st.session_state:
        st.session_state["kiosk_pin"] = ""
    if "kiosk_phase" not in st.session_state:
        st.session_state["kiosk_phase"] = "pin_eingabe"  # pin_eingabe | aktion | bestaetigung
    if "kiosk_mitarbeiter" not in st.session_state:
        st.session_state["kiosk_mitarbeiter"] = None
    if "kiosk_offline" not in st.session_state:
        st.session_state["kiosk_offline"] = False
    if "kiosk_buchung_typ" not in st.session_state:
        st.session_state["kiosk_buchung_typ"] = None
    if "kiosk_buchung_zeit" not in st.session_state:
        st.session_state["kiosk_buchung_zeit"] = None
    if "offline_puffer" not in st.session_state:
        st.session_state["offline_puffer"] = []

    # Offline-Puffer synchronisieren (im Hintergrund versuchen)
    if st.session_state.get("offline_puffer"):
        try:
            synced = offline_puffer_synchronisieren(betrieb_id)
            if synced > 0:
                st.toast(f"✅ {synced} Offline-Einträge synchronisiert", icon="✅")
        except Exception:
            pass

    # ── Kopfzeile ──
    jetzt = get_jetzt_berlin()
    offline = st.session_state.get("kiosk_offline", False)
    puffer_anzahl = len(st.session_state.get("offline_puffer", []))

    col_logo, col_status = st.columns([3, 1])
    with col_logo:
        st.markdown(f"""
        <div class="kiosk-header">
            <div style="font-size:1.1rem; color:#888; font-weight:600; letter-spacing:2px;">STEMPELUHR</div>
            <div style="font-size:1.5rem; font-weight:700; color:#1a1a2e;">{geraet_name}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_status:
        if offline:
            st.markdown(f'<div style="text-align:right; padding-top:20px;"><span class="offline-badge">⚡ OFFLINE ({puffer_anzahl})</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:right; padding-top:20px;"><span class="online-badge">● ONLINE</span></div>', unsafe_allow_html=True)

    # Uhr und Datum
    st.markdown(f'<div class="kiosk-uhr">{format_uhrzeit(jetzt)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kiosk-datum">{format_datum(jetzt)}</div>', unsafe_allow_html=True)

    # ── Phase-Routing ──
    phase = st.session_state["kiosk_phase"]

    if phase == "pin_eingabe":
        _zeige_pin_eingabe(betrieb_id, geraet_name)
    elif phase == "aktion":
        _zeige_aktion(betrieb_id, geraet_name)
    elif phase == "bestaetigung":
        _zeige_bestaetigung(betrieb_id)


def _zeige_pin_eingabe(betrieb_id: int, geraet_name: str):
    """PIN-Eingabe-Bildschirm mit Numpad."""
    pin = st.session_state["kiosk_pin"]

    # PIN-Anzeige (Punkte)
    punkte = "●" * len(pin) + "○" * (4 - len(pin))
    st.markdown(f'<div class="pin-display">{punkte}</div>', unsafe_allow_html=True)
    st.markdown('<div class="pin-hint">Bitte 4-stelligen PIN eingeben</div>', unsafe_allow_html=True)

    # Fehlermeldung
    if st.session_state.get("kiosk_fehler"):
        st.markdown(f'<div class="error-box">❌ {st.session_state["kiosk_fehler"]}</div>', unsafe_allow_html=True)
        st.session_state["kiosk_fehler"] = None

    # Numpad 1-9
    st.markdown("<br>", unsafe_allow_html=True)
    for zeile in [[1, 2, 3], [4, 5, 6], [7, 8, 9]]:
        cols = st.columns(3)
        for i, zahl in enumerate(zeile):
            with cols[i]:
                if st.button(str(zahl), key=f"pin_{zahl}", use_container_width=True):
                    if len(st.session_state["kiosk_pin"]) < 4:
                        st.session_state["kiosk_pin"] += str(zahl)
                        if len(st.session_state["kiosk_pin"]) == 4:
                            _pin_pruefen(betrieb_id)
                        st.rerun()

    # Letzte Zeile: Löschen | 0 | Bestätigen
    col_del, col_0, col_ok = st.columns(3)
    with col_del:
        st.markdown('<div class="btn-loeschen">', unsafe_allow_html=True)
        if st.button("⌫", key="pin_del", use_container_width=True):
            st.session_state["kiosk_pin"] = st.session_state["kiosk_pin"][:-1]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col_0:
        if st.button("0", key="pin_0", use_container_width=True):
            if len(st.session_state["kiosk_pin"]) < 4:
                st.session_state["kiosk_pin"] += "0"
                if len(st.session_state["kiosk_pin"]) == 4:
                    _pin_pruefen(betrieb_id)
                st.rerun()
    with col_ok:
        st.markdown('<div class="btn-reset">', unsafe_allow_html=True)
        if st.button("✕ Reset", key="pin_reset", use_container_width=True):
            st.session_state["kiosk_pin"] = ""
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def _pin_pruefen(betrieb_id: int):
    """PIN gegen Datenbank prüfen und ggf. zur Aktion-Phase wechseln."""
    pin = st.session_state["kiosk_pin"]
    mitarbeiter = mitarbeiter_per_pin(betrieb_id, pin)
    if mitarbeiter:
        st.session_state["kiosk_mitarbeiter"] = mitarbeiter
        st.session_state["kiosk_phase"] = "aktion"
        st.session_state["kiosk_pin"] = ""
    else:
        st.session_state["kiosk_fehler"] = "Unbekannter PIN. Bitte erneut versuchen."
        st.session_state["kiosk_pin"] = ""


def _zeige_aktion(betrieb_id: int, geraet_name: str):
    """Kommen/Gehen-Auswahl nach erfolgreicher PIN-Eingabe."""
    ma = st.session_state["kiosk_mitarbeiter"]
    if not ma:
        st.session_state["kiosk_phase"] = "pin_eingabe"
        st.rerun()
        return

    name = f"{ma['vorname']} {ma['nachname']}"
    st.markdown(f'<div class="mitarbeiter-name">👤 {name}</div>', unsafe_allow_html=True)

    # Letzten Eintrag anzeigen (nur Typ + Uhrzeit, kein Lohn)
    letzter = letzter_eintrag(betrieb_id, ma["id"])
    if letzter:
        try:
            start = letzter.get("start_zeit")
            ende = letzter.get("ende_zeit")
            if ende:
                letzter_typ = "Gehen"
                letzter_uhr = str(ende)[:5]
            elif start:
                letzter_typ = "Kommen"
                letzter_uhr = str(start)[:5]
            else:
                letzter_typ = None
            if letzter_typ:
                st.markdown(f'<div style="text-align:center; color:#888; margin-bottom:20px;">Letzter Eintrag heute: <b>{letzter_typ}</b> um <b>{letzter_uhr} Uhr</b></div>', unsafe_allow_html=True)
        except Exception:
            pass

    st.markdown("<br>", unsafe_allow_html=True)

    col_k, col_g = st.columns(2)
    with col_k:
        st.markdown('<div class="btn-kommen">', unsafe_allow_html=True)
        if st.button("✅ KOMMEN", key="btn_kommen", use_container_width=True):
            _buchung_ausfuehren(betrieb_id, ma, "kommen", geraet_name)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_g:
        st.markdown('<div class="btn-gehen">', unsafe_allow_html=True)
        if st.button("🚪 GEHEN", key="btn_gehen", use_container_width=True):
            _buchung_ausfuehren(betrieb_id, ma, "gehen", geraet_name)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_abbruch, _ = st.columns([1, 2])
    with col_abbruch:
        if st.button("← Zurück", key="btn_zurueck"):
            st.session_state["kiosk_phase"] = "pin_eingabe"
            st.session_state["kiosk_mitarbeiter"] = None
            st.rerun()


def _buchung_ausfuehren(betrieb_id: int, ma: dict, typ: str, geraet_name: str):
    """Buchung durchführen und zur Bestätigungs-Phase wechseln."""
    erfolg, buchungszeit = stempel_buchen(betrieb_id, ma["id"], typ, geraet_name)
    st.session_state["kiosk_buchung_typ"] = typ
    st.session_state["kiosk_buchung_zeit"] = buchungszeit
    st.session_state["kiosk_buchung_erfolg"] = erfolg
    st.session_state["kiosk_phase"] = "bestaetigung"
    st.session_state["kiosk_rueckkehr_zeit"] = time.time()
    st.rerun()


def _zeige_bestaetigung(betrieb_id: int):
    """Bestätigungs-Bildschirm – kehrt nach 4 Sekunden zur PIN-Eingabe zurück."""
    ma = st.session_state["kiosk_mitarbeiter"]
    typ = st.session_state.get("kiosk_buchung_typ", "kommen")
    buchungszeit = st.session_state.get("kiosk_buchung_zeit")
    erfolg = st.session_state.get("kiosk_buchung_erfolg", True)

    name = f"{ma['vorname']} {ma['nachname']}" if ma else "Mitarbeiter"
    uhrzeit = buchungszeit.strftime("%H:%M") if buchungszeit else "--:--"

    if typ == "kommen":
        aktion_text = "KOMMEN gebucht"
        emoji = "✅"
        farbe = "success-box"
    else:
        aktion_text = "GEHEN gebucht"
        emoji = "🚪"
        farbe = "success-box"

    offline_hinweis = ""
    if not erfolg:
        offline_hinweis = "<br><small>⚡ Offline gespeichert – wird synchronisiert sobald Verbindung besteht</small>"
        farbe = "error-box"

    st.markdown(f"""
    <div class="{farbe}">
        <div style="font-size:3rem;">{emoji}</div>
        <div style="font-size:1.8rem; font-weight:700; margin:10px 0;">{name}</div>
        <div style="font-size:1.4rem;">{aktion_text} um <b>{uhrzeit} Uhr</b></div>
        {offline_hinweis}
    </div>
    """, unsafe_allow_html=True)

    # Countdown-Anzeige
    rueckkehr_zeit = st.session_state.get("kiosk_rueckkehr_zeit", time.time())
    verstrichen = time.time() - rueckkehr_zeit
    verbleibend = max(0, 4 - int(verstrichen))

    st.markdown(f'<div style="text-align:center; color:#888; margin-top:20px; font-size:1.1rem;">Zurück zur PIN-Eingabe in <b>{verbleibend}</b> Sekunden...</div>', unsafe_allow_html=True)

    # Sofort-Zurück-Button
    if st.button("← Jetzt zurück", key="btn_sofort_zurueck"):
        _kiosk_zuruecksetzen()
        st.rerun()

    # Auto-Rückkehr nach 4 Sekunden
    if verstrichen >= 4:
        _kiosk_zuruecksetzen()
        st.rerun()
    else:
        time.sleep(0.5)
        st.rerun()


def _kiosk_zuruecksetzen():
    """Kiosk-State zurücksetzen für nächsten Mitarbeiter."""
    st.session_state["kiosk_phase"] = "pin_eingabe"
    st.session_state["kiosk_mitarbeiter"] = None
    st.session_state["kiosk_pin"] = ""
    st.session_state["kiosk_buchung_typ"] = None
    st.session_state["kiosk_buchung_zeit"] = None
    st.session_state["kiosk_buchung_erfolg"] = None
    st.session_state["kiosk_rueckkehr_zeit"] = None
