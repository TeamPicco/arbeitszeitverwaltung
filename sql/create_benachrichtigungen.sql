-- Tabelle für Benachrichtigungen an Admin
CREATE TABLE IF NOT EXISTS benachrichtigungen (
    id BIGSERIAL PRIMARY KEY,
    mitarbeiter_id BIGINT REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    typ VARCHAR(50) NOT NULL,
    nachricht TEXT NOT NULL,
    gelesen BOOLEAN DEFAULT FALSE,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_benachrichtigungen_gelesen ON benachrichtigungen(gelesen);
CREATE INDEX IF NOT EXISTS idx_benachrichtigungen_erstellt ON benachrichtigungen(erstellt_am DESC);

-- Tabelle für Änderungsanfragen
CREATE TABLE IF NOT EXISTS aenderungsanfragen (
    id BIGSERIAL PRIMARY KEY,
    mitarbeiter_id BIGINT REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    feld VARCHAR(50) NOT NULL,
    alter_wert TEXT,
    neuer_wert TEXT NOT NULL,
    grund TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    bearbeitet_am TIMESTAMP WITH TIME ZONE,
    bearbeitet_von BIGINT REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_aenderungsanfragen_status ON aenderungsanfragen(status);
