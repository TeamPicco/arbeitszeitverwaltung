-- Tabelle für Plauderecke (interner Chat)
CREATE TABLE IF NOT EXISTS plauderecke (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    nachricht TEXT NOT NULL,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plauderecke_erstellt ON plauderecke(erstellt_am DESC);
CREATE INDEX IF NOT EXISTS idx_plauderecke_user ON plauderecke(user_id);
