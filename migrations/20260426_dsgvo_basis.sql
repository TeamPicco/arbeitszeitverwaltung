-- ============================================================
-- DSGVO-BASIS-MIGRATION
-- DSGVO-001: Automatische Pseudonymisierung nach Aufbewahrungsfrist
-- DSGVO-003: AVV-Register für Auftragsverarbeiter
-- DSGVO-004: DSE-Einwilligungsprotokoll
-- Datum: 2026-04-26
-- ============================================================

BEGIN;

-- ============================================================
-- 1) AVV-Register (Auftragsverarbeitungsverträge)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.avv_register (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    auftragsverarbeiter TEXT NOT NULL,
    zweck TEXT NOT NULL,
    datenkategorien TEXT,
    server_standort TEXT DEFAULT 'EU',
    avv_unterzeichnet BOOLEAN DEFAULT FALSE,
    unterzeichnet_am DATE,
    gueltig_bis DATE,
    dokument_pfad TEXT,
    notizen TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_avv_register_betrieb_id ON public.avv_register(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_avv_register_gueltig_bis ON public.avv_register(gueltig_bis);

-- Standard-Auftragsverarbeiter für alle neuen Betriebe eintragen
-- (wird beim Onboarding via Funktion befüllt)

-- ============================================================
-- 2) DSE-Einwilligungsprotokoll
-- ============================================================
CREATE TABLE IF NOT EXISTS public.dse_einwilligungen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    admin_username TEXT NOT NULL,
    dse_version TEXT NOT NULL DEFAULT '1.0',
    eingewilligt_am TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_adresse TEXT,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_dse_einwilligungen_betrieb ON public.dse_einwilligungen(betrieb_id);

-- ============================================================
-- 3) Pseudonymisierungs-Funktion (Art. 17 DSGVO)
-- Läuft monatlich via pg_cron oder manuell via Admin-Button
-- ============================================================
CREATE OR REPLACE FUNCTION public.pseudonymisiere_ausgeschiedene_mitarbeiter()
RETURNS TABLE(verarbeitet INT, pseudonymisiert INT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_verarbeitet INT := 0;
    v_pseudonymisiert INT := 0;
    v_cutoff DATE := (CURRENT_DATE - INTERVAL '10 years')::DATE;
    r RECORD;
BEGIN
    -- Mitarbeiter mit Austrittsdatum älter als 10 Jahre (§147 AO: Aufbewahrungsfrist Lohnunterlagen)
    FOR r IN
        SELECT id, vorname, nachname, personalnummer
        FROM public.mitarbeiter
        WHERE austrittsdatum IS NOT NULL
          AND austrittsdatum < v_cutoff
          AND vorname NOT LIKE 'GELÖSCHT%'
    LOOP
        v_verarbeitet := v_verarbeitet + 1;

        -- Personenbezogene Daten pseudonymisieren
        UPDATE public.mitarbeiter SET
            vorname             = 'GELÖSCHT',
            nachname            = 'GELÖSCHT-' || id::TEXT,
            email               = 'geloescht-' || id::TEXT || '@complio.invalid',
            telefon             = NULL,
            strasse             = NULL,
            plz                 = NULL,
            ort                 = NULL,
            geburtsdatum        = '1900-01-01',
            arbeitsvertrag_pfad = NULL,
            updated_at          = NOW()
        WHERE id = r.id;

        v_pseudonymisiert := v_pseudonymisiert + 1;

        -- Protokoll-Eintrag
        INSERT INTO public.datenschutz_loeschlog (
            mitarbeiter_id, aktion, ausgefuehrt_am, grund
        ) VALUES (
            r.id,
            'pseudonymisiert',
            NOW(),
            'Aufbewahrungsfrist abgelaufen (10 Jahre nach Austrittsdatum, §147 AO)'
        ) ON CONFLICT DO NOTHING;
    END LOOP;

    RETURN QUERY SELECT v_verarbeitet, v_pseudonymisiert;
END;
$$;

-- ============================================================
-- 4) Lösch-Protokoll-Tabelle
-- ============================================================
CREATE TABLE IF NOT EXISTS public.datenschutz_loeschlog (
    id BIGSERIAL PRIMARY KEY,
    mitarbeiter_id BIGINT NOT NULL,
    aktion TEXT NOT NULL DEFAULT 'pseudonymisiert',
    ausgefuehrt_am TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ausgefuehrt_von TEXT DEFAULT 'system',
    grund TEXT
);

CREATE INDEX IF NOT EXISTS idx_loeschlog_mitarbeiter ON public.datenschutz_loeschlog(mitarbeiter_id);
CREATE INDEX IF NOT EXISTS idx_loeschlog_datum ON public.datenschutz_loeschlog(ausgefuehrt_am);

-- ============================================================
-- 5) Monatlicher Cron-Job via pg_cron (falls Extension aktiv)
-- In Supabase: Datenbank → Extensions → pg_cron aktivieren
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        PERFORM cron.schedule(
            'complio-dsgvo-loeschung',
            '0 3 1 * *',  -- Jeden 1. des Monats um 03:00 Uhr
            'SELECT * FROM public.pseudonymisiere_ausgeschiedene_mitarbeiter()'
        );
    END IF;
END $$;

-- ============================================================
-- 6) Standard-AVV-Einträge für bestehende Betriebe
--    (Supabase, Render.com, Anthropic als bekannte Verarbeiter)
-- ============================================================
INSERT INTO public.avv_register (betrieb_id, auftragsverarbeiter, zweck, server_standort, datenkategorien, avv_unterzeichnet, notizen)
SELECT
    b.id,
    'Supabase Inc.',
    'Datenbankbetrieb und Datenspeicherung',
    'EU (Frankfurt)',
    'Mitarbeiterstammdaten, Zeiterfassungsdaten, Lohndaten',
    TRUE,
    'Standard Contractual Clauses (SCCs) + DPA vorhanden. Server: eu-central-1 (Frankfurt).'
FROM public.betriebe b
WHERE NOT EXISTS (
    SELECT 1 FROM public.avv_register a
    WHERE a.betrieb_id = b.id AND a.auftragsverarbeiter = 'Supabase Inc.'
);

INSERT INTO public.avv_register (betrieb_id, auftragsverarbeiter, zweck, server_standort, datenkategorien, avv_unterzeichnet, notizen)
SELECT
    b.id,
    'Render Inc.',
    'Anwendungs-Hosting und Deployment',
    'EU (Frankfurt)',
    'Alle Applikationsdaten (Zwischenspeicherung im RAM während der Verarbeitung)',
    FALSE,
    'AVV-Unterzeichnung ausstehend. Render DPA unter render.com/privacy abrufen und unterzeichnen.'
FROM public.betriebe b
WHERE NOT EXISTS (
    SELECT 1 FROM public.avv_register a
    WHERE a.betrieb_id = b.id AND a.auftragsverarbeiter = 'Render Inc.'
);

INSERT INTO public.avv_register (betrieb_id, auftragsverarbeiter, zweck, server_standort, datenkategorien, avv_unterzeichnet, notizen)
SELECT
    b.id,
    'Anthropic PBC',
    'KI-Gefährdungsbeurteilung (Claude API)',
    'USA (EU-Addendum erforderlich)',
    'Beschreibung von Betriebsprozessen (anonym, kein Personenbezug wenn korrekt implementiert)',
    FALSE,
    'EU Data Processing Addendum unter anthropic.com/legal anfordern. Sicherstellen dass keine personenbezogenen Daten an API gesendet werden.'
FROM public.betriebe b
WHERE NOT EXISTS (
    SELECT 1 FROM public.avv_register a
    WHERE a.betrieb_id = b.id AND a.auftragsverarbeiter = 'Anthropic PBC'
);

COMMIT;
