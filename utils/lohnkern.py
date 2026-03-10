"""
lohnkern.py – Kernlogik der Lohnberechnung

Lohnprinzip (vertragsbasiert, planovo-kompatibel):
  - Grundlohn  = vergütete_stunden × Stundenlohn
  - vergütete_stunden = gearbeitete Ist-Stunden + Urlaubsstunden + Krank-LFZ-Stunden
  - Überstunden (vergütete_h > Soll) → ins Arbeitszeitkonto, WERDEN BEZAHLT
  - Minusstunden (vergütete_h < Soll) → ins Arbeitszeitkonto, nur tatsächliche Stunden bezahlt
  - Sonntagszuschlag  = tatsächliche Sonntags-Stunden × Stundenlohn × 0,50
  - Feiertagszuschlag = tatsächliche Feiertags-Stunden × Stundenlohn × 1,00
  - Gesamtbrutto = Grundlohn + Sonntagszuschlag + Feiertagszuschlag

Keine Steuern, keine Sozialversicherung in dieser Funktion.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any

from utils.database import get_supabase_client


# ─────────────────────────────────────────────
# SCHRITT 1: Stunden eines Monats summieren
# ─────────────────────────────────────────────

def summiere_monatsstunden(mitarbeiter_id: int, monat: int, jahr: int) -> Dict[str, Any]:
    """
    Summiert alle vergütungsrelevanten Stunden eines Mitarbeiters für den Monat.

    Returns:
        {
            'gesamt_stunden': float,       # Netto-Arbeitsstunden (Ist, gearbeitet)
            'urlaub_stunden': float,       # Urlaubsstunden (vergütet)
            'krank_lfz_stunden': float,    # Krankheits-LFZ-Stunden (vergütet)
            'verguetete_stunden': float,   # = gesamt + urlaub + krank_lfz
            'sonntags_stunden': float,     # Für Zuschlagsberechnung
            'feiertags_stunden': float,    # Für Zuschlagsberechnung
            'anzahl_eintraege': int,
            'fehler': None | str
        }
    """
    result = {
        'gesamt_stunden': 0.0,
        'urlaub_stunden': 0.0,
        'krank_lfz_stunden': 0.0,
        'verguetete_stunden': 0.0,
        'sonntags_stunden': 0.0,
        'feiertags_stunden': 0.0,
        'anzahl_eintraege': 0,
        'fehler': None
    }

    try:
        supabase = get_supabase_client()

        von = date(jahr, monat, 1).isoformat()
        bis = date(jahr + 1, 1, 1).isoformat() if monat == 12 else date(jahr, monat + 1, 1).isoformat()

        # Alle Zeiterfassungs-Einträge des Mitarbeiters im Monat laden
        # Hinweis: zeiterfassung hat KEINE schichttyp-Spalte, stattdessen abwesenheitstyp + ist_krank
        response = supabase.table('zeiterfassung').select(
            'arbeitsstunden, start_zeit, ende_zeit, pause_minuten, '
            'ist_sonntag, ist_feiertag, quelle, abwesenheitstyp, ist_krank'
        ).eq('mitarbeiter_id', mitarbeiter_id).gte('datum', von).lt('datum', bis).execute()

        if not response.data:
            return result

        for eintrag in response.data:
            # Historische Saldo-Einträge überspringen
            if eintrag.get('quelle') == 'historischer_saldo':
                continue

            # abwesenheitstyp ist das korrekte Feld in zeiterfassung
            abwesenheitstyp = (eintrag.get('abwesenheitstyp') or '').lower()
            ist_krank_flag = eintrag.get('ist_krank') or False

            # ── Urlaubsstunden ────────────────────────────────────────────
            if abwesenheitstyp in ('urlaub', 'vacation', 'u'):
                urlaub_h = float(eintrag.get('arbeitsstunden') or 0)
                result['urlaub_stunden'] += urlaub_h
                continue

            # ── Krankheitsstunden (LFZ) ───────────────────────────────────
            # Erkannt durch abwesenheitstyp='krank' ODER ist_krank=True
            if abwesenheitstyp in ('krank', 'k', 'krank_lfz') or ist_krank_flag:
                krank_h = float(eintrag.get('arbeitsstunden') or 0)
                result['krank_lfz_stunden'] += krank_h
                continue

            # ── Reguläre Arbeitsstunden ───────────────────────────────────
            try:
                # Gespeicherte Arbeitsstunden bevorzugen
                if eintrag.get('arbeitsstunden') is not None:
                    netto_h = float(eintrag['arbeitsstunden'])
                elif eintrag.get('ende_zeit'):
                    fmt = '%H:%M:%S'
                    start = datetime.strptime(eintrag['start_zeit'], fmt)
                    ende = datetime.strptime(eintrag['ende_zeit'], fmt)
                    differenz_min = (ende - start).seconds / 60
                    pause = int(eintrag.get('pause_minuten') or 0)
                    netto_min = differenz_min - pause
                    if netto_min <= 0:
                        continue
                    netto_h = round(netto_min / 60, 4)
                else:
                    continue  # Offene Buchung – überspringen

                if netto_h <= 0:
                    continue

                result['gesamt_stunden'] += netto_h
                result['anzahl_eintraege'] += 1

                if eintrag.get('ist_sonntag'):
                    result['sonntags_stunden'] += netto_h
                if eintrag.get('ist_feiertag'):
                    result['feiertags_stunden'] += netto_h

            except Exception:
                continue

        # Vergütete Stunden = gearbeitet + Urlaub + Krank-LFZ
        result['verguetete_stunden'] = round(
            result['gesamt_stunden'] + result['urlaub_stunden'] + result['krank_lfz_stunden'], 2
        )

        # Runden
        result['gesamt_stunden'] = round(result['gesamt_stunden'], 2)
        result['urlaub_stunden'] = round(result['urlaub_stunden'], 2)
        result['krank_lfz_stunden'] = round(result['krank_lfz_stunden'], 2)
        result['sonntags_stunden'] = round(result['sonntags_stunden'], 2)
        result['feiertags_stunden'] = round(result['feiertags_stunden'], 2)

    except Exception as e:
        result['fehler'] = f"Datenbankfehler beim Laden der Zeiterfassung: {str(e)}"

    return result


# ─────────────────────────────────────────────
# SCHRITT 2: Bruttolohn berechnen
# ─────────────────────────────────────────────

def berechneMonatslohn(mitarbeiter_id: int, monat: int, jahr: int) -> Dict[str, Any]:
    """
    Hauptfunktion: Berechnet den Bruttolohn für einen Mitarbeiter und Monat.

    Lohnprinzip:
        vergütete_h     = gearbeitete Ist-h + Urlaubs-h + Krank-LFZ-h
        grundlohn       = vergütete_h × stundenlohn_brutto
        sonntagszuschlag  = sonntags_h × stundenlohn × 0,50  (wenn aktiv)
        feiertagszuschlag = feiertags_h × stundenlohn × 1,00 (wenn aktiv)
        gesamtbrutto    = grundlohn + sonntagszuschlag + feiertagszuschlag

        Saldo (Arbeitszeitkonto) = vergütete_h - soll_h
        (positiv = Überstunden, negativ = Minusstunden)

    Returns dict mit allen Berechnungsdetails.
    """
    leeres_ergebnis = {
        'ok': False, 'fehler': None,
        'mitarbeiter_name': '', 'stundenlohn': 0.0,
        'soll_stunden': 0.0,
        'gesamt_stunden': 0.0,        # Nur gearbeitete Stunden
        'urlaub_stunden': 0.0,        # Urlaubsstunden
        'krank_lfz_stunden': 0.0,     # Krank-LFZ-Stunden
        'verguetete_stunden': 0.0,    # Basis für Grundlohn
        'saldo_stunden': 0.0,         # Arbeitszeitkonto-Saldo
        'sonntags_stunden': 0.0,
        'feiertags_stunden': 0.0,
        'grundlohn': 0.0,
        'sonntagszuschlag': 0.0,
        'feiertagszuschlag': 0.0,
        'gesamtbrutto': 0.0,
        'anzahl_eintraege': 0,
    }

    try:
        supabase = get_supabase_client()

        # ── Mitarbeiterdaten laden ──────────────────────────────────────────
        ma_resp = supabase.table('mitarbeiter').select(
            'id, vorname, nachname, stundenlohn_brutto, '
            'monatliche_soll_stunden, jahres_urlaubstage, resturlaub_vorjahr, '
            'sonntagszuschlag_aktiv, feiertagszuschlag_aktiv, '
            'beschaeftigungsart, minijob_monatsgrenze, eintrittsdatum'
        ).eq('id', mitarbeiter_id).execute()

        if not ma_resp.data:
            leeres_ergebnis['fehler'] = f"Fehler: Mitarbeiter mit ID {mitarbeiter_id} nicht gefunden."
            return leeres_ergebnis

        ma = ma_resp.data[0]
        name = f"{ma['vorname']} {ma['nachname']}"

        # ── Stundensatz prüfen ─────────────────────────────────────────────
        stundenlohn_raw = ma.get('stundenlohn_brutto')
        if stundenlohn_raw is None:
            leeres_ergebnis['fehler'] = f"Fehler: Stundensatz für {name} nicht hinterlegt."
            leeres_ergebnis['mitarbeiter_name'] = name
            return leeres_ergebnis

        stundenlohn = float(stundenlohn_raw)
        if stundenlohn <= 0:
            leeres_ergebnis['fehler'] = f"Fehler: Stundensatz für {name} ist 0,00 €. Bitte korrekten Wert eintragen."
            leeres_ergebnis['mitarbeiter_name'] = name
            return leeres_ergebnis

        # ── Soll-Stunden (Vertragsbasis für Saldo-Berechnung) ─────────────
        soll_stunden = float(ma.get('monatliche_soll_stunden') or 0.0)

        # ── Stunden aus DB summieren ───────────────────────────────────────
        stunden_data = summiere_monatsstunden(mitarbeiter_id, monat, jahr)

        if stunden_data['fehler']:
            leeres_ergebnis['fehler'] = stunden_data['fehler']
            leeres_ergebnis['mitarbeiter_name'] = name
            return leeres_ergebnis

        ist_h = stunden_data['gesamt_stunden']
        urlaub_h = stunden_data['urlaub_stunden']
        krank_lfz_h = stunden_data['krank_lfz_stunden']
        verguetete_h = stunden_data['verguetete_stunden']
        sonntags_h = stunden_data['sonntags_stunden']
        feiertags_h = stunden_data['feiertags_stunden']

        # ── Saldo (Arbeitszeitkonto) ───────────────────────────────────────
        saldo = round(verguetete_h - soll_stunden, 2) if soll_stunden > 0 else 0.0

        # ── Bezahlte Stunden (max. Soll-Stunden) ──────────────────────────
        # Überstunden (vergütete_h > soll_h) → ins Arbeitszeitkonto, NICHT bezahlt
        # Minusstunden (vergütete_h < soll_h) → nur tatsächliche Stunden bezahlt
        bezahlte_h = round(min(verguetete_h, soll_stunden), 2) if soll_stunden > 0 else verguetete_h

        # ── Lohnberechnung ─────────────────────────────────────────────────
        # Grundlohn auf bezahlte Stunden (max. Soll-Stunden)
        grundlohn = round(bezahlte_h * stundenlohn, 2)

        # Zuschläge auf tatsächlich gearbeitete Sonderstunden
        sonntagszuschlag = 0.0
        if ma.get('sonntagszuschlag_aktiv') and sonntags_h > 0:
            sonntagszuschlag = round(sonntags_h * stundenlohn * 0.50, 2)

        feiertagszuschlag = 0.0
        if ma.get('feiertagszuschlag_aktiv') and feiertags_h > 0:
            feiertagszuschlag = round(feiertags_h * stundenlohn * 1.00, 2)

        gesamtbrutto = round(grundlohn + sonntagszuschlag + feiertagszuschlag, 2)

        # ── Minijob-spezifische Prüfungen (§ 8 SGB IV, EntgFG, MiLoG) ──────────────────────
        ist_minijob = (ma.get('beschaeftigungsart') or '') == 'minijob'
        minijob_grenze = float(ma.get('minijob_monatsgrenze') or 556.0)
        # Gesetzlicher Mindestlohn 2026: 12,82 EUR/h (§ 1 MiLoG)
        MINDESTLOHN_2026 = 12.82
        minijob_warnungen = []
        minijob_status = None  # None | 'vollstaendig' | 'ueberschritten'
        referenz_stunden_tag = 0.0

        if ist_minijob:
            # 1. Mindestlohn-Check (§ 1 MiLoG)
            if stundenlohn < MINDESTLOHN_2026:
                minijob_warnungen.append(
                    f"MINDESTLOHN-VERSTOSS: {stundenlohn:.2f} EUR/h < {MINDESTLOHN_2026:.2f} EUR/h "
                    f"(gesetzlicher Mindestlohn 2026 gemäß § 1 MiLoG). Sofort korrigieren!"
                )

            # 2. EntgFG-Deckelung: Ist + LFZ (Krank + Urlaub) darf Soll (30h) nicht überschreiten
            # § 4 EntgFG: Krankheits-LFZ zählt als gearbeitete Zeit für Stundendeckelung
            stunden_gesamt_inkl_fehlzeiten = round(ist_h + krank_lfz_h + urlaub_h, 2)
            if soll_stunden > 0 and stunden_gesamt_inkl_fehlzeiten >= soll_stunden:
                minijob_status = 'vollstaendig'

            # 3. Minijob-Entgeltgrenze-Check (§ 8 SGB IV)
            if gesamtbrutto > minijob_grenze:
                minijob_status = 'ueberschritten'
                minijob_warnungen.append(
                    f"MINIJOB-GRENZE ÜBERSCHRITTEN: {gesamtbrutto:.2f} EUR > "
                    f"{minijob_grenze:.2f} EUR (§ 8 SGB IV). "
                    f"Sozialversicherungspflicht droht! Stunden reduzieren."
                )

            # 4. EntgFG-Referenzprinzip: Durchschnittliche Tagesstunden für LFZ-Berechnung
            # § 4 Abs. 1 EntgFG: Referenz = Durchschnitt der letzten 13 Wochen
            # Vereinfacht für Minijob 30h/Monat: Soll / Arbeitstage (ohne Mo/Di Ruhetage)
            # Betrieb: Mo/Di Ruhetage -> ca. 15 Arbeitstage/Monat (Mi-So x 3 Wochen + Reste)
            if soll_stunden > 0:
                arbeitstage_monat_naeherung = 15  # Mi/Do/Fr/Sa/So = 5 Tage x ~3 Wochen
                referenz_stunden_tag = round(soll_stunden / arbeitstage_monat_naeherung, 2)

        return {
            'ok': True,
            'fehler': None,
            'mitarbeiter_name': name,
            'stundenlohn': stundenlohn,
            'soll_stunden': soll_stunden,
            'gesamt_stunden': ist_h,
            'urlaub_stunden': urlaub_h,
            'krank_lfz_stunden': krank_lfz_h,
            'verguetete_stunden': verguetete_h,
            'bezahlte_stunden': bezahlte_h,
            'saldo_stunden': saldo,
            'sonntags_stunden': sonntags_h,
            'feiertags_stunden': feiertags_h,
            'grundlohn': grundlohn,
            'sonntagszuschlag': sonntagszuschlag,
            'feiertagszuschlag': feiertagszuschlag,
            'gesamtbrutto': gesamtbrutto,
            'anzahl_eintraege': stunden_data['anzahl_eintraege'],
            # Minijob-spezifische Felder
            'ist_minijob': ist_minijob,
            'minijob_grenze': minijob_grenze if ist_minijob else None,
            'minijob_status': minijob_status,        # None | 'vollstaendig' | 'ueberschritten'
            'minijob_warnungen': minijob_warnungen,  # Liste mit Warnmeldungen
            'referenz_stunden_tag': referenz_stunden_tag,  # EntgFG-Referenz-Tagesstunden
            'stunden_inkl_fehlzeiten': round(ist_h + krank_lfz_h + urlaub_h, 2) if ist_minijob else None,
        }

    except Exception as e:
        import traceback
        leeres_ergebnis['fehler'] = f"Unerwarteter Fehler bei der Lohnberechnung: {str(e)}\n{traceback.format_exc()}"
        return leeres_ergebnis


# ─────────────────────────────────────────────
# SCHRITT 3: Ergebnis in DB speichern
# ─────────────────────────────────────────────

def speichereMonatslohn(mitarbeiter_id: int, monat: int, jahr: int) -> Dict[str, Any]:
    """
    Berechnet den Monatslohn und speichert ihn in lohnabrechnungen.
    Überschreibt bestehende Einträge (UPSERT-Logik).
    """
    ergebnis = berechneMonatslohn(mitarbeiter_id, monat, jahr)

    if not ergebnis['ok']:
        ergebnis['gespeichert'] = False
        return ergebnis

    try:
        # Service-Role-Client verwenden um RLS-42501 zu umgehen
        try:
            from utils.database import get_service_role_client
            supabase = get_service_role_client()
        except Exception:
            supabase = get_supabase_client()

        daten = {
            'mitarbeiter_id': mitarbeiter_id,
            'monat': monat,
            'jahr': jahr,
            'arbeitsstunden': ergebnis['gesamt_stunden'],
            'sonntagsstunden': ergebnis['sonntags_stunden'],
            'feiertagsstunden': ergebnis['feiertags_stunden'],
            'grundlohn': ergebnis['grundlohn'],
            'sonntagszuschlag': ergebnis['sonntagszuschlag'],
            'feiertagszuschlag': ergebnis['feiertagszuschlag'],
            'gesamtbrutto': ergebnis['gesamtbrutto'],
        }

        # Neue Felder hinzufügen falls vorhanden (Migration nötig)
        try:
            supabase.table('lohnabrechnungen').select('soll_stunden').limit(0).execute()
            daten['soll_stunden'] = ergebnis['soll_stunden']
            daten['ueberstunden'] = ergebnis['saldo_stunden']
        except Exception:
            pass  # Felder noch nicht migriert – ignorieren

        # Prüfe ob bereits vorhanden
        existing = supabase.table('lohnabrechnungen').select('id').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('monat', monat).eq('jahr', jahr).execute()

        if existing.data:
            supabase.table('lohnabrechnungen').update(daten).eq(
                'id', existing.data[0]['id']
            ).execute()
        else:
            supabase.table('lohnabrechnungen').insert(daten).execute()

        ergebnis['gespeichert'] = True

    except Exception as e:
        ergebnis['gespeichert'] = False
        ergebnis['fehler'] = f"Fehler beim Speichern der Lohnabrechnung: {str(e)}"

    return ergebnis
