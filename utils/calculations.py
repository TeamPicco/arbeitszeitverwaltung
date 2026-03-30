"""
Berechnungs-Funktionen für Arbeitszeit, Urlaub, Lohn und AZK-Status
Steakhouse Piccolo - Optimierte Version
"""

from datetime import datetime, date, time, timedelta
from typing import Tuple, List, Optional
import holidays
import os

# --- ZEIT-PARSING & DATUM ---

def parse_zeit(zeit_str: str):
    """
    Parst einen Zeitstring im Format 'HH:MM:SS' oder 'HH:MM'.
    Behandelt '24:00:00' als Mitternacht.
    """
    if not zeit_str:
        return time(0, 0, 0), False
    
    teil = zeit_str.strip()[:8]
    try:
        stunde = int(teil[:2])
        minute = int(teil[3:5]) if len(teil) >= 5 else 0
        sekunde = int(teil[6:8]) if len(teil) >= 8 else 0
    except (ValueError, IndexError):
        return time(0, 0, 0), False
    
    if stunde >= 24:
        return time(0, minute, sekunde), True
    
    return time(stunde, minute, sekunde), False

def get_german_holidays(year: int, bundesland: str = None) -> holidays.HolidayBase:
    if bundesland is None:
        bundesland = os.getenv('BUNDESLAND', 'NW')
    return holidays.Germany(years=year, prov=bundesland)

def is_feiertag(datum: date, bundesland: str = None) -> bool:
    """Prüft Feiertag (Mo/Di Ruhetage zählen nicht für Zuschläge)"""
    feiertage = get_german_holidays(datum.year, bundesland)
    if datum not in feiertage:
        return False
    if datum.weekday() in (0, 1):  # Montag oder Dienstag
        return False
    return True

# --- ARBEITSZEIT-BERECHNUNG ---

def berechne_arbeitsstunden(start_zeit: time, ende_zeit: time, pause_minuten: int, naechster_tag: bool = False) -> float:
    """Berechnet Netto-Arbeitsstunden (gerundet)"""
    start_dt = datetime.combine(date.today(), start_zeit)
    ende_dt = datetime.combine(date.today(), ende_zeit)
    
    if naechster_tag or ende_dt <= start_dt:
        ende_dt += timedelta(days=1)
    
    differenz = (ende_dt - start_dt).total_seconds() / 3600.0
    differenz -= pause_minuten / 60.0
    
    return round(max(0, differenz), 2)

def berechne_gesetzliche_pause(arbeitsstunden: float) -> int:
    """Gesetzliche Pausen nach § 4 ArbZG"""
    if arbeitsstunden <= 6:
        return 0
    elif arbeitsstunden <= 9:
        return 30
    else:
        return 45

# --- URLAUBS-BERECHNUNG ---

def berechne_urlaubstage(von_datum: date, bis_datum: date) -> float:
    """Berechnet Urlaubstage (Betriebstage: Mi-So)"""
    if bis_datum < von_datum:
        return 0
    tage = 0
    aktuelles_datum = von_datum
    while aktuelles_datum <= bis_datum:
        if aktuelles_datum.weekday() >= 2:  # Mi=2 bis So=6
            tage += 1
        aktuelles_datum += timedelta(days=1)
    return float(tage)

# --- ARBEITSZEITKONTO (AZK) LOGIK ---

def berechne_monats_differenz(ist_stunden: float, soll_stunden: float) -> float:
    """Berechnet Plus- oder Minusstunden für einen Monat"""
    return round(ist_stunden - soll_stunden, 2)

def berechne_azk_kumuliert(mitarbeiter_id, bis_monat: int, bis_jahr: int, supabase_client) -> float:
    """
    Berechnet den echten Gesamtstand des AZK. 
    Zieht für jeden Monat mit Einträgen das Soll ab.
    """
    # 1. Alle Zeiterfassungen holen
    res = supabase_client.table("zeiterfassung")\
        .select("stunden, monat, jahr")\
        .eq("mitarbeiter_id", mitarbeiter_id)\
        .execute()
    
    if not res.data:
        return 0.0

    # 2. Soll-Stunden aus Mitarbeiter-Tabelle holen
    ma_res = supabase_client.table("mitarbeiter")\
        .select("soll_stunden_monat")\
        .eq("id", mitarbeiter_id)\
        .single().execute()
    
    soll_pro_monat = ma_res.data.get('soll_stunden_monat', 160.0)

    # 3. Monatliche Verrechnung
    stunden_pro_monat = {}
    for r in res.data:
        key = (r['monat'], r['jahr'])
        stunden_pro_monat[key] = stunden_pro_monat.get(key, 0.0) + r['stunden']

    total_saldo = 0.0
    for (m, j), ist_stunden in stunden_pro_monat.items():
        # Nur Monate bis zum gewählten Zeitpunkt berücksichtigen
        if j < bis_jahr or (j == bis_jahr and m <= bis_monat):
            total_saldo += (ist_stunden - soll_pro_monat)
        
    return round(total_saldo, 2)

# --- LOHN-FUNKTIONEN ---

def berechne_grundlohn(stundenlohn: float, ist_stunden: float) -> float:
    return round(stundenlohn * ist_stunden, 2)

def berechne_sonntagszuschlag(stundenlohn: float, sonntagsstunden: float) -> float:
    return round(stundenlohn * sonntagsstunden * 0.50, 2)

def berechne_feiertagszuschlag(stundenlohn: float, feiertagsstunden: float) -> float:
    return round(stundenlohn * feiertagsstunden * 1.00, 2)

def berechne_gesamtlohn(grundlohn: float, sonntag: float, feiertag: float) -> float:
    return round(grundlohn + sonntag + feiertag, 2)

# --- FORMATIERUNG & HELPER ---

def format_stunden(stunden: float) -> str:
    stunden_int = int(stunden)
    minuten = int((abs(stunden) - abs(stunden_int)) * 60)
    return f"{stunden_int:02d}:{minuten:02d}"

def format_waehrung(betrag: float) -> str:
    return f"{betrag:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def get_monatsnamen(monat: int) -> str:
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return monate[monat - 1] if 1 <= monat <= 12 else ""

def get_wochentag(datum: date) -> str:
    wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    return wochentage[datum.weekday()]
