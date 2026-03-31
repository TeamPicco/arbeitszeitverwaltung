from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict


@dataclass
class AbsenceResult:
    days: float
    credited_hours: float
    typ: str


def _is_workday(d: date) -> bool:
    # Bestehende Betriebslogik: Montag/Dienstag sind Ruhetage.
    return d.weekday() not in (0, 1)


def workdays_between(start: date, end: date) -> float:
    cur = start
    total = 0.0
    while cur <= end:
        if _is_workday(cur):
            total += 1.0
        cur += timedelta(days=1)
    return total


def calculate_absence_credit(
    typ: str,
    start: date,
    end: date,
    monthly_target_hours: float,
    paid: bool = True,
) -> AbsenceResult:
    days = workdays_between(start, end)
    day_target = (float(monthly_target_hours or 0.0) / 21.65) if monthly_target_hours else 0.0
    hours = round(days * day_target, 2) if paid else 0.0
    return AbsenceResult(days=days, credited_hours=hours, typ=typ)


def store_absence(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    typ: str,
    start: date,
    end: date,
    monthly_target_hours: float,
    attest_pfad: str | None = None,
    grund: str | None = None,
    created_by: int | None = None,
) -> Dict[str, float | str]:
    paid = typ in ("urlaub", "krankheit", "sonderurlaub")
    result = calculate_absence_credit(
        typ=typ,
        start=start,
        end=end,
        monthly_target_hours=monthly_target_hours,
        paid=paid,
    )

    payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "typ": typ,
        "start_datum": start.isoformat(),
        "ende_datum": end.isoformat(),
        "bezahlte_zeit": paid,
        "stunden_gutschrift": result.credited_hours,
        "attest_pfad": attest_pfad,
        "grund": grund,
        "created_by": created_by,
    }
    supabase.table("abwesenheiten").insert(payload).execute()

    # Rückwärtskompatibilität: für bestehende Auswertungen in zeiterfassung spiegeln.
    cur = start
    per_day_credit = round(result.credited_hours / result.days, 2) if result.days else 0.0
    while cur <= end:
        if _is_workday(cur):
            legacy_row = {
                "mitarbeiter_id": mitarbeiter_id,
                "datum": cur.isoformat(),
                "start_zeit": "00:00:00",
                "ende_zeit": "00:00:00",
                "abwesenheitstyp": typ,
                "ist_krank": typ == "krankheit",
                "arbeitsstunden": per_day_credit if paid else 0.0,
                "pause_minuten": 0,
                "quelle": "abwesenheit_system",
                "monat": cur.month,
                "jahr": cur.year,
            }
            supabase.table("zeiterfassung").upsert(
                legacy_row,
                on_conflict="mitarbeiter_id,datum,start_zeit",
            ).execute()
        cur += timedelta(days=1)

    return {
        "tage": result.days,
        "stunden_gutschrift": result.credited_hours,
        "typ": typ,
    }
