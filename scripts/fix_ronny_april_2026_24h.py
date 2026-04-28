"""
Einmaliges Admin-Skript zur Korrektur eines fehlerhaften 24h-Zeiteintrags
für Ronny Franke (April 2026).

Nutzung:
  python3 scripts/fix_ronny_april_2026_24h.py

Voraussetzungen:
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY (oder SUPABASE_SERVICE_KEY / SUPABASE_KEY)
"""

from __future__ import annotations

import os
from datetime import datetime

from supabase import create_client


TARGET_DATES = ("2026-04-12", "2026-04-14")
MAX_HOURS = 10.0


def _get_client():
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
    )
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY fehlen.")
    return create_client(url, key)


def _hms_to_minutes(hms: str | None) -> int:
    if not hms:
        return 0
    raw = str(hms).strip()[:8]
    try:
        h = int(raw[0:2])
        m = int(raw[3:5])
        s = int(raw[6:8]) if len(raw) >= 8 else 0
    except Exception:
        return 0
    return h * 60 + m + (1 if s >= 30 else 0)


def _minutes_to_hhmmss(total_minutes: int) -> str:
    total_minutes = max(0, int(total_minutes))
    h = (total_minutes // 60) % 24
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}:00"


def main() -> None:
    sb = _get_client()

    employees = (
        sb.table("mitarbeiter")
        .select("id, vorname, nachname, personalnummer")
        .ilike("vorname", "Ronny")
        .ilike("nachname", "Franke")
        .execute()
        .data
        or []
    )
    if not employees:
        print("Ronny Franke nicht gefunden.")
        return
    ma = employees[0]
    ma_id = ma["id"]
    print("Mitarbeiter gefunden.")

    rows = (
        sb.table("zeiterfassung")
        .select("id, datum, start_zeit, ende_zeit, pause_minuten, arbeitsstunden, quelle")
        .eq("mitarbeiter_id", ma_id)
        .in_("datum", list(TARGET_DATES))
        .order("datum")
        .order("start_zeit")
        .execute()
        .data
        or []
    )
    if not rows:
        print("Keine Zeiteinträge auf Zielterminen gefunden.")
        return

    for row in rows:
        zid = row.get("id")
        datum = row.get("datum")
        start = row.get("start_zeit")
        ende = row.get("ende_zeit")
        pause = int(row.get("pause_minuten") or 0)
        logged_hours = float(row.get("arbeitsstunden") or 0.0)

        start_min = _hms_to_minutes(start)
        end_min = _hms_to_minutes(ende)
        gross = end_min - start_min
        if gross < 0:
            gross += 24 * 60
        net = max(0, gross - pause)
        net_h = round(net / 60.0, 2)

        print(
            f"[{datum}] id={zid} start={start} ende={ende} "
            f"pause={pause} calc={net_h}h db={logged_hours}h"
        )

        # Nur offensichtlich fehlerhafte Extremfälle korrigieren.
        if net_h <= MAX_HOURS and logged_hours <= MAX_HOURS:
            continue

        # 1) Falls Ende leer/00:00 ist -> auf max. 10h ab Start deckeln.
        # 2) Falls netto > 10h -> Ende entsprechend zurücksetzen.
        capped_net_minutes = int(MAX_HOURS * 60)
        capped_gross_minutes = capped_net_minutes + pause
        new_end_min = (start_min + capped_gross_minutes) % (24 * 60)
        new_end = _minutes_to_hhmmss(new_end_min)
        new_hours = round(capped_net_minutes / 60.0, 2)

        payload = {
            "ende_zeit": new_end,
            "arbeitsstunden": new_hours,
            "updated_at": datetime.utcnow().isoformat(),
            "korrektur_grund": "Auto-Korrektur: fehlerhafter Dienst auf 10h gedeckelt",
        }
        sb.table("zeiterfassung").update(payload).eq("id", zid).execute()
        print(f"  -> korrigiert: ende_zeit={new_end}, arbeitsstunden={new_hours}")


if __name__ == "__main__":
    main()
