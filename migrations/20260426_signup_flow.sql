-- ============================================================
-- SIGNUP FLOW MIGRATION
-- user_feature_plans Tabelle + email-Spalte für betriebe
-- ============================================================

BEGIN;

-- Tabelle für Plan/Testphase pro Betrieb
CREATE TABLE IF NOT EXISTS public.user_feature_plans (
    id          BIGSERIAL PRIMARY KEY,
    betrieb_id  BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    plan        TEXT NOT NULL DEFAULT 'starter' CHECK (plan IN ('starter', 'pro', 'multi')),
    valid_until DATE,
    upgraded_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(betrieb_id)
);

CREATE INDEX IF NOT EXISTS idx_feature_plans_betrieb ON public.user_feature_plans(betrieb_id);

-- E-Mail-Adresse des Admins an betriebe hängen (für Willkommensmail + PW-Reset)
ALTER TABLE public.betriebe
  ADD COLUMN IF NOT EXISTS admin_email TEXT,
  ADD COLUMN IF NOT EXISTS erstellt_am TIMESTAMPTZ DEFAULT NOW();

-- Bestehende Betriebe bekommen Starter-Plan ohne Ablaufzeit (Bestandskunden)
INSERT INTO public.user_feature_plans (betrieb_id, plan, valid_until)
SELECT id, 'pro', NULL
FROM public.betriebe
WHERE NOT EXISTS (
  SELECT 1 FROM public.user_feature_plans p WHERE p.betrieb_id = betriebe.id
);

COMMIT;
