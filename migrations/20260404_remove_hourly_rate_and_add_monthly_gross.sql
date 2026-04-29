-- Produktionshärtung April 2026:
-- 1) Stundenlohn aus Stammdaten entfernen
-- 2) Monatsbrutto als Vertragswert einführen
-- 3) Vertrags-Tabelle auf Monatsbrutto umstellen

BEGIN;

-- Mitarbeiter: neues Feld für Monatsbrutto
ALTER TABLE IF EXISTS public.mitarbeiter
    ADD COLUMN IF NOT EXISTS monatliche_brutto_verguetung NUMERIC(10,2);

-- Optionaler Daten-Backfill aus Legacy-Stundenlohn, nur wenn Legacy-Spalte existiert
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'mitarbeiter'
          AND column_name = 'stundenlohn_brutto'
    ) THEN
        EXECUTE '
            UPDATE public.mitarbeiter
            SET monatliche_brutto_verguetung = ROUND(
                COALESCE(monatliche_brutto_verguetung, 0)
                + (COALESCE(stundenlohn_brutto, 0) * COALESCE(monatliche_soll_stunden, 0)),
                2
            )
            WHERE COALESCE(monatliche_brutto_verguetung, 0) = 0
              AND COALESCE(stundenlohn_brutto, 0) > 0
              AND COALESCE(monatliche_soll_stunden, 0) > 0
        ';
    END IF;
END $$;

-- Verträge: Monatsbrutto ergänzen
ALTER TABLE IF EXISTS public.vertraege
    ADD COLUMN IF NOT EXISTS monatsbrutto_verguetung NUMERIC(10,2);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'vertraege'
          AND column_name = 'stundenlohn_brutto'
    ) THEN
        EXECUTE '
            UPDATE public.vertraege
            SET monatsbrutto_verguetung = ROUND(
                COALESCE(monatsbrutto_verguetung, 0)
                + (COALESCE(stundenlohn_brutto, 0) * COALESCE(soll_stunden_monat, 0)),
                2
            )
            WHERE COALESCE(monatsbrutto_verguetung, 0) = 0
              AND COALESCE(stundenlohn_brutto, 0) > 0
              AND COALESCE(soll_stunden_monat, 0) > 0
        ';
    END IF;
END $$;

-- Legacy-Felder entfernen (idempotent, nur wenn vorhanden)
ALTER TABLE IF EXISTS public.vertraege
    DROP COLUMN IF EXISTS stundenlohn_brutto;

ALTER TABLE IF EXISTS public.mitarbeiter
    DROP COLUMN IF EXISTS stundenlohn_brutto;

COMMIT;
