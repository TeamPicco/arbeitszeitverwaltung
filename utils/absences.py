from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Optional


@dataclass
class AbsenceResult:
    days: float
    credited_hours: float
    typ: str


ABSENCE_TYPE_LABELS: dict[str, str] = {
    "krankheit": "Krank",
    "urlaub": "Urlaub",
    "unbezahlter_urlaub": "Unbezahlter Urlaub",
    "sonderurlaub": "Sonderurlaub",
}

DEFAULT_ABSENCE_PAYMENT_RULES: dict[str, bool] = {
    "krankheit": True,
    "urlaub": True,
    "unbezahlter_urlaub": False,
    "sonderurlaub": True,
}


def get_absence_type_options() -> list[str]:
    """Relevante Typen für die UI (erweiterbar)."""
    return ["krankheit", "urlaub", "unbezahlter_urlaub"]


def get_absence_type_label(absence_type: str) -> str:
    raw = str(absence_type or "").strip().lower()
    return ABSENCE_TYPE_LABELS.get(raw, raw or "-")


def resolve_absence_payment_rules(supabase, betrieb_id: int | None) -> dict[str, bool]:
    """
    Lädt konfigurierbare Bezahl-Logik pro Abwesenheitstyp.
    Fallback auf rechtssichere Defaults bei fehlender Tabelle/Schema.
    """
    rules = dict(DEFAULT_ABSENCE_PAYMENT_RULES)
    if betrieb_id is None:
        return rules
    try:
        res = (
            supabase.table("betrieb_absence_rules")
            .select("typ, ist_bezahlt")
            .eq("betrieb_id", int(betrieb_id))
            .execute()
        )
        for row in res.data or []:
            typ = _normalize_absence_type(row.get("typ"))
            if not typ:
                continue
            if row.get("ist_bezahlt") is None:
                continue
            rules[typ] = bool(row.get("ist_bezahlt"))
    except Exception:
        pass
    return rules


def save_absence_payment_rules(
    supabase,
    *,
    betrieb_id: int,
    rules: dict[str, bool],
    changed_by: int | None = None,
) -> tuple[bool, str]:
    """
    Persistiert Bezahl-Regeln je Typ.
    """
    try:
        payload = []
        now_iso = datetime.utcnow().isoformat()
        for typ, bezahlt in (rules or {}).items():
            n_typ = _normalize_absence_type(typ)
            if not n_typ:
                continue
            payload.append(
                {
                    "betrieb_id": int(betrieb_id),
                    "typ": n_typ,
                    "ist_bezahlt": bool(bezahlt),
                    "updated_by": changed_by,
                    "updated_at": now_iso,
                }
            )
        if not payload:
            return False, "Keine gültigen Regelwerte."
        supabase.table("betrieb_absence_rules").upsert(payload, on_conflict="betrieb_id,typ").execute()
        return True, "Regeln gespeichert."
    except Exception as exc:
        return False, f"Regeln konnten nicht gespeichert werden: {exc}"


def is_absence_paid(absence_type: str, rules: dict[str, bool] | None = None) -> bool:
    n_typ = _normalize_absence_type(absence_type)
    merged = dict(DEFAULT_ABSENCE_PAYMENT_RULES)
    if rules:
        for k, v in rules.items():
            merged[_normalize_absence_type(k)] = bool(v)
    return bool(merged.get(n_typ, False))


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except Exception:
        return float(default)


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


def _month_bounds(day: date) -> tuple[date, date]:
    start = date(day.year, day.month, 1)
    end = date(
        day.year + (1 if day.month == 12 else 0),
        1 if day.month == 12 else day.month + 1,
        1,
    ) - timedelta(days=1)
    return start, end


def _month_workdays(day: date) -> int:
    start, end = _month_bounds(day)
    return int(workdays_between(start, end))


def _monthly_target_to_daily_hours(*, monthly_target_hours: float, reference_day: date) -> float:
    """
    Öffentlicher Helper für Tests/Validierung:
    Tagesziel = Monats-Soll / tatsächliche Arbeitstage im Referenzmonat.
    """
    workdays = _month_workdays(reference_day)
    if workdays <= 0:
        return 0.0
    return round(_to_float(monthly_target_hours, 0.0) / float(workdays), 4)


def _load_default_monthly_target_hours(supabase, mitarbeiter_id: int, fallback: float) -> float:
    try:
        res = (
            supabase.table("mitarbeiter")
            .select("monatliche_soll_stunden")
            .eq("id", mitarbeiter_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if rows:
            db_val = _to_float((rows[0] or {}).get("monatliche_soll_stunden"), 0.0)
            if db_val > 0:
                return db_val
    except Exception:
        pass
    return _to_float(fallback, 0.0)


def _load_contract_rows(supabase, mitarbeiter_id: int) -> list[dict]:
    try:
        res = (
            supabase.table("vertraege")
            .select(
                "gueltig_ab,gueltig_bis,soll_stunden_monat,wochenstunden,"
                "arbeitstage_pro_woche,wochenarbeitstage"
            )
            .eq("mitarbeiter_id", mitarbeiter_id)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def _resolve_workdays_per_week(contract: dict) -> float:
    for key in ("arbeitstage_pro_woche", "wochenarbeitstage"):
        try:
            v = float(contract.get(key) or 0.0)
            if 0.0 < v <= 6.0:
                return v
        except Exception:
            continue
    return 5.0


def _contract_active_on(contract: dict, day: date) -> bool:
    try:
        start = date.fromisoformat(str(contract.get("gueltig_ab")))
    except Exception:
        return False
    end_raw = contract.get("gueltig_bis")
    if not end_raw:
        return day >= start
    try:
        end = date.fromisoformat(str(end_raw))
    except Exception:
        return day >= start
    return start <= day <= end


def _resolve_daily_target_for_date(day: date, fallback_monthly_target: float, contract_rows: list[dict]) -> float:
    month_workdays = _month_workdays(day)
    if month_workdays <= 0:
        return 0.0

    active_contracts = [c for c in (contract_rows or []) if _contract_active_on(c, day)]
    active_contracts = sorted(active_contracts, key=lambda c: str(c.get("gueltig_ab") or ""), reverse=True)
    active = active_contracts[0] if active_contracts else None

    fallback_daily = _to_float(fallback_monthly_target) / float(month_workdays)
    if not active:
        return round(fallback_daily, 4)

    soll_monat = _to_float(active.get("soll_stunden_monat"), 0.0)
    if soll_monat > 0:
        return round(soll_monat / float(month_workdays), 4)

    wochenstunden = _to_float(active.get("wochenstunden"), 0.0)
    if wochenstunden > 0:
        workdays_per_week = _resolve_workdays_per_week(active)
        return round(wochenstunden / float(workdays_per_week), 4)

    return round(fallback_daily, 4)


def _calculate_daily_credit_map(
    *,
    start: date,
    end: date,
    paid: bool,
    fallback_monthly_target: float,
    contract_rows: list[dict],
) -> Dict[str, float]:
    daily: Dict[str, float] = {}
    cur = start
    while cur <= end:
        if _is_workday(cur):
            credit = 0.0
            if paid:
                credit = _resolve_daily_target_for_date(cur, fallback_monthly_target, contract_rows)
            daily[cur.isoformat()] = round(float(credit), 2)
        cur += timedelta(days=1)
    return daily


def calculate_absence_credit(
    typ: str,
    start: date,
    end: date,
    monthly_target_hours: float,
    paid: bool = True,
) -> AbsenceResult:
    # Fallback-Berechnung ohne Vertragskontext:
    # Tagessoll wird monatsgenau aus Sollstunden / tatsächlichen Arbeitstagen ermittelt.
    daily_map = _calculate_daily_credit_map(
        start=start,
        end=end,
        paid=paid,
        fallback_monthly_target=_to_float(monthly_target_hours, 0.0),
        contract_rows=[],
    )
    days = float(len(daily_map))
    hours = round(sum(daily_map.values()), 2)
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
    daily_credit_map: Dict[str, float] | None = None,
) -> None:
    cur = start
    days = workdays_between(start, end)
    per_day_credit_default = round(credited_hours / days, 2) if days else 0.0
    while cur <= end:
        if _is_workday(cur):
            iso = cur.isoformat()
            per_day_credit = float((daily_credit_map or {}).get(iso, per_day_credit_default))
            legacy_row = {
                "mitarbeiter_id": mitarbeiter_id,
                "datum": iso,
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


def _safe_date(value) -> Optional[date]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def _coerce_existing_absence_history(rows: list[dict]) -> list[dict]:
    history: list[dict] = []
    for r in rows or []:
        s = _safe_date((r or {}).get("start_datum") or (r or {}).get("datum"))
        e = _safe_date((r or {}).get("ende_datum") or (r or {}).get("datum")) or s
        if s is None:
            continue
        if e is None or e < s:
            e = s
        grund_raw = str((r or {}).get("grund") or "").strip()
        diag_from_grund = None
        if "diag:" in grund_raw.lower():
            try:
                diag_from_grund = grund_raw.split("diag:", 1)[1].strip()
            except Exception:
                diag_from_grund = None
        history.append(
            {
                "start_datum": s.isoformat(),
                "ende_datum": e.isoformat(),
                "diagnose": diag_from_grund or (r or {}).get("diagnose"),
                "diagnose_schluessel": diag_from_grund or (r or {}).get("diagnose_schluessel"),
                "diagnose_code": (r or {}).get("diagnose_code"),
                "icd10": (r or {}).get("icd10"),
            }
        )
    return history


def _load_existing_sick_episodes_same_diagnosis(
    supabase,
    *,
    mitarbeiter_id: int,
    current_absence_id: int | None = None,
) -> list[dict]:
    select_variants = [
        "id,typ,start_datum,ende_datum,grund,diagnose,diagnose_schluessel,diagnose_code,icd10",
        "id,typ,start_datum,ende_datum,grund",
        "id,typ,start_datum,ende_datum,diagnose",
        "id,typ,start_datum,ende_datum",
    ]
    for cols in select_variants:
        try:
            res = (
                supabase.table("abwesenheiten")
                .select(cols)
                .eq("mitarbeiter_id", mitarbeiter_id)
                .execute()
            )
            rows = res.data or []
            if current_absence_id is not None:
                rows = [r for r in rows if int(r.get("id") or 0) != int(current_absence_id)]
            rows = [r for r in rows if str(r.get("typ") or "").strip().lower() in {"krankheit", "krank"}]
            return _coerce_existing_absence_history(rows)
        except Exception:
            continue
    return []


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
    fallback_monthly_target = _load_default_monthly_target_hours(supabase, mitarbeiter_id, monthly_target_hours)
    contract_rows = _load_contract_rows(supabase, mitarbeiter_id)
    daily_credit_map = _calculate_daily_credit_map(
        start=start,
        end=end,
        paid=paid,
        fallback_monthly_target=fallback_monthly_target,
        contract_rows=contract_rows,
    )
    result = AbsenceResult(
        days=float(len(daily_credit_map)),
        credited_hours=round(sum(daily_credit_map.values()), 2),
        typ=normalized_typ,
    )

    diagnose_schluessel = ""
    grund_with_diag = grund
    if normalized_typ == "krankheit":
        diagnose_schluessel = str((grund or "")).strip()
        if diagnose_schluessel:
            base = str(grund or "").strip()
            grund_with_diag = f"{base} | diag:{diagnose_schluessel}" if base else f"diag:{diagnose_schluessel}"
    payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "typ": normalized_typ,
        "start_datum": start.isoformat(),
        "ende_datum": end.isoformat(),
        "bezahlte_zeit": paid,
        "stunden_gutschrift": result.credited_hours,
        "attest_pfad": attest_pfad,
        "grund": grund_with_diag,
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
        daily_credit_map=daily_credit_map,
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
    fallback_monthly_target = _load_default_monthly_target_hours(supabase, int(current.get("mitarbeiter_id")), monthly_target_hours)
    contract_rows = _load_contract_rows(supabase, int(current.get("mitarbeiter_id")))
    daily_credit_map = _calculate_daily_credit_map(
        start=start,
        end=end,
        paid=paid,
        fallback_monthly_target=fallback_monthly_target,
        contract_rows=contract_rows,
    )
    result = AbsenceResult(
        days=float(len(daily_credit_map)),
        credited_hours=round(sum(daily_credit_map.values()), 2),
        typ=normalized_typ,
    )

    old_start = _parse_iso_date(current.get("start_datum") or current.get("datum")) or start
    old_end = _parse_iso_date(current.get("ende_datum") or current.get("datum")) or old_start
    mitarbeiter_id = int(current.get("mitarbeiter_id"))
    betrieb_id = int(current.get("betrieb_id") or 0)

    diagnose_schluessel = ""
    grund_with_diag = grund
    if normalized_typ == "krankheit":
        diagnose_schluessel = str((grund or "")).strip()
        if diagnose_schluessel:
            base = str(grund or "").strip()
            grund_with_diag = f"{base} | diag:{diagnose_schluessel}" if base else f"diag:{diagnose_schluessel}"

    attempts = []
    for db_typ in _candidate_db_types(normalized_typ):
        payload = {
            "typ": db_typ,
            "start_datum": start.isoformat(),
            "ende_datum": end.isoformat(),
            "bezahlte_zeit": paid,
            "stunden_gutschrift": result.credited_hours,
            "attest_pfad": attest_pfad,
            "grund": grund_with_diag,
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
        daily_credit_map=daily_credit_map,
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


def build_efzg_episode_history(
    supabase,
    *,
    mitarbeiter_id: int,
    bis_datum: date,
    max_lookback_days: int = 540,
) -> list[dict]:
    """
    Baut eine einfache Episoden-Historie aus abwesenheiten (Typ Krankheit).
    Ergebnis kompatibel zu utils.efzg.berechne_efzg_status(..., vorerkrankungen=...).
    """
    start_lookback = bis_datum - timedelta(days=max(1, int(max_lookback_days)))
    try:
        res = (
            supabase.table("abwesenheiten")
            .select("start_datum,ende_datum,grund")
            .eq("mitarbeiter_id", int(mitarbeiter_id))
            .in_("typ", ["krankheit", "krank"])
            .gte("start_datum", start_lookback.isoformat())
            .lte("start_datum", bis_datum.isoformat())
            .order("start_datum")
            .execute()
        )
        rows = res.data or []
    except Exception:
        rows = []

    episodes: list[dict] = []
    for row in rows:
        s = _parse_iso_date(row.get("start_datum"))
        e = _parse_iso_date(row.get("ende_datum")) or s
        if s is None:
            continue
        if e is None or e < s:
            e = s
        episodes.append(
            {
                "start_datum": s.isoformat(),
                "ende_datum": e.isoformat(),
                # Diagnose-Schlüssel nur wenn im Feld grund explizit als Prefix mitgegeben.
                # Beispiel: "diag:M54.5"
                "diagnose_schluessel": (str(row.get("grund") or "").strip().split("diag:", 1)[1].strip()
                                        if "diag:" in str(row.get("grund") or "") else None),
            }
        )
    return episodes


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
