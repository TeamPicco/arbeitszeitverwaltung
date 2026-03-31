from datetime import datetime, timezone

from utils.compliance import (
    check_arbzg_breaks,
    check_daily_work_limit,
    check_rest_period,
)


def test_break_rule_violation():
    findings = check_arbzg_breaks(work_minutes=8 * 60, break_minutes=15)
    assert any(f.code == "ARBZG_4_BREAK" for f in findings)


def test_daily_limit_warning_and_error():
    warn = check_daily_work_limit(work_minutes=9 * 60)
    err = check_daily_work_limit(work_minutes=11 * 60)
    assert any(f.code == "ARBZG_3_DAILY_SOFT" for f in warn)
    assert any(f.code == "ARBZG_3_DAILY_HARD" for f in err)


def test_rest_period_violation():
    end_prev = datetime(2026, 3, 10, 22, 0, tzinfo=timezone.utc)
    start_next = datetime(2026, 3, 11, 6, 0, tzinfo=timezone.utc)
    findings = check_rest_period(end_prev, start_next)
    assert any(f.code == "ARBZG_5_REST" for f in findings)
