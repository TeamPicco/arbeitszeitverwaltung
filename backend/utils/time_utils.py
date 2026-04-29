from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


GERMAN_TZ_NAME = "Europe/Berlin"


def get_berlin_tz():
    if ZoneInfo is not None:
        return ZoneInfo(GERMAN_TZ_NAME)
    return timezone.utc


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_berlin() -> datetime:
    return now_utc().astimezone(get_berlin_tz())


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_berlin_tz())
    return dt.astimezone(timezone.utc)


def to_berlin(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_berlin_tz())


def format_date_de(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d.%m.%Y")


def format_time_de(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%H:%M")


def format_datetime_de(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d.%m.%Y %H:%M")


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None
