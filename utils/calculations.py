from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Dict, Tuple

try:
    import holidays
except Exception:  # pragma: no cover
    holidays = None


MONATE_DE = [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]

WOCHENTAGE_DE = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]


def get_monatsnamen(monat: int) -> str:
    return MONATE_DE[monat - 1] if 1 <= monat <= 12 else ""


def get_wochentag(datum: date) -> str:
    if not isinstance(datum, date):
        return ""
    return WOCHENTAGE_DE[datum.weekday()]


def parse_zeit(zeitwert) -> Tuple[time, bool]:
    """
    Parse Zeitwerte in (time, naechster_tag).

    Unterstützt:
    - datetime.time
    - "HH:MM"
    - "HH:MM:SS"
    - "24:xx" (wird als 00:xx am nächsten Tag interpretiert)
    """
    if isinstance(zeitwert, time):
        return zeitwert, False

    if zeitwert is None:
        return time(0, 0), False

    text = str(zeitwert).strip()
    if not text:
        return time(0, 0), False

    teil = text[:8]
    parts = teil.split(":")
    try:
        stunde = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        sekunde = int(parts[2]) if len(parts) > 2 else 0
    except Exception:
        return time(0, 0), False

    naechster_tag = stunde >= 24
    if naechster_tag:
        stunde = stunde % 24
    return time(stunde, minute, sekunde), naechster_tag


def berechne_arbeitsstunden(
    start_zeit: time, ende_zeit: time, pause_minuten: int = 0, naechster_tag: bool = False
) -> float:
    """Berechnet Netto-Arbeitsstunden aus Zeiten und Pause."""
    basis = date.today()
    start_dt = datetime.combine(basis, start_zeit)
    ende_dt = datetime.combine(basis, ende_zeit)

    if naechster_tag or ende_dt <= start_dt:
        ende_dt += timedelta(days=1)

    brutto_minuten = (ende_dt - start_dt).total_seconds() / 60.0
    netto_minuten = max(0.0, brutto_minuten - float(pause_minuten or 0))
    return round(netto_minuten / 60.0, 4)


def berechne_arbeitsstunden_mit_pause(start_zeit: time, ende_zeit: time) -> Tuple[float, int]:
    """
    Berechnet Brutto-Stunden plus gesetzliche Mindestpause (§ 4 ArbZG).
    """
    brutto_h = berechne_arbeitsstunden(start_zeit, ende_zeit, pause_minuten=0)
    if brutto_h > 9:
        pause = 45
    elif brutto_h > 6:
        pause = 30
    else:
        pause = 0
    return round(brutto_h, 4), pause


def berechne_grundlohn(stundenlohn: float, stunden: float) -> float:
    return round(float(stundenlohn or 0) * float(stunden or 0), 2)


def berechne_sonntagszuschlag(stundenlohn: float, sonntagsstunden: float) -> float:
    return round(float(stundenlohn or 0) * float(sonntagsstunden or 0) * 0.5, 2)


def berechne_feiertagszuschlag(stundenlohn: float, feiertagsstunden: float) -> float:
    return round(float(stundenlohn or 0) * float(feiertagsstunden or 0) * 1.0, 2)


def berechne_gesamtlohn(grundlohn: float, sonntagszuschlag: float, feiertagszuschlag: float) -> float:
    return round(float(grundlohn or 0) + float(sonntagszuschlag or 0) + float(feiertagszuschlag or 0), 2)


def format_waehrung(betrag: float) -> str:
    return f"{float(betrag or 0):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def format_stunden(stunden: float) -> str:
    """
    Formatiert Dezimalstunden als ``HH:MM``.

    Negative Werte werden auf ``00:00`` geklemmt. Für Saldo-Anzeigen mit
    Vorzeichen ist :func:`utils.azk.h_zu_hhmm` vorgesehen.
    """
    value = float(stunden or 0)
    if value < 0:
        value = 0.0
    h = int(value)
    m = int(round((value - h) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{h:02d}:{m:02d}"


def get_german_holidays(jahr: int, bundesland: str = "SN") -> Dict[date, str]:
    if holidays is None:
        return {}
    try:
        return dict(holidays.Germany(years=jahr, subdiv=bundesland))
    except Exception:
        return {}


def is_sonntag(datum: date) -> bool:
    return isinstance(datum, date) and datum.weekday() == 6


def is_feiertag(datum: date, bundesland: str = "SN") -> bool:
    """
    Feiertagsprüfung für den Betrieb.
    Montag/Dienstag gelten hier als betriebliche Ruhetage und nicht als Zuschlagstag.
    """
    if not isinstance(datum, date):
        return False
    if datum.weekday() in (0, 1):
        return False
    feiertage = get_german_holidays(datum.year, bundesland=bundesland)
    return datum in feiertage


def berechne_urlaubstage(von_datum: date, bis_datum: date) -> float:
    if not isinstance(von_datum, date) or not isinstance(bis_datum, date) or bis_datum < von_datum:
        return 0.0
    tage = 0.0
    aktuell = von_datum
    while aktuell <= bis_datum:
        if aktuell.weekday() not in (0, 1):
            tage += 1.0
        aktuell += timedelta(days=1)
    return tage


def _row_stunden(row: dict) -> float:
    return float(row.get("arbeitsstunden") or row.get("stunden") or 0.0)


def erstelle_zeitraum_auswertung(mitarbeiter_id, start_datum, end_datum, supabase):
    """Erstellt einen täglichen Soll/Ist/Saldo-Bericht für den Zeitraum."""
    # Lazy-Import: pandas wird nur für diese Auswertung benötigt.
    import pandas as pd

    if isinstance(start_datum, datetime):
        start_datum = start_datum.date()
    if isinstance(end_datum, datetime):
        end_datum = end_datum.date()

    ma_res = (
        supabase.table("mitarbeiter")
        .select("monatliche_soll_stunden, soll_stunden_monat")
        .eq("id", mitarbeiter_id)
        .single()
        .execute()
    )
    ma_data = ma_res.data or {}
    soll_monat = float(ma_data.get("monatliche_soll_stunden") or ma_data.get("soll_stunden_monat") or 160.0)

    # Arbeitstage im Zeitraum (ohne Mo/Di Ruhetage)
    arbeitstage_im_zeitraum = sum(
        1 for n in range((end_datum - start_datum).days + 1)
        if (start_datum + timedelta(days=n)).weekday() not in (0, 1)
    )
    # Arbeitstage im vollen Monat für Verhältnisberechnung
    from calendar import monthrange
    monat_start = start_datum.replace(day=1)
    monat_ende = start_datum.replace(day=monthrange(start_datum.year, start_datum.month)[1])
    arbeitstage_monat = sum(
        1 for n in range((monat_ende - monat_start).days + 1)
        if (monat_start + timedelta(days=n)).weekday() not in (0, 1)
    )
    soll_tag = (soll_monat / arbeitstage_monat) if arbeitstage_monat > 0 else 0.0

    ist_res = (
        supabase.table("zeiterfassung")
        .select("datum, arbeitsstunden, stunden")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .gte("datum", start_datum.isoformat())
        .lte("datum", end_datum.isoformat())
        .execute()
    )

    ist_map: Dict[str, float] = {}
    for row in ist_res.data or []:
        key = row.get("datum")
        if not key:
            continue
        ist_map[key] = ist_map.get(key, 0.0) + _row_stunden(row)

    auswertung = []
    lauf_saldo = 0.0
    aktuell = start_datum
    while aktuell <= end_datum:
        ist = float(ist_map.get(aktuell.isoformat(), 0.0))
        tages_saldo = ist - soll_tag
        lauf_saldo += tages_saldo
        auswertung.append(
            {
                "Datum": aktuell.strftime("%d.%m.%Y"),
                "Soll": round(soll_tag, 2),
                "Ist": round(ist, 2),
                "Saldo": round(tages_saldo, 2),
                "laufender Saldo": round(lauf_saldo, 2),
            }
        )
        aktuell += timedelta(days=1)

    return pd.DataFrame(auswertung)
