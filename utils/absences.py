from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Optional


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


def _normalize_absence_type(typ: str) -> str:
    normalized = (typ or "").strip().lower()
    if normalized == "krank":
        return "krankheit"
    return normalized


def _candidate_db_types(normalized_typ: str) -> list[str]:
    # Legacy-Instanzen akzeptieren teils "krank" statt "krankheit".
    if normalized_typ == "krankheit":
        return ["krankheit", "krank"]
    return [normalized_typ]


def _is_not_null_datum_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "datum" in msg and ("not-null" in msg or "not null" in msg or "23502" in msg)


def _is_typ_check_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "abwesenheiten_typ_check" in msg or ("23514" in msg and "typ" in msg)


def _parse_iso_date(value) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _mirror_absence_into_legacy(
    supabase,
    *,
    mitarbeiter_id: int,
    typ: str,
    start: date,
    end: date,
    paid: bool,
    credited_hours: float,
) -> None:
    cur = start
    days = workdays_between(start, end)
    per_day_credit = round(credited_hours / days, 2) if days else 0.0
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


def _remove_legacy_absence_mirror(
    supabase,
    *,
    mitarbeiter_id: int,
    start: date,
    end: date,
) -> None:
    try:
        (
            supabase.table("zeiterfassung")
            .delete()
            .eq("mitarbeiter_id", mitarbeiter_id)
            .eq("quelle", "abwesenheit_system")
            .gte("datum", start.isoformat())
            .lte("datum", end.isoformat())
            .execute()
        )
    except Exception:
        # Legacy-Instanzen können eingeschränkte Filter/Spalten haben.
        pass


def _write_absence_audit_log(
    supabase,
    *,
    event_type: str,
    betrieb_id: int,
    mitarbeiter_id: int,
    user_id: int | None,
    entity_id: int,
    before_data: dict | None,
    after_data: dict | None,
    reason: str,
) -> None:
    try:
        supabase.table("audit_logs").insert(
            {
                "betrieb_id": betrieb_id,
                "mitarbeiter_id": mitarbeiter_id,
                "user_id": user_id,
                "event_type": event_type,
                "entity": "abwesenheiten",
                "entity_id": str(entity_id),
                "before_data": before_data,
                "after_data": after_data,
                "reason": reason,
            }
        ).execute()
    except Exception:
        # Audit-Log darf den eigentlichen Workflow nicht blockieren.
        pass


def _load_absence_by_id(supabase, absence_id: int) -> dict | None:
    res = supabase.table("abwesenheiten").select("*").eq("id", absence_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def _insert_absence_compat(supabase, base_payload: dict, start: date) -> str:
    attempts: list[dict] = []
    for db_typ in _candidate_db_types(base_payload["typ"]):
        payload = {**base_payload, "typ": db_typ}
        attempts.append(payload)
        attempts.append({**payload, "datum": start.isoformat()})

    last_exc: Exception | None = None
    for idx, payload in enumerate(attempts):
        try:
            supabase.table("abwesenheiten").insert(payload).execute()
            return str(payload["typ"])
        except Exception as exc:
            last_exc = exc
            has_next = idx < len(attempts) - 1
            if has_next and (_is_not_null_datum_error(exc) or _is_typ_check_error(exc)):
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("Abwesenheit konnte nicht gespeichert werden.")


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
    normalized_typ = _normalize_absence_type(typ)
    paid = normalized_typ in ("urlaub", "krankheit", "sonderurlaub")
    result = calculate_absence_credit(
        typ=normalized_typ,
        start=start,
        end=end,
        monthly_target_hours=monthly_target_hours,
        paid=paid,
    )

    payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "typ": normalized_typ,
        "start_datum": start.isoformat(),
        "ende_datum": end.isoformat(),
        "bezahlte_zeit": paid,
        "stunden_gutschrift": result.credited_hours,
        "attest_pfad": attest_pfad,
        "grund": grund,
        "created_by": created_by,
    }
    _insert_absence_compat(supabase, payload, start)

    # Rückwärtskompatibilität: für bestehende Auswertungen in zeiterfassung spiegeln.
    _mirror_absence_into_legacy(
        supabase,
        mitarbeiter_id=mitarbeiter_id,
        typ=normalized_typ,
        start=start,
        end=end,
        paid=paid,
        credited_hours=result.credited_hours,
    )

    return {
        "tage": result.days,
        "stunden_gutschrift": result.credited_hours,
        "typ": normalized_typ,
    }


def update_absence(
    supabase,
    *,
    absence_id: int,
    typ: str,
    start: date,
    end: date,
    monthly_target_hours: float,
    change_reason: str,
    changed_by: int | None = None,
    attest_pfad: str | None = None,
    grund: str | None = None,
) -> Dict[str, float | str]:
    reason = (change_reason or "").strip()
    if not reason:
        raise ValueError("Begründungskommentar ist erforderlich.")

    current = _load_absence_by_id(supabase, absence_id)
    if not current:
        raise ValueError("Abwesenheit nicht gefunden.")

    normalized_typ = _normalize_absence_type(typ)
    paid = normalized_typ in ("urlaub", "krankheit", "sonderurlaub")
    result = calculate_absence_credit(
        typ=normalized_typ,
        start=start,
        end=end,
        monthly_target_hours=monthly_target_hours,
        paid=paid,
    )

    old_start = _parse_iso_date(current.get("start_datum") or current.get("datum")) or start
    old_end = _parse_iso_date(current.get("ende_datum") or current.get("datum")) or old_start
    mitarbeiter_id = int(current.get("mitarbeiter_id"))
    betrieb_id = int(current.get("betrieb_id") or 0)

    attempts = []
    for db_typ in _candidate_db_types(normalized_typ):
        payload = {
            "typ": db_typ,
            "start_datum": start.isoformat(),
            "ende_datum": end.isoformat(),
            "bezahlte_zeit": paid,
            "stunden_gutschrift": result.credited_hours,
            "attest_pfad": attest_pfad,
            "grund": grund,
        }
        attempts.append(payload)
        attempts.append({**payload, "datum": start.isoformat()})

    last_exc: Exception | None = None
    for idx, payload in enumerate(attempts):
        try:
            supabase.table("abwesenheiten").update(payload).eq("id", absence_id).execute()
            break
        except Exception as exc:
            last_exc = exc
            has_next = idx < len(attempts) - 1
            if has_next and (_is_not_null_datum_error(exc) or _is_typ_check_error(exc)):
                continue
            raise
    else:
        if last_exc:
            raise last_exc

    _remove_legacy_absence_mirror(
        supabase,
        mitarbeiter_id=mitarbeiter_id,
        start=old_start,
        end=old_end,
    )
    _mirror_absence_into_legacy(
        supabase,
        mitarbeiter_id=mitarbeiter_id,
        typ=normalized_typ,
        start=start,
        end=end,
        paid=paid,
        credited_hours=result.credited_hours,
    )

    updated = _load_absence_by_id(supabase, absence_id)
    _write_absence_audit_log(
        supabase,
        event_type="absence_updated",
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter_id,
        user_id=changed_by,
        entity_id=absence_id,
        before_data=current,
        after_data=updated,
        reason=reason,
    )

    return {
        "tage": result.days,
        "stunden_gutschrift": result.credited_hours,
        "typ": normalized_typ,
    }


def delete_absence(
    supabase,
    *,
    absence_id: int,
    delete_reason: str,
    deleted_by: int | None = None,
) -> Dict[str, bool]:
    reason = (delete_reason or "").strip()
    if not reason:
        raise ValueError("Begründungskommentar ist erforderlich.")

    current = _load_absence_by_id(supabase, absence_id)
    if not current:
        raise ValueError("Abwesenheit nicht gefunden.")

    mitarbeiter_id = int(current.get("mitarbeiter_id"))
    betrieb_id = int(current.get("betrieb_id") or 0)
    start = _parse_iso_date(current.get("start_datum") or current.get("datum")) or date.today()
    end = _parse_iso_date(current.get("ende_datum") or current.get("datum")) or start

    supabase.table("abwesenheiten").delete().eq("id", absence_id).execute()
    _remove_legacy_absence_mirror(
        supabase,
        mitarbeiter_id=mitarbeiter_id,
        start=start,
        end=end,
    )
    _write_absence_audit_log(
        supabase,
        event_type="absence_deleted",
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter_id,
        user_id=deleted_by,
        entity_id=absence_id,
        before_data=current,
        after_data=None,
        reason=reason,
    )
    return {"deleted": True}
