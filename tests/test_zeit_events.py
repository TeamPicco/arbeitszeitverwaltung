from datetime import datetime, timezone

from utils.zeit_events import (
    EVENT_BREAK_END,
    EVENT_BREAK_START,
    EVENT_CLOCK_IN,
    EVENT_CLOCK_OUT,
    evaluate_daily_compliance,
    validate_event_transition,
)


def _evt(action: str, ts: str):
    return {"aktion": action, "_ts": datetime.fromisoformat(ts.replace("Z", "+00:00"))}


def test_transition_rules():
    events = []
    ok, _ = validate_event_transition(events, EVENT_CLOCK_OUT)
    assert not ok

    events = [_evt(EVENT_CLOCK_IN, "2026-03-31T08:00:00Z")]
    ok, _ = validate_event_transition(events, EVENT_BREAK_START)
    assert ok
    ok, _ = validate_event_transition(events, EVENT_CLOCK_IN)
    assert not ok


def test_daily_compliance_detects_short_break():
    day = datetime(2026, 3, 31, tzinfo=timezone.utc).date()
    events = [
        _evt(EVENT_CLOCK_IN, "2026-03-31T07:00:00Z"),
        _evt(EVENT_BREAK_START, "2026-03-31T12:00:00Z"),
        _evt(EVENT_BREAK_END, "2026-03-31T12:10:00Z"),
        _evt(EVENT_CLOCK_OUT, "2026-03-31T16:30:00Z"),
    ]
    findings = evaluate_daily_compliance(events, day)
    assert any(f.code == "ARBZG_4_BREAK" for f in findings)

