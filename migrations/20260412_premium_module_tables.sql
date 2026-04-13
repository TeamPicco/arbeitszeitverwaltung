-- Premium-Module: Feature-Pläne, Gefährdungsbeurteilung, Rechts-Updates
-- Nicht-destruktiv: Es werden ausschließlich neue Tabellen/Funktionen/Trigger angelegt.

BEGIN;

-- ------------------------------------------------------------
-- Gemeinsame Trigger-Funktion für updated_at
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

-- ------------------------------------------------------------
-- 1) Nutzer-Feature-Pläne
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_feature_plans (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    plan TEXT NOT NULL CHECK (plan IN ('starter', 'professional', 'compliance', 'complete')),
    valid_until DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_feature_plans_user_id
    ON public.user_feature_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feature_plans_valid_until
    ON public.user_feature_plans(valid_until);

DROP TRIGGER IF EXISTS trg_user_feature_plans_updated_at ON public.user_feature_plans;
CREATE TRIGGER trg_user_feature_plans_updated_at
BEFORE UPDATE ON public.user_feature_plans
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at_timestamp();

-- ------------------------------------------------------------
-- 2) Gefährdungsbeurteilungen
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.hazard_assessments (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    industry TEXT NOT NULL CHECK (industry IN ('gastronomie', 'einzelhandel', 'handwerk', 'buero', 'sonstiges')),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'entwurf' CHECK (status IN ('entwurf', 'aktiv', 'ueberfaellig')),
    last_reviewed_at DATE,
    next_review_due DATE GENERATED ALWAYS AS ((last_reviewed_at + INTERVAL '1 year')::DATE) STORED,
    created_by BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hazard_assessments_betrieb_id
    ON public.hazard_assessments(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_hazard_assessments_status
    ON public.hazard_assessments(status);
CREATE INDEX IF NOT EXISTS idx_hazard_assessments_next_review_due
    ON public.hazard_assessments(next_review_due);

DROP TRIGGER IF EXISTS trg_hazard_assessments_updated_at ON public.hazard_assessments;
CREATE TRIGGER trg_hazard_assessments_updated_at
BEFORE UPDATE ON public.hazard_assessments
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at_timestamp();

-- ------------------------------------------------------------
-- 3) Schritte der Gefährdungsbeurteilung (1-5)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.hazard_assessment_steps (
    id BIGSERIAL PRIMARY KEY,
    assessment_id BIGINT NOT NULL REFERENCES public.hazard_assessments(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL CHECK (step_number BETWEEN 1 AND 5),
    step_name TEXT NOT NULL,
    content TEXT,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (assessment_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_hazard_assessment_steps_assessment_id
    ON public.hazard_assessment_steps(assessment_id);
CREATE INDEX IF NOT EXISTS idx_hazard_assessment_steps_completed
    ON public.hazard_assessment_steps(completed);

DROP TRIGGER IF EXISTS trg_hazard_assessment_steps_updated_at ON public.hazard_assessment_steps;
CREATE TRIGGER trg_hazard_assessment_steps_updated_at
BEFORE UPDATE ON public.hazard_assessment_steps
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at_timestamp();

-- ------------------------------------------------------------
-- 4) Rechtliche Updates (z. B. Mindestlohn, ArbZG)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.legal_update_log (
    id BIGSERIAL PRIMARY KEY,
    law_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    valid_from DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_legal_update_log_law_name
    ON public.legal_update_log(law_name);
CREATE INDEX IF NOT EXISTS idx_legal_update_log_valid_from
    ON public.legal_update_log(valid_from);

COMMIT;
