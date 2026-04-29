-- ============================================================================
-- ADMIN-PASSWORT ZURÜCKSETZEN
-- ============================================================================
-- Dieses Skript setzt das Admin-Passwort auf: RangeRover2026
-- Führen Sie es in Supabase SQL Editor aus
-- ============================================================================

UPDATE public.users
SET password_hash = '$2b$12$Fv96cAJ6aglgFVzVnNDJZuxHUkFWG3RJ/cdIZXqjBGpFjCVpi0A4y'
WHERE username = 'admin';

-- Prüfe ob Update erfolgreich war
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO updated_count FROM public.users WHERE username = 'admin';
    
    IF updated_count > 0 THEN
        RAISE NOTICE '✅ Admin-Passwort erfolgreich zurückgesetzt!';
        RAISE NOTICE '🔑 Neues Passwort: RangeRover2026';
        RAISE NOTICE '👤 Benutzername: admin';
        RAISE NOTICE '🏢 Betriebsnummer: 20262204';
    ELSE
        RAISE NOTICE '❌ Admin-User nicht gefunden!';
    END IF;
END $$;
