from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, Optional

from utils.lohnberechnung import berechne_arbeitszeitkonto_saldo


@dataclass
class WorkAccountSnapshot:
    soll_stunden: float
    ist_stunden: float
    ueberstunden_saldo: float
    urlaubstage_gesamt: float
    urlaubstage_genommen: float
    krankheitstage_gesamt: float
    ueberstunden_vortrag: float = 0.0
    differenz_stunden: float = 0.0
    monat_abgeschlossen: bool = False
    manuelle_korrektur_saldo: float = 0.0
    korrektur_grund: str | None = None


def set_work_account_opening_balance(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
    opening_hours: float,
    opening_vacation_taken: float = 0.0,
    opening_sick_days: float = 0.0,
    correction_reason: str = "",
    is_initialization: bool = False,
    created_by: Optional[int] = None,
) -> WorkAccountSnapshot:
    """
    Setzt einen festen Anfangsbestand für einen Startmonat (z. B. 04/2026).
    Dafür wird ein Snapshot auf dem Vormonat erzeugt, damit im Startmonat gilt:
    Neuer Saldo = (Ist - Soll) + Saldenvortrag.
    """
    opening = round(float(opening_hours or 0.0), 2)
    opening_vac = round(float(opening_vacation_taken or 0.0), 2)
    opening_sick = round(float(opening_sick_days or 0.0), 2)
    reason = str(correction_reason or "").strip() or "Initialisierung Vorträge"

    prev_monat = 12 if int(monat) == 1 else int(monat) - 1
    prev_jahr = int(jahr) - 1 if int(monat) == 1 else int(jahr)

    try:
        existing = (
            supabase.table("azk_monatsabschluesse")
            .select("id")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .eq("monat", prev_monat)
            .eq("jahr", prev_jahr)
            .limit(1)
            .execute()
        )
        if existing.data:
            # Bereits vorhanden -> nur Snapshot des Startmonats synchronisieren.
            return sync_work_account_for_month(
                supabase,
                betrieb_id=betrieb_id,
                mitarbeiter_id=mitarbeiter_id,
                monat=monat,
                jahr=jahr,
            )
    except Exception:
        # Wenn Tabelle/Schema nicht vorhanden ist, fällt der spätere Insert ggf. auch aus.
        pass

    extended_payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "monat": int(prev_monat),
        "jahr": int(prev_jahr),
        "soll_stunden": 0.0,
        "ist_stunden": 0.0,
        "differenz_stunden": 0.0,
        "ueberstunden_saldo_start": opening,
        "ueberstunden_saldo_ende": opening,
        "urlaubstage_gesamt": 0.0,
        "urlaubstage_genommen": opening_vac,
        "krankheitstage_gesamt": opening_sick,
        "manuelle_korrektur_saldo": opening,
        "korrektur_grund": reason,
        "ist_initialisierung": bool(is_initialization),
        "initialisierungs_monat": int(monat),
        "initialisierungs_jahr": int(jahr),
        "created_by": created_by,
    }
    legacy_payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "monat": int(prev_monat),
        "jahr": int(prev_jahr),
        "soll_stunden": 0.0,
        "ist_stunden": 0.0,
        "differenz_stunden": 0.0,
        "ueberstunden_saldo_start": opening,
        "ueberstunden_saldo_ende": opening,
        "urlaubstage_gesamt": 0.0,
        "urlaubstage_genommen": opening_vac,
        "krankheitstage_gesamt": opening_sick,
        "created_by": created_by,
    }
    try:
        try:
            supabase.table("azk_monatsabschluesse").insert(extended_payload).execute()
        except Exception:
            supabase.table("azk_monatsabschluesse").insert(legacy_payload).execute()
    except Exception:
        # Fallback ohne Snapshot-Tabelle: live Konto direkt setzen.
        _upsert_live_account(
            supabase,
            betrieb_id=betrieb_id,
            mitarbeiter_id=mitarbeiter_id,
            snapshot=WorkAccountSnapshot(
                soll_stunden=0.0,
                ist_stunden=0.0,
                ueberstunden_saldo=opening,
                urlaubstage_gesamt=0.0,
                urlaubstage_genommen=opening_vac,
                krankheitstage_gesamt=opening_sick,
                differenz_stunden=0.0,
                monat_abgeschlossen=False,
                manuelle_korrektur_saldo=opening,
                korrektur_grund=reason,
            ),
        )
        return WorkAccountSnapshot(
            soll_stunden=0.0,
            ist_stunden=0.0,
            ueberstunden_saldo=opening,
            urlaubstage_gesamt=0.0,
            urlaubstage_genommen=opening_vac,
            krankheitstage_gesamt=opening_sick,
            differenz_stunden=0.0,
            monat_abgeschlossen=False,
            manuelle_korrektur_saldo=opening,
            korrektur_grund=reason,
        )

    return sync_work_account_for_month(
        supabase,
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter_id,
        monat=monat,
        jahr=jahr,
    )


def _daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _is_workday(d: date) -> bool:
    # Betriebslogik der bestehenden App: Mo/Di Ruhetag.
    return d.weekday() not in (0, 1)


def _to_float(value) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _is_on_conflict_constraint_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "42p10" in msg or "no unique or exclusion constraint matching the on conflict" in msg


def _month_bounds(monat: int, jahr: int) -> tuple[date, date]:
    start = date(jahr, monat, 1)
    end = date(
        jahr + (1 if monat == 12 else 0),
        1 if monat == 12 else monat + 1,
        1,
    ) - timedelta(days=1)
    return start, end


def _month_key(monat: int, jahr: int) -> int:
    return jahr * 100 + monat


def _latest_row(rows: Iterable[dict], key_fn) -> Optional[dict]:
    data = list(rows)
    if not data:
        return None
    return sorted(data, key=key_fn, reverse=True)[0]


def calculate_absence_days(start: date, end: date) -> float:
    return float(sum(1 for d in _daterange(start, end) if _is_workday(d)))


def _load_mitarbeiter_defaults(supabase, mitarbeiter_id: int) -> dict:
    res = (
        supabase.table("mitarbeiter")
        .select("monatliche_soll_stunden, jahres_urlaubstage, resturlaub_vorjahr")
        .eq("id", mitarbeiter_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else {}


def _load_contract_rows(supabase, mitarbeiter_id: int) -> list[dict]:
    try:
        res = (
            supabase.table("vertraege")
            .select("gueltig_ab, gueltig_bis, soll_stunden_monat, wochenstunden, urlaubstage_jahr")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .execute()
        )
        return res.data or []
    except Exception:
        # Vor Migrationstabelle oder ältere Instanzen ohne Verträge
        return []


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


def _resolve_daily_target_hours(contract: dict, month_workdays: int) -> float:
    soll_monat = _to_float(contract.get("soll_stunden_monat"))
    if soll_monat > 0 and month_workdays > 0:
        return soll_monat / float(month_workdays)
    wochenstunden = _to_float(contract.get("wochenstunden"))
    if wochenstunden > 0:
        # Betriebsmodell ist 5 Arbeitstage (Mi-So).
        return wochenstunden / 5.0
    return 0.0


def _resolve_month_soll_and_vacation(
    *,
    month_start: date,
    month_end: date,
    mitarbeiter_defaults: dict,
    contract_rows: list[dict],
) -> tuple[float, float]:
    workdays = [d for d in _daterange(month_start, month_end) if _is_workday(d)]
    month_workdays = len(workdays)

    fallback_monthly_soll = _to_float(mitarbeiter_defaults.get("monatliche_soll_stunden"))
    fallback_daily_soll = (
        fallback_monthly_soll / float(month_workdays) if month_workdays > 0 and fallback_monthly_soll > 0 else 0.0
    )

    soll_hours = 0.0
    for day in workdays:
        active_contracts = [c for c in contract_rows if _contract_active_on(c, day)]
        active = _latest_row(
            active_contracts,
            key_fn=lambda c: (str(c.get("gueltig_ab") or "1900-01-01"), str(c.get("gueltig_bis") or "9999-12-31")),
        )
        if active:
            soll_hours += _resolve_daily_target_hours(active, month_workdays) or fallback_daily_soll
        else:
            soll_hours += fallback_daily_soll

    yearly_vacation_from_contract = _latest_row(
        [c for c in contract_rows if _to_float(c.get("urlaubstage_jahr")) > 0],
        key_fn=lambda c: str(c.get("gueltig_ab") or "1900-01-01"),
    )
    if yearly_vacation_from_contract:
        urlaubstage_gesamt = _to_float(yearly_vacation_from_contract.get("urlaubstage_jahr"))
    else:
        urlaubstage_gesamt = _to_float(mitarbeiter_defaults.get("jahres_urlaubstage")) + _to_float(
            mitarbeiter_defaults.get("resturlaub_vorjahr")
        )

    return round(soll_hours, 2), round(urlaubstage_gesamt, 2)


def resolve_month_contract_targets(
    supabase,
    *,
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
) -> dict:
    """
    Liefert die vertraglich wirksamen Monatsziele für einen Mitarbeiter.

    Rückgabe:
    {
        "soll_stunden": float,
        "arbeitstage": int,
        "tagessoll_stunden": float,
        "urlaubstage_gesamt": float,
    }
    """
    month_start, month_end = _month_bounds(monat, jahr)
    defaults = _load_mitarbeiter_defaults(supabase, mitarbeiter_id)
    contracts = _load_contract_rows(supabase, mitarbeiter_id)
    soll_stunden, urlaubstage_gesamt = _resolve_month_soll_and_vacation(
        month_start=month_start,
        month_end=month_end,
        mitarbeiter_defaults=defaults,
        contract_rows=contracts,
    )
    arbeitstage = int(sum(1 for d in _daterange(month_start, month_end) if _is_workday(d)))
    tagessoll_stunden = round((soll_stunden / float(arbeitstage)) if arbeitstage > 0 else 0.0, 4)
    return {
        "soll_stunden": round(float(soll_stunden or 0.0), 2),
        "arbeitstage": arbeitstage,
        "tagessoll_stunden": tagessoll_stunden,
        "urlaubstage_gesamt": round(float(urlaubstage_gesamt or 0.0), 2),
    }


def _resolve_daily_target_for_day(
    *,
    day: date,
    month_workdays: int,
    fallback_monthly_soll: float,
    contract_rows: list[dict],
) -> float:
    fallback_daily = (float(fallback_monthly_soll or 0.0) / float(month_workdays)) if month_workdays > 0 else 0.0
    active_contracts = [c for c in (contract_rows or []) if _contract_active_on(c, day)]
    active = _latest_row(
        active_contracts,
        key_fn=lambda c: (str(c.get("gueltig_ab") or "1900-01-01"), str(c.get("gueltig_bis") or "9999-12-31")),
    )
    if not active:
        return round(fallback_daily, 4)
    return round(_resolve_daily_target_hours(active, month_workdays) or fallback_daily, 4)


def _is_krank_row(row: dict) -> bool:
    source = str(row.get("quelle") or "").strip().lower()
    abw_typ = str(row.get("abwesenheitstyp") or "").strip().lower()
    return bool(row.get("ist_krank")) or source in {"au_bescheinigung", "abwesenheit_system"} or abw_typ in {
        "krank",
        "krankheit",
    }


def _load_month_ist_hours(
    supabase,
    mitarbeiter_id: int,
    month_start: date,
    month_end: date,
    *,
    mitarbeiter_defaults: Optional[dict] = None,
    contract_rows: Optional[list[dict]] = None,
) -> float:
    try:
        zeit_res = (
            supabase.table("zeiterfassung")
            .select("datum,arbeitsstunden,stunden,quelle,ist_krank,abwesenheitstyp")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .gte("datum", month_start.isoformat())
            .lte("datum", month_end.isoformat())
            .execute()
        )
    except Exception:
        # Legacy-Fallback mit reduziertem Feldsatz
        zeit_res = (
            supabase.table("zeiterfassung")
            .select("datum,arbeitsstunden,stunden,quelle,ist_krank")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .gte("datum", month_start.isoformat())
            .lte("datum", month_end.isoformat())
            .execute()
        )

    rows = zeit_res.data or []
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        day = str(row.get("datum") or "").strip()[:10]
        if not day:
            continue
        grouped.setdefault(day, []).append(row)

    workdays = [d for d in _daterange(month_start, month_end) if _is_workday(d)]
    month_workdays = len(workdays)
    fallback_monthly_soll = _to_float((mitarbeiter_defaults or {}).get("monatliche_soll_stunden"))
    if fallback_monthly_soll <= 0:
        fallback_monthly_soll = _to_float(_load_mitarbeiter_defaults(supabase, mitarbeiter_id).get("monatliche_soll_stunden"))
    contracts = list(contract_rows or [])
    if not contracts:
        contracts = _load_contract_rows(supabase, mitarbeiter_id)

    daily_target_cache: dict[str, float] = {}
    for wd in workdays:
        daily_target_cache[wd.isoformat()] = _resolve_daily_target_for_day(
            day=wd,
            month_workdays=month_workdays,
            fallback_monthly_soll=fallback_monthly_soll,
            contract_rows=contracts,
        )

    total = 0.0
    for day in sorted(grouped.keys()):
        day_rows = grouped[day]
        productive_rows = [r for r in day_rows if str(r.get("quelle") or "").strip().lower() != "historischer_saldo"]
        if not productive_rows:
            continue

        # Kranktag hat Vorrang: verhindert Doppelzählung aus "krank + stempeln" am selben Datum.
        if any(_is_krank_row(r) for r in productive_rows):
            total += float(daily_target_cache.get(day, 0.0))
            continue

        for row in productive_rows:
            total += _to_float(row.get("arbeitsstunden") or row.get("stunden"))
    return round(total, 2)


def _load_month_absence_counters(supabase, mitarbeiter_id: int, month_start: date, month_end: date) -> tuple[float, float]:
    try:
        abw_res = (
            supabase.table("abwesenheiten")
            .select("typ, start_datum, ende_datum")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .lte("start_datum", month_end.isoformat())
            .gte("ende_datum", month_start.isoformat())
            .execute()
        )
    except Exception:
        return 0.0, 0.0

    urlaub_genommen = 0.0
    krank_tage = 0.0
    for row in abw_res.data or []:
        try:
            start = date.fromisoformat(str(row["start_datum"]))
            end = date.fromisoformat(str(row["ende_datum"]))
        except Exception:
            continue

        overlap_start = max(start, month_start)
        overlap_end = min(end, month_end)
        if overlap_end < overlap_start:
            continue
        tage = calculate_absence_days(overlap_start, overlap_end)
        typ = str(row.get("typ") or "").lower()
        if typ == "urlaub":
            urlaub_genommen += tage
        elif typ in ("krankheit", "krank"):
            krank_tage += tage

    # Manuelle Korrekturmarker aus Zeiterfassung (mit Pflichtbegründung) addieren.
    # Format in manuell_kommentar:
    # - manuelle_korrektur_urlaub:<tage>
    # - manuelle_korrektur_krank:<tage>
    try:
        marker_res = (
            supabase.table("zeiterfassung")
            .select("manuell_kommentar, quelle")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .eq("quelle", "manuell_admin")
            .gte("datum", month_start.isoformat())
            .lte("datum", month_end.isoformat())
            .execute()
        )
        for mr in marker_res.data or []:
            marker = str(mr.get("manuell_kommentar") or "").strip()
            if marker.startswith("manuelle_korrektur_urlaub:"):
                try:
                    urlaub_genommen += float(marker.split(":", 1)[1])
                except Exception:
                    pass
            elif marker.startswith("manuelle_korrektur_krank:"):
                try:
                    krank_tage += float(marker.split(":", 1)[1])
                except Exception:
                    pass
    except Exception:
        pass

    return round(urlaub_genommen, 2), round(krank_tage, 2)


def compute_work_account_snapshot(
    supabase,
    *,
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
) -> WorkAccountSnapshot:
    """
    Liefert den deterministischen Monats-Snapshot aus den Quelltabellen.
    """
    return _build_month_snapshot(
        supabase,
        monat=monat,
        jahr=jahr,
        mitarbeiter_id=mitarbeiter_id,
    )


def build_work_account_payload(
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    snapshot: WorkAccountSnapshot,
) -> Dict[str, float | int]:
    """
    Baut das einheitliche Persistenz-Payload für arbeitszeit_konten.
    """
    return {
        "betrieb_id": int(betrieb_id),
        "mitarbeiter_id": int(mitarbeiter_id),
        "soll_stunden": round(snapshot.soll_stunden, 2),
        "ist_stunden": round(snapshot.ist_stunden, 2),
        "ueberstunden_saldo": round(snapshot.ueberstunden_saldo, 2),
        "urlaubstage_gesamt": round(snapshot.urlaubstage_gesamt, 2),
        "urlaubstage_genommen": round(snapshot.urlaubstage_genommen, 2),
        "krankheitstage_gesamt": round(snapshot.krankheitstage_gesamt, 2),
    }


def validate_work_account_cycle(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
    tolerance_hours: float = 0.05,
) -> dict:
    """
    Prüft den geschlossenen Kreislauf:
    Quelle (Zeiterfassung/Abwesenheit/Vertrag) -> Snapshot -> Persistierter Kontostand.
    """
    expected = compute_work_account_snapshot(
        supabase,
        mitarbeiter_id=mitarbeiter_id,
        monat=monat,
        jahr=jahr,
    )
    expected_payload = build_work_account_payload(
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter_id,
        snapshot=expected,
    )

    persisted = None
    try:
        persisted_res = (
            supabase.table("arbeitszeit_konten")
            .select("*")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .limit(1)
            .execute()
        )
        if persisted_res.data:
            persisted = persisted_res.data[0]
    except Exception:
        persisted = None

    issues: list[str] = []
    if not persisted:
        issues.append("Kein persistierter Eintrag in arbeitszeit_konten vorhanden.")
    else:
        checks = [
            ("soll_stunden", "Soll-Stunden"),
            ("ist_stunden", "Ist-Stunden"),
            ("ueberstunden_saldo", "Überstunden-Saldo"),
            ("urlaubstage_gesamt", "Urlaub gesamt"),
            ("urlaubstage_genommen", "Urlaub genommen"),
            ("krankheitstage_gesamt", "Krankheitstage"),
        ]
        for key, label in checks:
            expected_v = float(expected_payload.get(key) or 0.0)
            persisted_v = float(persisted.get(key) or 0.0)
            if abs(expected_v - persisted_v) > float(tolerance_hours):
                issues.append(
                    f"{label} abweichend: erwartet {expected_v:.2f}, gespeichert {persisted_v:.2f}"
                )

    # Quellklassifikation: Jede Zeile muss eine klar bekannte Quelle tragen.
    allowed_sources = {
        "stempeluhr",
        "abwesenheit_system",
        "historischer_saldo",
        "manuell_admin",
        "au_bescheinigung",
    }
    source_rows = []
    try:
        month_start, month_end = _month_bounds(monat, jahr)
        source_rows = (
            supabase.table("zeiterfassung")
            .select("id,quelle")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .gte("datum", month_start.isoformat())
            .lte("datum", month_end.isoformat())
            .execute()
            .data
            or []
        )
    except Exception:
        source_rows = []

    unknown_sources = []
    invalid_purpose_rows = []
    for row in source_rows:
        source = str(row.get("quelle") or "").strip().lower()
        if not source or source not in allowed_sources:
            unknown_sources.append({"id": row.get("id"), "quelle": row.get("quelle")})
            continue
        if source == "abwesenheit_system":
            # Abwesenheitsspiegel muss neutrale 00:00-00:00 Markerzeilen sein.
            start_zeit = str(row.get("start_zeit") or "")
            ende_zeit = str(row.get("ende_zeit") or "")
            if not (start_zeit.startswith("00:00") and ende_zeit.startswith("00:00")):
                invalid_purpose_rows.append(
                    {
                        "id": row.get("id"),
                        "quelle": row.get("quelle"),
                        "grund": "abwesenheit_system ohne 00:00-00:00 Marker",
                    }
                )
    if unknown_sources:
        issues.append(f"Unklare Quellen in Zeiterfassung: {len(unknown_sources)}")
    if invalid_purpose_rows:
        issues.append(f"Zweckverletzung in Zeiterfassung: {len(invalid_purpose_rows)}")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "expected": expected_payload,
        "persisted": persisted,
        "unknown_sources": unknown_sources[:20],
        "invalid_purpose_rows": len(invalid_purpose_rows),
        "invalid_purpose_details": invalid_purpose_rows[:20],
    }


# Backward-compatible alias used by dashboard imports.
def validate_work_account_month(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
    tolerance_hours: float = 0.05,
) -> dict:
    return validate_work_account_cycle(
        supabase,
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter_id,
        monat=monat,
        jahr=jahr,
        tolerance_hours=tolerance_hours,
    )


def _load_closed_snapshot(supabase, mitarbeiter_id: int, monat: int, jahr: int) -> Optional[dict]:
    try:
        res = (
            supabase.table("azk_monatsabschluesse")
            .select("*")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .eq("monat", monat)
            .eq("jahr", jahr)
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    rows = res.data or []
    return rows[0] if rows else None


def _load_previous_balance(supabase, mitarbeiter_id: int, monat: int, jahr: int) -> float:
    try:
        res = supabase.table("azk_monatsabschluesse").select(
            "monat, jahr, ueberstunden_saldo_ende"
        ).eq("mitarbeiter_id", mitarbeiter_id).execute()
    except Exception:
        return 0.0

    prev_key = _month_key(monat, jahr)
    candidates = [
        row for row in (res.data or []) if _month_key(int(row.get("monat") or 0), int(row.get("jahr") or 0)) < prev_key
    ]
    latest = _latest_row(candidates, key_fn=lambda r: _month_key(int(r.get("monat") or 0), int(r.get("jahr") or 0)))
    if not latest:
        return 0.0
    return round(_to_float(latest.get("ueberstunden_saldo_ende")), 2)


def _upsert_live_account(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    snapshot: WorkAccountSnapshot,
) -> None:
    payload = build_work_account_payload(
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter_id,
        snapshot=snapshot,
    )
    try:
        supabase.table("arbeitszeit_konten").upsert(payload, on_conflict="mitarbeiter_id").execute()
        return
    except Exception as exc:
        if not _is_on_conflict_constraint_error(exc):
            raise

    # Legacy-Fallback: Instanzen ohne passenden UNIQUE-Index für ON CONFLICT.
    existing = (
        supabase.table("arbeitszeit_konten")
        .select("id")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        supabase.table("arbeitszeit_konten").update(payload).eq("mitarbeiter_id", mitarbeiter_id).execute()
    else:
        supabase.table("arbeitszeit_konten").insert(payload).execute()


def _build_month_snapshot(
    supabase,
    *,
    monat: int,
    jahr: int,
    mitarbeiter_id: int,
) -> WorkAccountSnapshot:
    month_start, month_end = _month_bounds(monat, jahr)
    defaults = _load_mitarbeiter_defaults(supabase, mitarbeiter_id)
    contracts = _load_contract_rows(supabase, mitarbeiter_id)

    soll_stunden, urlaubstage_gesamt = _resolve_month_soll_and_vacation(
        month_start=month_start,
        month_end=month_end,
        mitarbeiter_defaults=defaults,
        contract_rows=contracts,
    )
    ist_stunden = _load_month_ist_hours(
        supabase,
        mitarbeiter_id,
        month_start,
        month_end,
        mitarbeiter_defaults=defaults,
        contract_rows=contracts,
    )
    urlaub_genommen, krank_tage = _load_month_absence_counters(supabase, mitarbeiter_id, month_start, month_end)

    diff = round(ist_stunden - soll_stunden, 2)
    saldo_vormonat = _load_previous_balance(supabase, mitarbeiter_id, monat, jahr)
    neuer_saldo = berechne_arbeitszeitkonto_saldo(
        ist_stunden=ist_stunden,
        soll_stunden=soll_stunden,
        saldenvortrag=saldo_vormonat,
    )

    return WorkAccountSnapshot(
        soll_stunden=round(soll_stunden, 2),
        ist_stunden=round(ist_stunden, 2),
        ueberstunden_saldo=round(neuer_saldo, 2),
        urlaubstage_gesamt=round(urlaubstage_gesamt, 2),
        urlaubstage_genommen=round(urlaub_genommen, 2),
        krankheitstage_gesamt=round(krank_tage, 2),
        differenz_stunden=diff,
        monat_abgeschlossen=False,
        manuelle_korrektur_saldo=round(saldo_vormonat, 2),
    )


def sync_work_account_for_month(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
) -> WorkAccountSnapshot:
    closed = _load_closed_snapshot(supabase, mitarbeiter_id, monat, jahr)
    if closed:
        locked = WorkAccountSnapshot(
            soll_stunden=round(_to_float(closed.get("soll_stunden")), 2),
            ist_stunden=round(_to_float(closed.get("ist_stunden")), 2),
            ueberstunden_saldo=round(_to_float(closed.get("ueberstunden_saldo_ende")), 2),
            urlaubstage_gesamt=round(_to_float(closed.get("urlaubstage_gesamt")), 2),
            urlaubstage_genommen=round(_to_float(closed.get("urlaubstage_genommen")), 2),
            krankheitstage_gesamt=round(_to_float(closed.get("krankheitstage_gesamt")), 2),
            differenz_stunden=round(_to_float(closed.get("differenz_stunden")), 2),
            monat_abgeschlossen=True,
            manuelle_korrektur_saldo=round(
                _to_float(
                    closed.get("manuelle_korrektur_saldo")
                    if closed.get("manuelle_korrektur_saldo") is not None
                    else closed.get("ueberstunden_saldo_start")
                ),
                2,
            ),
            korrektur_grund=(str(closed.get("korrektur_grund") or "").strip() or None),
        )
        _upsert_live_account(
            supabase,
            betrieb_id=betrieb_id,
            mitarbeiter_id=mitarbeiter_id,
            snapshot=locked,
        )
        return locked

    current = _build_month_snapshot(
        supabase,
        monat=monat,
        jahr=jahr,
        mitarbeiter_id=mitarbeiter_id,
    )
    _upsert_live_account(
        supabase,
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter_id,
        snapshot=current,
    )
    return current


def close_work_account_month(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
    created_by: Optional[int] = None,
) -> WorkAccountSnapshot:
    existing = _load_closed_snapshot(supabase, mitarbeiter_id, monat, jahr)
    if existing:
        return sync_work_account_for_month(
            supabase,
            betrieb_id=betrieb_id,
            mitarbeiter_id=mitarbeiter_id,
            monat=monat,
            jahr=jahr,
        )

    snapshot = _build_month_snapshot(
        supabase,
        monat=monat,
        jahr=jahr,
        mitarbeiter_id=mitarbeiter_id,
    )
    saldo_start = round(snapshot.ueberstunden_saldo - snapshot.differenz_stunden, 2)
    try:
        supabase.table("azk_monatsabschluesse").insert(
            {
                "betrieb_id": betrieb_id,
                "mitarbeiter_id": mitarbeiter_id,
                "monat": int(monat),
                "jahr": int(jahr),
                "soll_stunden": round(snapshot.soll_stunden, 2),
                "ist_stunden": round(snapshot.ist_stunden, 2),
                "differenz_stunden": round(snapshot.differenz_stunden, 2),
                "ueberstunden_saldo_start": saldo_start,
                "ueberstunden_saldo_ende": round(snapshot.ueberstunden_saldo, 2),
                "urlaubstage_gesamt": round(snapshot.urlaubstage_gesamt, 2),
                "urlaubstage_genommen": round(snapshot.urlaubstage_genommen, 2),
                "krankheitstage_gesamt": round(snapshot.krankheitstage_gesamt, 2),
                "created_by": created_by,
            }
        ).execute()
    except Exception:
        # Falls Tabelle noch nicht migriert ist, bleibt es beim deterministischen Live-Sync.
        _upsert_live_account(
            supabase,
            betrieb_id=betrieb_id,
            mitarbeiter_id=mitarbeiter_id,
            snapshot=snapshot,
        )
        return snapshot

    return sync_work_account_for_month(
        supabase,
        betrieb_id=betrieb_id,
        mitarbeiter_id=mitarbeiter_id,
        monat=monat,
        jahr=jahr,
    )


def sync_work_account_range(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    start_monat: int,
    start_jahr: int,
    end_monat: int,
    end_jahr: int,
) -> list[WorkAccountSnapshot]:
    """
    Synchronisiert Arbeitszeitkonten für einen Monatsbereich (inklusive Grenzen).

    Nützlich nach historischen Importen, damit sich das laufende Konto automatisch
    über Folgemonate aktualisiert.
    """
    snapshots: list[WorkAccountSnapshot] = []
    cur_jahr = int(start_jahr)
    cur_monat = int(start_monat)
    target_key = _month_key(int(end_monat), int(end_jahr))

    while _month_key(cur_monat, cur_jahr) <= target_key:
        snapshots.append(
            sync_work_account_for_month(
                supabase,
                betrieb_id=betrieb_id,
                mitarbeiter_id=mitarbeiter_id,
                monat=cur_monat,
                jahr=cur_jahr,
            )
        )
        if cur_monat == 12:
            cur_monat = 1
            cur_jahr += 1
        else:
            cur_monat += 1

    return snapshots

