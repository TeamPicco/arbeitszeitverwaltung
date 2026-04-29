-- ============================================
-- MIGRATION: Dienstplan Schichttypen (Urlaub/Frei/Arbeit)
-- Datum: 2025-02
-- Ausführen in Supabase SQL-Editor
-- ============================================

-- Schichttyp-Spalte hinzufügen
ALTER TABLE dienstplaene
    ADD COLUMN IF NOT EXISTS schichttyp VARCHAR(10) DEFAULT 'arbeit'
    CHECK (schichttyp IN ('arbeit', 'urlaub', 'frei'));

-- Urlaubsstunden pro Tag (für Lohnberechnung)
ALTER TABLE dienstplaene
    ADD COLUMN IF NOT EXISTS urlaub_stunden DECIMAL(5,2) DEFAULT NULL;

-- Verknüpfung mit Urlaubsantrag (BIGINT, da alle IDs BIGSERIAL sind)
ALTER TABLE dienstplaene
    ADD COLUMN IF NOT EXISTS urlaubsantrag_id BIGINT REFERENCES urlaubsantraege(id) ON DELETE SET NULL;

-- Bestehende Einträge auf 'arbeit' setzen
UPDATE dienstplaene
    SET schichttyp = 'arbeit'
    WHERE schichttyp IS NULL;

-- Arbeitszeitkonto: urlaubsstunden-Spalte hinzufügen
ALTER TABLE arbeitszeitkonto
    ADD COLUMN IF NOT EXISTS urlaubsstunden DECIMAL(6,2) DEFAULT 0;

-- Unique-Constraint für mitarbeiter_id + datum (verhindert Duplikate)
-- Nur ausführen wenn noch nicht vorhanden:
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'dienstplaene_mitarbeiter_datum_unique'
    ) THEN
        ALTER TABLE dienstplaene
            ADD CONSTRAINT dienstplaene_mitarbeiter_datum_unique
            UNIQUE (mitarbeiter_id, datum);
    END IF;
END $$;

-- Fertig
-- Nach Ausführung dieser Migration sind Urlaub/Frei-Einträge im Dienstplan möglich.
