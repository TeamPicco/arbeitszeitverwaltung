"""
Kiosk-Modus Stempeluhr
======================
Dauerhaft eingeloggter Kiosk-Modus für Mitarbeiter-Zeiterfassung.
Authentifizierung per 4-stelligem PIN (Numpad + Tastatur).
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
/* ── Grundlayout ── */
[data-testid="stAppViewContainer"] {
    background: #0f1923 !important;
}
[data-testid="stHeader"] {
    background: transparent !important;
}
.block-container {
    padding-top: 1rem !important;
    max-width: 700px !important;
    margin: 0 auto !important;
}

/* ── Kopfzeile ── */
.kiosk-header-wrap {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    background: #1a2535;
    border-radius: 14px;
    margin-bottom: 18px;
    border: 1px solid #2a3a50;
}
.kiosk-brand {
    font-size: 0.85rem;
    color: #7a9cc0;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.kiosk-geraet {
    font-size: 1.3rem;
    font-weight: 800;
    color: #e8f0fe;
}
.offline-badge {
    background: #e65100;
    color: #fff;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.online-badge {
    background: #1b5e20;
    color: #a5d6a7;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    border: 1px solid #2e7d32;
}

/* ── Uhr & Datum ── */
.kiosk-uhr {
    font-size: 4rem;
    font-weight: 800;
    color: #e8f0fe;
    text-align: center;
    letter-spacing: 4px;
    font-variant-numeric: tabular-nums;
    margin: 4px 0 0 0;
    line-height: 1.1;
}
.kiosk-datum {
    font-size: 1.1rem;
    color: #7a9cc0;
    text-align: center;
    margin-bottom: 22px;
    font-weight: 500;
}

/* ── PIN-Anzeige ── */
.pin-display-wrap {
    background: #1a2535;
    border: 2px solid #3a6ea8;
    border-radius: 16px;
    padding: 18px 30px;
    margin: 0 auto 8px auto;
    max-width: 320px;
    text-align: center;
    box-shadow: 0 0 20px rgba(58, 110, 168, 0.3);
}
.pin-dots {
    font-size: 2.2rem;
    letter-spacing: 18px;
    color: #4a90d9;
    line-height: 1;
}
.pin-hint {
    text-align: center;
    color: #7a9cc0;
    font-size: 0.92rem;
    margin-bottom: 18px;
    font-weight: 500;
}
.pin-keyboard-hint {
    text-align: center;
    color: #4a6a8a;
    font-size: 0.78rem;
    margin-bottom: 14px;
    font-style: italic;
}

/* ── Fehler/Erfolg-Boxen ── */
.error-box {
    background: #3e1010;
    border: 2px solid #c62828;
    border-radius: 14px;
    padding: 16px 20px;
    text-align: center;
    font-size: 1.1rem;
    color: #ff8a80;
    margin: 10px 0 16px 0;
    font-weight: 600;
}
.success-box {
    background: #0d2b0d;
    border: 2px solid #2e7d32;
    border-radius: 18px;
    padding: 30px 24px;
    text-align: center;
    color: #a5d6a7;
    margin: 10px 0;
}
.success-box-offline {
    background: #2b1a00;
    border: 2px solid #e65100;
    border-radius: 18px;
    padding: 30px 24px;
    text-align: center;
    color: #ffcc80;
    margin: 10px 0;
}

/* ── Mitarbeiter-Name ── */
.mitarbeiter-name {
    font-size: 2rem;
    font-weight: 800;
    text-align: center;
    color: #e8f0fe;
    margin: 8px 0 4px 0;
}
.letzter-eintrag {
    text-align: center;
    color: #7a9cc0;
    font-size: 0.95rem;
    margin-bottom: 22px;
    font-weight: 500;
}

/* ── Numpad-Buttons ── */
div[data-testid="stButton"] > button {
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    height: 72px !important;
    border-radius: 12px !important;
    border: 2px solid #2a3a50 !important;
    background: #1e2d42 !important;
    color: #c8ddf0 !important;
    width: 100% !important;
    transition: all 0.12s ease !important;
    letter-spacing: 1px !important;
}
div[data-testid="stButton"] > button:hover {
    background: #2a4060 !important;
    border-color: #4a90d9 !important;
    color: #ffffff !important;
    transform: scale(1.04) !important;
    box-shadow: 0 0 12px rgba(74, 144, 217, 0.4) !important;
}
div[data-testid="stButton"] > button:active {
    transform: scale(0.96) !important;
    background: #3a5a80 !important;
}

/* ── Löschen-Button ── */
.btn-loeschen div[data-testid="stButton"] > button {
    background: #4a2000 !important;
    color: #ffb74d !important;
    border-color: #e65100 !important;
    font-size: 1.5rem !important;
}
.btn-loeschen div[data-testid="stButton"] > button:hover {
    background: #7a3800 !important;
    border-color: #ff8f00 !important;
}

/* ── Reset-Button ── */
.btn-reset div[data-testid="stButton"] > button {
    background: #1a2535 !important;
    color: #90a4ae !important;
    border-color: #37474f !important;
    font-size: 1rem !important;
}
.btn-reset div[data-testid="stButton"] > button:hover {
    background: #263545 !important;
    color: #cfd8dc !important;
}

/* ── KOMMEN-Button (via Streamlit st-key-Klasse) ── */
.st-key-btn_kommen button {
    background: linear-gradient(135deg, #1b5e20, #2e7d32) !important;
    color: #ffffff !important;
    font-size: 1.6rem !important;
    height: 110px !important;
    border-radius: 18px !important;
    border: 2px solid #4caf50 !important;
    letter-spacing: 2px !important;
    box-shadow: 0 4px 20px rgba(46, 125, 50, 0.5) !important;
    text-shadow: 0 1px 3px rgba(0,0,0,0.4) !important;
}
.st-key-btn_kommen button:hover {
    background: linear-gradient(135deg, #2e7d32, #43a047) !important;
    box-shadow: 0 6px 28px rgba(76, 175, 80, 0.6) !important;
    transform: scale(1.02) !important;
    border-color: #66bb6a !important;
}

/* ── GEHEN-Button (via Streamlit st-key-Klasse) ── */
.st-key-btn_gehen button {
    background: linear-gradient(135deg, #7f0000, #c62828) !important;
    color: #ffffff !important;
    font-size: 1.6rem !important;
    height: 110px !important;
    border-radius: 18px !important;
    border: 2px solid #ef5350 !important;
    letter-spacing: 2px !important;
    box-shadow: 0 4px 20px rgba(198, 40, 40, 0.5) !important;
    text-shadow: 0 1px 3px rgba(0,0,0,0.4) !important;
}
.st-key-btn_gehen button:hover {
    background: linear-gradient(135deg, #c62828, #e53935) !important;
    box-shadow: 0 6px 28px rgba(239, 83, 80, 0.6) !important;
    transform: scale(1.02) !important;
    border-color: #ef9a9a !important;
}

/* ── Zurück-Button ── */
.st-key-btn_zurueck button {
    background: #1a2535 !important;
    color: #7a9cc0 !important;
    border-color: #2a3a50 !important;
    font-size: 0.95rem !important;
    height: 44px !important;
    border-radius: 10px !important;
}
.st-key-btn_zurueck button:hover {
    background: #263545 !important;
    color: #c8ddf0 !important;
}

/* ── Countdown ── */
.countdown-text {
    text-align: center;
    color: #7a9cc0;
    margin-top: 18px;
    font-size: 1rem;
    font-weight: 500;
}

/* ── Tastatur-Input (versteckt) ── */
.keyboard-input-wrapper input {
    position: absolute !important;
    opacity: 0 !important;
    pointer-events: none !important;
    width: 1px !important;
    height: 1px !important;
}
</style>
"""

# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def get_jetzt_berlin():
    """Aktuelle Zeit in Europe/Berlin."""
    from datetime import timezone, timedelta
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        return datetime.now(tz)
    except Exception:
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
    except Exception:
        st.session_state["kiosk_offline"] = True
    return None


def letzter_eintrag(betrieb_id: int, mitarbeiter_id: int):
    """Letzten Zeiterfassungs-Eintrag des Mitarbeiters heute abrufen."""
    try:
        supabase = get_supabase()
        heute = get_jetzt_berlin().date().isoformat()
        result = supabase.table("zeiterfassung").select(
            "id, datum, start_zeit, ende_zeit"
        ).eq("mitarbeiter_id", mitarbeiter_id).eq(
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
    Schema: datum, start_zeit, ende_zeit (kein betrieb_id in zeiterfassung)
    """
    jetzt = get_jetzt_berlin()
    heute = jetzt.date().isoformat()
    uhrzeit = jetzt.strftime("%H:%M:%S")

    try:
        supabase = get_supabase()

        if typ == "kommen":
            eintrag = {
                "mitarbeiter_id": mitarbeiter_id,
                "datum": heute,
                "start_zeit": uhrzeit,
            }
            supabase.table("zeiterfassung").insert(eintrag).execute()
        else:  # gehen
            offene = supabase.table("zeiterfassung").select("id").eq(
                "mitarbeiter_id", mitarbeiter_id
            ).eq("datum", heute).is_("ende_zeit", "null").order(
                "created_at", desc=True
            ).limit(1).execute()

            if offene.data:
                supabase.table("zeiterfassung").update({
                    "ende_zeit": uhrzeit
                }).eq("id", offene.data[0]["id"]).execute()
            else:
                eintrag = {
                    "mitarbeiter_id": mitarbeiter_id,
                    "datum": heute,
                    "ende_zeit": uhrzeit,
                }
                supabase.table("zeiterfassung").insert(eintrag).execute()

        st.session_state["kiosk_offline"] = False
        return True, jetzt
    except Exception:
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
                    "mitarbeiter_id": eintrag["mitarbeiter_id"],
                    "datum": heute,
                    "start_zeit": uhrzeit,
                }
                supabase.table("zeiterfassung").insert(db_eintrag).execute()
            else:
                offene = supabase.table("zeiterfassung").select("id").eq(
                    "mitarbeiter_id", eintrag["mitarbeiter_id"]
                ).eq("datum", heute).is_(
                    "ende_zeit", "null"
                ).order("created_at", desc=True).limit(1).execute()
                if offene.data:
                    supabase.table("zeiterfassung").update(
                        {"ende_zeit": uhrzeit}
                    ).eq("id", offene.data[0]["id"]).execute()
                else:
                    db_eintrag = {
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


# ─── Tastatur-Input-Handling ─────────────────────────────────────────────────

KEYBOARD_JS = """
<script>
(function() {
    // Warte bis Streamlit bereit ist
    function attachKeyListener() {
        document.removeEventListener('keydown', handleKey);
        document.addEventListener('keydown', handleKey);
    }

    function handleKey(e) {
        // Nur wenn kein Input-Feld fokussiert ist (außer unserem versteckten)
        const tag = document.activeElement ? document.activeElement.tagName : '';
        if (tag === 'INPUT' || tag === 'TEXTAREA') return;

        const key = e.key;

        // Ziffern 0-9
        if (/^[0-9]$/.test(key)) {
            e.preventDefault();
            const btn = document.querySelector('[data-testid="stButton"] button[kind="secondary"]');
            // Suche den Button mit dem passenden Text
            const buttons = document.querySelectorAll('[data-testid="stButton"] button');
            for (let b of buttons) {
                if (b.textContent.trim() === key) {
                    b.click();
                    break;
                }
            }
        }
        // Backspace / Delete
        else if (key === 'Backspace' || key === 'Delete') {
            e.preventDefault();
            const buttons = document.querySelectorAll('[data-testid="stButton"] button');
            for (let b of buttons) {
                if (b.textContent.includes('⌫')) {
                    b.click();
                    break;
                }
            }
        }
        // Escape = Reset
        else if (key === 'Escape') {
            e.preventDefault();
            const buttons = document.querySelectorAll('[data-testid="stButton"] button');
            for (let b of buttons) {
                if (b.textContent.includes('Reset') || b.textContent.includes('✕')) {
                    b.click();
                    break;
                }
            }
        }
    }

    // Sofort und nach kurzer Verzögerung (für Streamlit-Reruns)
    attachKeyListener();
    setTimeout(attachKeyListener, 500);
    setTimeout(attachKeyListener, 1500);

    // MutationObserver für Streamlit-Reruns
    const observer = new MutationObserver(function() {
        attachKeyListener();
    });
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
"""


# ─── Haupt-Kiosk-Funktion ────────────────────────────────────────────────────

def zeige_kiosk(betrieb_id: int, geraet_name: str = "Kiosk"):
    """Haupt-Einstiegspunkt für den Kiosk-Modus."""
    st.markdown(KIOSK_CSS, unsafe_allow_html=True)

    # Session-State initialisieren
    defaults = {
        "kiosk_pin": "",
        "kiosk_phase": "pin_eingabe",
        "kiosk_mitarbeiter": None,
        "kiosk_offline": False,
        "kiosk_buchung_typ": None,
        "kiosk_buchung_zeit": None,
        "kiosk_buchung_erfolg": None,
        "kiosk_rueckkehr_zeit": None,
        "kiosk_fehler": None,
        "offline_puffer": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Offline-Puffer synchronisieren
    if st.session_state.get("offline_puffer"):
        try:
            synced = offline_puffer_synchronisieren(betrieb_id)
            if synced > 0:
                st.toast(f"✅ {synced} Offline-Einträge synchronisiert")
        except Exception:
            pass

    # ── Kopfzeile ──
    jetzt = get_jetzt_berlin()
    offline = st.session_state.get("kiosk_offline", False)
    puffer_anzahl = len(st.session_state.get("offline_puffer", []))

    if offline:
        status_html = f'<span class="offline-badge">⚡ OFFLINE ({puffer_anzahl})</span>'
    else:
        status_html = '<span class="online-badge">● ONLINE</span>'

    st.markdown(f"""
    <div class="kiosk-header-wrap">
        <div>
            <div class="kiosk-brand">Stempeluhr</div>
            <div class="kiosk-geraet">{geraet_name}</div>
        </div>
        <div>{status_html}</div>
    </div>
    """, unsafe_allow_html=True)

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
    """PIN-Eingabe-Bildschirm mit Numpad + Tastaturunterstützung."""
    pin = st.session_state["kiosk_pin"]

    # Tastatur-JS einbinden
    st.components.v1.html(KEYBOARD_JS, height=0)

    # PIN-Anzeige (Punkte)
    punkte = "●" * len(pin) + "○" * (4 - len(pin))
    st.markdown(f"""
    <div class="pin-display-wrap">
        <div class="pin-dots">{punkte}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="pin-hint">Bitte 4-stelligen PIN eingeben</div>', unsafe_allow_html=True)
    st.markdown('<div class="pin-keyboard-hint">Eingabe auch über Tastatur möglich (0–9, Backspace, Esc)</div>', unsafe_allow_html=True)

    # Fehlermeldung
    if st.session_state.get("kiosk_fehler"):
        st.markdown(f'<div class="error-box">❌ {st.session_state["kiosk_fehler"]}</div>', unsafe_allow_html=True)
        st.session_state["kiosk_fehler"] = None

    # Numpad 1-9
    for zeile in [[1, 2, 3], [4, 5, 6], [7, 8, 9]]:
        cols = st.columns(3)
        for i, zahl in enumerate(zeile):
            with cols[i]:
                if st.button(str(zahl), key=f"pin_{zahl}", use_container_width=True):
                    _pin_ziffer_hinzufuegen(betrieb_id, str(zahl))

    # Letzte Zeile: Löschen | 0 | Reset
    col_del, col_0, col_ok = st.columns(3)
    with col_del:
        st.markdown('<div class="btn-loeschen">', unsafe_allow_html=True)
        if st.button("⌫", key="pin_del", use_container_width=True):
            st.session_state["kiosk_pin"] = st.session_state["kiosk_pin"][:-1]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col_0:
        if st.button("0", key="pin_0", use_container_width=True):
            _pin_ziffer_hinzufuegen(betrieb_id, "0")
    with col_ok:
        st.markdown('<div class="btn-reset">', unsafe_allow_html=True)
        if st.button("✕ Reset", key="pin_reset", use_container_width=True):
            st.session_state["kiosk_pin"] = ""
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def _pin_ziffer_hinzufuegen(betrieb_id: int, ziffer: str):
    """Eine Ziffer zum PIN hinzufügen und ggf. prüfen."""
    if len(st.session_state["kiosk_pin"]) < 4:
        st.session_state["kiosk_pin"] += ziffer
        if len(st.session_state["kiosk_pin"]) == 4:
            _pin_pruefen(betrieb_id)
        st.rerun()


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
                st.markdown(
                    f'<div class="letzter-eintrag">Letzter Eintrag heute: '
                    f'<b>{letzter_typ}</b> um <b>{letzter_uhr} Uhr</b></div>',
                    unsafe_allow_html=True
                )
        except Exception:
            pass
    else:
        st.markdown('<div class="letzter-eintrag">Noch kein Eintrag heute</div>', unsafe_allow_html=True)

    col_k, col_g = st.columns(2)
    with col_k:
        st.markdown('<div class="btn-kommen">', unsafe_allow_html=True)
        if st.button("✅  KOMMEN", key="btn_kommen", use_container_width=True):
            _buchung_ausfuehren(betrieb_id, ma, "kommen", geraet_name)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_g:
        st.markdown('<div class="btn-gehen">', unsafe_allow_html=True)
        if st.button("🚪  GEHEN", key="btn_gehen", use_container_width=True):
            _buchung_ausfuehren(betrieb_id, ma, "gehen", geraet_name)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="btn-zurueck">', unsafe_allow_html=True)
    if st.button("← Zurück zur PIN-Eingabe", key="btn_zurueck", use_container_width=False):
        st.session_state["kiosk_phase"] = "pin_eingabe"
        st.session_state["kiosk_mitarbeiter"] = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


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
        emoji = "✅"
        aktion_text = "KOMMEN gebucht"
        gruss = "Schönen Arbeitstag!"
    else:
        emoji = "🚪"
        aktion_text = "GEHEN gebucht"
        gruss = "Schönen Feierabend!"

    if erfolg:
        box_class = "success-box"
        offline_hinweis = ""
    else:
        box_class = "success-box-offline"
        offline_hinweis = '<div style="font-size:0.9rem; margin-top:10px; opacity:0.8;">⚡ Offline gespeichert – wird automatisch synchronisiert</div>'

    st.markdown(f"""
    <div class="{box_class}">
        <div style="font-size:3.5rem; margin-bottom:8px;">{emoji}</div>
        <div style="font-size:2rem; font-weight:800; margin-bottom:6px;">{name}</div>
        <div style="font-size:1.5rem; font-weight:600; margin-bottom:4px;">{aktion_text}</div>
        <div style="font-size:1.2rem; opacity:0.85;">um <b>{uhrzeit} Uhr</b></div>
        <div style="font-size:1.1rem; margin-top:12px; opacity:0.7;">{gruss}</div>
        {offline_hinweis}
    </div>
    """, unsafe_allow_html=True)

    # Countdown
    rueckkehr_zeit = st.session_state.get("kiosk_rueckkehr_zeit", time.time())
    verstrichen = time.time() - rueckkehr_zeit
    verbleibend = max(0, 4 - int(verstrichen))

    st.markdown(
        f'<div class="countdown-text">Zurück zur PIN-Eingabe in <b>{verbleibend}</b> Sekunden...</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="btn-zurueck">', unsafe_allow_html=True)
    if st.button("← Jetzt zurück", key="btn_sofort_zurueck"):
        _kiosk_zuruecksetzen()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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
