-- CrewBase - Vereinfachte Row Level Security (RLS) Policies
-- Dieses Skript aktiviert RLS und erlaubt Service Role vollen Zugriff
-- Da die App den Service Role Key verwendet, funktioniert alles

-- ============================================
-- WICHTIG: Warum diese vereinfachte Lösung?
-- ============================================
-- Die App verwendet den Supabase Service Role Key (nicht Anon Key)
-- Service Role hat immer vollen Zugriff, unabhängig von RLS Policies
-- Wir aktivieren RLS für Sicherheit, aber brauchen nur Service Role Policy
-- Datenschutz wird auf Anwendungsebene durch betrieb_id sichergestellt

-- ============================================
-- 1. BETRIEBE
-- ============================================

ALTER TABLE public.betriebe ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.betriebe FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================
-- 2. USERS
-- ============================================

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.users FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================
-- 3. MITARBEITER
-- ============================================

ALTER TABLE public.mitarbeiter ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.mitarbeiter FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================
-- 4. ZEITERFASSUNGEN (falls vorhanden)
-- ============================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'zeiterfassungen') THEN
        ALTER TABLE public.zeiterfassungen ENABLE ROW LEVEL SECURITY;
        
        EXECUTE 'CREATE POLICY "Service Role voller Zugriff"
        ON public.zeiterfassungen FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)';
        
        RAISE NOTICE '✅ RLS für zeiterfassungen aktiviert';
    END IF;
END $$;

-- ============================================
-- 5. URLAUBSANTRÄGE (falls vorhanden)
-- ============================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'urlaubsantraege') THEN
        ALTER TABLE public.urlaubsantraege ENABLE ROW LEVEL SECURITY;
        
        EXECUTE 'CREATE POLICY "Service Role voller Zugriff"
        ON public.urlaubsantraege FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)';
        
        RAISE NOTICE '✅ RLS für urlaubsantraege aktiviert';
    END IF;
END $$;

-- ============================================
-- 6. DIENSTPLÄNE (falls vorhanden)
-- ============================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'dienstplaene') THEN
        ALTER TABLE public.dienstplaene ENABLE ROW LEVEL SECURITY;
        
        EXECUTE 'CREATE POLICY "Service Role voller Zugriff"
        ON public.dienstplaene FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)';
        
        RAISE NOTICE '✅ RLS für dienstplaene aktiviert';
    END IF;
END $$;

-- ============================================
-- 7. BENACHRICHTIGUNGEN
-- ============================================

ALTER TABLE public.benachrichtigungen ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.benachrichtigungen FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================
-- 8. PLAUDERECKE
-- ============================================

ALTER TABLE public.plauderecke ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.plauderecke FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================
-- 9. ÄNDERUNGSANFRAGEN
-- ============================================

ALTER TABLE public.aenderungsanfragen ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.aenderungsanfragen FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================
-- 10. MASTERGERÄTE
-- ============================================

ALTER TABLE public.mastergeraete ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.mastergeraete FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================
-- FERTIG!
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '🎉 RLS erfolgreich aktiviert!';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Alle Tabellen haben RLS aktiviert';
    RAISE NOTICE '✅ Service Role hat vollen Zugriff';
    RAISE NOTICE '✅ Datenschutz durch betrieb_id auf App-Ebene';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Wie es funktioniert:';
    RAISE NOTICE '  - App verwendet Supabase Service Role Key';
    RAISE NOTICE '  - Service Role hat immer vollen Zugriff';
    RAISE NOTICE '  - RLS ist aktiviert für Sicherheit';
    RAISE NOTICE '  - Datenisolation durch betrieb_id im Code';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Arbeitsvertrag-Upload sollte jetzt funktionieren!';
END $$;
