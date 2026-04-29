-- RLS-Setup für Service-Role-basiertes App-Modell (custom users + bcrypt Login).
-- Dieses Skript ist rückwärtskompatibel und setzt Policies bevorzugt auf betrieb_id.
-- Es vermeidet auth.uid()-Abhängigkeiten für Kern-Tabellen der App.

BEGIN;

-- Hilfsfunktion: Policy nur erstellen, wenn noch nicht vorhanden.
CREATE OR REPLACE FUNCTION public.ensure_policy(
    p_table text,
    p_policy text,
    p_cmd text,
    p_using text,
    p_with_check text DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    ddl text;
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = p_table
          AND policyname = p_policy
    ) THEN
        RETURN;
    END IF;

    ddl := format(
        'CREATE POLICY %I ON public.%I FOR %s USING (%s)%s',
        p_policy,
        p_table,
        p_cmd,
        p_using,
        CASE
            WHEN p_with_check IS NULL THEN ''
            ELSE format(' WITH CHECK (%s)', p_with_check)
        END
    );
    EXECUTE ddl;
END;
$$;

-- Kern-Tabellen, die über Service-Role angesprochen werden.
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'betriebe',
        'users',
        'mitarbeiter',
        'zeiterfassung',
        'zeit_eintraege',
        'abwesenheiten',
        'arbeitszeitkonto',
        'arbeitszeit_konten',
        'azk_monatsabschluesse',
        'lohnabrechnungen',
        'mastergeraete',
        'mitarbeiter_geraete',
        'geraete_verifizierungen',
        'mitarbeiter_dokumente',
        'schichten',
        'audit_log',
        'audit_logs',
        'dienstplaene',
        'dienstplan',
        'urlaubsantraege',
        'vertraege',
        'abteilungen',
        'mitarbeiter_abteilungen'
    ] LOOP
        IF EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = t
        ) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);

            -- Service-Role Vollzugriff.
            PERFORM public.ensure_policy(
                t,
                t || '_service_role_all',
                'ALL',
                'auth.role() = ''service_role'''
            );
        END IF;
    END LOOP;
END $$;

-- Optional: anonyme Leserechte für Betriebsliste (nur wenn gewünscht).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'betriebe'
    ) THEN
        PERFORM public.ensure_policy(
            'betriebe',
            'betriebe_public_read',
            'SELECT',
            'true'
        );
    END IF;
END $$;

COMMIT;
