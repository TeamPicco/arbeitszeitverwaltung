-- ============================================================
-- SICHERHEITS-MIGRATION: Row Level Security (RLS) vollständig
-- SEC-002 / DSGVO-002: Mitarbeiter können nur eigene Daten lesen
-- Datum: 2026-04-26
-- ============================================================
-- Ausführen im Supabase SQL-Editor als Service-Role.
-- Alle Policies sind additiv (bestehende Admin-Policies bleiben).
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- HELPER: aktuelle betrieb_id aus Session-Variable lesen
-- Wird nach Login via set_config('app.current_betrieb_id') gesetzt.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_betrieb_id()
RETURNS BIGINT
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_betrieb_id', TRUE), '')::BIGINT;
$$;

-- ------------------------------------------------------------
-- HELPER: aktuelle user_id aus Session-Variable lesen
-- ------------------------------------------------------------
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
  USING (betrieb_id = public.current_betrieb_id());

-- Mitarbeiter: nur eigene Zeile lesen
DROP POLICY IF EXISTS users_self_select ON public.users;
CREATE POLICY users_self_select ON public.users
  FOR SELECT
  USING (id = public.current_app_user_id());

-- ============================================================
-- TABELLE: mitarbeiter
-- ============================================================
ALTER TABLE public.mitarbeiter ENABLE ROW LEVEL SECURITY;

-- Admin: alle Mitarbeiter des eigenen Betriebs
DROP POLICY IF EXISTS mitarbeiter_admin_betrieb ON public.mitarbeiter;
CREATE POLICY mitarbeiter_admin_betrieb ON public.mitarbeiter
  FOR ALL
  USING (betrieb_id = public.current_betrieb_id());

-- Mitarbeiter: nur eigener Datensatz
DROP POLICY IF EXISTS mitarbeiter_self_select ON public.mitarbeiter;
CREATE POLICY mitarbeiter_self_select ON public.mitarbeiter
  FOR SELECT
  USING (
    betrieb_id = public.current_betrieb_id()
    AND user_id = public.current_app_user_id()
  );

DROP POLICY IF EXISTS mitarbeiter_self_update ON public.mitarbeiter;
CREATE POLICY mitarbeiter_self_update ON public.mitarbeiter
  FOR UPDATE
  USING (
    betrieb_id = public.current_betrieb_id()
    AND user_id = public.current_app_user_id()
  )
  WITH CHECK (
    betrieb_id = public.current_betrieb_id()
    AND user_id = public.current_app_user_id()
  );

-- ============================================================
-- TABELLE: zeiterfassung / zeit_events
-- ============================================================
ALTER TABLE public.zeiterfassung ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS zeiterfassung_admin ON public.zeiterfassung;
CREATE POLICY zeiterfassung_admin ON public.zeiterfassung
  FOR ALL
  USING (betrieb_id = public.current_betrieb_id());

DROP POLICY IF EXISTS zeiterfassung_self ON public.zeiterfassung;
CREATE POLICY zeiterfassung_self ON public.zeiterfassung
  FOR SELECT
  USING (
    betrieb_id = public.current_betrieb_id()
    AND mitarbeiter_id IN (
      SELECT id FROM public.mitarbeiter
      WHERE betrieb_id = public.current_betrieb_id()
        AND user_id = public.current_app_user_id()
    )
  );

-- ============================================================
-- TABELLE: urlaubsantraege
-- ============================================================
ALTER TABLE public.urlaubsantraege ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS urlaub_admin ON public.urlaubsantraege;
CREATE POLICY urlaub_admin ON public.urlaubsantraege
  FOR ALL
  USING (betrieb_id = public.current_betrieb_id());

DROP POLICY IF EXISTS urlaub_self ON public.urlaubsantraege;
CREATE POLICY urlaub_self ON public.urlaubsantraege
  FOR SELECT
  USING (
    betrieb_id = public.current_betrieb_id()
    AND mitarbeiter_id IN (
      SELECT id FROM public.mitarbeiter
      WHERE betrieb_id = public.current_betrieb_id()
        AND user_id = public.current_app_user_id()
    )
  );

DROP POLICY IF EXISTS urlaub_self_insert ON public.urlaubsantraege;
CREATE POLICY urlaub_self_insert ON public.urlaubsantraege
  FOR INSERT
  WITH CHECK (
    betrieb_id = public.current_betrieb_id()
    AND mitarbeiter_id IN (
      SELECT id FROM public.mitarbeiter
      WHERE betrieb_id = public.current_betrieb_id()
        AND user_id = public.current_app_user_id()
    )
  );

-- ============================================================
-- TABELLE: lohnabrechnungen
-- ============================================================
ALTER TABLE public.lohnabrechnungen ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lohn_admin ON public.lohnabrechnungen;
CREATE POLICY lohn_admin ON public.lohnabrechnungen
  FOR ALL
  USING (betrieb_id = public.current_betrieb_id());

DROP POLICY IF EXISTS lohn_self ON public.lohnabrechnungen;
CREATE POLICY lohn_self ON public.lohnabrechnungen
  FOR SELECT
  USING (
    betrieb_id = public.current_betrieb_id()
    AND mitarbeiter_id IN (
      SELECT id FROM public.mitarbeiter
      WHERE betrieb_id = public.current_betrieb_id()
        AND user_id = public.current_app_user_id()
    )
  );

-- ============================================================
-- TABELLE: betriebe — nur Admin des eigenen Betriebs
-- ============================================================
ALTER TABLE public.betriebe ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS betriebe_own ON public.betriebe;
CREATE POLICY betriebe_own ON public.betriebe
  FOR ALL
  USING (id = public.current_betrieb_id());

-- ============================================================
-- SET user_id in Session nach Login
-- utils/database.py muss set_betrieb_session() erweitern:
-- set_config('app.current_user_id', str(user_id), false)
-- ============================================================

COMMIT;
