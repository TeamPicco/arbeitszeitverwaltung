-- ============================================
-- MIGRATION: Beschäftigungsart und Minijob-Grenze
-- Datum: 2025-02
-- Ausführen in Supabase SQL-Editor
-- ============================================

-- Spalte beschaeftigungsart hinzufügen (falls nicht vorhanden)
ALTER TABLE mitarbeiter
    ADD COLUMN IF NOT EXISTS beschaeftigungsart VARCHAR(20) DEFAULT 'vollzeit'
    CHECK (beschaeftigungsart IN ('vollzeit', 'teilzeit', 'minijob', 'werkstudent', 'azubi'));

-- Spalte minijob_monatsgrenze hinzufügen (falls nicht vorhanden)
ALTER TABLE mitarbeiter
    ADD COLUMN IF NOT EXISTS minijob_monatsgrenze DECIMAL(8,2) DEFAULT NULL;

-- Bestehende Datensätze auf 'vollzeit' setzen
UPDATE mitarbeiter
    SET beschaeftigungsart = 'vollzeit'
    WHERE beschaeftigungsart IS NULL;

-- Fertig
-- Nach Ausführung dieser Migration sind die neuen Felder
-- in der App unter Mitarbeiterverwaltung → Bearbeiten sichtbar.
