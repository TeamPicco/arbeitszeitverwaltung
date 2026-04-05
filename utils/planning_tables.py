from __future__ import annotations

from functools import lru_cache
from time import monotonic
from typing import Iterable, List, Optional


@lru_cache(maxsize=1)
def _planning_table_candidates() -> tuple[str, str]:
    # Bevorzugt das neue/pluralisierte Schema, fällt auf Legacy zurück.
    return ("dienstplaene", "dienstplan")


_PLANNING_TABLE_CACHE_SECONDS = 600.0
_planning_table_cache_value: str | None = None
_planning_table_cache_ts: float = 0.0


def clear_planning_table_cache() -> None:
    global _planning_table_cache_value, _planning_table_cache_ts
    _planning_table_cache_value = None
    _planning_table_cache_ts = 0.0


def resolve_planning_table(supabase) -> str:
    """
    Ermittelt die verfügbare Dienstplan-Tabelle.
    """
    global _planning_table_cache_value, _planning_table_cache_ts
    now = monotonic()
    if _planning_table_cache_value and (now - _planning_table_cache_ts) < _PLANNING_TABLE_CACHE_SECONDS:
        return _planning_table_cache_value

    existing: list[tuple[str, int]] = []
    for table in _planning_table_candidates():
        try:
            res = supabase.table(table).select("id", count="exact").limit(1).execute()
            cnt = int(res.count or 0)
            existing.append((table, cnt))
        except Exception:
            continue
    if existing:
        # Wenn beide Tabellen existieren, bevorzugen wir die mit Daten.
        with_data = [row for row in existing if row[1] > 0]
        if with_data:
            with_data.sort(key=lambda x: x[1], reverse=True)
            _planning_table_cache_value = with_data[0][0]
            _planning_table_cache_ts = now
            return _planning_table_cache_value
        # Beide leer: nimm den ersten existierenden Kandidaten.
        _planning_table_cache_value = existing[0][0]
        _planning_table_cache_ts = now
        return _planning_table_cache_value
    # Letzter Fallback: historischer Name.
    _planning_table_cache_value = "dienstplan"
    _planning_table_cache_ts = now
    return _planning_table_cache_value

