-- ============================================================
-- AZK-Startsaldo-Korrekturen per 01.03.2026
-- Task 2: Setzt ueberstunden_saldo_ende in azk_monatsabschluesse
--         für Monat 02/2026 (Vormonat des Startmonats 03/2026).
--
-- Vor Ausführung: Mitarbeiter-IDs prüfen:
--   SELECT id, vorname || ' ' || nachname AS name
--   FROM mitarbeiter WHERE betrieb_id = 1 ORDER BY nachname;
-- ============================================================

-- Hilfsfunktion: Vormonat-Zeile upserten
-- (Supabase unterstützt kein DO $$ ... END $$  direkt im SQL Editor,
--  daher als einzelne INSERT ... ON CONFLICT Statements)

-- Fernando Marrero Lopez   AZK -31,23 h
INSERT INTO azk_monatsabschluesse
  (betrieb_id, mitarbeiter_id, monat, jahr,
   soll_stunden, ist_stunden, differenz_stunden,
   ueberstunden_saldo_start, ueberstunden_saldo_ende,
   urlaubstage_gesamt, urlaubstage_genommen, krankheitstage_gesamt,
   manuelle_korrektur_saldo, korrektur_grund, ist_initialisierung,
   initialisierungs_monat, initialisierungs_jahr)
SELECT
  1,
  id,
  2, 2026,
  0, 0, 0,
  -31.23, -31.23,
  0, 0, 0,
  -31.23, 'AZK-Startsaldo Vortrag per 01.03.2026', TRUE,
  3, 2026
FROM mitarbeiter
WHERE betrieb_id = 1
  AND vorname ILIKE 'Fernando'
  AND nachname ILIKE 'Marrero%'
ON CONFLICT (mitarbeiter_id, monat, jahr)
DO UPDATE SET
  ueberstunden_saldo_start  = EXCLUDED.ueberstunden_saldo_start,
  ueberstunden_saldo_ende   = EXCLUDED.ueberstunden_saldo_ende,
  manuelle_korrektur_saldo  = EXCLUDED.manuelle_korrektur_saldo,
  korrektur_grund           = EXCLUDED.korrektur_grund,
  ist_initialisierung       = EXCLUDED.ist_initialisierung;

-- Hans Jürgen Lasinski   AZK +28,13 h
INSERT INTO azk_monatsabschluesse
  (betrieb_id, mitarbeiter_id, monat, jahr,
   soll_stunden, ist_stunden, differenz_stunden,
   ueberstunden_saldo_start, ueberstunden_saldo_ende,
   urlaubstage_gesamt, urlaubstage_genommen, krankheitstage_gesamt,
   manuelle_korrektur_saldo, korrektur_grund, ist_initialisierung,
   initialisierungs_monat, initialisierungs_jahr)
SELECT
  1,
  id,
  2, 2026,
  0, 0, 0,
  28.13, 28.13,
  0, 0, 0,
  28.13, 'AZK-Startsaldo Vortrag per 01.03.2026', TRUE,
  3, 2026
FROM mitarbeiter
WHERE betrieb_id = 1
  AND vorname ILIKE 'Hans%'
  AND nachname ILIKE 'Lasinski'
ON CONFLICT (mitarbeiter_id, monat, jahr)
DO UPDATE SET
  ueberstunden_saldo_start  = EXCLUDED.ueberstunden_saldo_start,
  ueberstunden_saldo_ende   = EXCLUDED.ueberstunden_saldo_ende,
  manuelle_korrektur_saldo  = EXCLUDED.manuelle_korrektur_saldo,
  korrektur_grund           = EXCLUDED.korrektur_grund,
  ist_initialisierung       = EXCLUDED.ist_initialisierung;

-- Melanie Lasinski   AZK +1,76 h
INSERT INTO azk_monatsabschluesse
  (betrieb_id, mitarbeiter_id, monat, jahr,
   soll_stunden, ist_stunden, differenz_stunden,
   ueberstunden_saldo_start, ueberstunden_saldo_ende,
   urlaubstage_gesamt, urlaubstage_genommen, krankheitstage_gesamt,
   manuelle_korrektur_saldo, korrektur_grund, ist_initialisierung,
   initialisierungs_monat, initialisierungs_jahr)
SELECT
  1,
  id,
  2, 2026,
  0, 0, 0,
  1.76, 1.76,
  0, 0, 0,
  1.76, 'AZK-Startsaldo Vortrag per 01.03.2026', TRUE,
  3, 2026
FROM mitarbeiter
WHERE betrieb_id = 1
  AND vorname ILIKE 'Melanie'
  AND nachname ILIKE 'Lasinski'
ON CONFLICT (mitarbeiter_id, monat, jahr)
DO UPDATE SET
  ueberstunden_saldo_start  = EXCLUDED.ueberstunden_saldo_start,
  ueberstunden_saldo_ende   = EXCLUDED.ueberstunden_saldo_ende,
  manuelle_korrektur_saldo  = EXCLUDED.manuelle_korrektur_saldo,
  korrektur_grund           = EXCLUDED.korrektur_grund,
  ist_initialisierung       = EXCLUDED.ist_initialisierung;

-- Ronny Franke   AZK +17,70 h
INSERT INTO azk_monatsabschluesse
  (betrieb_id, mitarbeiter_id, monat, jahr,
   soll_stunden, ist_stunden, differenz_stunden,
   ueberstunden_saldo_start, ueberstunden_saldo_ende,
   urlaubstage_gesamt, urlaubstage_genommen, krankheitstage_gesamt,
   manuelle_korrektur_saldo, korrektur_grund, ist_initialisierung,
   initialisierungs_monat, initialisierungs_jahr)
SELECT
  1,
  id,
  2, 2026,
  0, 0, 0,
  17.70, 17.70,
  0, 0, 0,
  17.70, 'AZK-Startsaldo Vortrag per 01.03.2026', TRUE,
  3, 2026
FROM mitarbeiter
WHERE betrieb_id = 1
  AND vorname ILIKE 'Ronny'
  AND nachname ILIKE 'Franke'
ON CONFLICT (mitarbeiter_id, monat, jahr)
DO UPDATE SET
  ueberstunden_saldo_start  = EXCLUDED.ueberstunden_saldo_start,
  ueberstunden_saldo_ende   = EXCLUDED.ueberstunden_saldo_ende,
  manuelle_korrektur_saldo  = EXCLUDED.manuelle_korrektur_saldo,
  korrektur_grund           = EXCLUDED.korrektur_grund,
  ist_initialisierung       = EXCLUDED.ist_initialisierung;

-- Silke Reibrandt   AZK -65,27 h
INSERT INTO azk_monatsabschluesse
  (betrieb_id, mitarbeiter_id, monat, jahr,
   soll_stunden, ist_stunden, differenz_stunden,
   ueberstunden_saldo_start, ueberstunden_saldo_ende,
   urlaubstage_gesamt, urlaubstage_genommen, krankheitstage_gesamt,
   manuelle_korrektur_saldo, korrektur_grund, ist_initialisierung,
   initialisierungs_monat, initialisierungs_jahr)
SELECT
  1,
  id,
  2, 2026,
  0, 0, 0,
  -65.27, -65.27,
  0, 0, 0,
  -65.27, 'AZK-Startsaldo Vortrag per 01.03.2026', TRUE,
  3, 2026
FROM mitarbeiter
WHERE betrieb_id = 1
  AND vorname ILIKE 'Silke'
  AND nachname ILIKE 'Reibrandt'
ON CONFLICT (mitarbeiter_id, monat, jahr)
DO UPDATE SET
  ueberstunden_saldo_start  = EXCLUDED.ueberstunden_saldo_start,
  ueberstunden_saldo_ende   = EXCLUDED.ueberstunden_saldo_ende,
  manuelle_korrektur_saldo  = EXCLUDED.manuelle_korrektur_saldo,
  korrektur_grund           = EXCLUDED.korrektur_grund,
  ist_initialisierung       = EXCLUDED.ist_initialisierung;

-- Thomas Fröhlich   AZK +0,98 h
INSERT INTO azk_monatsabschluesse
  (betrieb_id, mitarbeiter_id, monat, jahr,
   soll_stunden, ist_stunden, differenz_stunden,
   ueberstunden_saldo_start, ueberstunden_saldo_ende,
   urlaubstage_gesamt, urlaubstage_genommen, krankheitstage_gesamt,
   manuelle_korrektur_saldo, korrektur_grund, ist_initialisierung,
   initialisierungs_monat, initialisierungs_jahr)
SELECT
  1,
  id,
  2, 2026,
  0, 0, 0,
  0.98, 0.98,
  0, 0, 0,
  0.98, 'AZK-Startsaldo Vortrag per 01.03.2026', TRUE,
  3, 2026
FROM mitarbeiter
WHERE betrieb_id = 1
  AND vorname ILIKE 'Thomas'
  AND nachname ILIKE 'Fröhlich'
ON CONFLICT (mitarbeiter_id, monat, jahr)
DO UPDATE SET
  ueberstunden_saldo_start  = EXCLUDED.ueberstunden_saldo_start,
  ueberstunden_saldo_ende   = EXCLUDED.ueberstunden_saldo_ende,
  manuelle_korrektur_saldo  = EXCLUDED.manuelle_korrektur_saldo,
  korrektur_grund           = EXCLUDED.korrektur_grund,
  ist_initialisierung       = EXCLUDED.ist_initialisierung;


-- ============================================================
-- Verifizierung: Zeigt die gesetzten Startsalden
-- ============================================================
SELECT
  m.vorname || ' ' || m.nachname AS name,
  a.monat, a.jahr,
  a.ueberstunden_saldo_ende AS startsaldo_h,
  a.korrektur_grund
FROM azk_monatsabschluesse a
JOIN mitarbeiter m ON m.id = a.mitarbeiter_id
WHERE a.betrieb_id = 1
  AND a.monat = 2 AND a.jahr = 2026
ORDER BY m.nachname;


-- ============================================================
-- Task 4: Urlaubstage-Korrekturen per 01.03.2026
-- ============================================================

-- Fernando Marrero Lopez: 27 Tage gesamt offen (inkl. 3 Tage Vorjahresrest)
UPDATE mitarbeiter
SET jahres_urlaubstage = 24,
    resturlaub_vorjahr  = 3
WHERE betrieb_id = 1
  AND vorname ILIKE 'Fernando'
  AND nachname ILIKE 'Marrero%';

-- Hans Jürgen Lasinski: 24 Tage laut Vertrag, kein Vorjahresrest
UPDATE mitarbeiter
SET jahres_urlaubstage = 24,
    resturlaub_vorjahr  = 0
WHERE betrieb_id = 1
  AND vorname ILIKE 'Hans%'
  AND nachname ILIKE 'Lasinski';

-- Melanie Lasinski: 24 Tage laut Vertrag, kein Vorjahresrest
UPDATE mitarbeiter
SET jahres_urlaubstage = 24,
    resturlaub_vorjahr  = 0
WHERE betrieb_id = 1
  AND vorname ILIKE 'Melanie'
  AND nachname ILIKE 'Lasinski';

-- Ronny Franke: 24 Tage gesamt (inkl. 4 Tage Vorjahresrest)
UPDATE mitarbeiter
SET jahres_urlaubstage = 20,
    resturlaub_vorjahr  = 4
WHERE betrieb_id = 1
  AND vorname ILIKE 'Ronny'
  AND nachname ILIKE 'Franke';

-- Silke Reibrandt: 24 Tage laut Vertrag, kein Vorjahresrest
UPDATE mitarbeiter
SET jahres_urlaubstage = 24,
    resturlaub_vorjahr  = 0
WHERE betrieb_id = 1
  AND vorname ILIKE 'Silke'
  AND nachname ILIKE 'Reibrandt';

-- Nadine Lutschin: 22 Tage ab Feb 2026 (Hauptvertrag), kein Vorjahresrest
-- Hinweis: Jan 2026 Probebeschäftigung (2 Tage) separat abgelten falls nicht bereits geschehen.
UPDATE mitarbeiter
SET jahres_urlaubstage = 22,
    resturlaub_vorjahr  = 0
WHERE betrieb_id = 1
  AND vorname ILIKE 'Nadine'
  AND nachname ILIKE 'Lutschin';


-- ============================================================
-- Verifizierung Urlaubstage
-- ============================================================
SELECT
  vorname || ' ' || nachname AS name,
  jahres_urlaubstage,
  resturlaub_vorjahr,
  jahres_urlaubstage + resturlaub_vorjahr AS gesamt_anspruch
FROM mitarbeiter
WHERE betrieb_id = 1
  AND (nachname IN ('Lasinski','Franke','Reibrandt','Fröhlich','Lutschin')
       OR nachname ILIKE 'Marrero%')
ORDER BY nachname;
