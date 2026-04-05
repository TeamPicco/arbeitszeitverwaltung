from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils.compliance import (
    ComplianceFinding,
    check_arbzg_breaks,
    check_daily_work_limit,
    check_rest_period,
)
from utils.time_utils import get_berlin_tz, now_utc, to_berlin, to_utc

MAX_AUTO_SHIFT_HOURS = 10.0

EVENT_CLOCK_IN = "clock_in"
EVENT_CLOCK_OUT = "clock_out"
EVENT_BREAK_START = "break_start"
EVENT_BREAK_END = "break_end"


def _is_rls_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    code = None
    try:
        # postgrest.exceptions.APIError exposes a json() payload with code/message.
        json_method = getattr(exc, "json", None)
        if callable(json_method):
            payload = json_method() or {}
            code = str(payload.get("code") or "").lower()
            payload_msg = str(payload.get("message") or "").lower()
            if payload_msg:
                msg = f"{msg} {payload_msg}"
    except Exception:
        pass

    return (
        code == "42501"
        or "42501" in msg
        or "row-level security" in msg
        or "violates row-level security policy" in msg
    )


def _service_role_client_or_none():
    try:
        from utils.database import get_service_role_client

        return get_service_role_client()
    except Exception:
        return None


def _insert_event_with_rls_fallback(primary_client, payload: Dict[str, Any]) -> Any:
    """
    Versucht Insert mit Primary-Client, fällt bei RLS auf Service-Role zurück.
    Gibt den tatsächlich verwendeten Client zurück.
    """
    try:
        primary_client.table("zeit_eintraege").insert(payload).execute()
        return primary_client
    except Exception as exc:
        if not _is_rls_error(exc):
            raise
        svc = _service_role_client_or_none()
        if svc is None:
            raise RuntimeError(
                "RLS-Fehler beim Schreiben der Zeit-Events und kein Service-Role-Key verfügbar."
            ) from exc
        svc.table("zeit_eintraege").insert(payload).execute()
        return svc


def _normalize_event_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []
    for row in rows or []:
        ts = row.get("zeitpunkt_utc")
        if isinstance(ts, str):
            try:
                parsed_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                row["_ts"] = parsed_dt
            except Exception:
                continue
        elif isinstance(ts, datetime):
            row["_ts"] = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
        else:
            continue
        parsed.append(row)
    parsed.sort(key=lambda x: x["_ts"])
    return parsed


def _same_day(dt: datetime, day: date) -> bool:
    return to_berlin(dt).date() == day


def _build_legacy_payload(
    mitarbeiter_id: int,
    day: date,
    start_dt: datetime,
    end_dt: Optional[datetime],
    break_minutes: int,
    source: str,
) -> Dict[str, Any]:
    work_hours = None
    if end_dt is not None:
        total_minutes = max(0, int((end_dt - start_dt).total_seconds() // 60))
        net_minutes = max(0, total_minutes - break_minutes)
        work_hours = round(net_minutes / 60.0, 2)

    start_local = to_berlin(start_dt)
    end_local = to_berlin(end_dt) if end_dt else None

    return {
        "mitarbeiter_id": mitarbeiter_id,
        "datum": day.isoformat(),
        "start_zeit": start_local.time().strftime("%H:%M:%S"),
        "ende_zeit": end_local.time().strftime("%H:%M:%S") if end_local else None,
        "pause_minuten": break_minutes,
        "arbeitsstunden": work_hours,
        "monat": day.month,
        "jahr": day.year,
        "quelle": source,
    }


def _shift_duration_hours(start_dt: datetime, end_dt: Optional[datetime]) -> float:
    if end_dt is None:
        return 0.0
    minutes = max(0, int((end_dt - start_dt).total_seconds() // 60))
    return round(minutes / 60.0, 4)


def _compute_break_minutes(events: List[Dict[str, Any]]) -> int:
    break_start: Optional[datetime] = None
    break_minutes = 0
    for ev in events:
        action = ev.get("aktion")
        ts = ev["_ts"]
        if action == EVENT_BREAK_START and break_start is None:
            break_start = ts
        elif action == EVENT_BREAK_END and break_start is not None:
            break_minutes += max(0, int((ts - break_start).total_seconds() // 60))
            break_start = None
    return break_minutes


def _last_open_shift(events: List[Dict[str, Any]]) -> Optional[datetime]:
    start_ts: Optional[datetime] = None
    for ev in events:
        if ev.get("aktion") == EVENT_CLOCK_IN:
            start_ts = ev["_ts"]
        elif ev.get("aktion") == EVENT_CLOCK_OUT and start_ts is not None:
            start_ts = None
    return start_ts


def _last_shift_end(events: List[Dict[str, Any]]) -> Optional[datetime]:
    for ev in reversed(events):
        if ev.get("aktion") == EVENT_CLOCK_OUT:
            return ev["_ts"]
    return None


def _max_open_shift_age_hours() -> int:
    # Harte Sicherung gegen Phantom-Status "eingestempelt seit gestern".
    return int(MAX_AUTO_SHIFT_HOURS)


def _close_stale_open_shift(
    client,
    *,
    mitarbeiter_id: int,
    betrieb_id: Optional[int],
    now_ts: datetime,
    source: str,
) -> None:
    """
    Schließt eine veraltete offene Schicht (ohne CLOCK_OUT) automatisch.
    Endzeit = Start + MAX_OPEN_SHIFT_AGE, um Dauerläufer zu verhindern.
    """
    try:
        cutoff = now_ts - timedelta(hours=_max_open_shift_age_hours())
        # Letztes CLOCK_IN suchen.
        in_res = (
            client.table("zeit_eintraege")
            .select("id, aktion, zeitpunkt_utc, betrieb_id, quelle, geraet_id, created_by")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .eq("aktion", EVENT_CLOCK_IN)
            .lte("zeitpunkt_utc", cutoff.isoformat())
            .order("zeitpunkt_utc", desc=True)
            .limit(1)
            .execute()
        )
        if not (in_res.data or []):
            return
        last_in = in_res.data[0]
        in_ts = datetime.fromisoformat(str(last_in["zeitpunkt_utc"]).replace("Z", "+00:00"))
        if in_ts.tzinfo is None:
            in_ts = in_ts.replace(tzinfo=timezone.utc)

        # Gibt es nach diesem IN schon ein OUT? Dann nichts tun.
        out_res = (
            client.table("zeit_eintraege")
            .select("id")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .eq("aktion", EVENT_CLOCK_OUT)
            .gte("zeitpunkt_utc", in_ts.isoformat())
            .order("zeitpunkt_utc")
            .limit(1)
            .execute()
        )
        if out_res.data:
            return

        forced_out = in_ts + timedelta(hours=_max_open_shift_age_hours())
        insert_payload = {
            "betrieb_id": int(last_in.get("betrieb_id") or betrieb_id or 0) or None,
            "mitarbeiter_id": mitarbeiter_id,
            "aktion": EVENT_CLOCK_OUT,
            "zeitpunkt_utc": forced_out.isoformat(),
            "quelle": source,
            "geraet_id": last_in.get("geraet_id"),
            "created_by": last_in.get("created_by"),
            "notiz": "Auto-Close: offene Schicht > 10h wurde systemseitig beendet (Admin-Pruefung erforderlich)",
        }
        _insert_event_with_rls_fallback(client, insert_payload)
    except Exception:
        # Kein Hard-Fail im Stempelworkflow.
        return


def validate_event_transition(events: List[Dict[str, Any]], action: str) -> Tuple[bool, str]:
    open_shift = _last_open_shift(events)

    if action == EVENT_CLOCK_IN:
        if open_shift is not None:
            return False, "Bereits eingestempelt."
        return True, ""
    if action == EVENT_CLOCK_OUT:
        if open_shift is None:
            return False, "Nicht eingestempelt."
        return True, ""

    # Pausen nur innerhalb offener Schicht.
    if action in (EVENT_BREAK_START, EVENT_BREAK_END):
        if open_shift is None:
            return False, "Keine aktive Schicht für Pausenbuchung."
        breaks_open = False
        for ev in events:
            if ev.get("aktion") == EVENT_BREAK_START:
                breaks_open = True
            elif ev.get("aktion") == EVENT_BREAK_END:
                breaks_open = False
        if action == EVENT_BREAK_START and breaks_open:
            return False, "Pause läuft bereits."
        if action == EVENT_BREAK_END and not breaks_open:
            return False, "Keine laufende Pause."
        return True, ""

    return False, "Unbekannte Aktion."


def _collect_daily_events(events: List[Dict[str, Any]], day: date) -> List[Dict[str, Any]]:
    return [ev for ev in events if _same_day(ev["_ts"], day)]


def get_event_state_for_day(
    supabase,
    *,
    mitarbeiter_id: int,
    day: date,
) -> Dict[str, bool]:
    """
    Liefert den aktuellen Schicht-/Pausenstatus für einen Tag.
    """
    tz_berlin = get_berlin_tz()
    start_local = datetime.combine(day, time(0, 0), tzinfo=tz_berlin)
    end_local = datetime.combine(day + timedelta(days=1), time(0, 0), tzinfo=tz_berlin)
    start = to_utc(start_local).isoformat()
    end = to_utc(end_local).isoformat()
    read_client = _service_role_client_or_none() or supabase
    _close_stale_open_shift(
        read_client,
        mitarbeiter_id=mitarbeiter_id,
        betrieb_id=None,
        now_ts=now_utc(),
        source="system_auto_close",
    )

    ev_res = (
        read_client.table("zeit_eintraege")
        .select("aktion, zeitpunkt_utc")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .gte("zeitpunkt_utc", start)
        .lt("zeitpunkt_utc", end)
        .order("zeitpunkt_utc")
        .execute()
    )
    events = _normalize_event_rows(ev_res.data or [])

    eingestempelt = False
    pause_aktiv = False
    for ev in events:
        action = ev.get("aktion")
        if action == EVENT_CLOCK_IN:
            eingestempelt = True
            pause_aktiv = False
        elif action == EVENT_CLOCK_OUT:
            eingestempelt = False
            pause_aktiv = False
        elif action == EVENT_BREAK_START and eingestempelt:
            pause_aktiv = True
        elif action == EVENT_BREAK_END and eingestempelt:
            pause_aktiv = False

    return {"eingestempelt": eingestempelt, "pause_aktiv": pause_aktiv}


def evaluate_daily_compliance(
    all_events: List[Dict[str, Any]],
    day: date,
    previous_shift_end: Optional[datetime] = None,
) -> List[ComplianceFinding]:
    daily = _collect_daily_events(all_events, day)
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    for ev in daily:
        if ev.get("aktion") == EVENT_CLOCK_IN:
            start = ev["_ts"]
        elif ev.get("aktion") == EVENT_CLOCK_OUT:
            end = ev["_ts"]

    if start is None or end is None:
        return []

    total_minutes = max(0, int((end - start).total_seconds() // 60))
    break_minutes = _compute_break_minutes(daily)
    work_minutes = max(0, total_minutes - break_minutes)

    findings: List[ComplianceFinding] = []
    findings.extend(check_arbzg_breaks(work_minutes, break_minutes))
    findings.extend(check_daily_work_limit(work_minutes))
    findings.extend(check_rest_period(previous_shift_end, start))
    return findings


def register_time_event(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    action: str,
    source: str = "stempeluhr",
    geraet_id: Optional[str] = None,
    created_by: Optional[int] = None,
    event_time_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Schreibt ein Zeit-Event und synchronisiert rückwärtskompatibel zeiterfassung.
    """
    event_time = to_utc(event_time_utc or now_utc())

    # Wenn vorhanden, service_role bevorzugen, um RLS-bedingte Runtime-Fehler
    # im serverseitigen Streamlit-Prozess zu vermeiden.
    service_client = _service_role_client_or_none()

    # Historie laden (letzte 7 Tage reichen für Restzeitchecks).
    since = (event_time - timedelta(days=7)).isoformat()
    read_client = service_client or supabase
    # Vor dem Übergangscheck veraltete offene Schichten automatisch schließen.
    _close_stale_open_shift(
        read_client,
        mitarbeiter_id=mitarbeiter_id,
        betrieb_id=betrieb_id,
        now_ts=event_time,
        source=source,
    )
    try:
        ev_res = (
            read_client.table("zeit_eintraege")
            .select("*")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .gte("zeitpunkt_utc", since)
            .order("zeitpunkt_utc")
            .execute()
        )
    except Exception as exc:
        if read_client is not supabase:
            raise
        if not _is_rls_error(exc):
            raise
        svc = service_client or _service_role_client_or_none()
        if svc is None:
            return {"ok": False, "error": f"RLS-Fehler beim Lesen der Zeit-Events: {exc}"}
        ev_res = (
            svc.table("zeit_eintraege")
            .select("*")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .gte("zeitpunkt_utc", since)
            .order("zeitpunkt_utc")
            .execute()
        )
    events = _normalize_event_rows(ev_res.data or [])

    ok, reason = validate_event_transition(events, action)
    if not ok:
        return {"ok": False, "error": reason}

    insert_payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "aktion": action,
        "zeitpunkt_utc": event_time.isoformat(),
        "quelle": source,
        "geraet_id": geraet_id,
        "created_by": created_by,
    }
    write_client = service_client or supabase
    try:
        write_client.table("zeit_eintraege").insert(insert_payload).execute()
    except Exception as exc:
        # Wenn wir bereits mit service_role schreiben, weiterreichen.
        if write_client is not supabase:
            raise
        if not _is_rls_error(exc):
            raise
        svc = _service_role_client_or_none()
        if svc is None:
            return {"ok": False, "error": f"RLS-Fehler beim Schreiben der Zeit-Events: {exc}"}
        write_client = svc
        write_client.table("zeit_eintraege").insert(insert_payload).execute()

    # Eventliste inkl. neuem Event.
    events.append({"aktion": action, "_ts": event_time, "zeitpunkt_utc": event_time})
    events.sort(key=lambda x: x["_ts"])
    day = to_berlin(event_time).date()
    daily = _collect_daily_events(events, day)

    # Legacy-Write nur bei clock_in/clock_out
    if action in (EVENT_CLOCK_IN, EVENT_CLOCK_OUT):
        start_dt: Optional[datetime] = None
        end_dt: Optional[datetime] = None
        for ev in daily:
            if ev.get("aktion") == EVENT_CLOCK_IN:
                start_dt = ev["_ts"]
            elif ev.get("aktion") == EVENT_CLOCK_OUT:
                end_dt = ev["_ts"]
        if start_dt is not None:
            break_minutes = _compute_break_minutes(daily)
            legacy = _build_legacy_payload(
                mitarbeiter_id=mitarbeiter_id,
                day=day,
                start_dt=start_dt,
                end_dt=end_dt,
                break_minutes=break_minutes,
                source=source,
            )
            write_client.table("zeiterfassung").upsert(
                legacy,
                on_conflict="mitarbeiter_id,datum,start_zeit",
            ).execute()

    prev_end = _last_shift_end([ev for ev in events if to_berlin(ev["_ts"]).date() < day])
    findings = evaluate_daily_compliance(events, day, previous_shift_end=prev_end)
    if findings:
        # Optional auf Legacy-Tabelle spiegeln, wenn Spalte vorhanden.
        try:
            write_client.table("zeiterfassung").update(
                {"compliance_warnungen": [f.__dict__ for f in findings]}
            ).eq("mitarbeiter_id", mitarbeiter_id).eq("datum", day.isoformat()).execute()
        except Exception:
            pass
        try:
            write_client.table("audit_logs").insert(
                {
                    "betrieb_id": betrieb_id,
                    "mitarbeiter_id": mitarbeiter_id,
                    "user_id": created_by,
                    "event_type": "compliance_warning",
                    "entity": "zeit_eintraege",
                    "entity_id": str(mitarbeiter_id),
                    "after_data": [f.__dict__ for f in findings],
                    "reason": "Automatische ArbZG-Prüfung",
                }
            ).execute()
        except Exception:
            # Rückwärtskompatibilität: wenn audit_logs noch nicht migriert ist.
            pass

    return {"ok": True, "findings": [f.__dict__ for f in findings]}

