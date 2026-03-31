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
    for table in _planning_table_candidates():
        try:
            supabase.table(table).select("id").limit(1).execute()
            return table
        except Exception:
            continue
    # Letzter Fallback: historischer Name.
    return "dienstplan"

