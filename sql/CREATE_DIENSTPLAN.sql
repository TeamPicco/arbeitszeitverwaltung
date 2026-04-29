-- Dienstplan-System: Schichtvorlagen und Dienstpläne

-- ============================================
-- 1. SCHICHTVORLAGEN
-- ============================================

CREATE TABLE IF NOT EXISTS public.schichtvorlagen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    beschreibung TEXT,
    start_zeit TIME NOT NULL,
    ende_zeit TIME NOT NULL,
    pause_minuten INTEGER DEFAULT 0,
    farbe VARCHAR(7) DEFAULT '#0d6efd',  -- Hex-Farbe für Kalender-Darstellung
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index für Performance
CREATE INDEX IF NOT EXISTS idx_schichtvorlagen_betrieb ON public.schichtvorlagen(betrieb_id);

-- Kommentare
COMMENT ON TABLE public.schichtvorlagen IS 'Wiederverwendbare Schichtvorlagen (z.B. Frühschicht, Spätschicht)';
COMMENT ON COLUMN public.schichtvorlagen.farbe IS 'Hex-Farbe für Kalender-Darstellung (z.B. #0d6efd)';

-- ============================================
-- 2. DIENSTPLÄNE
-- ============================================

CREATE TABLE IF NOT EXISTS public.dienstplaene (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    datum DATE NOT NULL,
    schichtvorlage_id BIGINT REFERENCES public.schichtvorlagen(id) ON DELETE SET NULL,
    start_zeit TIME NOT NULL,
    ende_zeit TIME NOT NULL,
    pause_minuten INTEGER DEFAULT 0,
    notiz TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(mitarbeiter_id, datum)  -- Ein Mitarbeiter kann nur eine Schicht pro Tag haben
);

-- Indizes für Performance
CREATE INDEX IF NOT EXISTS idx_dienstplaene_betrieb ON public.dienstplaene(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_dienstplaene_mitarbeiter ON public.dienstplaene(mitarbeiter_id);
CREATE INDEX IF NOT EXISTS idx_dienstplaene_datum ON public.dienstplaene(datum);
CREATE INDEX IF NOT EXISTS idx_dienstplaene_monat ON public.dienstplaene(DATE_TRUNC('month', datum));

-- Kommentare
COMMENT ON TABLE public.dienstplaene IS 'Geplante Dienste/Schichten für Mitarbeiter';
COMMENT ON COLUMN public.dienstplaene.schichtvorlage_id IS 'Optional: Referenz zur verwendeten Schichtvorlage';

-- ============================================
-- 3. ROW LEVEL SECURITY (RLS)
-- ============================================

-- Schichtvorlagen
ALTER TABLE public.schichtvorlagen ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.schichtvorlagen FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Dienstpläne
ALTER TABLE public.dienstplaene ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role voller Zugriff"
ON public.dienstplaene FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================
-- 4. STANDARD-SCHICHTVORLAGEN (Optional)
-- ============================================

-- Füge Standard-Schichtvorlagen für Piccolo hinzu (falls Betrieb existiert)
DO $$
DECLARE
    piccolo_id BIGINT;
BEGIN
    SELECT id INTO piccolo_id FROM public.betriebe WHERE betriebsnummer = '20262204';
    
    IF piccolo_id IS NOT NULL THEN
        -- Frühschicht
        INSERT INTO public.schichtvorlagen (betrieb_id, name, beschreibung, start_zeit, ende_zeit, pause_minuten, farbe)
        VALUES (piccolo_id, 'Frühschicht', 'Frühschicht 08:00 - 16:00', '08:00:00', '16:00:00', 30, '#198754')
        ON CONFLICT DO NOTHING;
        
        -- Spätschicht
        INSERT INTO public.schichtvorlagen (betrieb_id, name, beschreibung, start_zeit, ende_zeit, pause_minuten, farbe)
        VALUES (piccolo_id, 'Spätschicht', 'Spätschicht 16:00 - 00:00', '16:00:00', '00:00:00', 30, '#0d6efd')
        ON CONFLICT DO NOTHING;
        
        -- Mittagsschicht
        INSERT INTO public.schichtvorlagen (betrieb_id, name, beschreibung, start_zeit, ende_zeit, pause_minuten, farbe)
        VALUES (piccolo_id, 'Mittagsschicht', 'Mittagsschicht 11:00 - 15:00', '11:00:00', '15:00:00', 0, '#ffc107')
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE '✅ Standard-Schichtvorlagen für Piccolo erstellt';
    END IF;
END $$;
