"""
Kalenderbasierte Datumshilfen.

Zentrale Single-Source-of-Truth für Monatsarithmetik, um redundante
``_add_months`` / ``_plus_months``-Implementierungen in mehreren Modulen zu
vermeiden.
"""

from __future__ import annotations

import calendar
from datetime import date


def add_months(source: date, months: int) -> date:
    """
    Addiert ``months`` Monate kalendergenau zu ``source``.

    - Negative Werte subtrahieren.
    - Wenn der Ursprungstag im Zielmonat nicht existiert (z. B. 31.01. + 1),
      wird auf den letzten gültigen Tag des Zielmonats gekappt.
    - ``months == 0`` gibt ``source`` unverändert zurück.
    """
    if not isinstance(source, date):
        raise TypeError("source muss ein datetime.date sein")
    months = int(months)
    if months == 0:
        return source

    total_month_index = (source.month - 1) + months
    year = source.year + total_month_index // 12
    month = total_month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(source.day, last_day)
    return date(year, month, day)
