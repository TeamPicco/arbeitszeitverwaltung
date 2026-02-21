-- Prüfe und korrigiere plauderecke-Tabelle

-- 1. Zeige aktuelle Struktur
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'plauderecke'
ORDER BY ordinal_position;

-- 2. Entferne username-Spalte falls vorhanden (sollte nicht in plauderecke sein)
ALTER TABLE public.plauderecke 
DROP COLUMN IF EXISTS username CASCADE;

-- 3. Stelle sicher, dass user_id eine Foreign Key Referenz hat
DO $$
BEGIN
    -- Prüfe ob Foreign Key existiert
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_type = 'FOREIGN KEY' 
        AND table_name = 'plauderecke' 
        AND constraint_name LIKE '%user_id%'
    ) THEN
        -- Füge Foreign Key hinzu
        ALTER TABLE public.plauderecke 
        ADD CONSTRAINT fk_plauderecke_user_id 
        FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
        
        RAISE NOTICE '✅ Foreign Key zu users hinzugefügt';
    ELSE
        RAISE NOTICE '⏭️  Foreign Key existiert bereits';
    END IF;
END $$;

-- 4. Zeige finale Struktur
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'plauderecke'
ORDER BY ordinal_position;
