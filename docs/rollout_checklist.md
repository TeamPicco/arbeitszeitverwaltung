# Rollout-Checklist (Migrations + RLS + Verify)

## 1. Migration ausführen

Im Supabase SQL-Editor:

1. `migrations/20260331_produktionskern_zeiterfassung.sql` ausführen
2. Erfolgreich prüfen:
   - `zeit_eintraege`
   - `abwesenheiten`
   - `arbeitszeit_konten`
   - `mitarbeiter_geraete`
   - `audit_logs`

## 2. RLS-Skript ausführen

Im Supabase SQL-Editor:

1. `sql/SETUP_RLS_SERVICE_ROLE.sql` ausführen
2. Sicherstellen, dass die App mit Service-Role-fähigem Backendpfad läuft.

## 3. Lokal/CI-Verify

```bash
python3 scripts/verify_prod_setup.py
```

Erwartung:
- Ausgabe `Produktions-Setup-Verify erfolgreich`

## 4. Smoke Tests in der App

1. **Terminal-Stempeln**
   - Kommen → Pause Start → Pause Ende → Gehen
2. **Abwesenheit**
   - Urlaub/Krankheit/Sonderurlaub mit optionalem Attest speichern
3. **Arbeitszeitkonto**
   - Synchronisierung im Admin-Tab ausführen
   - Werte in Mitarbeiteransicht prüfen
4. **Dienstplanung**
   - Prüfen, dass sowohl `dienstplaene` als auch Legacy `dienstplan` in der Umgebung funktionieren.
