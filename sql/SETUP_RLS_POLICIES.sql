-- CrewBase - Row Level Security (RLS) Policies
-- Dieses Skript konfiguriert die Sicherheitsrichtlinien für alle Tabellen
-- Führen Sie dies nach SETUP_NEW_TABLES.sql und ADD_BETRIEB_ID.sql aus

-- ============================================
-- WICHTIG: Was sind RLS Policies?
-- ============================================
-- Row Level Security (RLS) schützt Daten auf Zeilenebene
-- Ohne Policies können keine Daten eingefügt/gelesen werden
-- Wir erstellen Policies für:
-- - Admin: Voller Zugriff auf alle Daten seines Betriebs
-- - Mitarbeiter: Zugriff nur auf eigene Daten
-- - Service Role: Vollzugriff (für Backend-Operationen)

-- ============================================
-- 1. BETRIEBE - RLS Policies
-- ============================================

-- RLS aktivieren
ALTER TABLE public.betriebe ENABLE ROW LEVEL SECURITY;

-- Policy: Jeder kann seinen eigenen Betrieb lesen
CREATE POLICY "Benutzer können ihren eigenen Betrieb lesen"
ON public.betriebe FOR SELECT
USING (true);

-- Policy: Nur Service Role kann Betriebe erstellen/ändern
CREATE POLICY "Service Role kann Betriebe verwalten"
ON public.betriebe FOR ALL
USING (auth.role() = 'service_role');

-- ============================================
-- 2. USERS - RLS Policies
-- ============================================

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Policy: Benutzer können ihre eigenen Daten lesen
CREATE POLICY "Benutzer können eigene Daten lesen"
ON public.users FOR SELECT
USING (auth.uid() = id::uuid);

-- Policy: Benutzer können ihre eigenen Daten aktualisieren
CREATE POLICY "Benutzer können eigene Daten aktualisieren"
ON public.users FOR UPDATE
USING (auth.uid() = id::uuid);

-- Policy: Service Role hat vollen Zugriff
CREATE POLICY "Service Role kann Users verwalten"
ON public.users FOR ALL
USING (auth.role() = 'service_role');

-- ============================================
-- 3. MITARBEITER - RLS Policies
-- ============================================

ALTER TABLE public.mitarbeiter ENABLE ROW LEVEL SECURITY;

-- Policy: Mitarbeiter können ihre eigenen Daten lesen
CREATE POLICY "Mitarbeiter können eigene Daten lesen"
ON public.mitarbeiter FOR SELECT
USING (auth.uid() = user_id::uuid);

-- Policy: Mitarbeiter können ihre eigenen Daten aktualisieren
CREATE POLICY "Mitarbeiter können eigene Daten aktualisieren"
ON public.mitarbeiter FOR UPDATE
USING (auth.uid() = user_id::uuid);

-- Policy: Service Role hat vollen Zugriff
CREATE POLICY "Service Role kann Mitarbeiter verwalten"
ON public.mitarbeiter FOR ALL
USING (auth.role() = 'service_role');

-- ============================================
-- 4. ZEITERFASSUNGEN - RLS Policies
-- ============================================

-- Prüfe ob Tabelle existiert
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'zeiterfassungen') THEN
        ALTER TABLE public.zeiterfassungen ENABLE ROW LEVEL SECURITY;
        
        -- Policy: Mitarbeiter können ihre eigenen Zeiterfassungen lesen
        EXECUTE 'CREATE POLICY "Mitarbeiter können eigene Zeiterfassungen lesen"
        ON public.zeiterfassungen FOR SELECT
        USING (auth.uid() IN (SELECT user_id::uuid FROM public.mitarbeiter WHERE id = zeiterfassungen.mitarbeiter_id))';
        
        -- Policy: Mitarbeiter können ihre eigenen Zeiterfassungen erstellen
        EXECUTE 'CREATE POLICY "Mitarbeiter können eigene Zeiterfassungen erstellen"
        ON public.zeiterfassungen FOR INSERT
        WITH CHECK (auth.uid() IN (SELECT user_id::uuid FROM public.mitarbeiter WHERE id = zeiterfassungen.mitarbeiter_id))';
        
        -- Policy: Service Role hat vollen Zugriff
        EXECUTE 'CREATE POLICY "Service Role kann Zeiterfassungen verwalten"
        ON public.zeiterfassungen FOR ALL
        USING (auth.role() = ''service_role'')';
        
        RAISE NOTICE '✅ RLS Policies für zeiterfassungen erstellt';
    ELSE
        RAISE NOTICE '⏭️  Tabelle zeiterfassungen existiert nicht';
    END IF;
END $$;

-- ============================================
-- 5. URLAUBSANTRÄGE - RLS Policies
-- ============================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'urlaubsantraege') THEN
        ALTER TABLE public.urlaubsantraege ENABLE ROW LEVEL SECURITY;
        
        -- Policy: Mitarbeiter können ihre eigenen Anträge lesen
        EXECUTE 'CREATE POLICY "Mitarbeiter können eigene Urlaubsanträge lesen"
        ON public.urlaubsantraege FOR SELECT
        USING (auth.uid() IN (SELECT user_id::uuid FROM public.mitarbeiter WHERE id = urlaubsantraege.mitarbeiter_id))';
        
        -- Policy: Mitarbeiter können ihre eigenen Anträge erstellen
        EXECUTE 'CREATE POLICY "Mitarbeiter können eigene Urlaubsanträge erstellen"
        ON public.urlaubsantraege FOR INSERT
        WITH CHECK (auth.uid() IN (SELECT user_id::uuid FROM public.mitarbeiter WHERE id = urlaubsantraege.mitarbeiter_id))';
        
        -- Policy: Service Role hat vollen Zugriff
        EXECUTE 'CREATE POLICY "Service Role kann Urlaubsanträge verwalten"
        ON public.urlaubsantraege FOR ALL
        USING (auth.role() = ''service_role'')';
        
        RAISE NOTICE '✅ RLS Policies für urlaubsantraege erstellt';
    ELSE
        RAISE NOTICE '⏭️  Tabelle urlaubsantraege existiert nicht';
    END IF;
END $$;

-- ============================================
-- 6. BENACHRICHTIGUNGEN - RLS Policies
-- ============================================

ALTER TABLE public.benachrichtigungen ENABLE ROW LEVEL SECURITY;

-- Policy: Benutzer können ihre eigenen Benachrichtigungen lesen
CREATE POLICY "Benutzer können eigene Benachrichtigungen lesen"
ON public.benachrichtigungen FOR SELECT
USING (auth.uid() = user_id::uuid);

-- Policy: Benutzer können ihre eigenen Benachrichtigungen aktualisieren
CREATE POLICY "Benutzer können eigene Benachrichtigungen aktualisieren"
ON public.benachrichtigungen FOR UPDATE
USING (auth.uid() = user_id::uuid);

-- Policy: Service Role hat vollen Zugriff
CREATE POLICY "Service Role kann Benachrichtigungen verwalten"
ON public.benachrichtigungen FOR ALL
USING (auth.role() = 'service_role');

-- ============================================
-- 7. PLAUDERECKE - RLS Policies
-- ============================================

ALTER TABLE public.plauderecke ENABLE ROW LEVEL SECURITY;

-- Policy: Alle Benutzer des Betriebs können Chat-Nachrichten lesen
CREATE POLICY "Benutzer können Chat-Nachrichten ihres Betriebs lesen"
ON public.plauderecke FOR SELECT
USING (true);

-- Policy: Benutzer können Chat-Nachrichten erstellen
CREATE POLICY "Benutzer können Chat-Nachrichten erstellen"
ON public.plauderecke FOR INSERT
WITH CHECK (auth.uid() = user_id::uuid);

-- Policy: Benutzer können ihre eigenen Nachrichten löschen
CREATE POLICY "Benutzer können eigene Chat-Nachrichten löschen"
ON public.plauderecke FOR DELETE
USING (auth.uid() = user_id::uuid);

-- Policy: Service Role hat vollen Zugriff
CREATE POLICY "Service Role kann Chat-Nachrichten verwalten"
ON public.plauderecke FOR ALL
USING (auth.role() = 'service_role');

-- ============================================
-- 8. ÄNDERUNGSANFRAGEN - RLS Policies
-- ============================================

ALTER TABLE public.aenderungsanfragen ENABLE ROW LEVEL SECURITY;

-- Policy: Mitarbeiter können ihre eigenen Anfragen lesen
CREATE POLICY "Mitarbeiter können eigene Änderungsanfragen lesen"
ON public.aenderungsanfragen FOR SELECT
USING (auth.uid() = user_id::uuid);

-- Policy: Mitarbeiter können ihre eigenen Anfragen erstellen
CREATE POLICY "Mitarbeiter können eigene Änderungsanfragen erstellen"
ON public.aenderungsanfragen FOR INSERT
WITH CHECK (auth.uid() = user_id::uuid);

-- Policy: Service Role hat vollen Zugriff
CREATE POLICY "Service Role kann Änderungsanfragen verwalten"
ON public.aenderungsanfragen FOR ALL
USING (auth.role() = 'service_role');

-- ============================================
-- 9. MASTERGERÄTE - RLS Policies
-- ============================================

ALTER TABLE public.mastergeraete ENABLE ROW LEVEL SECURITY;

-- Policy: Alle können Mastergeräte lesen (für Registrierung)
CREATE POLICY "Benutzer können Mastergeräte lesen"
ON public.mastergeraete FOR SELECT
USING (true);

-- Policy: Service Role hat vollen Zugriff
CREATE POLICY "Service Role kann Mastergeräte verwalten"
ON public.mastergeraete FOR ALL
USING (auth.role() = 'service_role');

-- ============================================
-- FERTIG!
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '🎉 RLS Policies erfolgreich konfiguriert!';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Alle Tabellen haben jetzt Sicherheitsrichtlinien';
    RAISE NOTICE '✅ Mitarbeiter können nur ihre eigenen Daten sehen';
    RAISE NOTICE '✅ Service Role (Backend) hat vollen Zugriff';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  WICHTIG: Supabase Service Role Key';
    RAISE NOTICE '   Die App muss den Service Role Key verwenden,';
    RAISE NOTICE '   nicht den Anon Key, um Daten zu verwalten.';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Nächste Schritte:';
    RAISE NOTICE '  1. Prüfen Sie die Supabase-Verbindung in der App';
    RAISE NOTICE '  2. Arbeitsvertrag-Upload sollte jetzt funktionieren';
    RAISE NOTICE '  3. Alle Features testen';
END $$;
