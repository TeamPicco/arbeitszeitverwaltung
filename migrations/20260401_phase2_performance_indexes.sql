-- Phase 2 Performance: gezielte Indizes für häufige Filter-/Sortierpfade
-- Nicht-destruktiv, mehrfach ausführbar.

BEGIN;

-- Zeiterfassung: häufig nach Mitarbeiter + Zeitraum + Datum sortiert
CREATE INDEX IF NOT EXISTS idx_zeiterfassung_mitarbeiter_datum_desc
    ON public.zeiterfassung (mitarbeiter_id, datum DESC);

-- Zeiterfassung: häufige Mandantenfilter
CREATE INDEX IF NOT EXISTS idx_zeiterfassung_betrieb_id
    ON public.zeiterfassung (betrieb_id);

-- Abwesenheiten: Betrieb + created_at (Admin-Liste)
CREATE INDEX IF NOT EXISTS idx_abwesenheiten_betrieb_created_at_desc
    ON public.abwesenheiten (betrieb_id, created_at DESC);

-- Abwesenheiten: Mitarbeiter + Zeitraumabfragen
CREATE INDEX IF NOT EXISTS idx_abwesenheiten_mitarbeiter_zeitraum_phase2
    ON public.abwesenheiten (mitarbeiter_id, start_datum, ende_datum);

-- Urlaubsanträge: Status + Überlappung im Zeitraum
CREATE INDEX IF NOT EXISTS idx_urlaubsantraege_status_von_bis
    ON public.urlaubsantraege (status, von_datum, bis_datum);

-- Mitarbeiter: Mandant + Sortierung nach Nachname
CREATE INDEX IF NOT EXISTS idx_mitarbeiter_betrieb_nachname
    ON public.mitarbeiter (betrieb_id, nachname);

-- Arbeitszeitkonten: häufige Anzeige/Sortierung nach Mitarbeiter
CREATE INDEX IF NOT EXISTS idx_arbeitszeit_konten_mitarbeiter
    ON public.arbeitszeit_konten (mitarbeiter_id);

-- Monatsabschlüsse: Lookup pro Monat/Jahr/Betrieb
CREATE INDEX IF NOT EXISTS idx_azk_monatsabschluesse_betrieb_monat_jahr
    ON public.azk_monatsabschluesse (betrieb_id, monat, jahr, mitarbeiter_id);

-- Dienstplanung (neues Schema)
CREATE INDEX IF NOT EXISTS idx_dienstplaene_betrieb_datum
    ON public.dienstplaene (betrieb_id, datum);
CREATE INDEX IF NOT EXISTS idx_dienstplaene_mitarbeiter_datum
    ON public.dienstplaene (mitarbeiter_id, datum);

-- Dienstplanung (Legacy-Schema) - nur anlegen, wenn Tabelle existiert
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'dienstplan'
    ) THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_dienstplan_betrieb_datum ON public.dienstplan (betrieb_id, datum)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_dienstplan_mitarbeiter_datum ON public.dienstplan (mitarbeiter_id, datum)';
    END IF;
END $$;

COMMIT;
