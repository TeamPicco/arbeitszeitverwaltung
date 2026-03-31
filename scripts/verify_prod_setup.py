#!/usr/bin/env python3
"""
Schneller Verifikations-Check für Produktionskern-Rollout.

Prüft:
1) Kern-Migrationsdatei vorhanden
2) RLS-Service-Role-Skript vorhanden
3) Erwartete Tabellen/Funktionen im SQL enthalten
4) Erwartete Event-Aktionen im Python-Code referenziert
"""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "20260331_produktionskern_zeiterfassung.sql"
RLS = ROOT / "sql" / "SETUP_RLS_SERVICE_ROLE.sql"
ZEIT_EVENTS = ROOT / "utils" / "zeit_events.py"


def must_contain(path: Path, markers: list[str]) -> list[str]:
    missing: list[str] = []
    content = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in content:
            missing.append(f"{path.name}: '{marker}'")
    return missing


def main() -> int:
    errors: list[str] = []

    if not MIGRATION.exists():
        errors.append(f"Fehlt: {MIGRATION}")
    if not RLS.exists():
        errors.append(f"Fehlt: {RLS}")
    if not ZEIT_EVENTS.exists():
        errors.append(f"Fehlt: {ZEIT_EVENTS}")

    if not errors:
        errors.extend(
            must_contain(
                MIGRATION,
                [
                    "CREATE TABLE IF NOT EXISTS public.zeit_eintraege",
                    "CREATE TABLE IF NOT EXISTS public.abwesenheiten",
                    "CREATE TABLE IF NOT EXISTS public.arbeitszeit_konten",
                    "CREATE TABLE IF NOT EXISTS public.mitarbeiter_geraete",
                    "CREATE TABLE IF NOT EXISTS public.audit_logs",
                    "CREATE TYPE public.zeit_aktion AS ENUM ('clock_in', 'clock_out', 'break_start', 'break_end')",
                ],
            )
        )
        errors.extend(
            must_contain(
                RLS,
                [
                    "service_role",
                    "ALTER TABLE public.",
                    "CREATE OR REPLACE FUNCTION public.ensure_policy",
                ],
            )
        )
        errors.extend(
            must_contain(
                ZEIT_EVENTS,
                [
                    "EVENT_BREAK_START",
                    "EVENT_BREAK_END",
                    "register_time_event",
                    "validate_event_transition",
                ],
            )
        )

    if errors:
        print("❌ Produktions-Setup-Verify fehlgeschlagen:")
        for err in errors:
            print(f" - {err}")
        return 1

    print("✅ Produktions-Setup-Verify erfolgreich.")
    print(f" - Migration: {MIGRATION.relative_to(ROOT)}")
    print(f" - RLS:       {RLS.relative_to(ROOT)}")
    print(f" - Events:    {ZEIT_EVENTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

