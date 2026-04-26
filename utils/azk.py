"""
azk.py – Arbeitszeitkonto (AZK) Kernlogik

Reine Zeitwirtschaft ohne Lohn- oder Währungsberechnung.

Prinzipien:
  - AZK-Saldo = Startsaldo + Summe(Ist - Soll) über alle Monate
  - Krankheitstage: Ist = Soll (EFZG § 4, Neutralisierung)
  - Urlaubstage: Ist = Soll (vergütete Abwesenheit, kein Minussaldo)
  - Mo/Di = Ruhetage: kein LFZ, kein Urlaubsabzug
  - Manuelle Ausbuchungen via azk_korrekturen-Tabelle
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional

from utils.database import get_supabase_client


# ─────────────────────────────────────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────────────────────────────────────

def ist_ruhetag(d: date) -> bool:
    """Montag (0) und Dienstag (1) sind Ruhetage."""
    return d.weekday() in (0, 1)


def h_zu_hhmm(stunden: float | None) -> str:
    """
    Konvertiert Dezimalstunden in HH:MM-Format.
    Negativ wird als ``-HH:MM`` dargestellt, ``None`` wird als ``00:00`` behandelt.
    """
    if stunden is None:
        return "00:00"
    negativ = stunden < 0
    stunden_abs = abs(stunden)
    h = int(stunden_abs)
    m = round((stunden_abs - h) * 60)
    if m == 60:
        h += 1
        m = 0
    return f"{'-' if negativ else ''}{h:02d}:{m:02d}"


def soll_stunden_pro_tag(monatliche_soll: float, monat: int, jahr: int) -> float:
    """
    Berechnet die Soll-Stunden pro Arbeitstag (ohne Ruhetage Mo/Di).
    Arbeitstage = alle Tage im Monat OHNE Montag und Dienstag.
    """
    erster = date(jahr, monat, 1)
    letzter = date(jahr, monat + 1, 1) - timedelta(days=1) if monat < 12 else date(jahr, 12, 31)
    arbeitstage = sum(
        1 for d in (erster + timedelta(n) for n in range((letzter - erster).days + 1))
        if not ist_ruhetag(d)
    )
    if arbeitstage == 0 or monatliche_soll == 0:
        return 0.0
    return round(monatliche_soll / arbeitstage, 4)


# ─────────────────────────────────────────────────────────────────────────────
# KERNFUNKTION: Monatliche AZK-Berechnung
# ─────────────────────────────────────────────────────────────────────────────

def berechne_azk_monat(mitarbeiter_id: int, monat: int, jahr: int) -> Dict[str, Any]:
    """
    Berechnet das Arbeitszeitkonto für einen Mitarbeiter und Monat.

    Returns:
        {
            'ok': bool,
            'fehler': str | None,
            'tage': list[dict],          # Tagesdetails
            'ist_stunden': float,        # Tatsächlich gearbeitete Stunden
            'soll_stunden': float,       # Monatliches Soll
            'krank_stunden': float,      # LFZ-Stunden (Krankheit, neutralisiert)
            'urlaub_stunden': float,     # Urlaubsstunden
            'differenz': float,          # Ist - Soll (Monat)
            'azk_saldo_monat': float,    # Saldo dieses Monats
            'urlaub_genommen': float,    # Urlaubstage genommen
        }
    """
    ergebnis = {
        'ok': False, 'fehler': None,
        'tage': [],
        'ist_stunden': 0.0,
        'soll_stunden': 0.0,
        'krank_stunden': 0.0,
        'urlaub_stunden': 0.0,
        'differenz': 0.0,
        'azk_saldo_monat': 0.0,
        'urlaub_genommen': 0,
    }

    try:
        supabase = get_supabase_client()

        # Mitarbeiterdaten laden
        ma_resp = supabase.table('mitarbeiter').select(
            'id, vorname, nachname, monatliche_soll_stunden, wochensoll_stunden, azk_startsaldo'
        ).eq('id', mitarbeiter_id).single().execute()

        if not ma_resp.data:
            ergebnis['fehler'] = f"Mitarbeiter {mitarbeiter_id} nicht gefunden."
            return ergebnis

        ma = ma_resp.data
        soll_monat = float(ma.get('monatliche_soll_stunden') or 0)
        ergebnis['soll_stunden'] = soll_monat

        # Zeiterfassung laden
        von = date(jahr, monat, 1).isoformat()
        bis = date(jahr, monat + 1, 1).isoformat() if monat < 12 else date(jahr + 1, 1, 1).isoformat()

        ze_resp = supabase.table('zeiterfassung').select(
            'datum, start_zeit, ende_zeit, pause_minuten, arbeitsstunden, '
            'ist_krank, abwesenheitstyp, ist_sonntag, ist_feiertag, quelle'
        ).eq('mitarbeiter_id', mitarbeiter_id).gte('datum', von).lt('datum', bis).order('datum').execute()

        eintraege = ze_resp.data or []
        soll_tag = soll_stunden_pro_tag(soll_monat, monat, jahr)

        ist_h = 0.0
        krank_h = 0.0
        urlaub_h = 0.0
        urlaub_tage = 0
        tage = []
        kum_saldo = 0.0  # Kumulierter Tagessaldo innerhalb des Monats

        for e in eintraege:
            if e.get('quelle') == 'historischer_saldo':
                continue

            d = date.fromisoformat(e['datum'])
            wt_name = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][d.weekday()]
            ruhetag = ist_ruhetag(d)
            abwtyp = (e.get('abwesenheitstyp') or '').lower()
            krank_flag = e.get('ist_krank') or False
            h = float(e.get('arbeitsstunden') or 0)

            # Typ bestimmen
            if abwtyp in ('urlaub', 'vacation', 'u'):
                typ = 'Urlaub'
                if not ruhetag:
                    urlaub_h += h
                    urlaub_tage += 1
                    ist_eff = h  # Urlaub neutralisiert Soll
                else:
                    ist_eff = 0.0
            elif krank_flag or abwtyp in ('krank', 'k', 'krank_lfz'):
                typ = 'Krank (LFZ)'
                if not ruhetag:
                    krank_h += h
                    ist_eff = h  # Krankheit neutralisiert Soll (EFZG)
                else:
                    typ = 'Ruhetag (krank)'
                    ist_eff = 0.0
            else:
                typ = 'Arbeit'
                ist_h += h
                ist_eff = h

            # Soll für diesen Tag
            soll_eff = 0.0 if ruhetag else soll_tag

            # Differenz
            diff = round(ist_eff - soll_eff, 4)

            kum_saldo = round(kum_saldo + diff, 4)
            tage.append({
                'datum': e['datum'],
                'datum_fmt': d.strftime('%d.%m.%Y'),
                'wochentag': wt_name,
                'typ': typ,
                'start': (e.get('start_zeit') or '')[:5] or '--:--',
                'ende': (e.get('ende_zeit') or '')[:5] or '--:--',
                'pause_min': int(e.get('pause_minuten') or 0),
                'ist_h': round(ist_eff, 2),
                'soll_h': round(soll_eff, 2),
                'diff_h': diff,
                'ist_hhmm': h_zu_hhmm(ist_eff),
                'soll_hhmm': h_zu_hhmm(soll_eff),
                'diff_hhmm': h_zu_hhmm(diff),
                'kum_saldo_h': round(kum_saldo, 2),
                'kum_saldo_hhmm': h_zu_hhmm(kum_saldo),
                'ruhetag': ruhetag,
                'ist_sonntag': e.get('ist_sonntag', False),
            })

        # Gesamtwerte
        gesamt_ist = round(ist_h + krank_h + urlaub_h, 2)
        differenz = round(gesamt_ist - soll_monat, 2)

        ergebnis.update({
            'ok': True,
            'tage': tage,
            'ist_stunden': round(ist_h, 2),
            'krank_stunden': round(krank_h, 2),
            'urlaub_stunden': round(urlaub_h, 2),
            'gesamt_ist': gesamt_ist,
            'differenz': differenz,
            'azk_saldo_monat': differenz,
            'urlaub_genommen': urlaub_tage,
            'soll_tag': round(soll_tag, 2),
        })

    except Exception as ex:
        ergebnis['fehler'] = f"Fehler bei AZK-Berechnung: {str(ex)}"

    return ergebnis


# ─────────────────────────────────────────────────────────────────────────────
# KUMULIERTER AZK-SALDO (fortlaufend über alle Monate)
# ─────────────────────────────────────────────────────────────────────────────

def berechne_azk_kumuliert(mitarbeiter_id: int, bis_monat: int, bis_jahr: int) -> float:
    """
    Berechnet den kumulierten AZK-Saldo vom Eintrittsdatum bis zum angegebenen Monat.
    Startsaldo aus mitarbeiter.azk_startsaldo wird eingerechnet.
    Manuelle Korrekturen aus azk_korrekturen werden eingerechnet.
    """
    try:
        supabase = get_supabase_client()

        # Startsaldo und Eintrittsdatum laden
        ma_resp = supabase.table('mitarbeiter').select(
            'eintrittsdatum, azk_startsaldo'
        ).eq('id', mitarbeiter_id).single().execute()

        if not ma_resp.data:
            return 0.0

        ma = ma_resp.data
        startsaldo = float(ma.get('azk_startsaldo') or 0)
        eintritt_str = ma.get('eintrittsdatum') or '2020-01-01'
        eintritt = date.fromisoformat(eintritt_str)

        # Alle Monate vom Eintritt bis zum Zielmonat durchrechnen
        saldo = startsaldo
        aktuell = date(eintritt.year, eintritt.month, 1)
        ziel = date(bis_jahr, bis_monat, 1)

        while aktuell <= ziel:
            monat_ergebnis = berechne_azk_monat(mitarbeiter_id, aktuell.month, aktuell.year)
            if monat_ergebnis['ok']:
                saldo += monat_ergebnis['azk_saldo_monat']
            # Nächster Monat
            if aktuell.month == 12:
                aktuell = date(aktuell.year + 1, 1, 1)
            else:
                aktuell = date(aktuell.year, aktuell.month + 1, 1)

        # Manuelle Korrekturen einrechnen
        import calendar
        letzter_tag = calendar.monthrange(bis_jahr, bis_monat)[1]
        korr_resp = supabase.table('azk_korrekturen').select('stunden_delta, art').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).lte('datum', date(bis_jahr, bis_monat, letzter_tag).isoformat()).execute()

        for k in (korr_resp.data or []):
            # stunden_delta ist bereits vorzeichenbehaftet (negativ = Ausbuchung)
            h = float(k.get('stunden_delta') or 0)
            saldo += h

        return round(saldo, 2)

    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# URLAUBSKONTO
# ─────────────────────────────────────────────────────────────────────────────

def berechne_urlaubskonto(mitarbeiter_id: int, jahr: int) -> Dict[str, Any]:
    """
    Berechnet den Urlaubsstand für ein Jahr.

    Returns:
        {
            'gesamt_anspruch': int,   # Resturlaub Vorjahr + Jahresanspruch
            'genommen': int,          # Bisher genommene Urlaubstage
            'offen': int,             # Verbleibende Urlaubstage
            'resturlaub_vorjahr': int,
            'jahresanspruch': int,
        }
    """
    try:
        supabase = get_supabase_client()

        ma_resp = supabase.table('mitarbeiter').select(
            'jahres_urlaubstage, resturlaub_vorjahr, urlaubsanspruch_jahrestage'
        ).eq('id', mitarbeiter_id).single().execute()

        if not ma_resp.data:
            return {'gesamt_anspruch': 0, 'genommen': 0, 'offen': 0,
                    'resturlaub_vorjahr': 0, 'jahresanspruch': 0}

        ma = ma_resp.data
        # jahres_urlaubstage ist das bestehende Feld, urlaubsanspruch_jahrestage das neue
        jahresanspruch = int(ma.get('urlaubsanspruch_jahrestage') or ma.get('jahres_urlaubstage') or 0)
        resturlaub = int(ma.get('resturlaub_vorjahr') or 0)
        gesamt = jahresanspruch + resturlaub

        # Genommene Urlaubstage aus Zeiterfassung zählen
        von = date(jahr, 1, 1).isoformat()
        bis = date(jahr + 1, 1, 1).isoformat()

        ze_resp = supabase.table('zeiterfassung').select('datum, abwesenheitstyp').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).gte('datum', von).lt('datum', bis).execute()

        genommen = 0
        for e in (ze_resp.data or []):
            abwtyp = (e.get('abwesenheitstyp') or '').lower()
            if abwtyp in ('urlaub', 'vacation', 'u'):
                d = date.fromisoformat(e['datum'])
                if not ist_ruhetag(d):
                    genommen += 1

        # Auch aus urlaubsantraege zählen (genehmigte)
        ua_resp = supabase.table('urlaubsantraege').select('anzahl_tage').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('status', 'genehmigt').gte('von_datum', von).lt('von_datum', bis).execute()

        # Nur zählen wenn nicht bereits in Zeiterfassung
        # (Zeiterfassung ist die führende Quelle)
        if not ze_resp.data and ua_resp.data:
            genommen = sum(int(u.get('anzahl_tage') or 0) for u in ua_resp.data)

        offen = max(0, gesamt - genommen)

        return {
            'gesamt_anspruch': gesamt,
            'genommen': genommen,
            'offen': offen,
            'resturlaub_vorjahr': resturlaub,
            'jahresanspruch': jahresanspruch,
        }

    except Exception as ex:
        return {'gesamt_anspruch': 0, 'genommen': 0, 'offen': 0,
                'resturlaub_vorjahr': 0, 'jahresanspruch': 0,
                'fehler': str(ex)}


# ─────────────────────────────────────────────────────────────────────────────
# MANUELLE AZK-AUSBUCHUNG
# ─────────────────────────────────────────────────────────────────────────────

def buche_azk_korrektur(
    mitarbeiter_id: int,
    stunden: float,
    typ: str,  # 'ausbuchung' | 'gutschrift'
    grund: str,
    datum: Optional[date] = None,
    erstellt_von: Optional[str] = None,
    betrieb_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Bucht eine manuelle AZK-Korrektur (Ausbuchung oder Gutschrift).
    Niemals automatisch – nur durch expliziten Aufruf.
    """
    if typ not in ('ausbuchung', 'gutschrift'):
        return {'ok': False, 'fehler': "Typ muss 'ausbuchung' oder 'gutschrift' sein."}

    if stunden <= 0:
        return {'ok': False, 'fehler': "Stunden müssen positiv sein."}

    try:
        supabase = get_supabase_client()

        eintrag = {
            'mitarbeiter_id': mitarbeiter_id,
            'datum': (datum or date.today()).isoformat(),
            'stunden_delta': stunden if typ == 'gutschrift' else -stunden,
            'typ': typ,
            'grund': grund,
            'erstellt_von': erstellt_von or 'admin',
        }
        if betrieb_id:
            eintrag['betrieb_id'] = betrieb_id

        resp = supabase.table('azk_korrekturen').insert(eintrag).execute()

        if resp.data:
            return {'ok': True, 'id': resp.data[0]['id']}
        else:
            return {'ok': False, 'fehler': 'Fehler beim Speichern der Korrektur.'}

    except Exception as ex:
        return {'ok': False, 'fehler': str(ex)}


def lade_azk_korrekturen(mitarbeiter_id: int) -> List[Dict]:
    """Lädt alle manuellen AZK-Korrekturen für einen Mitarbeiter."""
    try:
        supabase = get_supabase_client()
        resp = supabase.table('azk_korrekturen').select('*').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).order('datum', desc=True).execute()
        return resp.data or []
    except Exception:
        return []
