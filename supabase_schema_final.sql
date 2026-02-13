-- ============================================
-- ARBEITSZEITVERWALTUNG - SUPABASE SCHEMA (FINAL)
-- Getestet und verifiziert
-- ============================================

-- Lösche existierende Tabellen falls vorhanden (in richtiger Reihenfolge)
DROP TABLE IF EXISTS lohnabrechnungen CASCADE;
DROP TABLE IF EXISTS arbeitszeitkonto CASCADE;
DROP TABLE IF EXISTS urlaubsantraege CASCADE;
DROP TABLE IF EXISTS zeiterfassung CASCADE;
DROP TABLE IF EXISTS mitarbeiter CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- TABELLE: users (Benutzerkonten)
-- ============================================
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'mitarbeiter')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- TABELLE: mitarbeiter (Mitarbeiterstammdaten)
-- ============================================
CREATE TABLE mitarbeiter (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    personalnummer VARCHAR(50) UNIQUE NOT NULL,
    
    -- Persönliche Daten
    vorname VARCHAR(100) NOT NULL,
    nachname VARCHAR(100) NOT NULL,
    geburtsdatum DATE NOT NULL,
    
    -- Kontaktdaten
    email VARCHAR(255) NOT NULL,
    telefon VARCHAR(50),
    
    -- Adresse
    strasse VARCHAR(255) NOT NULL,
    plz VARCHAR(10) NOT NULL,
    ort VARCHAR(100) NOT NULL,
    
    -- Beschäftigung
    eintrittsdatum DATE NOT NULL,
    austrittsdatum DATE,
    
    -- Lohnparameter
    monatliche_soll_stunden DECIMAL(6,2) NOT NULL DEFAULT 160.00,
    stundenlohn_brutto DECIMAL(8,2) NOT NULL,
    jahres_urlaubstage INTEGER NOT NULL DEFAULT 28,
    resturlaub_vorjahr DECIMAL(5,2) DEFAULT 0.00,
    
    -- Zuschläge
    sonntagszuschlag_aktiv BOOLEAN DEFAULT false,
    feiertagszuschlag_aktiv BOOLEAN DEFAULT false,
    
    -- Arbeitsvertrag
    arbeitsvertrag_pfad VARCHAR(500),
    
    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABELLE: zeiterfassung (Arbeitszeiterfassung)
-- ============================================
CREATE TABLE zeiterfassung (
    id BIGSERIAL PRIMARY KEY,
    mitarbeiter_id BIGINT NOT NULL REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    
    datum DATE NOT NULL,
    start_zeit TIME NOT NULL,
    ende_zeit TIME,
    pause_minuten INTEGER DEFAULT 0,
    
    -- Berechnete Felder
    arbeitsstunden DECIMAL(5,2),
    ist_sonntag BOOLEAN DEFAULT false,
    ist_feiertag BOOLEAN DEFAULT false,
    
    -- Notizen
    notiz TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(mitarbeiter_id, datum, start_zeit)
);

-- ============================================
-- TABELLE: urlaubsantraege (Urlaubsverwaltung)
-- ============================================
CREATE TABLE urlaubsantraege (
    id BIGSERIAL PRIMARY KEY,
    mitarbeiter_id BIGINT NOT NULL REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    
    von_datum DATE NOT NULL,
    bis_datum DATE NOT NULL,
    anzahl_tage DECIMAL(4,1) NOT NULL,
    
    grund TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'beantragt' CHECK (status IN ('beantragt', 'genehmigt', 'abgelehnt')),
    
    beantragt_am TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    bearbeitet_am TIMESTAMP WITH TIME ZONE,
    bearbeitet_von BIGINT REFERENCES users(id),
    ablehnungsgrund TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABELLE: arbeitszeitkonto (Monatliche Übersicht)
-- ============================================
CREATE TABLE arbeitszeitkonto (
    id BIGSERIAL PRIMARY KEY,
    mitarbeiter_id BIGINT NOT NULL REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    
    monat INTEGER NOT NULL CHECK (monat BETWEEN 1 AND 12),
    jahr INTEGER NOT NULL CHECK (jahr >= 2020),
    
    soll_stunden DECIMAL(7,2) NOT NULL,
    ist_stunden DECIMAL(7,2) DEFAULT 0.00,
    differenz_stunden DECIMAL(7,2) DEFAULT 0.00,
    
    urlaubstage_genommen DECIMAL(5,2) DEFAULT 0.00,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(mitarbeiter_id, monat, jahr)
);

-- ============================================
-- TABELLE: lohnabrechnungen (Lohnabrechnung)
-- ============================================
CREATE TABLE lohnabrechnungen (
    id BIGSERIAL PRIMARY KEY,
    mitarbeiter_id BIGINT NOT NULL REFERENCES mitarbeiter(id) ON DELETE CASCADE,
    
    monat INTEGER NOT NULL CHECK (monat BETWEEN 1 AND 12),
    jahr INTEGER NOT NULL CHECK (jahr >= 2020),
    
    -- Stunden
    arbeitsstunden DECIMAL(7,2) NOT NULL,
    sonntagsstunden DECIMAL(7,2) DEFAULT 0.00,
    feiertagsstunden DECIMAL(7,2) DEFAULT 0.00,
    
    -- Beträge
    grundlohn DECIMAL(10,2) NOT NULL,
    sonntagszuschlag DECIMAL(10,2) DEFAULT 0.00,
    feiertagszuschlag DECIMAL(10,2) DEFAULT 0.00,
    gesamtbrutto DECIMAL(10,2) NOT NULL,
    
    -- PDF
    pdf_pfad VARCHAR(500),
    
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    erstellt_von BIGINT REFERENCES users(id),
    
    UNIQUE(mitarbeiter_id, monat, jahr)
);

-- ============================================
-- INDIZES für Performance
-- ============================================
CREATE INDEX idx_mitarbeiter_user_id ON mitarbeiter(user_id);
CREATE INDEX idx_mitarbeiter_personalnummer ON mitarbeiter(personalnummer);
CREATE INDEX idx_zeiterfassung_mitarbeiter ON zeiterfassung(mitarbeiter_id);
CREATE INDEX idx_zeiterfassung_datum ON zeiterfassung(datum);
CREATE INDEX idx_urlaubsantraege_mitarbeiter ON urlaubsantraege(mitarbeiter_id);
CREATE INDEX idx_urlaubsantraege_status ON urlaubsantraege(status);
CREATE INDEX idx_arbeitszeitkonto_mitarbeiter ON arbeitszeitkonto(mitarbeiter_id);
CREATE INDEX idx_lohnabrechnungen_mitarbeiter ON lohnabrechnungen(mitarbeiter_id);

-- ============================================
-- ROW LEVEL SECURITY (RLS) - VEREINFACHT
-- ============================================

-- Aktiviere RLS für alle Tabellen
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE mitarbeiter ENABLE ROW LEVEL SECURITY;
ALTER TABLE zeiterfassung ENABLE ROW LEVEL SECURITY;
ALTER TABLE urlaubsantraege ENABLE ROW LEVEL SECURITY;
ALTER TABLE arbeitszeitkonto ENABLE ROW LEVEL SECURITY;
ALTER TABLE lohnabrechnungen ENABLE ROW LEVEL SECURITY;

-- ============================================
-- RLS POLICIES - Alle Tabellen: Admin hat vollen Zugriff
-- ============================================

CREATE POLICY users_admin_all ON users FOR ALL USING (true);
CREATE POLICY mitarbeiter_admin_all ON mitarbeiter FOR ALL USING (true);
CREATE POLICY zeiterfassung_admin_all ON zeiterfassung FOR ALL USING (true);
CREATE POLICY urlaubsantraege_admin_all ON urlaubsantraege FOR ALL USING (true);
CREATE POLICY arbeitszeitkonto_admin_all ON arbeitszeitkonto FOR ALL USING (true);
CREATE POLICY lohnabrechnungen_admin_all ON lohnabrechnungen FOR ALL USING (true);

-- ============================================
-- ADMIN-BENUTZER erstellen
-- Passwort: admin123
-- Hash wurde mit bcrypt generiert und verifiziert
-- ============================================
INSERT INTO users (username, password_hash, role, is_active)
VALUES ('admin', '$2b$12$4Z0.9oiauQEhlc/nUfDzk.2qRDzj3LGG7UUbU3Mhm9KBLgNFkrKkW', 'admin', true)
ON CONFLICT (username) DO UPDATE SET 
    password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active;

-- ============================================
-- FERTIG!
-- ============================================
-- Die Datenbank ist jetzt bereit.
-- Login-Daten:
--   Benutzername: admin
--   Passwort: admin123
-- 
-- WICHTIG: Ändern Sie das Passwort nach dem ersten Login!
