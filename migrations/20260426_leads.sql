-- ============================================================
-- LEADS & OUTREACH-SEQUENZ
-- Automatisierte Kundenfindung für Complio
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS public.leads (
    id              BIGSERIAL PRIMARY KEY,
    -- Betrieb
    firmenname      TEXT NOT NULL,
    branche         TEXT DEFAULT 'Gastronomie',
    strasse         TEXT,
    plz             TEXT,
    ort             TEXT,
    bundesland      TEXT,
    -- Kontakt
    email           TEXT,
    telefon         TEXT,
    website         TEXT,
    ansprechpartner TEXT,
    -- Quelle
    quelle          TEXT DEFAULT 'google_maps',
    google_place_id TEXT UNIQUE,
    -- Status
    status          TEXT NOT NULL DEFAULT 'neu'
                    CHECK (status IN ('neu','kontaktiert','antwort','interessiert','abschluss','abgelehnt','abgemeldet')),
    sequenz_schritt INT NOT NULL DEFAULT 0,
    naechste_email  DATE,
    -- Tracking
    emails_gesendet INT DEFAULT 0,
    letzter_kontakt TIMESTAMPTZ,
    notizen         TEXT,
    -- Meta
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_status       ON public.leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_naechste     ON public.leads(naechste_email);
CREATE INDEX IF NOT EXISTS idx_leads_ort          ON public.leads(ort);
CREATE INDEX IF NOT EXISTS idx_leads_email        ON public.leads(email);

CREATE TABLE IF NOT EXISTS public.lead_emails (
    id          BIGSERIAL PRIMARY KEY,
    lead_id     BIGINT NOT NULL REFERENCES public.leads(id) ON DELETE CASCADE,
    schritt     INT NOT NULL,
    betreff     TEXT NOT NULL,
    gesendet_am TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    geoeffnet   BOOLEAN DEFAULT FALSE,
    geklickt    BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_lead_emails_lead ON public.lead_emails(lead_id);

COMMIT;
