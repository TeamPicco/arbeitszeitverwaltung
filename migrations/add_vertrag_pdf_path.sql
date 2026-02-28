-- Migration: vertrag_pdf_path Spalte zur mitarbeiter-Tabelle hinzufügen
-- Fehler: PGRST204 "Could not find the 'vertrag_pdf_path' column"
-- Ausführen im Supabase SQL-Editor

ALTER TABLE mitarbeiter
    ADD COLUMN IF NOT EXISTS vertrag_pdf_path TEXT DEFAULT NULL;

-- Kommentar
COMMENT ON COLUMN mitarbeiter.vertrag_pdf_path IS 'Pfad zur Arbeitsvertrag-PDF in Supabase Storage (Bucket: arbeitsvertraege)';
