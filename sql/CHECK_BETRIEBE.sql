-- Prüfe betriebe-Tabelle
-- Zeige alle Spalten und Werte für Piccolo

SELECT 
    id,
    betriebsnummer,
    name,
    aktiv,
    pg_typeof(aktiv) as aktiv_typ,
    created_at
FROM betriebe
WHERE betriebsnummer = '20262204';

-- Zeige auch alle Betriebe (falls mehrere existieren)
SELECT * FROM betriebe;

-- Prüfe Tabellen-Schema
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'betriebe'
ORDER BY ordinal_position;
