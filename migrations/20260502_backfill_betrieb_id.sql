-- ============================================================
-- Datenmigration: betrieb_id in historischen Daten nachfüllen
--
-- Problem: Alte Daten aus dem Streamlit-System haben keine
--          betrieb_id gesetzt. Die neue React-App filtert
--          immer nach betrieb_id → historische Daten unsichtbar.
--
-- Ausführen: Supabase SQL-Editor, betrieb_id anpassen (Standard: 1)
-- ============================================================

-- ── 1. Dienstplan-Einträge ────────────────────────────────────────────────────
-- Setzt betrieb_id aus der verknüpften mitarbeiter-Tabelle

UPDATE dienstplaene dp
SET betrieb_id = ma.betrieb_id
FROM mitarbeiter ma
WHERE dp.mitarbeiter_id = ma.id
  AND dp.betrieb_id IS NULL;

-- Ergebnis prüfen:
-- SELECT COUNT(*) FROM dienstplaene WHERE betrieb_id IS NULL;

-- ── 2. Zeiterfassung ─────────────────────────────────────────────────────────
-- Setzt betrieb_id aus der verknüpften mitarbeiter-Tabelle

UPDATE zeiterfassung ze
SET betrieb_id = ma.betrieb_id
FROM mitarbeiter ma
WHERE ze.mitarbeiter_id = ma.id
  AND ze.betrieb_id IS NULL;

-- Ergebnis prüfen:
-- SELECT COUNT(*) FROM zeiterfassung WHERE betrieb_id IS NULL;

-- ── 3. Urlaubsanträge ────────────────────────────────────────────────────────
-- (falls betrieb_id-Spalte vorhanden ist)

UPDATE urlaubsantraege ua
SET betrieb_id = ma.betrieb_id
FROM mitarbeiter ma
WHERE ua.mitarbeiter_id = ma.id
  AND ua.betrieb_id IS NULL;

-- ── 4. Abwesenheiten ─────────────────────────────────────────────────────────

UPDATE abwesenheiten ab
SET betrieb_id = ma.betrieb_id
FROM mitarbeiter ma
WHERE ab.mitarbeiter_id = ma.id
  AND ab.betrieb_id IS NULL;

-- ── 5. Dienstplanwünsche ─────────────────────────────────────────────────────

UPDATE dienstplanwuensche dw
SET betrieb_id = ma.betrieb_id
FROM mitarbeiter ma
WHERE dw.mitarbeiter_id = ma.id
  AND dw.betrieb_id IS NULL;

-- ── Kontrollabfragen ─────────────────────────────────────────────────────────
-- Nach der Ausführung prüfen:

SELECT 'dienstplaene' AS tabelle, COUNT(*) AS gesamt,
       SUM(CASE WHEN betrieb_id IS NULL THEN 1 ELSE 0 END) AS ohne_betrieb_id
FROM dienstplaene
UNION ALL
SELECT 'zeiterfassung', COUNT(*),
       SUM(CASE WHEN betrieb_id IS NULL THEN 1 ELSE 0 END)
FROM zeiterfassung
UNION ALL
SELECT 'urlaubsantraege', COUNT(*),
       SUM(CASE WHEN betrieb_id IS NULL THEN 1 ELSE 0 END)
FROM urlaubsantraege
UNION ALL
SELECT 'abwesenheiten', COUNT(*),
       SUM(CASE WHEN betrieb_id IS NULL THEN 1 ELSE 0 END)
FROM abwesenheiten;
