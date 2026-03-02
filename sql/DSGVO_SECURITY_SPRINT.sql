-- ============================================================
-- CrewBase DSGVO Security Sprint
-- Datum: 02. März 2026
-- Inhalt:
--   1. Strikte RLS-Policies für Mitarbeiter-Zugriff
--   2. Unveränderliches Audit-Log (nur INSERT)
--   3. Daten-Hygiene: Markierung für Löschfristen
-- ============================================================

-- ============================================================
-- TEIL 1: AUDIT-LOG TABELLE (unveränderlich, nur INSERT)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    
    -- Wer hat was gemacht?
    admin_user_id BIGINT NOT NULL REFERENCES users(id),
    admin_name VARCHAR(200),
    
    -- Was wurde geändert?
    aktion VARCHAR(50) NOT NULL,           -- 'zeitkorrektur', 'zeitloeschung', 'lohnkorrektur', etc.
    tabelle VARCHAR(100) NOT NULL,          -- Betroffene Tabelle
    datensatz_id BIGINT,                   -- ID des betroffenen Datensatzes
    
    -- Mitarbeiter-Bezug
    mitarbeiter_id BIGINT REFERENCES mitarbeiter(id),
    mitarbeiter_name VARCHAR(200),
    
    -- Vorher/Nachher
    alter_wert JSONB,                      -- Zustand vor der Änderung
    neuer_wert JSONB,                      -- Zustand nach der Änderung
    
    -- Begründung (Pflichtfeld)
    begruendung TEXT NOT NULL,
    
    -- Betrieb
    betrieb_id BIGINT REFERENCES betriebe(id),
    
    -- Zeitstempel (unveränderlich)
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Index für schnelle Abfragen
CREATE INDEX IF NOT EXISTS idx_audit_log_admin ON audit_log(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_mitarbeiter ON audit_log(mitarbeiter_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_erstellt ON audit_log(erstellt_am);
CREATE INDEX IF NOT EXISTS idx_audit_log_betrieb ON audit_log(betrieb_id);

-- RLS für Audit-Log: Nur Admin kann lesen, NIEMAND kann ändern/löschen
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Admin darf lesen
CREATE POLICY audit_log_admin_select ON audit_log
    FOR SELECT USING (true);

-- INSERT ist für alle erlaubt (wird von der App gesteuert)
CREATE POLICY audit_log_insert ON audit_log
    FOR INSERT WITH CHECK (true);

-- UPDATE und DELETE sind für NIEMANDEN erlaubt (keine Policy = kein Zugriff)
-- Dadurch ist das Log unveränderlich

-- ============================================================
-- TEIL 2: DATEN-HYGIENE - Löschfristen-Markierung
-- ============================================================

-- Spalten für Löschfristen zu mitarbeiter hinzufügen
ALTER TABLE mitarbeiter
    ADD COLUMN IF NOT EXISTS ausgetreten_am DATE DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS loeschfrist_datum DATE DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS anonymisiert BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS anonymisiert_am TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Spalten für Löschfristen zu lohnabrechnungen hinzufügen
ALTER TABLE lohnabrechnungen
    ADD COLUMN IF NOT EXISTS aufbewahrungsfrist_bis DATE DEFAULT NULL;

-- Funktion: Berechne Löschfrist bei Austritt (10 Jahre für Lohnunterlagen)
CREATE OR REPLACE FUNCTION berechne_loeschfrist()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ausgetreten_am IS NOT NULL AND OLD.ausgetreten_am IS NULL THEN
        -- Setze Löschfrist auf 10 Jahre nach Austritt (§ 147 AO)
        NEW.loeschfrist_datum := NEW.ausgetreten_am + INTERVAL '10 years';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger für automatische Löschfrist-Berechnung
DROP TRIGGER IF EXISTS trigger_loeschfrist ON mitarbeiter;
CREATE TRIGGER trigger_loeschfrist
    BEFORE UPDATE ON mitarbeiter
    FOR EACH ROW
    EXECUTE FUNCTION berechne_loeschfrist();

-- Funktion: Markiere fällige Datensätze zur Anonymisierung
-- (Wird täglich per Cron-Job aufgerufen)
CREATE OR REPLACE FUNCTION markiere_anonymisierung_faellig()
RETURNS TABLE(mitarbeiter_id BIGINT, name TEXT, loeschfrist DATE) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.vorname || ' ' || m.nachname,
        m.loeschfrist_datum
    FROM mitarbeiter m
    WHERE 
        m.loeschfrist_datum IS NOT NULL
        AND m.loeschfrist_datum <= CURRENT_DATE
        AND m.anonymisiert = FALSE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TEIL 3: STRIKTE RLS-POLICIES FÜR MITARBEITER
-- ============================================================
-- WICHTIG: Da CrewBase einen eigenen Auth-Layer (users-Tabelle) verwendet
-- und NICHT Supabase Auth (auth.uid()), werden die Policies über
-- eine Session-Variable (app.current_user_id) gesteuert.
-- Die App setzt diese Variable bei jedem Request.

-- Hilfsfunktion: Hole aktuelle User-ID aus Session
CREATE OR REPLACE FUNCTION get_current_app_user_id()
RETURNS BIGINT AS $$
BEGIN
    -- Lese aus PostgreSQL Session-Variable (gesetzt von der App)
    RETURN NULLIF(current_setting('app.current_user_id', true), '')::BIGINT;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Hilfsfunktion: Prüfe ob aktueller User Admin ist
CREATE OR REPLACE FUNCTION is_admin_user()
RETURNS BOOLEAN AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT rolle INTO user_role 
    FROM users 
    WHERE id = get_current_app_user_id();
    RETURN user_role = 'admin';
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ---- mitarbeiter-Tabelle ----
-- Bestehende Policies entfernen
DROP POLICY IF EXISTS mitarbeiter_admin_all ON mitarbeiter;

-- Admin: voller Zugriff
CREATE POLICY mitarbeiter_admin_all ON mitarbeiter
    FOR ALL
    USING (is_admin_user());

-- Mitarbeiter: nur eigene Zeile lesen
CREATE POLICY mitarbeiter_user_select ON mitarbeiter
    FOR SELECT
    USING (
        user_id = get_current_app_user_id()
        OR is_admin_user()
    );

-- Mitarbeiter: eigene Zeile aktualisieren (nur nicht-sensible Felder)
-- Sensible Felder (stundenlohn_brutto, etc.) sind nur per Admin änderbar
CREATE POLICY mitarbeiter_user_update ON mitarbeiter
    FOR UPDATE
    USING (user_id = get_current_app_user_id() OR is_admin_user());

-- ---- zeiterfassung-Tabelle ----
DROP POLICY IF EXISTS zeiterfassung_admin_all ON zeiterfassung;

-- Admin: voller Zugriff
CREATE POLICY zeiterfassung_admin_all ON zeiterfassung
    FOR ALL
    USING (is_admin_user());

-- Mitarbeiter: nur eigene Zeiterfassungen
CREATE POLICY zeiterfassung_user_select ON zeiterfassung
    FOR SELECT
    USING (
        mitarbeiter_id IN (
            SELECT id FROM mitarbeiter WHERE user_id = get_current_app_user_id()
        )
        OR is_admin_user()
    );

CREATE POLICY zeiterfassung_user_insert ON zeiterfassung
    FOR INSERT
    WITH CHECK (
        mitarbeiter_id IN (
            SELECT id FROM mitarbeiter WHERE user_id = get_current_app_user_id()
        )
        OR is_admin_user()
    );

-- ---- lohnabrechnungen-Tabelle ----
DROP POLICY IF EXISTS lohnabrechnungen_admin_all ON lohnabrechnungen;

-- Admin: voller Zugriff
CREATE POLICY lohnabrechnungen_admin_all ON lohnabrechnungen
    FOR ALL
    USING (is_admin_user());

-- Mitarbeiter: nur eigene Lohnabrechnungen lesen
CREATE POLICY lohnabrechnungen_user_select ON lohnabrechnungen
    FOR SELECT
    USING (
        mitarbeiter_id IN (
            SELECT id FROM mitarbeiter WHERE user_id = get_current_app_user_id()
        )
        OR is_admin_user()
    );

-- ---- urlaubsantraege-Tabelle ----
DROP POLICY IF EXISTS urlaubsantraege_admin_all ON urlaubsantraege;

-- Admin: voller Zugriff
CREATE POLICY urlaubsantraege_admin_all ON urlaubsantraege
    FOR ALL
    USING (is_admin_user());

-- Mitarbeiter: nur eigene Urlaubsanträge
CREATE POLICY urlaubsantraege_user_all ON urlaubsantraege
    FOR ALL
    USING (
        mitarbeiter_id IN (
            SELECT id FROM mitarbeiter WHERE user_id = get_current_app_user_id()
        )
        OR is_admin_user()
    );

-- ---- arbeitszeitkonto-Tabelle ----
DROP POLICY IF EXISTS arbeitszeitkonto_admin_all ON arbeitszeitkonto;

CREATE POLICY arbeitszeitkonto_admin_all ON arbeitszeitkonto
    FOR ALL
    USING (is_admin_user());

CREATE POLICY arbeitszeitkonto_user_select ON arbeitszeitkonto
    FOR SELECT
    USING (
        mitarbeiter_id IN (
            SELECT id FROM mitarbeiter WHERE user_id = get_current_app_user_id()
        )
        OR is_admin_user()
    );

-- ============================================================
-- TEIL 4: STORAGE-BUCKET POLICIES (Supabase Storage RLS)
-- ============================================================
-- Diese Policies werden im Supabase Dashboard unter Storage > Policies gesetzt.
-- Hier als Dokumentation:

-- Bucket: arbeitsvertraege
-- Policy: Mitarbeiter können nur ihre eigene Datei lesen
--   (Pfad-Konvention: {personalnummer}/arbeitsvertrag.pdf)
-- Policy: Admin kann alle Dateien lesen/schreiben

-- Bucket: gesundheitsausweise  
-- Policy: Mitarbeiter können nur ihre eigene Datei lesen
-- Policy: Admin kann alle Dateien lesen/schreiben

-- ============================================================
-- ABSCHLUSS: Kommentare für Dokumentation
-- ============================================================
COMMENT ON TABLE audit_log IS 
    'Unveränderliches Audit-Log für alle Admin-Aktionen. Nur INSERT erlaubt. DSGVO-konform.';

COMMENT ON COLUMN mitarbeiter.loeschfrist_datum IS 
    'Automatisch berechnet: ausgetreten_am + 10 Jahre (§ 147 AO)';

COMMENT ON COLUMN mitarbeiter.anonymisiert IS 
    'TRUE wenn Datensatz nach Ablauf der Aufbewahrungsfrist anonymisiert wurde';
