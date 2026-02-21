-- Multi-Tenancy: Betriebe-Tabelle
CREATE TABLE IF NOT EXISTS betriebe (
    id BIGSERIAL PRIMARY KEY,
    betriebsnummer VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    beschreibung TEXT,
    logo_url TEXT,
    aktiv BOOLEAN DEFAULT TRUE,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    aktualisiert_am TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_betriebe_betriebsnummer ON betriebe(betriebsnummer);
CREATE INDEX IF NOT EXISTS idx_betriebe_aktiv ON betriebe(aktiv);

COMMENT ON TABLE betriebe IS 'Betriebe/Mandanten für Multi-Tenancy';
COMMENT ON COLUMN betriebe.betriebsnummer IS 'Eindeutige Betriebsnummer für Login';

-- Füge Betrieb-Referenz zu users-Tabelle hinzu
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES betriebe(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_users_betrieb ON users(betrieb_id);

-- Füge Betrieb-Referenz zu mitarbeiter-Tabelle hinzu
ALTER TABLE mitarbeiter 
ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES betriebe(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_mitarbeiter_betrieb ON mitarbeiter(betrieb_id);

-- Füge Betrieb-Referenz zu allen relevanten Tabellen hinzu
ALTER TABLE zeiterfassungen 
ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES betriebe(id) ON DELETE CASCADE;

ALTER TABLE urlaubsantraege 
ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES betriebe(id) ON DELETE CASCADE;

ALTER TABLE benachrichtigungen 
ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES betriebe(id) ON DELETE CASCADE;

ALTER TABLE aenderungsanfragen 
ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES betriebe(id) ON DELETE CASCADE;

ALTER TABLE plauderecke 
ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES betriebe(id) ON DELETE CASCADE;

ALTER TABLE mastergeraete 
ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES betriebe(id) ON DELETE CASCADE;

-- Indizes für Performance
CREATE INDEX IF NOT EXISTS idx_zeiterfassungen_betrieb ON zeiterfassungen(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_urlaubsantraege_betrieb ON urlaubsantraege(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_benachrichtigungen_betrieb ON benachrichtigungen(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_aenderungsanfragen_betrieb ON aenderungsanfragen(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_plauderecke_betrieb ON plauderecke(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_mastergeraete_betrieb ON mastergeraete(betrieb_id);

-- Erstelle Steakhouse Piccolo als ersten Betrieb
INSERT INTO betriebe (betriebsnummer, name, beschreibung, aktiv)
VALUES ('20262204', 'Steakhouse Piccolo', 'Steakhouse Piccolo Leipzig', TRUE)
ON CONFLICT (betriebsnummer) DO NOTHING;

-- Aktualisiere bestehende Daten mit Piccolo betrieb_id
-- WICHTIG: Dies muss nach dem ersten INSERT ausgeführt werden
DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    -- Hole Piccolo ID
    SELECT id INTO piccolo_id FROM betriebe WHERE betriebsnummer = '20262204';
    
    IF piccolo_id IS NOT NULL THEN
        -- Aktualisiere users
        UPDATE users SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        
        -- Aktualisiere mitarbeiter
        UPDATE mitarbeiter SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        
        -- Aktualisiere zeiterfassungen
        UPDATE zeiterfassungen SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        
        -- Aktualisiere urlaubsantraege
        UPDATE urlaubsantraege SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        
        -- Aktualisiere benachrichtigungen
        UPDATE benachrichtigungen SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        
        -- Aktualisiere aenderungsanfragen
        UPDATE aenderungsanfragen SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        
        -- Aktualisiere plauderecke
        UPDATE plauderecke SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        
        -- Aktualisiere mastergeraete
        UPDATE mastergeraete SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
    END IF;
END $$;
