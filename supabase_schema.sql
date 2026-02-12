-- ============================================================================
-- Arbeitszeitverwaltung - Supabase SQL Schema
-- DSGVO-konform & Nachweisgesetz-konform
-- ============================================================================

-- Aktiviere UUID-Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. USERS TABELLE (Authentifizierung)
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'mitarbeiter')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Index für schnelle Login-Abfragen
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

COMMENT ON TABLE users IS 'Benutzer-Authentifizierung für Mitarbeiter und Administrator';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt-gehashtes Passwort (Faktor 12)';

-- ============================================================================
-- 2. MITARBEITER TABELLE (Stammdaten & Vertragswesen)
-- ============================================================================

CREATE TABLE mitarbeiter (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Persönliche Daten
    vorname VARCHAR(100) NOT NULL,
    nachname VARCHAR(100) NOT NULL,
    geburtsdatum DATE NOT NULL,
    
    -- Adressdaten
    strasse VARCHAR(200) NOT NULL,
    plz VARCHAR(10) NOT NULL,
    ort VARCHAR(100) NOT NULL,
    
    -- Kontaktdaten
    email VARCHAR(255) NOT NULL,
    telefon VARCHAR(50),
    
    -- Beschäftigungsdaten
    personalnummer VARCHAR(50) UNIQUE NOT NULL,
    eintrittsdatum DATE NOT NULL,
    austrittsdatum DATE,
    vertrag_pdf_path TEXT,
    
    -- Lohnparameter
    monatliche_soll_stunden DECIMAL(6,2) NOT NULL CHECK (monatliche_soll_stunden > 0),
    stundenlohn_brutto DECIMAL(8,2) NOT NULL CHECK (stundenlohn_brutto > 0),
    jahres_urlaubstage INTEGER NOT NULL CHECK (jahres_urlaubstage >= 20),
    resturlaub_vorjahr DECIMAL(5,2) DEFAULT 0 CHECK (resturlaub_vorjahr >= 0),
    
    -- Zuschläge
    sonntagszuschlag_aktiv BOOLEAN DEFAULT FALSE,
    feiertagszuschlag_aktiv BOOLEAN DEFAULT FALSE,
    
    -- Metadaten
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indizes
CREATE INDEX idx_mitarbeiter_user_id ON mitarbeiter(user_id);
CREATE INDEX idx_mitarbeiter_personalnummer ON mitarbeiter(personalnummer);
CREATE INDEX idx_mitarbeiter_nachname ON mitarbeiter(nachname);

COMMENT ON TABLE mitarbeiter IS 'Stammdaten und Vertragsinformationen der Mitarbeiter';
COMMENT ON COLUMN mitarbeiter.vertrag_pdf_path IS 'Pfad zum Arbeitsvertrag in Supabase Storage';
COMMENT ON COLUMN mitarbeiter.jahres_urlaubstage IS 'Mindestens 20 Tage nach BUrlG';

-- Trigger für automatische Aktualisierung von updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_mitarbeiter_updated_at
    BEFORE UPDATE ON mitarbeiter
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 3. ZEITERFASSUNG TABELLE (Arbeitszeiterfassung)
-- ============================================================================

CREATE TABLE zeiterfassung (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mitarbeiter_id UUID NOT NULL REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    
    -- Zeitdaten
    datum DATE NOT NULL,
    start_zeit TIME NOT NULL,
    ende_zeit TIME,
    pause_minuten INTEGER DEFAULT 0 CHECK (pause_minuten >= 0),
    
    -- Zuschlagsrelevante Informationen
    ist_sonntag BOOLEAN DEFAULT FALSE,
    ist_feiertag BOOLEAN DEFAULT FALSE,
    
    -- Zusätzliche Informationen
    notiz TEXT,
    
    -- Metadaten (Audit-Trail)
    erstellt_am TIMESTAMP DEFAULT NOW(),
    geaendert_am TIMESTAMP DEFAULT NOW()
);

-- Indizes für Performance
CREATE INDEX idx_zeiterfassung_mitarbeiter_datum ON zeiterfassung(mitarbeiter_id, datum);
CREATE INDEX idx_zeiterfassung_datum ON zeiterfassung(datum);

COMMENT ON TABLE zeiterfassung IS 'Objektive und verlässliche Zeiterfassung gemäß EuGH-Urteil';
COMMENT ON COLUMN zeiterfassung.ist_sonntag IS 'Für 50% Sonntagszuschlag';
COMMENT ON COLUMN zeiterfassung.ist_feiertag IS 'Für 100% Feiertagszuschlag';

-- Trigger für automatische Aktualisierung von geaendert_am
CREATE TRIGGER update_zeiterfassung_geaendert_am
    BEFORE UPDATE ON zeiterfassung
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 4. URLAUBSANTRAEGE TABELLE (Urlaubsverwaltung)
-- ============================================================================

CREATE TABLE urlaubsantraege (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mitarbeiter_id UUID NOT NULL REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    
    -- Urlaubszeitraum
    von_datum DATE NOT NULL,
    bis_datum DATE NOT NULL CHECK (bis_datum >= von_datum),
    anzahl_tage DECIMAL(4,2) NOT NULL CHECK (anzahl_tage > 0),
    
    -- Workflow
    status VARCHAR(20) NOT NULL DEFAULT 'beantragt' CHECK (status IN ('beantragt', 'genehmigt', 'abgelehnt')),
    bemerkung_mitarbeiter TEXT,
    bemerkung_admin TEXT,
    
    -- Zeitstempel
    beantragt_am TIMESTAMP DEFAULT NOW(),
    bearbeitet_am TIMESTAMP,
    bearbeitet_von UUID REFERENCES users(id)
);

-- Indizes
CREATE INDEX idx_urlaubsantraege_mitarbeiter ON urlaubsantraege(mitarbeiter_id);
CREATE INDEX idx_urlaubsantraege_status ON urlaubsantraege(status);
CREATE INDEX idx_urlaubsantraege_datum ON urlaubsantraege(von_datum, bis_datum);

COMMENT ON TABLE urlaubsantraege IS 'Verwaltung von Urlaubsanträgen mit Genehmigungsworkflow';
COMMENT ON COLUMN urlaubsantraege.anzahl_tage IS 'Kann Dezimalwerte haben (z.B. 0.5 für halben Tag)';

-- ============================================================================
-- 5. ARBEITSZEITKONTO TABELLE (Zeitkonto-Salden)
-- ============================================================================

CREATE TABLE arbeitszeitkonto (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mitarbeiter_id UUID NOT NULL REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    
    -- Abrechnungszeitraum
    monat INTEGER NOT NULL CHECK (monat BETWEEN 1 AND 12),
    jahr INTEGER NOT NULL CHECK (jahr >= 2020),
    
    -- Stundenkonto
    soll_stunden DECIMAL(6,2) NOT NULL,
    ist_stunden DECIMAL(6,2) NOT NULL DEFAULT 0,
    differenz_stunden DECIMAL(7,2) GENERATED ALWAYS AS (ist_stunden - soll_stunden) STORED,
    
    -- Urlaub
    urlaubstage_genommen DECIMAL(4,2) DEFAULT 0,
    
    -- Zuschlagsstunden
    sonntagsstunden DECIMAL(6,2) DEFAULT 0,
    feiertagsstunden DECIMAL(6,2) DEFAULT 0,
    
    -- Metadaten
    berechnet_am TIMESTAMP DEFAULT NOW(),
    
    -- Eindeutigkeit pro Mitarbeiter/Monat/Jahr
    CONSTRAINT unique_arbeitszeitkonto UNIQUE (mitarbeiter_id, monat, jahr)
);

-- Indizes
CREATE INDEX idx_arbeitszeitkonto_mitarbeiter ON arbeitszeitkonto(mitarbeiter_id);
CREATE INDEX idx_arbeitszeitkonto_periode ON arbeitszeitkonto(jahr, monat);

COMMENT ON TABLE arbeitszeitkonto IS 'Monatliche Zusammenfassung des Arbeitszeitkontos';
COMMENT ON COLUMN arbeitszeitkonto.differenz_stunden IS 'Automatisch berechnet: Ist - Soll';

-- ============================================================================
-- 6. LOHNABRECHNUNGEN TABELLE (Entgeltaufstellungen)
-- ============================================================================

CREATE TABLE lohnabrechnungen (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mitarbeiter_id UUID NOT NULL REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    
    -- Abrechnungszeitraum
    monat INTEGER NOT NULL CHECK (monat BETWEEN 1 AND 12),
    jahr INTEGER NOT NULL CHECK (jahr >= 2020),
    
    -- Referenz zum Arbeitszeitkonto
    arbeitszeitkonto_id UUID NOT NULL REFERENCES arbeitszeitkonto(id),
    
    -- Lohnbestandteile
    grundlohn DECIMAL(10,2) NOT NULL,
    sonntagszuschlag DECIMAL(10,2) DEFAULT 0,
    feiertagszuschlag DECIMAL(10,2) DEFAULT 0,
    gesamtbetrag DECIMAL(10,2) NOT NULL,
    
    -- PDF-Speicherung
    pdf_path TEXT,
    
    -- Metadaten
    erstellt_am TIMESTAMP DEFAULT NOW(),
    
    -- Eindeutigkeit pro Mitarbeiter/Monat/Jahr
    CONSTRAINT unique_lohnabrechnung UNIQUE (mitarbeiter_id, monat, jahr)
);

-- Indizes
CREATE INDEX idx_lohnabrechnungen_mitarbeiter ON lohnabrechnungen(mitarbeiter_id);
CREATE INDEX idx_lohnabrechnungen_periode ON lohnabrechnungen(jahr, monat);

COMMENT ON TABLE lohnabrechnungen IS 'Gespeicherte Lohnabrechnungen für PDF-Export';
COMMENT ON COLUMN lohnabrechnungen.pdf_path IS 'Pfad zum PDF in Supabase Storage';

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - DSGVO-Konformität
-- ============================================================================

-- Aktiviere RLS für alle Tabellen
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE mitarbeiter ENABLE ROW LEVEL SECURITY;
ALTER TABLE zeiterfassung ENABLE ROW LEVEL SECURITY;
ALTER TABLE urlaubsantraege ENABLE ROW LEVEL SECURITY;
ALTER TABLE arbeitszeitkonto ENABLE ROW LEVEL SECURITY;
ALTER TABLE lohnabrechnungen ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS POLICIES - USERS
-- ============================================================================

-- Admin kann alle Benutzer sehen
CREATE POLICY "Admin kann alle Benutzer sehen"
    ON users FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users u 
            WHERE u.id = auth.uid() AND u.role = 'admin'
        )
    );

-- Mitarbeiter können nur eigene Daten sehen
CREATE POLICY "Mitarbeiter können eigene Daten sehen"
    ON users FOR SELECT
    USING (id = auth.uid());

-- ============================================================================
-- RLS POLICIES - MITARBEITER
-- ============================================================================

-- Admin kann alle Mitarbeiter sehen und bearbeiten
CREATE POLICY "Admin Vollzugriff auf Mitarbeiter"
    ON mitarbeiter FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users u 
            WHERE u.id = auth.uid() AND u.role = 'admin'
        )
    );

-- Mitarbeiter können nur eigene Daten sehen
CREATE POLICY "Mitarbeiter können eigene Daten sehen"
    ON mitarbeiter FOR SELECT
    USING (user_id = auth.uid());

-- ============================================================================
-- RLS POLICIES - ZEITERFASSUNG
-- ============================================================================

-- Admin kann alle Zeiterfassungen sehen
CREATE POLICY "Admin kann alle Zeiterfassungen sehen"
    ON zeiterfassung FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users u 
            WHERE u.id = auth.uid() AND u.role = 'admin'
        )
    );

-- Mitarbeiter können nur eigene Zeiterfassungen sehen und bearbeiten
CREATE POLICY "Mitarbeiter können eigene Zeiterfassungen verwalten"
    ON zeiterfassung FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM mitarbeiter m 
            WHERE m.id = zeiterfassung.mitarbeiter_id 
            AND m.user_id = auth.uid()
        )
    );

-- ============================================================================
-- RLS POLICIES - URLAUBSANTRAEGE
-- ============================================================================

-- Admin kann alle Urlaubsanträge sehen und bearbeiten
CREATE POLICY "Admin kann alle Urlaubsanträge verwalten"
    ON urlaubsantraege FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users u 
            WHERE u.id = auth.uid() AND u.role = 'admin'
        )
    );

-- Mitarbeiter können eigene Urlaubsanträge erstellen und sehen
CREATE POLICY "Mitarbeiter können eigene Urlaubsanträge verwalten"
    ON urlaubsantraege FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM mitarbeiter m 
            WHERE m.id = urlaubsantraege.mitarbeiter_id 
            AND m.user_id = auth.uid()
        )
    );

-- ============================================================================
-- RLS POLICIES - ARBEITSZEITKONTO
-- ============================================================================

-- Admin kann alle Arbeitszeitkonten sehen
CREATE POLICY "Admin kann alle Arbeitszeitkonten sehen"
    ON arbeitszeitkonto FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users u 
            WHERE u.id = auth.uid() AND u.role = 'admin'
        )
    );

-- Mitarbeiter können nur eigenes Arbeitszeitkonto sehen
CREATE POLICY "Mitarbeiter können eigenes Arbeitszeitkonto sehen"
    ON arbeitszeitkonto FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM mitarbeiter m 
            WHERE m.id = arbeitszeitkonto.mitarbeiter_id 
            AND m.user_id = auth.uid()
        )
    );

-- ============================================================================
-- RLS POLICIES - LOHNABRECHNUNGEN
-- ============================================================================

-- Admin kann alle Lohnabrechnungen sehen und erstellen
CREATE POLICY "Admin kann alle Lohnabrechnungen verwalten"
    ON lohnabrechnungen FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users u 
            WHERE u.id = auth.uid() AND u.role = 'admin'
        )
    );

-- Mitarbeiter können nur eigene Lohnabrechnungen sehen
CREATE POLICY "Mitarbeiter können eigene Lohnabrechnungen sehen"
    ON lohnabrechnungen FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM mitarbeiter m 
            WHERE m.id = lohnabrechnungen.mitarbeiter_id 
            AND m.user_id = auth.uid()
        )
    );

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Funktion zur Berechnung der Arbeitsstunden
CREATE OR REPLACE FUNCTION berechne_arbeitsstunden(
    p_start_zeit TIME,
    p_ende_zeit TIME,
    p_pause_minuten INTEGER
)
RETURNS DECIMAL(6,2) AS $$
DECLARE
    stunden DECIMAL(6,2);
BEGIN
    -- Berechne Differenz in Stunden
    stunden := EXTRACT(EPOCH FROM (p_ende_zeit - p_start_zeit)) / 3600.0;
    
    -- Ziehe Pause ab
    stunden := stunden - (p_pause_minuten / 60.0);
    
    -- Runde auf 2 Dezimalstellen
    RETURN ROUND(stunden, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION berechne_arbeitsstunden IS 'Berechnet Arbeitsstunden: (Ende - Start) - Pause';

-- Funktion zur Berechnung der Arbeitstage zwischen zwei Daten
CREATE OR REPLACE FUNCTION berechne_arbeitstage(
    p_von_datum DATE,
    p_bis_datum DATE
)
RETURNS DECIMAL(4,2) AS $$
DECLARE
    tage INTEGER;
    arbeitstage DECIMAL(4,2);
BEGIN
    -- Berechne alle Tage
    tage := p_bis_datum - p_von_datum + 1;
    
    -- Vereinfachte Berechnung: Alle Tage zählen
    -- (Erweiterte Version würde Wochenenden und Feiertage ausschließen)
    arbeitstage := tage;
    
    RETURN arbeitstage;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION berechne_arbeitstage IS 'Berechnet Anzahl der Arbeitstage zwischen zwei Daten';

-- ============================================================================
-- VIEWS FÜR REPORTING
-- ============================================================================

-- View: Aktueller Urlaubsanspruch pro Mitarbeiter
CREATE OR REPLACE VIEW v_urlaubsanspruch AS
SELECT 
    m.id AS mitarbeiter_id,
    m.vorname,
    m.nachname,
    m.jahres_urlaubstage,
    m.resturlaub_vorjahr,
    COALESCE(SUM(CASE WHEN u.status = 'genehmigt' THEN u.anzahl_tage ELSE 0 END), 0) AS genommene_tage,
    (m.jahres_urlaubstage + m.resturlaub_vorjahr - 
     COALESCE(SUM(CASE WHEN u.status = 'genehmigt' THEN u.anzahl_tage ELSE 0 END), 0)) AS verfuegbare_tage
FROM mitarbeiter m
LEFT JOIN urlaubsantraege u ON m.id = u.mitarbeiter_id 
    AND EXTRACT(YEAR FROM u.von_datum) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY m.id, m.vorname, m.nachname, m.jahres_urlaubstage, m.resturlaub_vorjahr;

COMMENT ON VIEW v_urlaubsanspruch IS 'Aktueller Urlaubsanspruch und verfügbare Tage pro Mitarbeiter';

-- View: Arbeitszeitkonto-Übersicht
CREATE OR REPLACE VIEW v_arbeitszeitkonto_uebersicht AS
SELECT 
    m.id AS mitarbeiter_id,
    m.vorname,
    m.nachname,
    a.jahr,
    a.monat,
    a.soll_stunden,
    a.ist_stunden,
    a.differenz_stunden,
    SUM(a.differenz_stunden) OVER (
        PARTITION BY m.id 
        ORDER BY a.jahr, a.monat
    ) AS kumulierte_differenz
FROM mitarbeiter m
JOIN arbeitszeitkonto a ON m.id = a.mitarbeiter_id
ORDER BY m.nachname, m.vorname, a.jahr, a.monat;

COMMENT ON VIEW v_arbeitszeitkonto_uebersicht IS 'Arbeitszeitkonto mit kumulierter Differenz';

-- ============================================================================
-- INITIAL DATA (Optional - für Testzwecke)
-- ============================================================================

-- Erstelle Admin-Benutzer (Passwort: admin123 - MUSS nach Deployment geändert werden!)
-- Passwort-Hash für 'admin123' mit bcrypt (Faktor 12)
-- WICHTIG: Dieser Hash ist nur ein Beispiel. Generiere einen neuen Hash!

INSERT INTO users (username, password_hash, role) 
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYfQYvmixxO', 'admin')
ON CONFLICT (username) DO NOTHING;

-- ============================================================================
-- ENDE DES SCHEMAS
-- ============================================================================

-- Ausgabe der Tabellen zur Verifizierung
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) AS column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
ORDER BY table_name;
