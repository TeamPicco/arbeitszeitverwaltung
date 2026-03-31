-- Produktionskern-Erweiterung (rückwärtskompatibel, nicht-destruktiv)
-- Fokus: Zeiterfassungs-Events, Compliance, Arbeitszeitkonto, Abwesenheiten,
--        Dokumente, Schichtplanung, Geräteautorisierung und Auditierbarkeit.

BEGIN;

-- ------------------------------------------------------------
-- Basiserweiterungen bestehender Tabellen
-- ------------------------------------------------------------

ALTER TABLE IF EXISTS public.zeiterfassung
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS pause_minuten INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS arbeitsstunden NUMERIC(7, 2),
    ADD COLUMN IF NOT EXISTS quelle TEXT DEFAULT 'stempeluhr',
    ADD COLUMN IF NOT EXISTS manuell_kommentar TEXT,
    ADD COLUMN IF NOT EXISTS abwesenheitstyp TEXT,
    ADD COLUMN IF NOT EXISTS ist_krank BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS compliance_warnungen JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS bearbeitet_von BIGINT REFERENCES public.users(id),
    ADD COLUMN IF NOT EXISTS bearbeitet_am TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS monat INTEGER,
    ADD COLUMN IF NOT EXISTS jahr INTEGER;

ALTER TABLE IF EXISTS public.zeiterfassung
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_zeiterfassung_betrieb ON public.zeiterfassung(betrieb_id);
CREATE INDEX IF NOT EXISTS idx_zeiterfassung_mitarbeiter_datum ON public.zeiterfassung(mitarbeiter_id, datum);
CREATE INDEX IF NOT EXISTS idx_zeiterfassung_monat_jahr ON public.zeiterfassung(mitarbeiter_id, jahr, monat);

CREATE OR REPLACE FUNCTION public.set_zeiterfassung_monat_jahr()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.datum IS NOT NULL THEN
        NEW.monat := EXTRACT(MONTH FROM NEW.datum)::INT;
        NEW.jahr := EXTRACT(YEAR FROM NEW.datum)::INT;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_zeiterfassung_monat_jahr ON public.zeiterfassung;
CREATE TRIGGER trg_zeiterfassung_monat_jahr
BEFORE INSERT OR UPDATE ON public.zeiterfassung
FOR EACH ROW
EXECUTE FUNCTION public.set_zeiterfassung_monat_jahr();

-- ------------------------------------------------------------
-- Zeit-Events (clock_in/out, break_start/end) als append-only Log
-- ------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'zeit_aktion') THEN
        CREATE TYPE public.zeit_aktion AS ENUM ('clock_in', 'clock_out', 'break_start', 'break_end');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.zeit_eintraege (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    aktion public.zeit_aktion NOT NULL,
    zeitpunkt_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    quelle TEXT NOT NULL DEFAULT 'stempeluhr',
    geraet_id TEXT,
    verifiziert BOOLEAN DEFAULT FALSE,
    notiz TEXT,
    meta JSONB DEFAULT '{}'::jsonb,
    created_by BIGINT REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Legacy-Kompatibilität: bestehende zeit_eintraege-Tabelle erweitern
ALTER TABLE IF EXISTS public.zeit_eintraege
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS aktion TEXT,
    ADD COLUMN IF NOT EXISTS zeitpunkt_utc TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS quelle TEXT DEFAULT 'stempeluhr',
    ADD COLUMN IF NOT EXISTS geraet_id TEXT,
    ADD COLUMN IF NOT EXISTS verifiziert BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS notiz TEXT,
    ADD COLUMN IF NOT EXISTS meta JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES public.users(id),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill aus möglichen Legacy-Spalten (zeitpunkt)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='zeit_eintraege' AND column_name='zeitpunkt'
    ) THEN
        EXECUTE 'UPDATE public.zeit_eintraege
                 SET zeitpunkt_utc = COALESCE(zeitpunkt_utc, zeitpunkt)
                 WHERE zeitpunkt_utc IS NULL';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_zeit_eintraege_mitarbeiter_zeitpunkt
    ON public.zeit_eintraege(mitarbeiter_id, zeitpunkt_utc DESC);
CREATE INDEX IF NOT EXISTS idx_zeit_eintraege_betrieb_zeitpunkt
    ON public.zeit_eintraege(betrieb_id, zeitpunkt_utc DESC);
CREATE INDEX IF NOT EXISTS idx_zeit_eintraege_aktion
    ON public.zeit_eintraege(aktion);

-- ------------------------------------------------------------
-- Arbeitszeitkonten (fortlaufend)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.arbeitszeit_konten (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    soll_stunden NUMERIC(7,2) NOT NULL DEFAULT 0,
    ist_stunden NUMERIC(7,2) NOT NULL DEFAULT 0,
    ueberstunden_saldo NUMERIC(9,2) NOT NULL DEFAULT 0,
    urlaubstage_gesamt NUMERIC(5,2) NOT NULL DEFAULT 0,
    urlaubstage_genommen NUMERIC(5,2) NOT NULL DEFAULT 0,
    krankheitstage_gesamt NUMERIC(5,2) NOT NULL DEFAULT 0,
    letztes_update_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (mitarbeiter_id)
);

-- Legacy-Kompatibilität: bestehende arbeitszeit_konten-Tabelle erweitern
ALTER TABLE IF EXISTS public.arbeitszeit_konten
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS soll_stunden NUMERIC(7,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ist_stunden NUMERIC(7,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ueberstunden_saldo NUMERIC(9,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS urlaubstage_gesamt NUMERIC(5,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS urlaubstage_genommen NUMERIC(5,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS krankheitstage_gesamt NUMERIC(5,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS letztes_update_utc TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_arbeitszeit_konten_betrieb
    ON public.arbeitszeit_konten(betrieb_id, mitarbeiter_id);

-- ------------------------------------------------------------
-- Abwesenheiten inkl. Attest
-- ------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'abwesenheit_typ') THEN
        CREATE TYPE public.abwesenheit_typ AS ENUM ('urlaub', 'krankheit', 'sonderurlaub');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.abwesenheiten (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    typ public.abwesenheit_typ NOT NULL,
    start_datum DATE NOT NULL,
    ende_datum DATE NOT NULL,
    ganztag BOOLEAN NOT NULL DEFAULT TRUE,
    bezahlte_zeit BOOLEAN NOT NULL DEFAULT TRUE,
    stunden_gutschrift NUMERIC(7,2) DEFAULT 0,
    attest_pfad TEXT,
    grund TEXT,
    status TEXT NOT NULL DEFAULT 'genehmigt',
    created_by BIGINT REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ende_datum >= start_datum)
);

-- WICHTIG: Wenn eine ältere abwesenheiten-Tabelle bereits existiert,
-- ergänzt CREATE TABLE IF NOT EXISTS keine fehlenden Spalten.
-- Daher explizit kompatibel nachziehen:
ALTER TABLE IF EXISTS public.abwesenheiten
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS typ TEXT,
    ADD COLUMN IF NOT EXISTS start_datum DATE,
    ADD COLUMN IF NOT EXISTS ende_datum DATE,
    ADD COLUMN IF NOT EXISTS ganztag BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS bezahlte_zeit BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS stunden_gutschrift NUMERIC(7,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS attest_pfad TEXT,
    ADD COLUMN IF NOT EXISTS grund TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'genehmigt',
    ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES public.users(id),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill von Altspalten (falls vorhanden):
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'abwesenheiten' AND column_name = 'von_datum'
    ) THEN
        EXECUTE 'UPDATE public.abwesenheiten
                 SET start_datum = COALESCE(start_datum, von_datum)
                 WHERE start_datum IS NULL';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'abwesenheiten' AND column_name = 'bis_datum'
    ) THEN
        EXECUTE 'UPDATE public.abwesenheiten
                 SET ende_datum = COALESCE(ende_datum, bis_datum)
                 WHERE ende_datum IS NULL';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'abwesenheiten' AND column_name = 'datum'
    ) THEN
        EXECUTE 'UPDATE public.abwesenheiten
                 SET start_datum = COALESCE(start_datum, datum),
                     ende_datum = COALESCE(ende_datum, datum)
                 WHERE start_datum IS NULL OR ende_datum IS NULL';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_abwesenheiten_mitarbeiter_zeitraum
    ON public.abwesenheiten(mitarbeiter_id, start_datum, ende_datum);

-- NOT NULL nur setzen, wenn Backfill erfolgreich war:
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.abwesenheiten
        WHERE start_datum IS NULL OR ende_datum IS NULL
    ) THEN
        EXECUTE 'ALTER TABLE public.abwesenheiten
                 ALTER COLUMN start_datum SET NOT NULL,
                 ALTER COLUMN ende_datum SET NOT NULL';
    END IF;
END $$;

-- ------------------------------------------------------------
-- Mitarbeiter-Stammdaten (normalisiert)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.vertraege (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    gueltig_ab DATE NOT NULL,
    gueltig_bis DATE,
    wochenstunden NUMERIC(6,2),
    soll_stunden_monat NUMERIC(6,2),
    urlaubstage_jahr NUMERIC(5,2),
    stundenlohn_brutto NUMERIC(10,2),
    vertrag_dokument_pfad TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (gueltig_bis IS NULL OR gueltig_bis >= gueltig_ab)
);

-- Legacy-Kompatibilität: bestehende vertraege-Tabelle erweitern
ALTER TABLE IF EXISTS public.vertraege
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS gueltig_ab DATE,
    ADD COLUMN IF NOT EXISTS gueltig_bis DATE,
    ADD COLUMN IF NOT EXISTS wochenstunden NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS soll_stunden_monat NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS urlaubstage_jahr NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS stundenlohn_brutto NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS vertrag_dokument_pfad TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

CREATE TABLE IF NOT EXISTS public.abteilungen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    beschreibung TEXT,
    aktiv BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (betrieb_id, name)
);

-- Legacy-Kompatibilität: bestehende abteilungen-Tabelle erweitern
ALTER TABLE IF EXISTS public.abteilungen
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS name TEXT,
    ADD COLUMN IF NOT EXISTS beschreibung TEXT,
    ADD COLUMN IF NOT EXISTS aktiv BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

CREATE TABLE IF NOT EXISTS public.mitarbeiter_abteilungen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    abteilung_id BIGINT NOT NULL REFERENCES public.abteilungen(id) ON DELETE CASCADE,
    rolle TEXT,
    primaer BOOLEAN NOT NULL DEFAULT FALSE,
    gueltig_ab DATE NOT NULL DEFAULT CURRENT_DATE,
    gueltig_bis DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (gueltig_bis IS NULL OR gueltig_bis >= gueltig_ab),
    UNIQUE (mitarbeiter_id, abteilung_id, gueltig_ab)
);

-- Legacy-Kompatibilität: bestehende mitarbeiter_abteilungen-Tabelle erweitern
ALTER TABLE IF EXISTS public.mitarbeiter_abteilungen
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS abteilung_id BIGINT REFERENCES public.abteilungen(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS rolle TEXT,
    ADD COLUMN IF NOT EXISTS primaer BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS gueltig_ab DATE DEFAULT CURRENT_DATE,
    ADD COLUMN IF NOT EXISTS gueltig_bis DATE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- ------------------------------------------------------------
-- Dokumentenverwaltung
-- ------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dokument_status') THEN
        CREATE TYPE public.dokument_status AS ENUM ('aktiv', 'abgelaufen', 'fehlend');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.mitarbeiter_dokumente (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    typ TEXT NOT NULL,
    file_path TEXT,
    file_url TEXT,
    status public.dokument_status NOT NULL DEFAULT 'aktiv',
    gueltig_bis DATE,
    metadaten JSONB NOT NULL DEFAULT '{}'::jsonb,
    erstellt_von BIGINT REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Legacy-Kompatibilität: bestehende mitarbeiter_dokumente-Tabelle erweitern
ALTER TABLE IF EXISTS public.mitarbeiter_dokumente
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS name TEXT,
    ADD COLUMN IF NOT EXISTS typ TEXT,
    ADD COLUMN IF NOT EXISTS file_path TEXT,
    ADD COLUMN IF NOT EXISTS file_url TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'aktiv',
    ADD COLUMN IF NOT EXISTS gueltig_bis DATE,
    ADD COLUMN IF NOT EXISTS metadaten JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS erstellt_von BIGINT REFERENCES public.users(id),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_mitarbeiter_dokumente_mitarbeiter
    ON public.mitarbeiter_dokumente(mitarbeiter_id, status);

-- ------------------------------------------------------------
-- Schichtplanung (Monat, direkte Bearbeitung, Konfliktprüfung)
-- ------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS public.schichten (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    datum DATE NOT NULL,
    start_zeit_utc TIMESTAMPTZ NOT NULL,
    ende_zeit_utc TIMESTAMPTZ NOT NULL,
    pause_minuten INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'geplant',
    erstellt_von BIGINT REFERENCES public.users(id),
    bemerkung TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ende_zeit_utc > start_zeit_utc)
);

-- Legacy-Kompatibilität: bestehende schichten-Tabelle erweitern
ALTER TABLE IF EXISTS public.schichten
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS datum DATE,
    ADD COLUMN IF NOT EXISTS start_zeit_utc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS ende_zeit_utc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS pause_minuten INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'geplant',
    ADD COLUMN IF NOT EXISTS erstellt_von BIGINT REFERENCES public.users(id),
    ADD COLUMN IF NOT EXISTS bemerkung TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill aus möglichen Legacy-Spalten start_zeit/ende_zeit + datum
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'schichten' AND column_name = 'start_zeit'
    ) THEN
        EXECUTE 'UPDATE public.schichten
                 SET start_zeit_utc = COALESCE(
                        start_zeit_utc,
                        CASE
                            WHEN datum IS NOT NULL AND start_zeit IS NOT NULL
                            THEN (datum::text || '' '' || start_zeit::text)::timestamptz
                            ELSE NULL
                        END
                 )
                 WHERE start_zeit_utc IS NULL';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'schichten' AND column_name = 'ende_zeit'
    ) THEN
        EXECUTE 'UPDATE public.schichten
                 SET ende_zeit_utc = COALESCE(
                        ende_zeit_utc,
                        CASE
                            WHEN datum IS NOT NULL AND ende_zeit IS NOT NULL
                            THEN (datum::text || '' '' || ende_zeit::text)::timestamptz
                            ELSE NULL
                        END
                 )
                 WHERE ende_zeit_utc IS NULL';
    END IF;
END $$;

-- Fallback, damit Constraints/Indizes nicht wegen NULL-Spalten scheitern
UPDATE public.schichten
SET
    status = COALESCE(status, 'geplant'),
    start_zeit_utc = COALESCE(start_zeit_utc, NOW()),
    ende_zeit_utc = COALESCE(ende_zeit_utc, NOW() + INTERVAL '1 hour')
WHERE status IS NULL OR start_zeit_utc IS NULL OR ende_zeit_utc IS NULL;

CREATE INDEX IF NOT EXISTS idx_schichten_mitarbeiter_datum
    ON public.schichten(mitarbeiter_id, datum);
CREATE INDEX IF NOT EXISTS idx_schichten_betrieb_datum
    ON public.schichten(betrieb_id, datum);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'schichten_no_overlap'
    ) THEN
        ALTER TABLE public.schichten
            ADD CONSTRAINT schichten_no_overlap
            EXCLUDE USING gist (
                mitarbeiter_id WITH =,
                tstzrange(start_zeit_utc, ende_zeit_utc, '[)') WITH &&
            )
            WHERE (status IN ('geplant', 'veroeffentlicht'));
    END IF;
END $$;

-- ------------------------------------------------------------
-- Gerätesicherheit (max. 2 autorisierte Geräte / Mitarbeiter)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.mitarbeiter_geraete (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    device_fingerprint TEXT NOT NULL,
    device_name TEXT,
    autorisiert BOOLEAN NOT NULL DEFAULT FALSE,
    ausnahme_genehmigt BOOLEAN NOT NULL DEFAULT FALSE,
    autorisiert_durch BIGINT REFERENCES public.users(id),
    autorisiert_am TIMESTAMPTZ,
    letzter_kontakt_utc TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (mitarbeiter_id, device_fingerprint)
);

ALTER TABLE IF EXISTS public.mitarbeiter_geraete
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS device_fingerprint TEXT,
    ADD COLUMN IF NOT EXISTS device_name TEXT,
    ADD COLUMN IF NOT EXISTS autorisiert BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ausnahme_genehmigt BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS autorisiert_durch BIGINT REFERENCES public.users(id),
    ADD COLUMN IF NOT EXISTS autorisiert_am TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS letzter_kontakt_utc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_mitarbeiter_geraete_mitarbeiter
    ON public.mitarbeiter_geraete(mitarbeiter_id, autorisiert);

CREATE TABLE IF NOT EXISTS public.geraete_verifizierungen (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT NOT NULL REFERENCES public.betriebe(id) ON DELETE CASCADE,
    mitarbeiter_id BIGINT NOT NULL REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    device_fingerprint TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at_utc TIMESTAMPTZ NOT NULL,
    consumed_at_utc TIMESTAMPTZ,
    created_by BIGINT REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE IF EXISTS public.geraete_verifizierungen
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS device_fingerprint TEXT,
    ADD COLUMN IF NOT EXISTS code_hash TEXT,
    ADD COLUMN IF NOT EXISTS expires_at_utc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS consumed_at_utc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES public.users(id),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_geraete_verif_lookup
    ON public.geraete_verifizierungen(mitarbeiter_id, device_fingerprint, expires_at_utc DESC);

CREATE OR REPLACE FUNCTION public.enforce_max_authorized_devices()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    cnt INTEGER;
BEGIN
    IF NEW.autorisiert IS TRUE AND NEW.ausnahme_genehmigt IS FALSE THEN
        SELECT COUNT(*)
        INTO cnt
        FROM public.mitarbeiter_geraete mg
        WHERE mg.mitarbeiter_id = NEW.mitarbeiter_id
          AND mg.autorisiert = TRUE
          AND mg.ausnahme_genehmigt = FALSE
          AND (TG_OP = 'INSERT' OR mg.id <> NEW.id);

        IF cnt >= 2 THEN
            RAISE EXCEPTION 'Maximal zwei autorisierte Geräte pro Mitarbeiter erlaubt';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_enforce_max_authorized_devices ON public.mitarbeiter_geraete;
CREATE TRIGGER trg_enforce_max_authorized_devices
BEFORE INSERT OR UPDATE ON public.mitarbeiter_geraete
FOR EACH ROW
EXECUTE FUNCTION public.enforce_max_authorized_devices();

-- ------------------------------------------------------------
-- Revisionssicheres Audit-Log (append-only)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE SET NULL,
    mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE SET NULL,
    user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    before_data JSONB,
    after_data JSONB,
    reason TEXT,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE IF EXISTS public.audit_logs
    ADD COLUMN IF NOT EXISTS betrieb_id BIGINT REFERENCES public.betriebe(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS mitarbeiter_id BIGINT REFERENCES public.mitarbeiter(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS event_type TEXT,
    ADD COLUMN IF NOT EXISTS entity TEXT,
    ADD COLUMN IF NOT EXISTS entity_id TEXT,
    ADD COLUMN IF NOT EXISTS before_data JSONB,
    ADD COLUMN IF NOT EXISTS after_data JSONB,
    ADD COLUMN IF NOT EXISTS reason TEXT,
    ADD COLUMN IF NOT EXISTS created_at_utc TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON public.audit_logs(entity, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON public.audit_logs(created_at_utc DESC);

CREATE OR REPLACE FUNCTION public.audit_logs_prevent_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs ist append-only';
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_logs_no_update ON public.audit_logs;
CREATE TRIGGER trg_audit_logs_no_update
BEFORE UPDATE OR DELETE ON public.audit_logs
FOR EACH ROW
EXECUTE FUNCTION public.audit_logs_prevent_mutation();

COMMIT;
