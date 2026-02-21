-- ============================================================================
-- CREWBASE - VOLLSTÄNDIGES DATENBANK-SETUP
-- ============================================================================
-- Dieses Skript richtet alle benötigten Tabellen und Daten ein
-- Führen Sie es in Supabase SQL Editor aus
-- Kann mehrfach ausgeführt werden ohne Fehler
-- ============================================================================

-- ============================================================================
-- SCHRITT 1: Erstelle betriebe-Tabelle
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'betriebe') THEN
        CREATE TABLE public.betriebe (
            id BIGSERIAL PRIMARY KEY,
            betriebsnummer VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            logo_url TEXT,
            aktiv BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        RAISE NOTICE 'Tabelle betriebe erstellt';
        
        -- Füge Piccolo-Betrieb hinzu
        INSERT INTO public.betriebe (betriebsnummer, name, aktiv)
        VALUES ('20262204', 'Steakhouse Piccolo', TRUE);
        
        RAISE NOTICE 'Piccolo-Betrieb (20262204) hinzugefügt';
    ELSE
        RAISE NOTICE 'Tabelle betriebe existiert bereits';
        
        -- Stelle sicher, dass Piccolo-Betrieb existiert
        IF NOT EXISTS (SELECT FROM public.betriebe WHERE betriebsnummer = '20262204') THEN
            INSERT INTO public.betriebe (betriebsnummer, name, aktiv)
            VALUES ('20262204', 'Steakhouse Piccolo', TRUE);
            RAISE NOTICE 'Piccolo-Betrieb (20262204) hinzugefügt';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- SCHRITT 2: Füge betrieb_id zu users-Tabelle hinzu
-- ============================================================================
DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    -- Hole Piccolo Betrieb-ID
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    -- Füge betrieb_id-Spalte hinzu falls nicht vorhanden
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'users' 
        AND column_name = 'betrieb_id'
    ) THEN
        ALTER TABLE public.users ADD COLUMN betrieb_id BIGINT;
        RAISE NOTICE 'Spalte betrieb_id zu users hinzugefügt';
        
        -- Setze alle existierenden Benutzer auf Piccolo
        UPDATE public.users SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        RAISE NOTICE 'Alle Benutzer dem Piccolo-Betrieb zugeordnet';
    ELSE
        RAISE NOTICE 'Spalte betrieb_id existiert bereits in users';
        
        -- Aktualisiere NULL-Werte
        UPDATE public.users SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
    END IF;
END $$;

-- ============================================================================
-- SCHRITT 3: Füge betrieb_id zu mitarbeiter-Tabelle hinzu
-- ============================================================================
DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    -- Hole Piccolo Betrieb-ID
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'mitarbeiter') THEN
        -- Füge betrieb_id-Spalte hinzu falls nicht vorhanden
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'mitarbeiter' 
            AND column_name = 'betrieb_id'
        ) THEN
            ALTER TABLE public.mitarbeiter ADD COLUMN betrieb_id BIGINT;
            RAISE NOTICE 'Spalte betrieb_id zu mitarbeiter hinzugefügt';
            
            -- Setze alle existierenden Mitarbeiter auf Piccolo
            UPDATE public.mitarbeiter SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
            RAISE NOTICE 'Alle Mitarbeiter dem Piccolo-Betrieb zugeordnet';
        ELSE
            RAISE NOTICE 'Spalte betrieb_id existiert bereits in mitarbeiter';
            
            -- Aktualisiere NULL-Werte
            UPDATE public.mitarbeiter SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        END IF;
        
        -- Füge mobile_zeiterfassung-Spalte hinzu falls nicht vorhanden
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'mitarbeiter' 
            AND column_name = 'mobile_zeiterfassung'
        ) THEN
            ALTER TABLE public.mitarbeiter ADD COLUMN mobile_zeiterfassung BOOLEAN DEFAULT FALSE;
            RAISE NOTICE 'Spalte mobile_zeiterfassung zu mitarbeiter hinzugefügt';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- SCHRITT 4: Erstelle neue Tabellen für Features
-- ============================================================================

-- Mastergeräte-Tabelle
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'mastergeraete') THEN
        CREATE TABLE public.mastergeraete (
            id BIGSERIAL PRIMARY KEY,
            betrieb_id BIGINT NOT NULL,
            geraete_id VARCHAR(100) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            standort VARCHAR(255),
            beschreibung TEXT,
            registrierungscode VARCHAR(8) NOT NULL,
            aktiv BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        RAISE NOTICE 'Tabelle mastergeraete erstellt';
    END IF;
END $$;

-- Benachrichtigungen-Tabelle
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'benachrichtigungen') THEN
        CREATE TABLE public.benachrichtigungen (
            id BIGSERIAL PRIMARY KEY,
            betrieb_id BIGINT NOT NULL,
            user_id TEXT NOT NULL,
            titel VARCHAR(255) NOT NULL,
            nachricht TEXT NOT NULL,
            typ VARCHAR(50),
            gelesen BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        RAISE NOTICE 'Tabelle benachrichtigungen erstellt';
    END IF;
END $$;

-- Plauderecke-Tabelle
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'plauderecke') THEN
        CREATE TABLE public.plauderecke (
            id BIGSERIAL PRIMARY KEY,
            betrieb_id BIGINT NOT NULL,
            user_id TEXT NOT NULL,
            nachricht TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        RAISE NOTICE 'Tabelle plauderecke erstellt';
    END IF;
END $$;

-- Änderungsanfragen-Tabelle
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'aenderungsanfragen') THEN
        CREATE TABLE public.aenderungsanfragen (
            id BIGSERIAL PRIMARY KEY,
            betrieb_id BIGINT NOT NULL,
            mitarbeiter_id BIGINT NOT NULL,
            feld VARCHAR(100) NOT NULL,
            alter_wert TEXT,
            neuer_wert TEXT,
            grund TEXT,
            status VARCHAR(50) DEFAULT 'Ausstehend',
            bearbeitet_von BIGINT,
            bearbeitet_am TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        RAISE NOTICE 'Tabelle aenderungsanfragen erstellt';
    END IF;
END $$;

-- ============================================================================
-- SCHRITT 5: Füge betrieb_id zu weiteren Tabellen hinzu (falls vorhanden)
-- ============================================================================

-- zeiterfassungen
DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'zeiterfassungen') THEN
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'zeiterfassungen' 
            AND column_name = 'betrieb_id'
        ) THEN
            ALTER TABLE public.zeiterfassungen ADD COLUMN betrieb_id BIGINT;
            UPDATE public.zeiterfassungen SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
            RAISE NOTICE 'Spalte betrieb_id zu zeiterfassungen hinzugefügt';
        END IF;
        
        -- Korrektur-Felder
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'zeiterfassungen' 
            AND column_name = 'korrigiert_von_admin'
        ) THEN
            ALTER TABLE public.zeiterfassungen ADD COLUMN korrigiert_von_admin BOOLEAN DEFAULT FALSE;
            ALTER TABLE public.zeiterfassungen ADD COLUMN korrektur_grund TEXT;
            ALTER TABLE public.zeiterfassungen ADD COLUMN korrektur_datum TIMESTAMP WITH TIME ZONE;
            RAISE NOTICE 'Korrektur-Felder zu zeiterfassungen hinzugefügt';
        END IF;
    END IF;
END $$;

-- urlaubsantraege
DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'urlaubsantraege') THEN
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'urlaubsantraege' 
            AND column_name = 'betrieb_id'
        ) THEN
            ALTER TABLE public.urlaubsantraege ADD COLUMN betrieb_id BIGINT;
            UPDATE public.urlaubsantraege SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
            RAISE NOTICE 'Spalte betrieb_id zu urlaubsantraege hinzugefügt';
        END IF;
    END IF;
END $$;

-- dienstplaene
DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'dienstplaene') THEN
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'dienstplaene' 
            AND column_name = 'betrieb_id'
        ) THEN
            ALTER TABLE public.dienstplaene ADD COLUMN betrieb_id BIGINT;
            UPDATE public.dienstplaene SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
            RAISE NOTICE 'Spalte betrieb_id zu dienstplaene hinzugefügt';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- ABSCHLUSS
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Setup abgeschlossen!';
    RAISE NOTICE '📋 Piccolo-Betriebsnummer: 20262204';
    RAISE NOTICE '🔑 Login sollte jetzt funktionieren';
END $$;
