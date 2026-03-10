"""
EFZG-Logik: Entgeltfortzahlungsgesetz (§ 3 EFZG)
Rechtssichere Berechnung von Krankheitstagen für Deutschland.

Regeln:
- 4-Wochen-Sperrfrist: Kein Anspruch auf Lohnfortzahlung in den ersten 28 Tagen
  des Arbeitsverhältnisses (§ 3 Abs. 3 EFZG)
- 6-Wochen-Regel: Lohnfortzahlung durch Arbeitgeber für max. 42 Kalendertage
  je zusammenhängender Erkrankung (§ 3 Abs. 1 EFZG)
- Ab Tag 43: Krankengeld durch Krankenkasse (kein Lohn vom Arbeitgeber)
- Lohnfortzahlung = 100% des Bruttolohns auf Basis der Soll-Stunden
- Krankheitstage sind SV-pflichtig (relevant für U1-Erstattungsantrag)
"""

from datetime import date, timedelta
from typing import Optional
import calendar


def berechne_efzg_status(
    datum: date,
    eintrittsdatum: date,
    episode_beginn: date,
    episode_tag_nr: int,  # Kalendertag innerhalb der Episode (1-basiert)
) -> str:
    """
    Bestimmt den EFZG-Status eines Krankheitstages.

    Returns:
        'sperrfrist'      – < 4 Wochen Betriebszugehörigkeit
        'lohnfortzahlung' – Tag 1–42 der Episode (Arbeitgeber zahlt)
        'krankengeld'     – Ab Tag 43 (Krankenkasse zahlt)
    """
    # 4-Wochen-Sperrfrist prüfen (§ 3 Abs. 3 EFZG)
    sperrfrist_ende = eintrittsdatum + timedelta(days=27)  # 28 Tage = 4 Wochen
    if datum <= sperrfrist_ende:
        return 'sperrfrist'

    # 6-Wochen-Regel: 42 Kalendertage ab Episode-Beginn
    lohnfortzahlung_ende = episode_beginn + timedelta(days=41)  # 42 Tage inkl. Tag 1
    if datum <= lohnfortzahlung_ende:
        return 'lohnfortzahlung'

    return 'krankengeld'


def berechne_lohnfortzahlung(
    soll_stunden_tag: float,
    stundenlohn: float,
    efzg_status: str,
) -> float:
    """
    Berechnet den Lohnfortzahlungsbetrag für einen Krankheitstag.

    Bei 'sperrfrist' oder 'krankengeld': 0,00 €
    Bei 'lohnfortzahlung': soll_stunden_tag × stundenlohn (100%)
    """
    if efzg_status != 'lohnfortzahlung':
        return 0.0
    return round(soll_stunden_tag * stundenlohn, 2)


def berechne_arbeitstage_im_monat(monat: int, jahr: int) -> int:
    """
    Zählt die tatsächlichen Arbeitstage (Mi–So) im angegebenen Monat.
    Montag (0) und Dienstag (1) sind Ruhetage und werden nicht gezählt.
    """
    _, tage_im_monat = calendar.monthrange(jahr, monat)
    anzahl = 0
    for tag in range(1, tage_im_monat + 1):
        wochentag = date(jahr, monat, tag).weekday()
        if wochentag not in (0, 1):  # nicht Mo, nicht Di
            anzahl += 1
    return anzahl


def berechne_soll_stunden_tag(
    monatliche_soll_stunden: float,
    arbeitstage_pro_monat: int = None,
    monat: int = None,
    jahr: int = None,
) -> float:
    """
    Berechnet die tägliche Soll-Arbeitszeit aus den monatlichen Soll-Stunden.
    Für diesen Betrieb: Mi–So = 5 Arbeitstage/Woche, Mo/Di = Ruhetage.

    Wenn monat und jahr angegeben, wird die echte Anzahl Arbeitstage berechnet.
    Sonst wird arbeitstage_pro_monat verwendet (Fallback: 22).
    """
    if monat and jahr:
        arbeitstage_pro_monat = berechne_arbeitstage_im_monat(monat, jahr)
    elif not arbeitstage_pro_monat:
        arbeitstage_pro_monat = 22  # Realistischer Durchschnitt für Mi-So Betrieb
    if arbeitstage_pro_monat <= 0:
        return 0.0
    return round(monatliche_soll_stunden / arbeitstage_pro_monat, 4)


def ist_arbeitstag(datum: date) -> bool:
    """
    Prüft ob ein Datum ein Arbeitstag ist (nicht Mo/Di = Ruhetage).
    Feiertage werden hier nicht berücksichtigt (separate Prüfung nötig).
    """
    return datum.weekday() not in (0, 1)  # 0=Montag, 1=Dienstag


def berechne_episode_tag_nr(
    datum: date,
    episode_beginn: date,
) -> int:
    """
    Berechnet die Kalender-Tag-Nummer innerhalb einer Krankheitsepisode.
    Tag 1 = Beginn der Episode.
    """
    return (datum - episode_beginn).days + 1


def erstelle_krankheitstag_eintrag(
    mitarbeiter_id: int,
    datum: date,
    eintrittsdatum: date,
    episode_beginn: date,
    episode_id: Optional[int],
    monatliche_soll_stunden: float,
    stundenlohn: float,
    arbeitstage_im_monat: int = None,  # Wird automatisch aus datum berechnet wenn None
    au_bescheinigung_nr: str = '',
    notiz: str = '',
    quelle: str = 'manuell',
) -> dict:
    """
    Erstellt einen vollständigen Krankheitstag-Eintrag mit EFZG-Berechnung.
    Tagessatz = monatliche_soll_stunden / echte Arbeitstage (Mi-So) im Monat des Datums.
    Mo/Di = Ruhetage, erhalten 0h LFZ.
    """
    episode_tag_nr = berechne_episode_tag_nr(datum, episode_beginn)
    efzg_status = berechne_efzg_status(datum, eintrittsdatum, episode_beginn, episode_tag_nr)

    # Mo/Di = Ruhetage: 0h LFZ
    if datum.weekday() in (0, 1):
        soll_stunden_tag = 0.0
    else:
        # Echte Arbeitstage im Monat des Krankheitstages berechnen
        soll_stunden_tag = berechne_soll_stunden_tag(
            monatliche_soll_stunden,
            arbeitstage_pro_monat=arbeitstage_im_monat,
            monat=datum.month,
            jahr=datum.year,
        )

    lohnfortzahlung_betrag = berechne_lohnfortzahlung(soll_stunden_tag, stundenlohn, efzg_status)

    # U1-Relevanz: Nur Lohnfortzahlungstage sind U1-relevant
    u1_relevant = efzg_status == 'lohnfortzahlung'

    return {
        'mitarbeiter_id': mitarbeiter_id,
        'datum': datum.isoformat(),
        'efzg_status': efzg_status,
        'soll_stunden_tag': float(soll_stunden_tag),
        'stundenlohn': float(stundenlohn),
        'lohnfortzahlung_betrag': float(lohnfortzahlung_betrag),
        'episode_id': episode_id,
        'episode_tag_nr': episode_tag_nr,
        'u1_relevant': u1_relevant,
        'au_bescheinigung_nr': au_bescheinigung_nr,
        'notiz': notiz,
        'quelle': quelle,
    }


def berechne_episode_zusammenfassung(krankheitstage: list) -> dict:
    """
    Berechnet die Zusammenfassung einer Krankheitsepisode aus einer Liste von Tagen.

    Args:
        krankheitstage: Liste von Krankheitstag-Dicts (aus erstelle_krankheitstag_eintrag)

    Returns:
        Dict mit Episoden-Statistiken
    """
    if not krankheitstage:
        return {}

    daten = sorted([t['datum'] for t in krankheitstage])
    beginn = daten[0]
    ende = daten[-1]

    lohnfortzahlung_tage = sum(1 for t in krankheitstage if t['efzg_status'] == 'lohnfortzahlung')
    krankengeld_tage = sum(1 for t in krankheitstage if t['efzg_status'] == 'krankengeld')
    sperrfrist_tage = sum(1 for t in krankheitstage if t['efzg_status'] == 'sperrfrist')
    gesamt_lohnfortzahlung = sum(t['lohnfortzahlung_betrag'] for t in krankheitstage)

    return {
        'beginn_datum': beginn,
        'ende_datum': ende,
        'gesamt_tage': (date.fromisoformat(ende) - date.fromisoformat(beginn)).days + 1,
        'arbeitstage_krank': len(krankheitstage),
        'lohnfortzahlung_tage': lohnfortzahlung_tage,
        'krankengeld_tage': krankengeld_tage,
        'sperrfrist_tage': sperrfrist_tage,
        'gesamt_lohnfortzahlung': round(gesamt_lohnfortzahlung, 2),
    }


def pruefe_4_wochen_sperrfrist(eintrittsdatum: date, datum: date) -> tuple[bool, int]:
    """
    Prüft ob die 4-Wochen-Sperrfrist noch gilt.

    Returns:
        (in_sperrfrist: bool, verbleibende_tage: int)
    """
    sperrfrist_ende = eintrittsdatum + timedelta(days=27)
    in_sperrfrist = datum <= sperrfrist_ende
    verbleibende_tage = max(0, (sperrfrist_ende - datum).days + 1) if in_sperrfrist else 0
    return in_sperrfrist, verbleibende_tage


def pruefe_6_wochen_regel(episode_beginn: date, datum: date) -> tuple[str, int]:
    """
    Prüft den Status der 6-Wochen-Regel für ein Datum.

    Returns:
        (status: str, verbleibende_lohnfortzahlung_tage: int)
        status: 'lohnfortzahlung' oder 'krankengeld'
    """
    lohnfortzahlung_ende = episode_beginn + timedelta(days=41)
    if datum <= lohnfortzahlung_ende:
        verbleibend = (lohnfortzahlung_ende - datum).days + 1
        return 'lohnfortzahlung', verbleibend
    return 'krankengeld', 0


# ── Hilfsfunktion für Monatsauswertung ───────────────────────

def erstelle_monatsauswertung_krankheit(
    krankheitstage_monat: list,
    mitarbeiter_name: str,
    monat: int,
    jahr: int,
) -> dict:
    """
    Erstellt eine strukturierte Monatsauswertung für den Steuerberater.

    Unterscheidet klar zwischen:
    - Lohnfortzahlungstagen (U1-relevant, SV-pflichtig)
    - Krankengeldtagen (Krankenkasse zahlt, kein Lohnaufwand)
    - Sperrtagen (kein Anspruch)
    """
    lohnfortzahlung = [t for t in krankheitstage_monat if t['efzg_status'] == 'lohnfortzahlung']
    krankengeld = [t for t in krankheitstage_monat if t['efzg_status'] == 'krankengeld']
    sperrfrist = [t for t in krankheitstage_monat if t['efzg_status'] == 'sperrfrist']

    gesamt_lohnfortzahlung = sum(t['lohnfortzahlung_betrag'] for t in lohnfortzahlung)

    return {
        'mitarbeiter': mitarbeiter_name,
        'monat': f'{monat:02d}/{jahr}',
        'krankheitstage_gesamt': len(krankheitstage_monat),
        'lohnfortzahlung': {
            'tage': len(lohnfortzahlung),
            'betrag': round(gesamt_lohnfortzahlung, 2),
            'u1_relevant': True,
            'hinweis': 'SV-pflichtig. U1-Erstattungsantrag möglich.',
            'daten': [t['datum'] for t in lohnfortzahlung],
        },
        'krankengeld': {
            'tage': len(krankengeld),
            'betrag': 0.0,
            'hinweis': 'Krankenkasse zahlt direkt. Kein Lohnaufwand für Arbeitgeber.',
            'daten': [t['datum'] for t in krankengeld],
        },
        'sperrfrist': {
            'tage': len(sperrfrist),
            'betrag': 0.0,
            'hinweis': '4-Wochen-Sperrfrist (§ 3 Abs. 3 EFZG). Kein Anspruch auf Lohnfortzahlung.',
            'daten': [t['datum'] for t in sperrfrist],
        },
    }
