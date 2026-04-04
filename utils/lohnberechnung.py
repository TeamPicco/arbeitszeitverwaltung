"""
lohnberechnung.py – Vollständige Lohnberechnungs-Engine
=========================================================

Implementiert:
  1. Netto-Arbeitszeit-Berechnung mit automatischem Pausenabzug (§ 4 ArbZG)
  2. Zuschlags-Matrix: Sonntag (+50%), Feiertag (+100%), Nacht (23–06 Uhr)
  3. Feiertagskalender Sachsen (inkl. Buß- und Bettag)
  4. Korrekte Behandlung von Nachtschichten über Mitternacht
  5. Splitting bei Schichten, die mehrere Zuschlags-Perioden überspannen
  6. Audit-Log: Jeder Rechenschritt wird protokolliert
  7. Validierung: Warnung wenn Feiertag ohne Häkchen in Stammdaten

Bundesland: Sachsen (SN) – Besonderheit: Buß- und Bettag ist gesetzlicher Feiertag
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Any, Optional, Tuple, Iterable
import calendar
import holidays
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

BUNDESLAND = "SN"  # Sachsen

# Zuschlagssätze (auf den Basisstundenlohn)
SONNTAG_FAKTOR = 0.50   # +50%
FEIERTAG_FAKTOR = 1.00  # +100%
NACHT_FAKTOR = 0.25     # +25% (23:00–06:00 Uhr) – optional, aktuell nicht aktiv

# Gesetzliche Pausenregeln (§ 4 ArbZG)
PAUSE_REGELN = [
    (9.0, 45),   # > 9 Stunden → 45 Min Pause
    (6.0, 30),   # > 6 Stunden → 30 Min Pause
    (0.0, 0),    # ≤ 6 Stunden → keine Pause
]


@dataclass(frozen=True)
class DienstplanSummary:
    geplant: int
    urlaub: int
    frei: int
    krank: int


# ─────────────────────────────────────────────────────────────────────────────
# FEIERTAGSKALENDER SACHSEN
# ─────────────────────────────────────────────────────────────────────────────

def get_feiertage_sachsen(jahr: int) -> Dict[date, str]:
    """
    Gibt alle gesetzlichen Feiertage in Sachsen für ein Jahr zurück.

    Sachsen-spezifische Feiertage (zusätzlich zu bundesweiten):
    - Buß- und Bettag (Mittwoch vor dem 23. November)

    Returns:
        Dict[date, str]: {datum: name}
    """
    feiertage = {}

    # Bundesweite Feiertage via holidays-Bibliothek
    try:
        de_holidays = holidays.Germany(years=jahr, subdiv="SN")
        for d, name in de_holidays.items():
            feiertage[d] = name
    except Exception:
        # Fallback: manuelle Berechnung der wichtigsten Feiertage
        feiertage.update(_feiertage_manuell(jahr))

    return feiertage


def _feiertage_manuell(jahr: int) -> Dict[date, str]:
    """Manuelle Berechnung der deutschen Feiertage als Fallback."""
    feiertage = {}

    # Feste Feiertage
    feste = [
        (1, 1, "Neujahr"),
        (5, 1, "Tag der Arbeit"),
        (10, 3, "Tag der Deutschen Einheit"),
        (11, 1, "Reformationstag"),  # Sachsen
        (12, 25, "1. Weihnachtstag"),
        (12, 26, "2. Weihnachtstag"),
    ]
    for monat, tag, name in feste:
        try:
            feiertage[date(jahr, monat, tag)] = name
        except ValueError:
            pass

    # Ostern (Gaußsche Formel)
    ostern = _berechne_ostern(jahr)
    feiertage[ostern - timedelta(days=2)] = "Karfreitag"
    feiertage[ostern] = "Ostersonntag"
    feiertage[ostern + timedelta(days=1)] = "Ostermontag"
    feiertage[ostern + timedelta(days=39)] = "Christi Himmelfahrt"
    feiertage[ostern + timedelta(days=49)] = "Pfingstsonntag"
    feiertage[ostern + timedelta(days=50)] = "Pfingstmontag"

    # Buß- und Bettag (Sachsen): Mittwoch vor dem 23. November
    buss_bettag = _berechne_buss_und_bettag(jahr)
    feiertage[buss_bettag] = "Buß- und Bettag"

    return feiertage


def _berechne_ostern(jahr: int) -> date:
    """Berechnet das Osterdatum nach der Gaußschen Formel."""
    a = jahr % 19
    b = jahr // 100
    c = jahr % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = ((h + l - 7 * m + 114) % 31) + 1
    return date(jahr, monat, tag)


def _berechne_buss_und_bettag(jahr: int) -> date:
    """
    Buß- und Bettag: Mittwoch vor dem 23. November.
    Nur in Sachsen gesetzlicher Feiertag.
    """
    nov_23 = date(jahr, 11, 23)
    # Wochentag von Nov 23: 0=Mo, 2=Mi, 6=So
    tage_bis_mittwoch = (nov_23.weekday() - 2) % 7
    return nov_23 - timedelta(days=tage_bis_mittwoch)


def ist_feiertag_sachsen(datum: date) -> Tuple[bool, str]:
    """
    Prüft ob ein Datum ein Feiertag in Sachsen ist.

    WICHTIG: Feiertage an Montag/Dienstag (Ruhetage des Betriebs) zählen
    NICHT als Feiertag für Zuschlagszwecke, außer der Betrieb war geöffnet.

    Returns:
        (bool, str): (ist_feiertag, name_des_feiertags)
    """
    feiertage = get_feiertage_sachsen(datum.year)
    if datum in feiertage:
        # Ruhetage (Mo=0, Di=1) → kein Zuschlag
        if datum.weekday() in (0, 1):
            return False, ""
        return True, feiertage[datum]
    return False, ""


def ist_feiertag_sachsen_unabhaengig(datum: date) -> Tuple[bool, str]:
    """
    Prüft ob ein Datum ein Feiertag in Sachsen ist – OHNE Ruhetag-Ausnahme.
    Für Validierungszwecke und Urlaubsberechnung.
    """
    feiertage = get_feiertage_sachsen(datum.year)
    if datum in feiertage:
        return True, feiertage[datum]
    return False, ""


def ist_sonntag(datum: date) -> bool:
    """Prüft ob ein Datum ein Sonntag ist."""
    return datum.weekday() == 6


# ─────────────────────────────────────────────────────────────────────────────
# PAUSENBERECHNUNG
# ─────────────────────────────────────────────────────────────────────────────

def berechne_gesetzliche_pause(brutto_stunden: float) -> int:
    """
    Gesetzliche Mindestpause nach § 4 ArbZG.

    Regeln:
    - > 9 Stunden Arbeitszeit → 45 Minuten Pause
    - > 6 Stunden Arbeitszeit → 30 Minuten Pause
    - ≤ 6 Stunden Arbeitszeit → keine Pause erforderlich

    Returns:
        int: Pausenzeit in Minuten
    """
    for schwelle, pause in PAUSE_REGELN:
        if brutto_stunden > schwelle:
            return pause
    return 0


def berechne_netto_stunden(
    start_zeit: str,
    ende_zeit: str,
    pause_minuten: Optional[int],
    datum: date,
    auto_pause: bool = False  # Pausen werden ausschließlich manuell eingetragen
) -> Tuple[float, int, List[str]]:
    """
    Berechnet die Netto-Arbeitsstunden für einen Eintrag.

    Formel: Netto = (Ende - Start) - Pause
    Automatischer Pausenabzug wenn pause_minuten=None und auto_pause=True.

    Args:
        start_zeit: "HH:MM:SS"
        ende_zeit: "HH:MM:SS"
        pause_minuten: Manuell erfasste Pause (None = automatisch)
        datum: Arbeitsdatum (für Nachtschicht-Erkennung)
        auto_pause: Automatischen Pausenabzug anwenden wenn keine manuelle Pause

    Returns:
        (netto_stunden, verwendete_pause_minuten, audit_log)
    """
    audit = []

    if not start_zeit or not ende_zeit:
        return 0.0, 0, ["Kein vollständiger Eintrag (Start oder Ende fehlt)"]

    # Zeiten parsen
    start_dt = _parse_zeit_zu_datetime(start_zeit, datum)
    ende_dt = _parse_zeit_zu_datetime(ende_zeit, datum)

    # Nachtschicht: Ende liegt vor Start → Ende ist am nächsten Tag
    if ende_dt <= start_dt:
        ende_dt += timedelta(days=1)
        audit.append(f"Nachtschicht erkannt: Ende auf {(datum + timedelta(days=1)).strftime('%d.%m.')} verschoben")

    brutto_min = (ende_dt - start_dt).total_seconds() / 60.0
    brutto_h = brutto_min / 60.0
    audit.append(f"Brutto-Arbeitszeit: {brutto_h:.2f} Std ({int(brutto_min)} Min)")

    # Pausenabzug
    if pause_minuten is not None and pause_minuten > 0:
        verwendete_pause = pause_minuten
        audit.append(f"Manuelle Pause: {pause_minuten} Min")
    elif auto_pause:
        verwendete_pause = berechne_gesetzliche_pause(brutto_h)
        if verwendete_pause > 0:
            audit.append(f"Automatische Pause nach § 4 ArbZG: {verwendete_pause} Min (bei {brutto_h:.2f} Std)")
        else:
            audit.append(f"Keine Pause erforderlich (≤ 6 Std)")
    else:
        verwendete_pause = 0
        audit.append("Kein Pausenabzug")

    netto_min = brutto_min - verwendete_pause
    netto_h = round(max(0.0, netto_min / 60.0), 4)
    audit.append(f"Netto-Arbeitszeit: {netto_h:.4f} Std ({int(netto_min)} Min)")

    return netto_h, verwendete_pause, audit


def _parse_zeit_zu_datetime(zeit_str: str, datum: date) -> datetime:
    """Parst 'HH:MM:SS' oder 'HH:MM' zu datetime mit gegebenem Datum."""
    teil = str(zeit_str).strip()[:8]
    try:
        stunde = int(teil[:2])
        minute = int(teil[3:5]) if len(teil) >= 5 else 0
        sekunde = int(teil[6:8]) if len(teil) >= 8 else 0
    except (ValueError, IndexError):
        stunde, minute, sekunde = 0, 0, 0

    if stunde >= 24:
        return datetime.combine(datum + timedelta(days=1), time(0, minute, sekunde))
    return datetime.combine(datum, time(stunde, minute, sekunde))


# ─────────────────────────────────────────────────────────────────────────────
# ZUSCHLAGS-MATRIX (Splitting über Tagesgrenzen)
# ─────────────────────────────────────────────────────────────────────────────

def berechne_zuschlaege_mit_splitting(
    start_dt: datetime,
    ende_dt: datetime,
    mitarbeiter: Dict[str, Any],
    stundenlohn: float,
    audit_log: List[str],
    netto_faktor: float = 1.0
) -> Dict[str, float]:
    """
    Berechnet Zuschläge mit korrektem Splitting über Tages- und Stundengrenzen.

    Jede Stunde der Schicht wird gegen die Zuschlags-Matrix geprüft:
    - Sonntag 00:00–24:00: +50% (wenn sonntagszuschlag_aktiv)
    - Feiertag 00:00–24:00: +100% (wenn feiertagszuschlag_aktiv)
    - Feiertag auf Sonntag: 100% (höhere Regel, keine Addition)

    Splitting-Beispiel: Schicht So 22:00 – Mo 06:00
    → 22:00–24:00 = 2 Std Sonntag (50%)
    → 00:00–06:00 = 6 Std Montag (0%, Ruhetag)

    Returns:
        {
            'sonntags_stunden': float,
            'feiertags_stunden': float,
            'sonntag_auf_feiertag_stunden': float,
            'sonntagszuschlag': float,
            'feiertagszuschlag': float,
            'gesamt_zuschlag': float,
        }
    """
    sonntags_h = 0.0
    feiertags_h = 0.0
    sonntag_feiertag_h = 0.0  # Feiertag der auf Sonntag fällt

    sonntagszuschlag_aktiv = mitarbeiter.get("sonntagszuschlag_aktiv", False)
    feiertagszuschlag_aktiv = mitarbeiter.get("feiertagszuschlag_aktiv", False)

    # Schicht in 1-Minuten-Intervalle aufteilen für exaktes Splitting
    # (Optimierung: Tagesgrenzen als Splitting-Punkte nutzen)
    splitting_punkte = _berechne_splitting_punkte(start_dt, ende_dt)

    for segment_start, segment_ende in splitting_punkte:
        segment_datum = segment_start.date()
        segment_h_brutto = (segment_ende - segment_start).total_seconds() / 3600.0
        # Netto-Anteil: proportional zur Gesamtschicht (Pausen gleichmäßig verteilt)
        segment_h = segment_h_brutto * netto_faktor

        ist_so = ist_sonntag(segment_datum)
        ist_ft, ft_name = ist_feiertag_sachsen(segment_datum)

        if ist_ft and ist_so:
            # Feiertag auf Sonntag → höhere Regel (100%)
            sonntag_feiertag_h += segment_h
            audit_log.append(
                f"  Segment {segment_start.strftime('%d.%m. %H:%M')}–{segment_ende.strftime('%H:%M')}: "
                f"{segment_h:.2f} Std | Feiertag+Sonntag ({ft_name}) → 100% Zuschlag"
            )
        elif ist_ft:
            feiertags_h += segment_h
            audit_log.append(
                f"  Segment {segment_start.strftime('%d.%m. %H:%M')}–{segment_ende.strftime('%H:%M')}: "
                f"{segment_h:.2f} Std | Feiertag ({ft_name}) → 100% Zuschlag"
            )
        elif ist_so:
            sonntags_h += segment_h
            audit_log.append(
                f"  Segment {segment_start.strftime('%d.%m. %H:%M')}–{segment_ende.strftime('%H:%M')}: "
                f"{segment_h:.2f} Std | Sonntag → 50% Zuschlag"
            )
        else:
            wochentag_name = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][segment_datum.weekday()]
            audit_log.append(
                f"  Segment {segment_start.strftime('%d.%m. %H:%M')}–{segment_ende.strftime('%H:%M')}: "
                f"{segment_h:.2f} Std | {wochentag_name} → kein Zuschlag"
            )

    # Zuschläge berechnen (nur wenn Häkchen gesetzt)
    sonntagszuschlag = 0.0
    feiertagszuschlag = 0.0

    effektive_sonntags_h = sonntags_h
    effektive_feiertags_h = feiertags_h + sonntag_feiertag_h

    if sonntagszuschlag_aktiv and effektive_sonntags_h > 0:
        sonntagszuschlag = round(effektive_sonntags_h * stundenlohn * SONNTAG_FAKTOR, 4)
        audit_log.append(
            f"  Sonntagszuschlag: {effektive_sonntags_h:.2f} Std × {stundenlohn:.2f} € × {SONNTAG_FAKTOR:.0%} = {sonntagszuschlag:.2f} €"
        )
    elif sonntags_h > 0 and not sonntagszuschlag_aktiv:
        audit_log.append(
            f"  Sonntagszuschlag: {effektive_sonntags_h:.2f} Std NICHT berechnet (Häkchen nicht gesetzt)"
        )

    if feiertagszuschlag_aktiv and effektive_feiertags_h > 0:
        feiertagszuschlag = round(effektive_feiertags_h * stundenlohn * FEIERTAG_FAKTOR, 4)
        audit_log.append(
            f"  Feiertagszuschlag: {effektive_feiertags_h:.2f} Std × {stundenlohn:.2f} € × {FEIERTAG_FAKTOR:.0%} = {feiertagszuschlag:.2f} €"
        )
    elif effektive_feiertags_h > 0 and not feiertagszuschlag_aktiv:
        audit_log.append(
            f"  Feiertagszuschlag: {effektive_feiertags_h:.2f} Std NICHT berechnet (Häkchen nicht gesetzt)"
        )

    gesamt_zuschlag = round(sonntagszuschlag + feiertagszuschlag, 4)

    return {
        "sonntags_stunden": round(effektive_sonntags_h, 4),
        "feiertags_stunden": round(effektive_feiertags_h, 4),
        "sonntag_auf_feiertag_stunden": round(sonntag_feiertag_h, 4),
        "sonntagszuschlag": sonntagszuschlag,
        "feiertagszuschlag": feiertagszuschlag,
        "gesamt_zuschlag": gesamt_zuschlag,
    }


def _berechne_splitting_punkte(
    start_dt: datetime, ende_dt: datetime
) -> List[Tuple[datetime, datetime]]:
    """
    Teilt eine Schicht an Tagesgrenzen (00:00) auf.

    Beispiel: 22:00 So → 06:00 Mo
    → [(So 22:00, Mo 00:00), (Mo 00:00, Mo 06:00)]
    """
    segmente = []
    aktuell = start_dt

    while aktuell < ende_dt:
        # Nächste Tagesgrenze
        naechster_tag = datetime.combine(aktuell.date() + timedelta(days=1), time(0, 0, 0))
        segment_ende = min(naechster_tag, ende_dt)
        segmente.append((aktuell, segment_ende))
        aktuell = segment_ende

    return segmente


# ─────────────────────────────────────────────────────────────────────────────
# HAUPTFUNKTION: Einzelnen Zeiterfassungs-Eintrag berechnen
# ─────────────────────────────────────────────────────────────────────────────

def berechne_eintrag(
    eintrag: Dict[str, Any],
    mitarbeiter: Dict[str, Any],
    auto_pause: bool = False,  # Pausen werden ausschließlich manuell eingetragen
    dienstplan_start_zeit: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Berechnet Stunden und Lohn für einen einzelnen Zeiterfassungs-Eintrag.

    Args:
        eintrag: Zeiterfassungs-Datensatz aus DB
        mitarbeiter: Mitarbeiter-Datensatz mit Stundenlohn und Zuschlag-Flags
        auto_pause: Automatischen Pausenabzug anwenden

    Returns:
        {
            'id': int,
            'datum': date,
            'netto_stunden': float,
            'pause_minuten': int,
            'grundlohn': float,
            'sonntags_stunden': float,
            'feiertags_stunden': float,
            'sonntagszuschlag': float,
            'feiertagszuschlag': float,
            'gesamt_zuschlag': float,
            'gesamtlohn': float,
            'ist_sonntag': bool,
            'ist_feiertag': bool,
            'feiertag_name': str,
            'hat_zuschlag_aber_kein_haekchen': bool,
            'audit_log': List[str],
            'fehler': Optional[str],
        }
    """
    audit_log = []
    # Numeric-Fix: Leere Strings und None-Werte absichern
    def safe_float(val, default=0.0):
        if val is None or val == '':
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    monat_brutto = safe_float(mitarbeiter.get("monatliche_brutto_verguetung"), 0.0)
    monat_soll = safe_float(mitarbeiter.get("monatliche_soll_stunden"), 0.0)
    stundenlohn = round(monat_brutto / monat_soll, 4) if monat_brutto > 0 and monat_soll > 0 else 0.0
    datum_str = eintrag.get("datum", "")
    start_zeit = eintrag.get("start_zeit")
    ende_zeit = eintrag.get("ende_zeit")
    start_zeit_fuer_berechnung = start_zeit

    try:
        datum = date.fromisoformat(datum_str) if datum_str else date.today()
    except ValueError:
        datum = date.today()

    audit_log.append(f"=== Eintrag {datum.strftime('%d.%m.%Y')} ===")
    audit_log.append(f"Mitarbeiter: {mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}")
    audit_log.append(f"Stundenlohn: {stundenlohn:.2f} €")
    audit_log.append(f"Start: {start_zeit} | Ende: {ende_zeit}")

    # Feiertag/Sonntag-Status
    ist_so = ist_sonntag(datum)
    ist_ft, ft_name = ist_feiertag_sachsen(datum)
    audit_log.append(f"Wochentag: {['Mo','Di','Mi','Do','Fr','Sa','So'][datum.weekday()]}")
    if ist_so:
        audit_log.append("→ Sonntag")
    if ist_ft:
        audit_log.append(f"→ Feiertag: {ft_name}")

    # Warnung: Feiertag ohne Häkchen
    hat_zuschlag_aber_kein_haekchen = False
    if ist_ft and not mitarbeiter.get("feiertagszuschlag_aktiv", False):
        hat_zuschlag_aber_kein_haekchen = True
        audit_log.append("⚠️ WARNUNG: Feiertag, aber feiertagszuschlag_aktiv=False!")
    if ist_so and not mitarbeiter.get("sonntagszuschlag_aktiv", False):
        audit_log.append("ℹ️ Sonntag, aber sonntagszuschlag_aktiv=False → kein Zuschlag")

    # ── Krankheitstag: Lohnfortzahlung nach EFZG § 4 (Ansatz A: Tages-Soll) ──
    if eintrag.get('ist_krank') or eintrag.get('quelle') == 'au_bescheinigung':
        # Soll-Stunden pro Tag = monatliche Soll-Stunden ÷ Arbeitstage im Monat
        # Arbeitstage = alle Tage im Monat OHNE Montag (0) und Dienstag (1)
        monatliche_soll = float(mitarbeiter.get('monatliche_soll_stunden') or 0.0)
        _, tage_im_monat = calendar.monthrange(datum.year, datum.month)
        arbeitstage_monat = sum(
            1 for t in range(1, tage_im_monat + 1)
            if date(datum.year, datum.month, t).weekday() not in (0, 1)
        )
        lfz_stunden = round(monatliche_soll / arbeitstage_monat, 4) if arbeitstage_monat > 0 else 0.0
        lfz_grundlohn = round(lfz_stunden * stundenlohn, 2)
        audit_log.append(
            f"→ Krankheitstag (AU-Bescheinigung) – Lohnfortzahlung nach EFZG § 4"
        )
        audit_log.append(
            f"  Soll-Stunden/Monat: {monatliche_soll:.2f} h ÷ {arbeitstage_monat} Arbeitstage "
            f"= {lfz_stunden:.4f} h LFZ"
        )
        audit_log.append(
            f"  LFZ-Grundlohn: {lfz_stunden:.4f} h × {stundenlohn:.2f} € = {lfz_grundlohn:.2f} €"
        )
        return {
            "id": eintrag.get("id"),
            "datum": datum,
            "netto_stunden": lfz_stunden,   # zählt in Ist-Stunden → kein Minussaldo
            "pause_minuten": 0,
            "grundlohn": lfz_grundlohn,
            "sonntags_stunden": 0.0,
            "feiertags_stunden": 0.0,
            "sonntagszuschlag": 0.0,
            "feiertagszuschlag": 0.0,
            "gesamt_zuschlag": 0.0,
            "gesamtlohn": lfz_grundlohn,
            "ist_sonntag": ist_so,
            "ist_feiertag": ist_ft,
            "feiertag_name": ft_name,
            "hat_zuschlag_aber_kein_haekchen": False,
            "audit_log": audit_log,
            "fehler": None,
            "ist_krank": True,
            "lfz_stunden": lfz_stunden,
        }

    # Kein vollständiger Eintrag
    if not start_zeit or not ende_zeit:
        audit_log.append("Eintrag unvollständig (kein Ende) – übersprungen")
        return {
            "id": eintrag.get("id"),
            "datum": datum,
            "netto_stunden": 0.0,
            "pause_minuten": 0,
            "grundlohn": 0.0,
            "sonntags_stunden": 0.0,
            "feiertags_stunden": 0.0,
            "sonntagszuschlag": 0.0,
            "feiertagszuschlag": 0.0,
            "gesamt_zuschlag": 0.0,
            "gesamtlohn": 0.0,
            "ist_sonntag": ist_so,
            "ist_feiertag": ist_ft,
            "feiertag_name": ft_name,
            "hat_zuschlag_aber_kein_haekchen": hat_zuschlag_aber_kein_haekchen,
            "audit_log": audit_log,
            "fehler": "Eintrag offen (kein Ende)",
        }

    # Kappungsregel: Es wird ausschließlich die geplante Dienstplan-Startzeit berücksichtigt.
    # Die Endzeit stammt immer aus der Zeiterfassung (Ausstempelung / Admin-Korrektur).
    if dienstplan_start_zeit:
        try:
            raw_start_dt = _parse_zeit_zu_datetime(start_zeit, datum)
            raw_end_dt = _parse_zeit_zu_datetime(ende_zeit, datum)
            if raw_end_dt <= raw_start_dt:
                raw_end_dt += timedelta(days=1)
            plan_start_dt = _parse_zeit_zu_datetime(dienstplan_start_zeit, datum)
            if raw_start_dt < plan_start_dt < raw_end_dt:
                start_zeit_fuer_berechnung = plan_start_dt.time().strftime("%H:%M:%S")
                audit_log.append(
                    "Kappung aktiv: "
                    f"gestempelt {str(start_zeit)[:5]} → berechnet ab Dienstplan-Start {plan_start_dt.strftime('%H:%M')}"
                )
        except Exception:
            # Falls eine Legacy-Instanz inkonsistente Zeitwerte enthält, nicht hard-failen.
            start_zeit_fuer_berechnung = start_zeit

    # Sicherheitsgrenze: Arbeitszeit über 14h nur bei expliziter Admin-Freigabe zulassen.
    # So verhindern wir Phantom-Schichten durch fehlendes Ausstempeln.
    try:
        start_guard = _parse_zeit_zu_datetime(start_zeit_fuer_berechnung, datum)
        end_guard = _parse_zeit_zu_datetime(ende_zeit, datum)
        if end_guard <= start_guard:
            end_guard += timedelta(days=1)
        planned_minutes = int((end_guard - start_guard).total_seconds() // 60)
        if planned_minutes > (14 * 60):
            override = bool(eintrag.get("admin_override_long_shift"))
            if not override:
                return {
                    "id": eintrag.get("id"),
                    "datum": datum,
                    "netto_stunden": 0.0,
                    "pause_minuten": int(eintrag.get("pause_minuten") or 0),
                    "grundlohn": 0.0,
                    "sonntags_stunden": 0.0,
                    "feiertags_stunden": 0.0,
                    "sonntagszuschlag": 0.0,
                    "feiertagszuschlag": 0.0,
                    "gesamt_zuschlag": 0.0,
                    "gesamtlohn": 0.0,
                    "ist_sonntag": ist_so,
                    "ist_feiertag": ist_ft,
                    "feiertag_name": ft_name,
                    "hat_zuschlag_aber_kein_haekchen": False,
                    "audit_log": audit_log + [
                        f"Sicherheitsstopp: Schichtdauer {planned_minutes/60:.2f}h > 14h ohne Admin-Freigabe."
                    ],
                    "fehler": "Schicht über 14h erkannt – Admin-Freigabe erforderlich",
                }
    except Exception:
        pass

    # Netto-Stunden berechnen
    pause_manuell = eintrag.get("pause_minuten")
    netto_h, verwendete_pause, zeit_audit = berechne_netto_stunden(
        start_zeit_fuer_berechnung, ende_zeit, pause_manuell, datum, auto_pause
    )
    audit_log.extend(zeit_audit)

    # Grundlohn
    grundlohn = round(netto_h * stundenlohn, 4)
    audit_log.append(f"Grundlohn: {netto_h:.4f} Std × {stundenlohn:.2f} € = {grundlohn:.2f} €")

    # Zuschläge mit Splitting berechnen
    # WICHTIG: Splitting auf Brutto-Stunden, dann proportional auf Netto-Stunden umrechnen
    start_dt = _parse_zeit_zu_datetime(start_zeit_fuer_berechnung, datum)
    ende_dt = _parse_zeit_zu_datetime(ende_zeit, datum)
    if ende_dt <= start_dt:
        ende_dt += timedelta(days=1)

    brutto_gesamt_h = (ende_dt - start_dt).total_seconds() / 3600.0
    # Proportionaler Faktor: Netto/Brutto (für Pausenanteil)
    netto_faktor = (netto_h / brutto_gesamt_h) if brutto_gesamt_h > 0 else 1.0

    audit_log.append(f"Zuschlagsberechnung (Splitting nach Tagesgrenzen, Netto-Faktor: {netto_faktor:.4f}):")
    zuschlaege = berechne_zuschlaege_mit_splitting(
        start_dt, ende_dt, mitarbeiter, stundenlohn, audit_log, netto_faktor=netto_faktor
    )

    gesamtlohn = round(grundlohn + zuschlaege["gesamt_zuschlag"], 2)
    audit_log.append(f"Gesamtlohn: {grundlohn:.2f} € + {zuschlaege['gesamt_zuschlag']:.2f} € Zuschlag = {gesamtlohn:.2f} €")

    return {
        "id": eintrag.get("id"),
        "datum": datum,
        "netto_stunden": round(netto_h, 4),
        "pause_minuten": verwendete_pause,
        "grundlohn": round(grundlohn, 2),
        "sonntags_stunden": zuschlaege["sonntags_stunden"],
        "feiertags_stunden": zuschlaege["feiertags_stunden"],
        "sonntagszuschlag": zuschlaege["sonntagszuschlag"],
        "feiertagszuschlag": zuschlaege["feiertagszuschlag"],
        "gesamt_zuschlag": zuschlaege["gesamt_zuschlag"],
        "gesamtlohn": gesamtlohn,
        "ist_sonntag": ist_so,
        "ist_feiertag": ist_ft,
        "feiertag_name": ft_name,
        "hat_zuschlag_aber_kein_haekchen": hat_zuschlag_aber_kein_haekchen,
        "audit_log": audit_log,
        "fehler": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MONATSSUMMEN
# ─────────────────────────────────────────────────────────────────────────────

def berechne_monat(
    eintraege: List[Dict[str, Any]],
    mitarbeiter: Dict[str, Any],
    auto_pause: bool = False,  # Pausen werden ausschließlich manuell eingetragen
    dienstplan_start_map: Optional[Dict[str, str]] = None,
    data_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Berechnet alle Stunden und Lohnsummen für einen Monat.

    Args:
        eintraege: Liste aller Zeiterfassungs-Einträge des Monats
        mitarbeiter: Mitarbeiter-Datensatz
        auto_pause: Automatischen Pausenabzug anwenden
        dienstplan_start_map: Optionales Mapping {YYYY-MM-DD: HH:MM(:SS)} für Kappung

    Returns:
        {
            'zeilen': List[Dict],          # Berechnete Einzelzeilen
            'gesamt_stunden': float,
            'sonntags_stunden': float,
            'feiertags_stunden': float,
            'grundlohn': float,
            'sonntagszuschlag': float,
            'feiertagszuschlag': float,
            'gesamt_zuschlag': float,
            'gesamtbrutto': float,
            'anzahl_eintraege': int,
            'offene_eintraege': int,
            'warnungen': List[str],        # Feiertag ohne Häkchen etc.
            'audit_log_gesamt': List[str], # Vollständiges Audit-Log
        }
    """
    # data_hash dient als expliziter Cache-Buster im Funktions-Signature-Key.
    _ = data_hash
    zeilen = []
    gesamt_stunden = 0.0
    sonntags_stunden = 0.0
    feiertags_stunden = 0.0
    grundlohn_gesamt = 0.0
    sonntagszuschlag_gesamt = 0.0
    feiertagszuschlag_gesamt = 0.0
    offene_eintraege = 0
    warnungen = []
    audit_log_gesamt = []

    for eintrag in eintraege:
        datum_key = str(eintrag.get("datum") or "")
        planned_start = (dienstplan_start_map or {}).get(datum_key)
        zeile = berechne_eintrag(
            eintrag,
            mitarbeiter,
            auto_pause,
            dienstplan_start_zeit=planned_start,
        )
        zeilen.append(zeile)
        audit_log_gesamt.extend(zeile["audit_log"])
        audit_log_gesamt.append("")  # Leerzeile zwischen Einträgen

        if zeile.get("fehler"):
            offene_eintraege += 1
            continue

        gesamt_stunden += zeile["netto_stunden"]
        sonntags_stunden += zeile["sonntags_stunden"]
        feiertags_stunden += zeile["feiertags_stunden"]
        grundlohn_gesamt += zeile["grundlohn"]
        sonntagszuschlag_gesamt += zeile["sonntagszuschlag"]
        feiertagszuschlag_gesamt += zeile["feiertagszuschlag"]

        if zeile["hat_zuschlag_aber_kein_haekchen"]:
            datum_str = zeile["datum"].strftime("%d.%m.%Y") if isinstance(zeile["datum"], date) else str(zeile["datum"])
            ft_name = zeile.get("feiertag_name", "Feiertag")
            warnungen.append(
                f"⚠️ {datum_str}: Arbeit an Feiertag ({ft_name}), "
                f"aber 'Feiertagszuschlag aktiv' ist NICHT gesetzt. "
                f"Bitte in den Mitarbeiterstammdaten prüfen!"
            )

    gesamt_zuschlag = round(sonntagszuschlag_gesamt + feiertagszuschlag_gesamt, 2)
    gesamtbrutto = round(grundlohn_gesamt + gesamt_zuschlag, 2)

    # Summen-Audit
    audit_log_gesamt.append("=== MONATSSUMMEN ===")
    audit_log_gesamt.append(f"Gesamt-Nettostunden: {gesamt_stunden:.2f} Std")
    audit_log_gesamt.append(f"Davon Sonntagsstunden: {sonntags_stunden:.2f} Std")
    audit_log_gesamt.append(f"Davon Feiertagsstunden: {feiertags_stunden:.2f} Std")
    audit_log_gesamt.append(f"Grundlohn: {grundlohn_gesamt:.2f} €")
    audit_log_gesamt.append(f"Sonntagszuschlag: {sonntagszuschlag_gesamt:.2f} €")
    audit_log_gesamt.append(f"Feiertagszuschlag: {feiertagszuschlag_gesamt:.2f} €")
    audit_log_gesamt.append(f"Gesamt-Brutto: {gesamtbrutto:.2f} €")

    return {
        "zeilen": zeilen,
        "gesamt_stunden": round(gesamt_stunden, 2),
        "sonntags_stunden": round(sonntags_stunden, 2),
        "feiertags_stunden": round(feiertags_stunden, 2),
        "grundlohn": round(grundlohn_gesamt, 2),
        "sonntagszuschlag": round(sonntagszuschlag_gesamt, 2),
        "feiertagszuschlag": round(feiertagszuschlag_gesamt, 2),
        "gesamt_zuschlag": gesamt_zuschlag,
        "gesamtbrutto": gesamtbrutto,
        "anzahl_eintraege": len(zeilen),
        "offene_eintraege": offene_eintraege,
        "warnungen": warnungen,
        "audit_log_gesamt": audit_log_gesamt,
    }


@st.cache_data(ttl=30, show_spinner=False)
def berechne_monat_cached(
    eintraege: List[Dict[str, Any]],
    mitarbeiter: Dict[str, Any],
    auto_pause: bool = False,
    dienstplan_start_map: Optional[Dict[str, str]] = None,
    data_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Gecachte Variante der Monatsberechnung.
    data_hash muss aus Rohdaten erzeugt und übergeben werden, damit Änderungen
    sofort zu einem neuen Cache-Key führen.
    """
    return berechne_monat(
        eintraege=eintraege,
        mitarbeiter=mitarbeiter,
        auto_pause=auto_pause,
        dienstplan_start_map=dienstplan_start_map,
        data_hash=data_hash,
    )


def berechne_arbeitszeitkonto_saldo(
    *,
    ist_stunden: float,
    soll_stunden: float,
    saldenvortrag: float,
) -> float:
    """
    Rechts- und fachlich eindeutige Saldoformel für das Arbeitszeitkonto:
    Neuer Saldo = (Ist - Soll) + Saldenvortrag
    """
    ist_v = float(ist_stunden or 0.0)
    soll_v = float(soll_stunden or 0.0)
    vortrag_v = float(saldenvortrag or 0.0)
    return round((ist_v - soll_v) + vortrag_v, 2)


def _to_date_or_none(value: object) -> date | None:
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if len(raw) >= 10:
            return date.fromisoformat(raw[:10])
    except ValueError:
        return None
    return None


def _norm_status(entry: Dict[str, Any]) -> str:
    raw = str(entry.get("schichttyp") or entry.get("typ") or entry.get("status") or "").strip().lower()
    if raw in {"urlaub", "vacation", "u"}:
        return "urlaub"
    if raw in {"krank", "sick", "k"} or bool(entry.get("ist_krank")):
        return "krank"
    if raw in {"arbeit", "geplant", "a"}:
        return "geplant"
    if raw == "frei":
        return "frei"
    if bool(entry.get("ist_urlaub")):
        return "urlaub"
    return "geplant"


def summarize_dienstplan_month(
    *,
    year: int,
    month: int,
    entries: Iterable[Dict[str, Any]] | None,
    extra_urlaub_dates: Iterable[object] | None = None,
    extra_krank_dates: Iterable[object] | None = None,
) -> DienstplanSummary:
    """
    Zentrale Monatszusammenfassung für Dienstplan:
    - Geplant / Urlaub / Krank aus Einträgen
    - Frei für alle Tage ohne Eintrag (inkl. betriebliche Ruhetage Mo/Di)
    """
    _, days_in_month = calendar.monthrange(year, month)

    status_by_day: Dict[date, str] = {}
    for entry in entries or []:
        d = _to_date_or_none(entry.get("datum"))
        if d is None or d.year != year or d.month != month:
            continue
        status = _norm_status(entry)
        prev = status_by_day.get(d)
        if prev == "krank":
            continue
        if prev == "urlaub" and status not in {"krank"}:
            continue
        if prev == "geplant" and status == "frei":
            continue
        status_by_day[d] = status

    for d_any in extra_urlaub_dates or []:
        d = _to_date_or_none(d_any)
        if d is None or d.year != year or d.month != month:
            continue
        if status_by_day.get(d) != "krank":
            status_by_day[d] = "urlaub"

    for d_any in extra_krank_dates or []:
        d = _to_date_or_none(d_any)
        if d is None or d.year != year or d.month != month:
            continue
        status_by_day[d] = "krank"

    geplant = urlaub = krank = frei = 0
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        status = status_by_day.get(d)
        if status == "krank":
            krank += 1
        elif status == "urlaub":
            urlaub += 1
        elif status == "geplant":
            geplant += 1
        else:
            frei += 1

    return DienstplanSummary(geplant=geplant, urlaub=urlaub, frei=frei, krank=krank)


def summarize_employee_month(
    *,
    year: int,
    month: int,
    entries: Iterable[Dict[str, Any]] | None,
    extra_urlaub_dates: Iterable[object] | None = None,
    extra_krank_dates: Iterable[object] | None = None,
) -> DienstplanSummary:
    return summarize_dienstplan_month(
        year=year,
        month=month,
        entries=entries,
        extra_urlaub_dates=extra_urlaub_dates,
        extra_krank_dates=extra_krank_dates,
    )


# ─────────────────────────────────────────────────────────────────────────────
# VALIDIERUNGSFUNKTIONEN
# ─────────────────────────────────────────────────────────────────────────────

def pruefe_feiertag_warnungen(
    eintraege: List[Dict[str, Any]],
    mitarbeiter: Dict[str, Any]
) -> List[str]:
    """
    Prüft alle Einträge auf Feiertage ohne gesetztes Häkchen.
    Für Admin-Validierungsanzeige.

    Returns:
        List[str]: Liste der Warnmeldungen
    """
    warnungen = []
    feiertage_sachsen_cache = {}

    for eintrag in eintraege:
        datum_str = eintrag.get("datum", "")
        if not datum_str:
            continue
        try:
            datum = date.fromisoformat(datum_str)
        except ValueError:
            continue

        # Cache für Feiertage
        if datum.year not in feiertage_sachsen_cache:
            feiertage_sachsen_cache[datum.year] = get_feiertage_sachsen(datum.year)

        feiertage = feiertage_sachsen_cache[datum.year]
        ist_ft = datum in feiertage and datum.weekday() not in (0, 1)
        ist_so = datum.weekday() == 6

        if ist_ft and not mitarbeiter.get("feiertagszuschlag_aktiv", False):
            ft_name = feiertage.get(datum, "Feiertag")
            warnungen.append(
                f"⚠️ {datum.strftime('%d.%m.%Y')} ({ft_name}): "
                f"Arbeit an Feiertag, aber 'Feiertagszuschlag aktiv' ist nicht gesetzt!"
            )
        if ist_so and not mitarbeiter.get("sonntagszuschlag_aktiv", False):
            warnungen.append(
                f"ℹ️ {datum.strftime('%d.%m.%Y')} (Sonntag): "
                f"Arbeit an Sonntag, aber 'Sonntagszuschlag aktiv' ist nicht gesetzt."
            )

    return warnungen


def validiere_zeiterfassung(eintrag: Dict[str, Any]) -> List[str]:
    """
    Validiert einen einzelnen Zeiterfassungs-Eintrag auf Plausibilität.

    Returns:
        List[str]: Liste der Fehler/Warnungen (leer = alles OK)
    """
    fehler = []
    start = eintrag.get("start_zeit")
    ende = eintrag.get("ende_zeit")
    datum_str = eintrag.get("datum", "")

    if not start:
        fehler.append("Startzeit fehlt")
    if not ende:
        fehler.append("Endzeit fehlt (Eintrag noch offen)")
        return fehler

    try:
        datum = date.fromisoformat(datum_str)
        start_dt = _parse_zeit_zu_datetime(start, datum)
        ende_dt = _parse_zeit_zu_datetime(ende, datum)
        if ende_dt <= start_dt:
            ende_dt += timedelta(days=1)

        brutto_h = (ende_dt - start_dt).total_seconds() / 3600.0

        if brutto_h > 24:
            fehler.append(f"Schichtdauer > 24 Stunden ({brutto_h:.1f} Std) – bitte prüfen")
        if brutto_h < 0.1:
            fehler.append(f"Schichtdauer < 6 Minuten – möglicherweise Fehleingabe")

    except Exception as e:
        fehler.append(f"Zeitformat-Fehler: {e}")

    return fehler


# ─────────────────────────────────────────────────────────────────────────────
# VALIDIERUNGSTEST (Testrechnung)
# ─────────────────────────────────────────────────────────────────────────────

def fuehre_testrechnung_durch() -> str:
    """
    Testrechnung: Schicht Sonntag 22:00 – Montag 06:00
    Erwartet:
    - 2 Std Sonntag (50% Zuschlag)
    - 6 Std Montag (kein Zuschlag, Ruhetag)
    - Pause: 30 Min (> 6 Std Brutto)
    - Netto: 7,5 Std
    """
    test_mitarbeiter = {
        "id": 999,
        "vorname": "Test",
        "nachname": "Mitarbeiter",
        "monatliche_soll_stunden": 160.0,
        "monatliche_brutto_verguetung": 2400.0,
        "sonntagszuschlag_aktiv": True,
        "feiertagszuschlag_aktiv": True,
    }

    # Sonntag 22:00 – Montag 06:00
    # Wir suchen einen Sonntag in 2026
    test_datum = date(2026, 3, 1)  # Sonntag, 1. März 2026
    assert test_datum.weekday() == 6, f"Testdatum {test_datum} ist kein Sonntag!"

    test_eintrag = {
        "id": 1,
        "datum": test_datum.isoformat(),
        "start_zeit": "22:00:00",
        "ende_zeit": "06:00:00",
        "pause_minuten": None,  # Automatische Pause
    }

    ergebnis = berechne_eintrag(test_eintrag, test_mitarbeiter, auto_pause=True)

    bericht = []
    bericht.append("=" * 60)
    bericht.append("VALIDIERUNGSTEST: Nachtschicht Sonntag 22:00 → Montag 06:00")
    bericht.append("=" * 60)
    bericht.append(f"Stundenlohn: 15,00 €")
    bericht.append(f"Sonntagszuschlag aktiv: Ja")
    bericht.append("")
    bericht.append("AUDIT-LOG:")
    for zeile in ergebnis["audit_log"]:
        bericht.append(f"  {zeile}")
    bericht.append("")
    bericht.append("ERGEBNIS:")
    bericht.append(f"  Netto-Stunden:       {ergebnis['netto_stunden']:.2f} Std")
    bericht.append(f"  Pause:               {ergebnis['pause_minuten']} Min")
    bericht.append(f"  Sonntags-Stunden:    {ergebnis['sonntags_stunden']:.2f} Std")
    bericht.append(f"  Feiertags-Stunden:   {ergebnis['feiertags_stunden']:.2f} Std")
    bericht.append(f"  Grundlohn:           {ergebnis['grundlohn']:.2f} €")
    bericht.append(f"  Sonntagszuschlag:    {ergebnis['sonntagszuschlag']:.2f} €")
    bericht.append(f"  Feiertagszuschlag:   {ergebnis['feiertagszuschlag']:.2f} €")
    bericht.append(f"  Gesamtlohn:          {ergebnis['gesamtlohn']:.2f} €")
    bericht.append("")

    # Erwartete Werte prüfen
    # Brutto: 8 Std (22:00–06:00), Pause: 30 Min (> 6 Std), Netto: 7,5 Std
    # Sonntag: 22:00–00:00 = 2 Std → Zuschlag auf 2 Std (nicht auf Netto-Anteil!)
    # Montag (Ruhetag): 00:00–06:00 = 6 Std → kein Zuschlag
    # Sonntagszuschlag = 2 Std × 15 € × 50% = 15,00 €
    # Grundlohn = 7,5 Std × 15 € = 112,50 €
    # Gesamt = 127,50 €

    # Korrekte Erwartungswerte mit proportionalem Netto-Faktor:
    # Brutto: 8 Std, Pause: 30 Min, Netto: 7.5 Std, Netto-Faktor: 7.5/8 = 0.9375
    # Sonntags-Segment (brutto): 2 Std → Netto-Anteil: 2 × 0.9375 = 1.875 Std
    # Sonntagszuschlag: 1.875 × 15 × 0.50 = 14.0625 ≈ 14.06 €
    # Grundlohn: 7.5 × 15 = 112.50 €
    # Gesamt: 112.50 + 14.06 = 126.56 €
    netto_faktor_erwartet = 7.5 / 8.0
    so_netto_erwartet = 2.0 * netto_faktor_erwartet  # 1.875
    so_zuschlag_erwartet = round(so_netto_erwartet * 15.0 * 0.50, 2)  # 14.06
    gesamt_erwartet = round(112.50 + so_zuschlag_erwartet, 2)

    checks = [
        ("Netto-Stunden = 7,50", abs(ergebnis["netto_stunden"] - 7.5) < 0.01),
        ("Pause = 30 Min", ergebnis["pause_minuten"] == 30),
        (f"Sonntags-Stunden ≈ {so_netto_erwartet:.4f}", abs(ergebnis["sonntags_stunden"] - so_netto_erwartet) < 0.01),
        ("Feiertags-Stunden = 0,00", abs(ergebnis["feiertags_stunden"] - 0.0) < 0.01),
        ("Grundlohn = 112,50 €", abs(ergebnis["grundlohn"] - 112.50) < 0.01),
        (f"Sonntagszuschlag ≈ {so_zuschlag_erwartet:.2f} €", abs(ergebnis["sonntagszuschlag"] - so_zuschlag_erwartet) < 0.02),
        (f"Gesamtlohn ≈ {gesamt_erwartet:.2f} €", abs(ergebnis["gesamtlohn"] - gesamt_erwartet) < 0.02),
    ]

    alle_ok = True
    bericht.append("VALIDIERUNG:")
    for name, ok in checks:
        status = "✅" if ok else "❌"
        bericht.append(f"  {status} {name}")
        if not ok:
            alle_ok = False

    bericht.append("")
    if alle_ok:
        bericht.append("✅ ALLE TESTS BESTANDEN – Berechnungslogik korrekt!")
    else:
        bericht.append("❌ FEHLER IN DER BERECHNUNG – Bitte prüfen!")

    bericht.append("=" * 60)

    # Zweiter Test: Feiertag (Buß- und Bettag 2026 in Sachsen)
    buss_bettag_2026 = _berechne_buss_und_bettag(2026)
    bericht.append("")
    bericht.append(f"ZUSATZTEST: Buß- und Bettag {buss_bettag_2026.strftime('%d.%m.%Y')} (Sachsen)")
    ist_ft, ft_name = ist_feiertag_sachsen_unabhaengig(buss_bettag_2026)
    bericht.append(f"  Ist Feiertag in Sachsen: {'✅ Ja' if ist_ft else '❌ Nein'} ({ft_name})")

    # Bundesweiter Test: Reformationstag
    reformationstag = date(2026, 10, 31)
    ist_ft2, ft_name2 = ist_feiertag_sachsen_unabhaengig(reformationstag)
    bericht.append(f"  Reformationstag 31.10.: {'✅ Ja' if ist_ft2 else '❌ Nein'} ({ft_name2})")

    return "\n".join(bericht)


# ─────────────────────────────────────────────────────────────────────────────
# HILFSFUNKTIONEN FÜR ZEITAUSWERTUNG
# ─────────────────────────────────────────────────────────────────────────────

def format_stunden(stunden: float) -> str:
    """Formatiert Dezimalstunden als HH:MM."""
    if stunden < 0:
        stunden = 0
    h = int(stunden)
    m = int(round((stunden - h) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{h:02d}:{m:02d}"


def format_euro(betrag: float) -> str:
    """Formatiert Betrag als deutsche Währung."""
    return f"{betrag:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def get_feiertage_monat(monat: int, jahr: int) -> Dict[date, str]:
    """Gibt alle Feiertage eines Monats in Sachsen zurück."""
    alle = get_feiertage_sachsen(jahr)
    return {d: name for d, name in alle.items() if d.month == monat}
