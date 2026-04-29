-- Alle Mitarbeiter ohne betrieb_id dem einzigen / ersten Betrieb zuordnen.
-- Einmalige Datenmigration für Bestandsdaten aus dem alten Streamlit-System.

UPDATE public.mitarbeiter
SET betrieb_id = (SELECT id FROM public.betriebe ORDER BY id LIMIT 1)
WHERE betrieb_id IS NULL;
