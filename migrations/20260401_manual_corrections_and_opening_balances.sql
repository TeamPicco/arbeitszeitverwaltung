-- April 2026 Produktionsstart: manuelle Korrekturen & Altdaten-Initialisierung
-- Nicht-destruktiv, mehrfach ausführbar.

BEGIN;

-- Zeiterfassung: Pflichtbegründung bei manueller Admin-Korrektur speicherbar machen
ALTER TABLE IF EXISTS public.zeiterfassung
    ADD COLUMN IF NOT EXISTS korrektur_grund TEXT;

-- Monatsabschlüsse: Startwert-/Korrektur-Metadaten
ALTER TABLE IF EXISTS public.azk_monatsabschluesse
    ADD COLUMN IF NOT EXISTS manuelle_korrektur_saldo NUMERIC(9,2),
    ADD COLUMN IF NOT EXISTS korrektur_grund TEXT,
    ADD COLUMN IF NOT EXISTS ist_initialisierung BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS initialisierungs_monat INTEGER,
    ADD COLUMN IF NOT EXISTS initialisierungs_jahr INTEGER;

-- Schnellere Abfragen für Einmal-Initialisierung 2026
CREATE INDEX IF NOT EXISTS idx_azk_init_2026_lookup
    ON public.azk_monatsabschluesse (mitarbeiter_id, jahr, ist_initialisierung);

COMMIT;
