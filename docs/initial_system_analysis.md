# Initiale Systemanalyse (Stand: 31.03.2026)

## 1) Architektur-Überblick

- **Frontend/UI:** Streamlit (`app.py`, `pages/*`, `kiosk_stempeluhr.py`)
- **Backend-Logik:** Python-Module in `utils/*` (kein separates API-Backend)
- **Datenbank:** Supabase PostgreSQL (mehrere SQL-Skripte + `migrations/*`)
- **Storage:** Supabase Storage (Dokumente/PDF Uploads via REST in `utils/database.py`)
- **Auth:** Custom Login über `users` + bcrypt (`verify_credentials_with_betrieb`), keine durchgängige Supabase-Auth-JWT-Architektur
- **Mandantenfähigkeit:** `betriebe` + `betrieb_id`-Felder, jedoch historisch inkonsistente Rollout-Skripte

## 2) Datenbank-Schema (Ist-Zustand vor Erweiterung)

### Kern-Tabellen (bereits vorhanden)
- `users`
- `mitarbeiter`
- `zeiterfassung`
- `urlaubsantraege`
- `arbeitszeitkonto`
- `lohnabrechnungen`
- Multi-Tenancy/Feature-Tabellen in `sql/*`: `betriebe`, `mastergeraete`, `benachrichtigungen`, `plauderecke`, `aenderungsanfragen`, u.a.

### Kritische Inkonsistenzen (gefunden)
- Tabellenname driftet zwischen `zeiterfassung` und `zeiterfassungen`.
- RLS-Skripte mischen `auth.uid()`-Policies mit einer App, die primär custom login nutzt.
- Mehrere "Setup"-Dateien mit überlappenden Zielen (`supabase_schema*.sql`, `sql/SETUP_*`), kein klarer Single Source of Truth.

## 3) Supabase-Konfiguration (Ist)

- **RLS:** vorhanden, aber uneinheitlich; teils zu offen (`USING (true)`), teils nicht passend zum Auth-Modell.
- **Storage:** Upload-Funktion vorhanden, aber ursprünglich teilweise unsaubere Datei.
- **Edge Functions:** im Repo nicht vorhanden.

## 4) Backend-/Domänenlogik (Ist)

- Umfangreiche Domänenmodule:
  - `utils/lohnberechnung.py` (Pausen, Zuschläge, Feiertagslogik Sachsen)
  - `utils/azk.py` / `utils/lohnabrechnung.py` / `utils/lohnkern.py`
- Zusätzlich signifikante Altlasten:
  - Syntaxfehler in Kernmodulen
  - doppelte/fragmentierte Logiken (AZK-Berechnung in mehreren Modulen)
  - fehlende konsistente Event-Architektur für `clock_in/out` + Pausenereignisse

## 5) Frontend/UI-Struktur

- Login + Terminal-Stempeln in `app.py`
- Kiosk-Modus in `kiosk_stempeluhr.py`
- Admin-Features in `pages/*`:
  - Dienstplanung
  - Mastergeräte
  - Zeitauswertung / Lohn

## 6) Zeiterfassungslogik (Ist)

- Primär tabellenzentriert (`zeiterfassung`), direkte Inserts/Updates pro Tag
- Kein durchgängiger Event-Stream für `clock_in`, `clock_out`, `break_start`, `break_end`
- Compliance-Prüfungen (ArbZG) nur teilweise modularisiert

## 7) Bereits funktionale Features (vor Fixes)

- Basis-Mitarbeiterverwaltung
- Admin-/Mitarbeiter-UI
- Dienstplanung (inkl. Vorlagen, PDF/CSV)
- Lohn-/Zeitauswertung
- Geräteverwaltung (Mastergeräte)
- Chat/Benachrichtigung (je nach Setup)

## 8) Hauptprobleme (vor Umsetzung)

1. **Lauffähigkeit:** zentrale Syntaxfehler in produktiven Modulen.
2. **Sicherheit:** Hardcoded Supabase Secret im Kiosk-Modul.
3. **Schema-Drift:** inkonsistente SQL-Artefakte, fehlende kanonische Erweiterung.
4. **RLS-Modell:** nicht konsistent mit custom-auth Architektur.
5. **Compliance/Eventing:** keine robuste Event-Buchungsarchitektur mit klaren Zustandsübergängen.

## 9) Umgesetzte Richtung in diesem Iterationsschritt

- Nicht-destruktive Produktionserweiterung per Migration:
  - `migrations/20260331_produktionskern_zeiterfassung.sql`
- Event-/Compliance-/Geräte-/Abwesenheits-Module ergänzt:
  - `utils/zeit_events.py`
  - `utils/compliance.py`
  - `utils/work_accounts.py`
  - `utils/absences.py`
  - `utils/device_authorization.py`
  - `utils/time_utils.py`
- RLS-Skript für Service-Role-kompatibles Modell:
  - `sql/SETUP_RLS_SERVICE_ROLE.sql`

