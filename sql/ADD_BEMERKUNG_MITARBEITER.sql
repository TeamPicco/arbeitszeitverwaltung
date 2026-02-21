-- Füge fehlende Spalte 'bemerkung_mitarbeiter' zur urlaubsantraege-Tabelle hinzu

ALTER TABLE public.urlaubsantraege 
ADD COLUMN IF NOT EXISTS bemerkung_mitarbeiter TEXT;

-- Kommentar hinzufügen
COMMENT ON COLUMN public.urlaubsantraege.bemerkung_mitarbeiter IS 'Optionale Bemerkung des Mitarbeiters zum Urlaubsantrag';
