-- CrewBase - Vollständiges Datenbank-Setup
-- Dieses Skript erstellt ALLE benötigten Tabellen für CrewBase
-- Führen Sie es in Supabase SQL Editor aus

-- ============================================
-- 1. BETRIEBE (Multi-Tenancy)
-- ============================================

CREATE TABLE IF NOT EXISTS public.betriebe (
    id BIGSERIAL PRIMARY KEY,
    betriebsnummer VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    logo_url TEXT,
    aktiv BOOLEAN DEFAULT true,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    aktualisiert_am TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index für schnelle Suche
CREATE INDEX IF NOT EXISTS idx_betriebe_betriebsnummer ON public.betriebe(betriebsnummer);

-- Piccolo-Betrieb einfügen
INSERT INTO public.betriebe (betriebsnummer, name, aktiv)
VALUES ('20262204', 'Steakhouse Piccolo', true)
ON CONFLICT (betriebsnummer) DO NOTHING;

-- ============================================
-- 2. USERS - betrieb_id hinzufügen (falls nicht vorhanden)
-- ============================================

-- Prüfe ob Spalte existiert und füge sie hinzu
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'users' 
        AND column_name = 'betrieb_id'
    ) THEN
        ALTER TABLE public.users ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
        
        -- Setze betrieb_id für existierende User auf Piccolo
        UPDATE public.users SET betrieb_id = (SELECT id FROM public.betriebe WHERE betriebsnummer = '20262204');
    END IF;
END $$;

-- ============================================
-- 3. MITARBEITER - betrieb_id und mobile_zeiterfassung hinzufügen
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'mitarbeiter' 
        AND column_name = 'betrieb_id'
    ) THEN
        ALTER TABLE public.mitarbeiter ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
        UPDATE public.mitarbeiter SET betrieb_id = (SELECT id FROM public.betriebe WHERE betriebsnummer = '20262204');
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'mitarbeiter' 
        AND column_name = 'mobile_zeiterfassung'
    ) THEN
        ALTER TABLE public.mitarbeiter ADD COLUMN mobile_zeiterfassung BOOLEAN DEFAULT false;
    END IF;
END $$;

-- ============================================
-- 4. MASTERGERÄTE
-- ============================================

CREATE TABLE IF NOT EXISTS public.mastergeraete (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    geraet_id UUID UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    standort VARCHAR(255),
    beschreibung TEXT,
    registrierungscode VARCHAR(20) UNIQUE NOT NULL,
    aktiv BOOLEAN DEFAULT true,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    letzter_zugriff TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_mastergeraete_betrieb ON public.mastergeraete(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_mastergeraete_code ON public.mastergeraete(registrierungscode);

-- ============================================
-- 5. BENACHRICHTIGUNGEN
-- ============================================

CREATE TABLE IF NOT EXISTS public.benachrichtigungen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    titel VARCHAR(255) NOT NULL,
    nachricht TEXT NOT NULL,
    typ VARCHAR(20) DEFAULT 'info', -- info, success, warning, error
    link TEXT,
    gelesen BOOLEAN DEFAULT false,
    gelesen_am TIMESTAMP WITH TIME ZONE,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_benachrichtigungen_user ON public.benachrichtigungen(user_id, gelesen);
CREATE INDEX IF NOT EXISTS idx_benachrichtigungen_betrieb ON public.benachrichtigungen(betrieb_id);

-- ============================================
-- 6. PLAUDERECKE (Chat)
-- ============================================

CREATE TABLE IF NOT EXISTS public.plauderecke (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    nachricht TEXT NOT NULL,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plauderecke_betrieb ON public.plauderecke(betrieb_id, erstellt_am DESC);

-- ============================================
-- 7. ZEITERFASSUNGEN - betrieb_id und Korrektur-Felder hinzufügen
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'zeiterfassungen' 
        AND column_name = 'betrieb_id'
    ) THEN
        ALTER TABLE public.zeiterfassungen ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
        UPDATE public.zeiterfassungen SET betrieb_id = (SELECT id FROM public.betriebe WHERE betriebsnummer = '20262204');
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'zeiterfassungen' 
        AND column_name = 'korrigiert_von_admin'
    ) THEN
        ALTER TABLE public.zeiterfassungen ADD COLUMN korrigiert_von_admin BOOLEAN DEFAULT false;
        ALTER TABLE public.zeiterfassungen ADD COLUMN korrektur_grund TEXT;
        ALTER TABLE public.zeiterfassungen ADD COLUMN korrektur_datum TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- ============================================
-- 8. URLAUBSANTRÄGE - betrieb_id hinzufügen
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'urlaubsantraege' 
        AND column_name = 'betrieb_id'
    ) THEN
        ALTER TABLE public.urlaubsantraege ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
        UPDATE public.urlaubsantraege SET betrieb_id = (SELECT id FROM public.betriebe WHERE betriebsnummer = '20262204');
    END IF;
END $$;

-- ============================================
-- 9. DIENSTPLÄNE - betrieb_id hinzufügen
-- ============================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'dienstplaene') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'dienstplaene' 
            AND column_name = 'betrieb_id'
        ) THEN
            ALTER TABLE public.dienstplaene ADD COLUMN betrieb_id BIGINT REFERENCES public.betriebe(id);
            UPDATE public.dienstplaene SET betrieb_id = (SELECT id FROM public.betriebe WHERE betriebsnummer = '20262204');
        END IF;
    END IF;
END $$;

-- ============================================
-- 10. ÄNDERUNGSANFRAGEN (für Stammdaten-Änderungen)
-- ============================================

CREATE TABLE IF NOT EXISTS public.aenderungsanfragen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    feld VARCHAR(100) NOT NULL,
    alter_wert TEXT,
    neuer_wert TEXT,
    grund TEXT,
    status VARCHAR(20) DEFAULT 'offen', -- offen, genehmigt, abgelehnt
    admin_kommentar TEXT,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    bearbeitet_am TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_aenderungsanfragen_betrieb ON public.aenderungsanfragen(betrieb_id, status);
CREATE INDEX IF NOT EXISTS idx_aenderungsanfragen_mitarbeiter ON public.aenderungsanfragen(mitarbeiter_id);

-- ============================================
-- FERTIG!
-- ============================================

-- Erfolgsmeldung
DO $$
BEGIN
    RAISE NOTICE '✅ CrewBase Datenbank-Setup erfolgreich abgeschlossen!';
    RAISE NOTICE 'Betrieb "Steakhouse Piccolo" (20262204) wurde erstellt.';
    RAISE NOTICE 'Alle Tabellen und Indizes wurden angelegt.';
END $$;
