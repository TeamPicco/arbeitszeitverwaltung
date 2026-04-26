-- ============================================================
-- SICHERHEITS-MIGRATION: Row Level Security (RLS) vollständig
-- SEC-002 / DSGVO-002: Mitarbeiter können nur eigene Daten lesen
-- Datum: 2026-04-26
-- FIX: TEXT-basierte Vergleiche für UUID- und BIGINT-Kompatibilität
-- ============================================================
-- Ausführen im Supabase SQL-Editor als Service-Role.
-- Alle Policies sind additiv (bestehende Admin-Policies bleiben).
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- HELPER: aktuelle betrieb_id als TEXT (funktioniert mit UUID & BIGINT)
-- Wird nach Login via set_config('app.current_betrieb_id') gesetzt.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_betrieb_id_text()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_betrieb_id', TRUE), '');
$$;

-- ------------------------------------------------------------
-- HELPER: aktuelle user_id als TEXT (funktioniert mit UUID & BIGINT)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_app_user_id_text()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_user_id', TRUE), '');
$$;

-- Rückwärtskompatible BIGINT-Varianten (falls anderswo verwendet)
CREATE OR REPLACE FUNCTION public.current_betrieb_id()
RETURNS BIGINT
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_betrieb_id', TRUE), '')::BIGINT;
$$;

CREATE OR REPLACE FUNCTION public.current_app_user_id()
RETURNS BIGINT
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_user_id', TRUE), '')::BIGINT;
$$;

-- ============================================================
-- TABELLE: users
-- ============================================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Admin: voller Zugriff auf alle User des eigenen Betriebs
DROP POLICY IF EXISTS users_admin_betrieb ON public.users;
CREATE POLICY users_admin_betrieb ON public.users
  FOR ALL
  USING (betrieb_id::TEXT = public.current_betrieb_id_text());

-- Mitarbeiter: nur eigene Zeile lesen
DROP POLICY IF EXISTS users_self_select ON public.users;
CREATE POLICY users_self_select ON public.users
  FOR SELECT
  USING (id::TEXT = public.current_app_user_id_text());

-- ============================================================
-- TABELLE: mitarbeiter
-- ============================================================
ALTER TABLE public.mitarbeiter ENABLE ROW LEVEL SECURITY;

-- Admin: alle Mitarbeiter des eigenen Betriebs
DROP POLICY IF EXISTS mitarbeiter_admin_betrieb ON public.mitarbeiter;
CREATE POLICY mitarbeiter_admin_betrieb ON public.mitarbeiter
  FOR ALL
  USING (betrieb_id::TEXT = public.current_betrieb_id_text());

-- Mitarbeiter: nur eigener Datensatz
DROP POLICY IF EXISTS mitarbeiter_self_select ON public.mitarbeiter;
CREATE POLICY mitarbeiter_self_select ON public.mitarbeiter
  FOR SELECT
  USING (
    betrieb_id::TEXT = public.current_betrieb_id_text()
    AND user_id::TEXT = public.current_app_user_id_text()
  );

DROP POLICY IF EXISTS mitarbeiter_self_update ON public.mitarbeiter;
CREATE POLICY mitarbeiter_self_update ON public.mitarbeiter
  FOR UPDATE
  USING (
    betrieb_id::TEXT = public.current_betrieb_id_text()
    AND user_id::TEXT = public.current_app_user_id_text()
  )
  WITH CHECK (
    betrieb_id::TEXT = public.current_betrieb_id_text()
    AND user_id::TEXT = public.current_app_user_id_text()
  );

-- ============================================================
-- TABELLE: zeiterfassung
-- ============================================================
ALTER TABLE public.zeiterfassung ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS zeiterfassung_admin ON public.zeiterfassung;
CREATE POLICY zeiterfassung_admin ON public.zeiterfassung
  FOR ALL
  USING (betrieb_id::TEXT = public.current_betrieb_id_text());

DROP POLICY IF EXISTS zeiterfassung_self ON public.zeiterfassung;
CREATE POLICY zeiterfassung_self ON public.zeiterfassung
  FOR SELECT
  USING (
    betrieb_id::TEXT = public.current_betrieb_id_text()
    AND mitarbeiter_id::TEXT IN (
      SELECT id::TEXT FROM public.mitarbeiter
      WHERE betrieb_id::TEXT = public.current_betrieb_id_text()
        AND user_id::TEXT = public.current_app_user_id_text()
    )
  );

-- ============================================================
-- TABELLE: urlaubsantraege
-- ============================================================
ALTER TABLE public.urlaubsantraege ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS urlaub_admin ON public.urlaubsantraege;
CREATE POLICY urlaub_admin ON public.urlaubsantraege
  FOR ALL
  USING (betrieb_id::TEXT = public.current_betrieb_id_text());

DROP POLICY IF EXISTS urlaub_self ON public.urlaubsantraege;
CREATE POLICY urlaub_self ON public.urlaubsantraege
  FOR SELECT
  USING (
    betrieb_id::TEXT = public.current_betrieb_id_text()
    AND mitarbeiter_id::TEXT IN (
      SELECT id::TEXT FROM public.mitarbeiter
      WHERE betrieb_id::TEXT = public.current_betrieb_id_text()
        AND user_id::TEXT = public.current_app_user_id_text()
    )
  );

DROP POLICY IF EXISTS urlaub_self_insert ON public.urlaubsantraege;
CREATE POLICY urlaub_self_insert ON public.urlaubsantraege
  FOR INSERT
  WITH CHECK (
    betrieb_id::TEXT = public.current_betrieb_id_text()
    AND mitarbeiter_id::TEXT IN (
      SELECT id::TEXT FROM public.mitarbeiter
      WHERE betrieb_id::TEXT = public.current_betrieb_id_text()
        AND user_id::TEXT = public.current_app_user_id_text()
    )
  );

-- ============================================================
-- TABELLE: lohnabrechnungen
-- ============================================================
ALTER TABLE public.lohnabrechnungen ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lohn_admin ON public.lohnabrechnungen;
CREATE POLICY lohn_admin ON public.lohnabrechnungen
  FOR ALL
  USING (betrieb_id::TEXT = public.current_betrieb_id_text());

DROP POLICY IF EXISTS lohn_self ON public.lohnabrechnungen;
CREATE POLICY lohn_self ON public.lohnabrechnungen
  FOR SELECT
  USING (
    betrieb_id::TEXT = public.current_betrieb_id_text()
    AND mitarbeiter_id::TEXT IN (
      SELECT id::TEXT FROM public.mitarbeiter
      WHERE betrieb_id::TEXT = public.current_betrieb_id_text()
        AND user_id::TEXT = public.current_app_user_id_text()
    )
  );

-- ============================================================
-- TABELLE: betriebe — nur Admin des eigenen Betriebs
-- ============================================================
ALTER TABLE public.betriebe ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS betriebe_own ON public.betriebe;
CREATE POLICY betriebe_own ON public.betriebe
  FOR ALL
  USING (id::TEXT = public.current_betrieb_id_text());

-- ============================================================
-- HINWEIS: utils/database.py setzt nach Login:
--   set_config('app.current_betrieb_id', str(betrieb_id), false)
--   set_config('app.current_user_id', str(user_id), false)
-- ============================================================

COMMIT;
