from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from utils.time_utils import to_utc


@dataclass
class ComplianceFinding:
    code: str
    level: str
    message: str


def _minutes(delta: timedelta) -> int:
    return int(delta.total_seconds() // 60)


def check_arbzg_breaks(work_minutes: int, break_minutes: int) -> List[ComplianceFinding]:
    findings: List[ComplianceFinding] = []
    required = 45 if work_minutes > 9 * 60 else 30 if work_minutes > 6 * 60 else 0
    if break_minutes < required:
        findings.append(
            ComplianceFinding(
                code="ARBZG_4_BREAK",
                level="warning",
                message=f"Pausenzeit zu kurz: {break_minutes} Min, erforderlich {required} Min (§4 ArbZG).",
            )
        )
    return findings


def check_daily_work_limit(work_minutes: int) -> List[ComplianceFinding]:
    findings: List[ComplianceFinding] = []
    if work_minutes > 10 * 60:
        findings.append(
            ComplianceFinding(
                code="ARBZG_3_DAILY_HARD",
                level="error",
                message="Tägliche Arbeitszeit über 10 Stunden (§3 ArbZG).",
            )
        )
    elif work_minutes > 8 * 60:
        findings.append(
            ComplianceFinding(
                code="ARBZG_3_DAILY_SOFT",
                level="warning",
                message="Tägliche Arbeitszeit über 8 Stunden; Ausgleich erforderlich (§3 ArbZG).",
            )
        )
    return findings


def check_rest_period(previous_shift_end: datetime | None, current_shift_start: datetime) -> List[ComplianceFinding]:
    findings: List[ComplianceFinding] = []
    if previous_shift_end is None:
        return findings

    end_utc = to_utc(previous_shift_end)
    start_utc = to_utc(current_shift_start)
    gap = _minutes(start_utc - end_utc)
    if gap < 11 * 60:
        findings.append(
            ComplianceFinding(
                code="ARBZG_5_REST",
                level="error",
                message=f"Ruhezeit unterschritten: {gap} Min statt mindestens 660 Min (§5 ArbZG).",
            )
        )
    return findings

