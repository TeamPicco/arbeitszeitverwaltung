-- ============================================================
-- SICHERHEITS-MIGRATION: Row Level Security (RLS) vollständig
-- SEC-002 / DSGVO-002: Mandantentrennung per RLS
-- Datum: 2026-04-26
-- FIX v3: Korrekte Spalten pro Tabelle, TEXT-Vergleiche für UUID/BIGINT
-- ============================================================
-- Ausführen im Supabase SQL-Editor als Service-Role.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- HELPER: Session-Variablen als TEXT lesen (UUID & BIGINT kompatibel)
-- Werden nach Login via set_config() in database.py gesetzt.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_betrieb_id_text()
RETURNS TEXT
LANGUAGE sql STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_betrieb_id', TRUE), '');
$$;

CREATE OR REPLACE FUNCTION public.current_app_user_id_text()
RETURNS TEXT
LANGUAGE sql STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_user_id', TRUE), '');
$$;

-- ============================================================
-- TABELLE: betriebe — nur eigener Betrieb sichtbar
-- ============================================================
ALTER TABLE public.betriebe ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS betriebe_own ON public.betriebe;
CREATE POLICY betriebe_own ON public.betriebe
  FOR ALL
  USING (id::TEXT = public.current_betrieb_id_text());

-- ============================================================
-- TABELLE: users — hat betrieb_id Spalte
-- ============================================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Admin: alle User des eigenen Betriebs
DROP POLICY IF EXISTS users_admin_betrieb ON public.users;
CREATE POLICY users_admin_betrieb ON public.users
  FOR ALL
  USING (betrieb_id::TEXT = public.current_betrieb_id_text());

-- Mitarbeiter: nur eigene Zeile
DROP POLICY IF EXISTS users_self_select ON public.users;
CREATE POLICY users_self_select ON public.users
  FOR SELECT
  USING (id::TEXT = public.current_app_user_id_text());

-- ============================================================
-- TABELLE: mitarbeiter — hat betrieb_id Spalte
-- ============================================================
ALTER TABLE public.mitarbeiter ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS mitarbeiter_admin_betrieb ON public.mitarbeiter;
CREATE POLICY mitarbeiter_admin_betrieb ON public.mitarbeiter
  FOR ALL
  USING (betrieb_id::TEXT = public.current_betrieb_id_text());

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
-- TABELLE: zeiterfassung — hat NUR mitarbeiter_id (kein betrieb_id)
-- Mandantentrennung über mitarbeiter-Join
-- ============================================================
ALTER TABLE public.zeiterfassung ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS zeiterfassung_admin ON public.zeiterfassung;
CREATE POLICY zeiterfassung_admin ON public.zeiterfassung
  FOR ALL
  USING (
    mitarbeiter_id::TEXT IN (
      SELECT id::TEXT FROM public.mitarbeiter
      WHERE betrieb_id::TEXT = public.current_betrieb_id_text()
    )
  );

DROP POLICY IF EXISTS zeiterfassung_self ON public.zeiterfassung;
CREATE POLICY zeiterfassung_self ON public.zeiterfassung
  FOR SELECT
  USING (
    mitarbeiter_id::TEXT IN (
      SELECT id::TEXT FROM public.mitarbeiter
      WHERE betrieb_id::TEXT = public.current_betrieb_id_text()
        AND user_id::TEXT = public.current_app_user_id_text()
    )
  );

-- ============================================================
-- TABELLE: urlaubsantraege — hat betrieb_id Spalte
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
-- TABELLE: lohnabrechnungen — hat NUR mitarbeiter_id (kein betrieb_id)
-- ============================================================
ALTER TABLE public.lohnabrechnungen ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lohn_admin ON public.lohnabrechnungen;
CREATE POLICY lohn_admin ON public.lohnabrechnungen
  FOR ALL
  USING (
    mitarbeiter_id::TEXT IN (
      SELECT id::TEXT FROM public.mitarbeiter
      WHERE betrieb_id::TEXT = public.current_betrieb_id_text()
    )
  );

DROP POLICY IF EXISTS lohn_self ON public.lohnabrechnungen;
CREATE POLICY lohn_self ON public.lohnabrechnungen
  FOR SELECT
  USING (
    mitarbeiter_id::TEXT IN (
      SELECT id::TEXT FROM public.mitarbeiter
      WHERE betrieb_id::TEXT = public.current_betrieb_id_text()
        AND user_id::TEXT = public.current_app_user_id_text()
    )
  );

COMMIT;
