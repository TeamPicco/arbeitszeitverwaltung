from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Optional


@dataclass
class WorkAccountSnapshot:
    soll_stunden: float
    ist_stunden: float
    ueberstunden_saldo: float
    urlaubstage_gesamt: float
    urlaubstage_genommen: float
    krankheitstage_gesamt: float


def _daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _is_workday(d: date) -> bool:
    # Betriebslogik der bestehenden App: Mo/Di Ruhetag.
    return d.weekday() not in (0, 1)


def calculate_absence_days(start: date, end: date) -> float:
    return float(sum(1 for d in _daterange(start, end) if _is_workday(d)))


def sync_work_account_for_month(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
) -> WorkAccountSnapshot:
    month_start = date(jahr, monat, 1)
    month_end = date(jahr + (1 if monat == 12 else 0), 1 if monat == 12 else monat + 1, 1) - timedelta(days=1)

    ma_res = supabase.table("mitarbeiter").select(
        "monatliche_soll_stunden, jahres_urlaubstage, resturlaub_vorjahr"
    ).eq("id", mitarbeiter_id).single().execute()
    ma = ma_res.data or {}
    soll_stunden = float(ma.get("monatliche_soll_stunden") or 0.0)
    urlaubstage_gesamt = float(ma.get("jahres_urlaubstage") or 0.0) + float(ma.get("resturlaub_vorjahr") or 0.0)

    zeit_res = (
        supabase.table("zeiterfassung")
        .select("arbeitsstunden, stunden")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .gte("datum", month_start.isoformat())
        .lte("datum", month_end.isoformat())
        .execute()
    )
    ist_stunden = 0.0
    for row in zeit_res.data or []:
        ist_stunden += float(row.get("arbeitsstunden") or row.get("stunden") or 0.0)

    abw_res = (
        supabase.table("abwesenheiten")
        .select("typ, start_datum, ende_datum")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .lte("start_datum", month_end.isoformat())
        .gte("ende_datum", month_start.isoformat())
        .execute()
    )
    urlaub_genommen = 0.0
    krank_tage = 0.0
    for row in abw_res.data or []:
        start = date.fromisoformat(row["start_datum"])
        end = date.fromisoformat(row["ende_datum"])
        overlap_start = max(start, month_start)
        overlap_end = min(end, month_end)
        if overlap_end < overlap_start:
            continue
        tage = calculate_absence_days(overlap_start, overlap_end)
        if row.get("typ") == "urlaub":
            urlaub_genommen += tage
        elif row.get("typ") == "krankheit":
            krank_tage += tage

    diff = round(ist_stunden - soll_stunden, 2)
    konto_res = supabase.table("arbeitszeit_konten").select(
        "ueberstunden_saldo"
    ).eq("mitarbeiter_id", mitarbeiter_id).limit(1).execute()
    alter_saldo = 0.0
    if konto_res.data:
        alter_saldo = float(konto_res.data[0].get("ueberstunden_saldo") or 0.0)
    neuer_saldo = round(alter_saldo + diff, 2)

    payload: Dict[str, float | int] = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "soll_stunden": round(soll_stunden, 2),
        "ist_stunden": round(ist_stunden, 2),
        "ueberstunden_saldo": neuer_saldo,
        "urlaubstage_gesamt": round(urlaubstage_gesamt, 2),
        "urlaubstage_genommen": round(urlaub_genommen, 2),
        "krankheitstage_gesamt": round(krank_tage, 2),
    }
    supabase.table("arbeitszeit_konten").upsert(payload, on_conflict="mitarbeiter_id").execute()

    return WorkAccountSnapshot(
        soll_stunden=round(soll_stunden, 2),
        ist_stunden=round(ist_stunden, 2),
        ueberstunden_saldo=neuer_saldo,
        urlaubstage_gesamt=round(urlaubstage_gesamt, 2),
        urlaubstage_genommen=round(urlaub_genommen, 2),
        krankheitstage_gesamt=round(krank_tage, 2),
    )

