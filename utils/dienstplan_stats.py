from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import calendar
from typing import Iterable


@dataclass(frozen=True)
class DienstplanSummary:
    geplant: int
    urlaub: int
    frei: int
    krank: int


def _to_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        try:
            return date.fromisoformat(raw[:10])
        except Exception:
            return None
    return None


def summarize_employee_month(
    *,
    year: int,
    month: int,
    entries: Iterable[dict],
    extra_urlaub_dates: Iterable[str] | None = None,
    extra_krank_dates: Iterable[str] | None = None,
) -> DienstplanSummary:
    """
    Ermittelt Monats-Summary pro Mitarbeiter nach einheitlicher Regel:
    - Geplant: mindestens ein Arbeitsdienst
    - Urlaub: Urlaubseintrag (oder extra_urlaub_dates)
    - Krank: Krankheitseintrag (oder extra_krank_dates)
    - Frei: weder Geplant noch Urlaub noch Krank (inkl. Ruhetage ohne Eintrag)
    """
    tags: dict[date, set[str]] = {}

    for entry in entries or []:
        d = _to_date(entry.get("datum"))
        if not d or d.year != year or d.month != month:
            continue
        schichttyp = str(entry.get("schichttyp") or "arbeit").strip().lower()
        if schichttyp not in {"arbeit", "urlaub", "krank", "frei"}:
            schichttyp = "arbeit"
        tags.setdefault(d, set()).add(schichttyp)

    for iso in extra_urlaub_dates or []:
        d = _to_date(iso)
        if d and d.year == year and d.month == month:
            tags.setdefault(d, set()).add("urlaub")

    for iso in extra_krank_dates or []:
        d = _to_date(iso)
        if d and d.year == year and d.month == month:
            tags.setdefault(d, set()).add("krank")

    geplant = 0
    urlaub = 0
    krank = 0
    frei = 0
    days_in_month = calendar.monthrange(year, month)[1]
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        day_types = tags.get(d, set())
        if "krank" in day_types:
            krank += 1
        elif "urlaub" in day_types:
            urlaub += 1
        elif "arbeit" in day_types:
            geplant += 1
        else:
            frei += 1

    return DienstplanSummary(geplant=geplant, urlaub=urlaub, frei=frei, krank=krank)
