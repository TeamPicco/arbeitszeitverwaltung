-- CrewBase - Neue Tabellen für Multi-Tenancy und Features
-- Dieses Skript erstellt NUR die neuen Tabellen
-- Existierende Tabellen werden NICHT verändert

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
-- 2. MASTERGERÄTE
-- ============================================

CREATE TABLE IF NOT EXISTS public.mastergeraete (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    geraet_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
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
-- 3. BENACHRICHTIGUNGEN
-- ============================================

CREATE TABLE IF NOT EXISTS public.benachrichtigungen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
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
-- 4. PLAUDERECKE (Chat)
-- ============================================

CREATE TABLE IF NOT EXISTS public.plauderecke (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    username VARCHAR(255) NOT NULL,
    nachricht TEXT NOT NULL,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plauderecke_betrieb ON public.plauderecke(betrieb_id, erstellt_am DESC);

-- ============================================
-- 5. ÄNDERUNGSANFRAGEN (für Stammdaten-Änderungen)
-- ============================================

CREATE TABLE IF NOT EXISTS public.aenderungsanfragen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT,
    user_id TEXT NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_aenderungsanfragen_user ON public.aenderungsanfragen(user_id);

-- ============================================
-- FERTIG!
-- ============================================

-- Erfolgsmeldung
DO $$
BEGIN
    RAISE NOTICE '✅ CrewBase neue Tabellen erfolgreich erstellt!';
    RAISE NOTICE 'Betrieb "Steakhouse Piccolo" (20262204) wurde angelegt.';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Erstellte Tabellen:';
    RAISE NOTICE '  - betriebe';
    RAISE NOTICE '  - mastergeraete';
    RAISE NOTICE '  - benachrichtigungen';
    RAISE NOTICE '  - plauderecke';
    RAISE NOTICE '  - aenderungsanfragen';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  WICHTIG: Die App funktioniert jetzt im Fallback-Modus.';
    RAISE NOTICE '   Für volle Multi-Tenancy-Funktionalität müssen existierende';
    RAISE NOTICE '   Tabellen manuell um betrieb_id erweitert werden.';
END $$;
