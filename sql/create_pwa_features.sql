-- Erweitere mitarbeiter-Tabelle um mobile Zeiterfassung
ALTER TABLE mitarbeiter 
ADD COLUMN IF NOT EXISTS mobile_zeiterfassung BOOLEAN DEFAULT FALSE;

-- Kommentar hinzufügen
COMMENT ON COLUMN mitarbeiter.mobile_zeiterfassung IS 'Erlaubt Zeiterfassung per Mobile App (für Außendienst)';

-- Tabelle für Mastergeräte (registrierte Terminals)
CREATE TABLE IF NOT EXISTS mastergeraete (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    beschreibung TEXT,
    geraete_code VARCHAR(50) UNIQUE NOT NULL,
    aktiv BOOLEAN DEFAULT TRUE,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    letzter_zugriff TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_mastergeraete_code ON mastergeraete(geraete_code);
CREATE INDEX IF NOT EXISTS idx_mastergeraete_aktiv ON mastergeraete(aktiv);

COMMENT ON TABLE mastergeraete IS 'Registrierte Terminals für Zeiterfassung';

-- Tabelle für Push-Subscriptions
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    user_agent TEXT,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user ON push_subscriptions(user_id);

COMMENT ON TABLE push_subscriptions IS 'Push-Benachrichtigungs-Abonnements für PWA';

-- Tabelle für Zeiterfassungs-Audit-Log (Admin-Korrekturen)
CREATE TABLE IF NOT EXISTS zeiterfassung_audit (
    id BIGSERIAL PRIMARY KEY,
    zeiterfassung_id BIGINT REFERENCES zeiterfassungen(id) ON DELETE CASCADE,
    admin_user_id BIGINT REFERENCES users(id),
    aktion VARCHAR(50) NOT NULL, -- 'korrektur', 'loeschung', 'erstellung'
    feld VARCHAR(50),
    alter_wert TEXT,
    neuer_wert TEXT,
    grund TEXT,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zeiterfassung_audit_zeiterfassung ON zeiterfassung_audit(zeiterfassung_id);
CREATE INDEX IF NOT EXISTS idx_zeiterfassung_audit_admin ON zeiterfassung_audit(admin_user_id);

COMMENT ON TABLE zeiterfassung_audit IS 'Protokoll aller Admin-Änderungen an Zeiterfassungen';
