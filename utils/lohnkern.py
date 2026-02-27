"""
lohnkern.py – Kernlogik der Lohnberechnung

Kette:
  1. Lade Mitarbeiterdaten (stundenlohn_brutto, jahres_urlaubstage, resturlaub_vorjahr)
  2. Summiere alle Zeiterfassungs-Stunden des Monats für diesen Mitarbeiter
  3. Berechne Bruttolohn: Summe_Stunden * Stundensatz
  4. Schreibe Ergebnis in lohnabrechnungen-Tabelle

Keine Steuern, keine Sozialversicherung in dieser Funktion.
Zuschläge (Sonntag/Feiertag) werden separat addiert.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any

from utils.database import get_supabase_client


# ─────────────────────────────────────────────
# SCHRITT 1: Stunden eines Monats summieren
# ─────────────────────────────────────────────

def summiere_monatsstunden(mitarbeiter_id: int, monat: int, jahr: int) -> Dict[str, Any]:
    """
    Summiert alle abgeschlossenen Zeiterfassungs-Einträge eines Mitarbeiters
    für den angegebenen Monat direkt aus der Datenbank.

    Returns:
        {
            'gesamt_stunden': float,       # Netto-Arbeitsstunden inkl. Pausenabzug
            'sonntags_stunden': float,
            'feiertags_stunden': float,
            'anzahl_eintraege': int,
            'fehler': None | str
        }
    """
    result = {
        'gesamt_stunden': 0.0,
        'sonntags_stunden': 0.0,
        'feiertags_stunden': 0.0,
        'anzahl_eintraege': 0,
        'fehler': None
    }

    try:
        supabase = get_supabase_client()

        von = date(jahr, monat, 1).isoformat()
        bis = date(jahr + 1, 1, 1).isoformat() if monat == 12 else date(jahr, monat + 1, 1).isoformat()

        # Direkte DB-Abfrage: alle abgeschlossenen Einträge des Mitarbeiters im Monat
        response = supabase.table('zeiterfassung').select(
            'start_zeit, ende_zeit, pause_minuten, ist_sonntag, ist_feiertag'
        ).eq('mitarbeiter_id', mitarbeiter_id).gte('datum', von).lt('datum', bis).execute()

        if not response.data:
            result['fehler'] = None  # Kein Fehler – einfach keine Einträge
            return result

        for eintrag in response.data:
            # Nur abgeschlossene Einträge (ende_zeit vorhanden)
            if not eintrag.get('ende_zeit'):
                continue

            try:
                # Zeitdifferenz in Stunden berechnen
                fmt = '%H:%M:%S'
                start = datetime.strptime(eintrag['start_zeit'], fmt)
                ende = datetime.strptime(eintrag['ende_zeit'], fmt)
                differenz_min = (ende - start).seconds / 60

                # Pausenabzug
                pause = int(eintrag.get('pause_minuten') or 0)
                netto_min = differenz_min - pause

                if netto_min <= 0:
                    continue

                netto_h = round(netto_min / 60, 4)
                result['gesamt_stunden'] += netto_h
                result['anzahl_eintraege'] += 1

                if eintrag.get('ist_sonntag'):
                    result['sonntags_stunden'] += netto_h
                if eintrag.get('ist_feiertag'):
                    result['feiertags_stunden'] += netto_h

            except Exception as parse_err:
                # Einzelnen fehlerhaften Eintrag überspringen, nicht abbrechen
                continue

        # Runden
        result['gesamt_stunden'] = round(result['gesamt_stunden'], 2)
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

    Logik:
        grundlohn      = gesamt_stunden * stundenlohn_brutto
        sonntag_bonus  = sonntags_stunden * stundenlohn_brutto * 0.50  (wenn aktiv)
        feiertag_bonus = feiertags_stunden * stundenlohn_brutto * 1.00 (wenn aktiv)
        gesamtbrutto   = grundlohn + sonntag_bonus + feiertag_bonus

    Returns:
        {
            'ok': bool,
            'fehler': None | str,           # Klare Fehlermeldung für die App
            'mitarbeiter_name': str,
            'stundenlohn': float,
            'gesamt_stunden': float,
            'sonntags_stunden': float,
            'feiertags_stunden': float,
            'grundlohn': float,
            'sonntagszuschlag': float,
            'feiertagszuschlag': float,
            'gesamtbrutto': float,
            'anzahl_eintraege': int,
        }
    """
    leeres_ergebnis = {
        'ok': False, 'fehler': None,
        'mitarbeiter_name': '', 'stundenlohn': 0.0,
        'gesamt_stunden': 0.0, 'sonntags_stunden': 0.0, 'feiertags_stunden': 0.0,
        'grundlohn': 0.0, 'sonntagszuschlag': 0.0, 'feiertagszuschlag': 0.0,
        'gesamtbrutto': 0.0, 'anzahl_eintraege': 0,
    }

    try:
        supabase = get_supabase_client()

        # ── Mitarbeiterdaten laden ──────────────────────────────────────────
        ma_resp = supabase.table('mitarbeiter').select(
            'id, vorname, nachname, stundenlohn_brutto, '
            'monatliche_soll_stunden, jahres_urlaubstage, resturlaub_vorjahr, '
            'sonntagszuschlag_aktiv, feiertagszuschlag_aktiv'
        ).eq('id', mitarbeiter_id).execute()

        if not ma_resp.data:
            leeres_ergebnis['fehler'] = f"Fehler: Mitarbeiter mit ID {mitarbeiter_id} nicht gefunden."
            return leeres_ergebnis

        ma = ma_resp.data[0]
        name = f"{ma['vorname']} {ma['nachname']}"

        # ── Stundensatz prüfen ─────────────────────────────────────────────
        stundenlohn_raw = ma.get('stundenlohn_brutto')
        if stundenlohn_raw is None:
            leeres_ergebnis['fehler'] = f"Fehler: Stundensatz für {name} nicht hinterlegt. Bitte in den Mitarbeiterdaten eintragen."
            leeres_ergebnis['mitarbeiter_name'] = name
            return leeres_ergebnis

        stundenlohn = float(stundenlohn_raw)
        if stundenlohn <= 0:
            leeres_ergebnis['fehler'] = f"Fehler: Stundensatz für {name} ist 0,00 €. Bitte korrekten Wert eintragen."
            leeres_ergebnis['mitarbeiter_name'] = name
            return leeres_ergebnis

        # ── Stunden aus DB summieren ───────────────────────────────────────
        stunden_data = summiere_monatsstunden(mitarbeiter_id, monat, jahr)

        if stunden_data['fehler']:
            leeres_ergebnis['fehler'] = stunden_data['fehler']
            leeres_ergebnis['mitarbeiter_name'] = name
            return leeres_ergebnis

        gesamt_h = stunden_data['gesamt_stunden']
        sonntags_h = stunden_data['sonntags_stunden']
        feiertags_h = stunden_data['feiertags_stunden']

        # ── Lohnberechnung ─────────────────────────────────────────────────
        grundlohn = round(gesamt_h * stundenlohn, 2)

        sonntagszuschlag = 0.0
        if ma.get('sonntagszuschlag_aktiv') and sonntags_h > 0:
            sonntagszuschlag = round(sonntags_h * stundenlohn * 0.50, 2)

        feiertagszuschlag = 0.0
        if ma.get('feiertagszuschlag_aktiv') and feiertags_h > 0:
            feiertagszuschlag = round(feiertags_h * stundenlohn * 1.00, 2)

        gesamtbrutto = round(grundlohn + sonntagszuschlag + feiertagszuschlag, 2)

        return {
            'ok': True,
            'fehler': None,
            'mitarbeiter_name': name,
            'stundenlohn': stundenlohn,
            'gesamt_stunden': gesamt_h,
            'sonntags_stunden': sonntags_h,
            'feiertags_stunden': feiertags_h,
            'grundlohn': grundlohn,
            'sonntagszuschlag': sonntagszuschlag,
            'feiertagszuschlag': feiertagszuschlag,
            'gesamtbrutto': gesamtbrutto,
            'anzahl_eintraege': stunden_data['anzahl_eintraege'],
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

    Returns:
        Ergebnis-Dict von berechneMonatslohn + 'gespeichert': bool
    """
    ergebnis = berechneMonatslohn(mitarbeiter_id, monat, jahr)

    if not ergebnis['ok']:
        ergebnis['gespeichert'] = False
        return ergebnis

    try:
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
