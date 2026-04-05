from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List, Optional


@lru_cache(maxsize=1)
def _planning_table_candidates() -> tuple[str, str]:
    # Bevorzugt das neue/pluralisierte Schema, fällt auf Legacy zurück.
    return ("dienstplaene", "dienstplan")


def resolve_planning_table(supabase) -> str:
    """
    Ermittelt die verfügbare Dienstplan-Tabelle.
    """
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
            return with_data[0][0]
        # Beide leer: nimm den ersten existierenden Kandidaten.
        return existing[0][0]
    # Letzter Fallback: historischer Name.
    return "dienstplan"

