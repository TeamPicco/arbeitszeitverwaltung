-- Employee Dashboard Requests/Artifacts
-- Adds optional tables required by the reactivated employee dashboard.
-- Idempotent and safe for repeated execution.

-- Dienstplanwünsche von Mitarbeitern an Admin
CREATE TABLE IF NOT EXISTS public.dienstplanwuensche (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
    monat INTEGER NOT NULL CHECK (monat BETWEEN 1 AND 12),
    jahr INTEGER NOT NULL CHECK (jahr >= 2000),
    wunsch_typ TEXT NOT NULL DEFAULT 'allgemein',
    von_datum DATE,
    bis_datum DATE,
    details TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'offen',
    admin_kommentar TEXT,
    erstellt_am TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bearbeitet_am TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_dienstplanwuensche_betrieb_status
    ON public.dienstplanwuensche(betrieb_id, status, jahr, monat);
CREATE INDEX IF NOT EXISTS idx_dienstplanwuensche_mitarbeiter
    ON public.dienstplanwuensche(mitarbeiter_id, erstellt_am DESC);

-- Monatsweise veröffentlichte Mitarbeiter-Dienstpläne (PDF/Dateipfad)
CREATE TABLE IF NOT EXISTS public.dienstplan_pdf_freigaben (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    monat INTEGER NOT NULL CHECK (monat BETWEEN 1 AND 12),
    jahr INTEGER NOT NULL CHECK (jahr >= 2000),
    titel TEXT,
    file_path TEXT,
    file_url TEXT,
    erstellt_von BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
    erstellt_am TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (mitarbeiter_id, monat, jahr)
);

CREATE INDEX IF NOT EXISTS idx_dienstplan_pdf_freigaben_betrieb
    ON public.dienstplan_pdf_freigaben(betrieb_id, jahr, monat);

-- Optional: status-Werte bei älteren Installationen angleichen (nur falls nicht vorhanden)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'aenderungsanfragen'
          AND column_name = 'status'
    ) THEN
        UPDATE public.aenderungsanfragen
        SET status = 'offen'
        WHERE COALESCE(TRIM(status), '') = '';
    END IF;
END $$;

