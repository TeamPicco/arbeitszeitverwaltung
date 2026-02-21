"""
Berechnungs-Funktionen für Arbeitszeit, Urlaub und Lohn
"""

from datetime import datetime, date, time, timedelta
from typing import Tuple, List
import holidays
import os


def get_german_holidays(year: int, bundesland: str = None) -> holidays.HolidayBase:
    """
    Gibt deutsche Feiertage für ein Jahr zurück
    
    Args:
        year: Jahr
        bundesland: Bundesland-Kürzel (z.B. 'NW', 'BY')
        
    Returns:
        holidays.HolidayBase: Feiertags-Objekt
    """
    if bundesland is None:
        bundesland = os.getenv('BUNDESLAND', 'NW')
    
    return holidays.Germany(years=year, prov=bundesland)


def is_feiertag(datum: date, bundesland: str = None) -> bool:
    """
    Prüft, ob ein Datum ein Feiertag ist
    
    Args:
        datum: Zu prüfendes Datum
        bundesland: Bundesland-Kürzel
        
    Returns:
        bool: True wenn Feiertag
    """
    feiertage = get_german_holidays(datum.year, bundesland)
    return datum in feiertage


def is_sonntag(datum: date) -> bool:
    """
    Prüft, ob ein Datum ein Sonntag ist
    
    Args:
        datum: Zu prüfendes Datum
        
    Returns:
        bool: True wenn Sonntag
    """
    return datum.weekday() == 6  # 6 = Sonntag


def berechne_arbeitsstunden(start_zeit: time, ende_zeit: time, pause_minuten: int) -> float:
    """
    Berechnet die Arbeitsstunden
    
    Args:
        start_zeit: Startzeit
        ende_zeit: Endzeit
        pause_minuten: Pausenzeit in Minuten
        
    Returns:
        float: Arbeitsstunden (gerundet auf 2 Dezimalstellen)
    """
    # Konvertiere zu datetime für Berechnung
    start_dt = datetime.combine(date.today(), start_zeit)
    ende_dt = datetime.combine(date.today(), ende_zeit)
    
    # Wenn Ende vor Start liegt, addiere einen Tag (Nachtschicht)
    if ende_dt < start_dt:
        ende_dt += timedelta(days=1)
    
    # Berechne Differenz in Stunden
    differenz = (ende_dt - start_dt).total_seconds() / 3600.0
    
    # Ziehe Pause ab
    differenz -= pause_minuten / 60.0
    
    # Runde auf 2 Dezimalstellen
    return round(max(0, differenz), 2)


def berechne_arbeitstage(von_datum: date, bis_datum: date, nur_werktage: bool = True) -> float:
    """
    Berechnet die Anzahl der Arbeitstage zwischen zwei Daten
    
    Args:
        von_datum: Startdatum
        bis_datum: Enddatum
        nur_werktage: Wenn True, werden nur Werktage gezählt (Mo-Fr)
        
    Returns:
        float: Anzahl der Arbeitstage
    """
    if bis_datum < von_datum:
        return 0
    
    tage = 0
    aktuelles_datum = von_datum
    
    while aktuelles_datum <= bis_datum:
        if nur_werktage:
            # Zähle nur Montag bis Freitag
            if aktuelles_datum.weekday() < 5:  # 0-4 = Mo-Fr
                tage += 1
        else:
            # Zähle alle Tage
            tage += 1
        
        aktuelles_datum += timedelta(days=1)
    
    return float(tage)


def berechne_urlaubstage(von_datum: date, bis_datum: date, bundesland: str = None) -> float:
    """
    Berechnet die Anzahl der Urlaubstage für 5-Tage-Woche (Mi-So)
    
    WICHTIG: Montag (0) und Dienstag (1) sind Ruhetage und werden NICHT gezählt!
    Arbeitstage: Mittwoch (2), Donnerstag (3), Freitag (4), Samstag (5), Sonntag (6)
    
    Args:
        von_datum: Startdatum
        bis_datum: Enddatum
        bundesland: Bundesland-Kürzel (aktuell nicht verwendet, da Sa/So Arbeitstage sind)
        
    Returns:
        float: Anzahl der Urlaubstage (nur Mi-So)
    """
    if bis_datum < von_datum:
        return 0
    
    tage = 0
    aktuelles_datum = von_datum
    
    while aktuelles_datum <= bis_datum:
        # Zähle nur Mi-So (weekday 2-6)
        # Montag (0) und Dienstag (1) sind Ruhetage und werden NICHT gezählt
        if aktuelles_datum.weekday() >= 2:  # Mi=2, Do=3, Fr=4, Sa=5, So=6
            tage += 1
        
        aktuelles_datum += timedelta(days=1)
    
    return float(tage)


def berechne_verfuegbare_urlaubstage(
    jahres_urlaubstage: int,
    resturlaub_vorjahr: float,
    genommene_tage: float
) -> float:
    """
    Berechnet die verfügbaren Urlaubstage
    
    Args:
        jahres_urlaubstage: Jährlicher Urlaubsanspruch
        resturlaub_vorjahr: Resturlaub aus Vorjahr
        genommene_tage: Bereits genommene Urlaubstage
        
    Returns:
        float: Verfügbare Urlaubstage
    """
    verfuegbar = jahres_urlaubstage + resturlaub_vorjahr - genommene_tage
    return round(max(0, verfuegbar), 2)


def berechne_grundlohn(stundenlohn: float, ist_stunden: float) -> float:
    """
    Berechnet den Grundlohn
    
    Args:
        stundenlohn: Stundenlohn (brutto)
        ist_stunden: Gearbeitete Stunden
        
    Returns:
        float: Grundlohn
    """
    return round(stundenlohn * ist_stunden, 2)


def berechne_sonntagszuschlag(stundenlohn: float, sonntagsstunden: float) -> float:
    """
    Berechnet den Sonntagszuschlag (50%)
    
    Args:
        stundenlohn: Stundenlohn (brutto)
        sonntagsstunden: Stunden an Sonntagen
        
    Returns:
        float: Sonntagszuschlag
    """
    return round(stundenlohn * sonntagsstunden * 0.50, 2)


def berechne_feiertagszuschlag(stundenlohn: float, feiertagsstunden: float) -> float:
    """
    Berechnet den Feiertagszuschlag (100%)
    
    Args:
        stundenlohn: Stundenlohn (brutto)
        feiertagsstunden: Stunden an Feiertagen
        
    Returns:
        float: Feiertagszuschlag
    """
    return round(stundenlohn * feiertagsstunden * 1.00, 2)


def berechne_gesamtlohn(
    grundlohn: float,
    sonntagszuschlag: float,
    feiertagszuschlag: float
) -> float:
    """
    Berechnet den Gesamtlohn
    
    Args:
        grundlohn: Grundlohn
        sonntagszuschlag: Sonntagszuschlag
        feiertagszuschlag: Feiertagszuschlag
        
    Returns:
        float: Gesamtlohn
    """
    return round(grundlohn + sonntagszuschlag + feiertagszuschlag, 2)


def format_stunden(stunden: float) -> str:
    """
    Formatiert Stunden im Format HH:MM
    
    Args:
        stunden: Stunden als Dezimalzahl
        
    Returns:
        str: Formatierte Stunden (z.B. "8:30")
    """
    stunden_int = int(stunden)
    minuten = int((stunden - stunden_int) * 60)
    return f"{stunden_int:02d}:{minuten:02d}"


def format_waehrung(betrag: float) -> str:
    """
    Formatiert einen Betrag als Währung
    
    Args:
        betrag: Betrag
        
    Returns:
        str: Formatierter Betrag (z.B. "1.234,56 €")
    """
    return f"{betrag:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def get_monatsnamen(monat: int) -> str:
    """
    Gibt den deutschen Monatsnamen zurück
    
    Args:
        monat: Monatsnummer (1-12)
        
    Returns:
        str: Monatsname
    """
    monate = [
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember"
    ]
    if 1 <= monat <= 12:
        return monate[monat - 1]
    return ""


def get_wochentag(datum: date) -> str:
    """
    Gibt den deutschen Wochentag zurück
    
    Args:
        datum: Datum
        
    Returns:
        str: Wochentag
    """
    wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    return wochentage[datum.weekday()]
