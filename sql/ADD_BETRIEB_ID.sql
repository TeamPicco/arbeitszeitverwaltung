-- CrewBase - betrieb_id zu existierenden Tabellen hinzufügen
-- Dieses Skript erweitert existierende Tabellen um die betrieb_id-Spalte
-- Führen Sie dies NACH SETUP_NEW_TABLES.sql aus

-- ============================================
-- WICHTIG: Voraussetzungen
-- ============================================
-- 1. SETUP_NEW_TABLES.sql muss bereits ausgeführt sein
-- 2. Die betriebe-Tabelle muss existieren
-- 3. Piccolo-Betrieb (20262204) muss in betriebe vorhanden sein

-- ============================================
-- 1. USERS - betrieb_id hinzufügen
-- ============================================

DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    -- Hole Piccolo betrieb_id
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    IF piccolo_id IS NULL THEN
        RAISE EXCEPTION 'Piccolo-Betrieb nicht gefunden. Bitte SETUP_NEW_TABLES.sql zuerst ausführen.';
    END IF;
    
    -- Füge betrieb_id-Spalte hinzu wenn nicht vorhanden
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'users' 
        AND column_name = 'betrieb_id'
    ) THEN
        ALTER TABLE public.users ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
        RAISE NOTICE '✅ users.betrieb_id Spalte hinzugefügt';
        
        -- Setze betrieb_id für alle existierenden User auf Piccolo
        UPDATE public.users SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        RAISE NOTICE '✅ Alle existierenden Users zu Piccolo zugeordnet';
    ELSE
        RAISE NOTICE '⏭️  users.betrieb_id existiert bereits';
    END IF;
END $$;

-- ============================================
-- 2. MITARBEITER - betrieb_id und mobile_zeiterfassung hinzufügen
-- ============================================

DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    -- Füge betrieb_id hinzu
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'mitarbeiter' 
        AND column_name = 'betrieb_id'
    ) THEN
        ALTER TABLE public.mitarbeiter ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
        RAISE NOTICE '✅ mitarbeiter.betrieb_id Spalte hinzugefügt';
        
        UPDATE public.mitarbeiter SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
        RAISE NOTICE '✅ Alle existierenden Mitarbeiter zu Piccolo zugeordnet';
    ELSE
        RAISE NOTICE '⏭️  mitarbeiter.betrieb_id existiert bereits';
    END IF;
    
    -- Füge mobile_zeiterfassung hinzu
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'mitarbeiter' 
        AND column_name = 'mobile_zeiterfassung'
    ) THEN
        ALTER TABLE public.mitarbeiter ADD COLUMN mobile_zeiterfassung BOOLEAN DEFAULT false;
        RAISE NOTICE '✅ mitarbeiter.mobile_zeiterfassung Spalte hinzugefügt';
    ELSE
        RAISE NOTICE '⏭️  mitarbeiter.mobile_zeiterfassung existiert bereits';
    END IF;
END $$;

-- ============================================
-- 3. ZEITERFASSUNGEN - betrieb_id und Korrektur-Felder hinzufügen
-- ============================================

DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    -- Prüfe ob Tabelle existiert
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'zeiterfassungen') THEN
        
        -- Füge betrieb_id hinzu
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'zeiterfassungen' 
            AND column_name = 'betrieb_id'
        ) THEN
            ALTER TABLE public.zeiterfassungen ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
            RAISE NOTICE '✅ zeiterfassungen.betrieb_id Spalte hinzugefügt';
            
            UPDATE public.zeiterfassungen SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
            RAISE NOTICE '✅ Alle existierenden Zeiterfassungen zu Piccolo zugeordnet';
        ELSE
            RAISE NOTICE '⏭️  zeiterfassungen.betrieb_id existiert bereits';
        END IF;
        
        -- Füge Korrektur-Felder hinzu
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'zeiterfassungen' 
            AND column_name = 'korrigiert_von_admin'
        ) THEN
            ALTER TABLE public.zeiterfassungen ADD COLUMN korrigiert_von_admin BOOLEAN DEFAULT false;
            ALTER TABLE public.zeiterfassungen ADD COLUMN korrektur_grund TEXT;
            ALTER TABLE public.zeiterfassungen ADD COLUMN korrektur_datum TIMESTAMP WITH TIME ZONE;
            RAISE NOTICE '✅ Korrektur-Felder zu zeiterfassungen hinzugefügt';
        ELSE
            RAISE NOTICE '⏭️  Korrektur-Felder existieren bereits';
        END IF;
        
    ELSE
        RAISE NOTICE '⚠️  Tabelle zeiterfassungen existiert nicht';
    END IF;
END $$;

-- ============================================
-- 4. URLAUBSANTRÄGE - betrieb_id hinzufügen
-- ============================================

DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'urlaubsantraege') THEN
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'urlaubsantraege' 
            AND column_name = 'betrieb_id'
        ) THEN
            ALTER TABLE public.urlaubsantraege ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
            RAISE NOTICE '✅ urlaubsantraege.betrieb_id Spalte hinzugefügt';
            
            UPDATE public.urlaubsantraege SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
            RAISE NOTICE '✅ Alle existierenden Urlaubsanträge zu Piccolo zugeordnet';
        ELSE
            RAISE NOTICE '⏭️  urlaubsantraege.betrieb_id existiert bereits';
        END IF;
        
    ELSE
        RAISE NOTICE '⚠️  Tabelle urlaubsantraege existiert nicht';
    END IF;
END $$;

-- ============================================
-- 5. DIENSTPLÄNE - betrieb_id hinzufügen (falls vorhanden)
-- ============================================

DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'dienstplaene') THEN
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'dienstplaene' 
            AND column_name = 'betrieb_id'
        ) THEN
            ALTER TABLE public.dienstplaene ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
            RAISE NOTICE '✅ dienstplaene.betrieb_id Spalte hinzugefügt';
            
            UPDATE public.dienstplaene SET betrieb_id = piccolo_id WHERE betrieb_id IS NULL;
            RAISE NOTICE '✅ Alle existierenden Dienstpläne zu Piccolo zugeordnet';
        ELSE
            RAISE NOTICE '⏭️  dienstplaene.betrieb_id existiert bereits';
        END IF;
        
    ELSE
        RAISE NOTICE '⚠️  Tabelle dienstplaene existiert nicht';
    END IF;
END $$;

-- ============================================
-- FERTIG!
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '🎉 Migration abgeschlossen!';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Alle existierenden Tabellen wurden erweitert';
    RAISE NOTICE '✅ Alle Daten wurden Piccolo (20262204) zugeordnet';
    RAISE NOTICE '✅ Multi-Tenancy ist jetzt vollständig aktiviert';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Nächste Schritte:';
    RAISE NOTICE '  1. App neu laden (Render.com deployt automatisch)';
    RAISE NOTICE '  2. Mit Betriebsnummer 20262204 einloggen';
    RAISE NOTICE '  3. Alle Features testen';
END $$;
