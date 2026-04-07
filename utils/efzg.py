"""
EFZG-Logik: Entgeltfortzahlungsgesetz (§ 3 EntgFG)
===================================================

Abgebildete Kernregeln (Stand 2026):
- § 3 Abs. 3 EntgFG: Wartezeit von 4 Wochen (28 Kalendertage)
- § 3 Abs. 1 EntgFG: max. 42 Kalendertage Entgeltfortzahlung je Krankheitsfall
- Wiederholungserkrankung derselben Krankheit:
  neuer 42-Tage-Anspruch nur bei
  a) mindestens 6 Monaten Beschwerdefreiheit ODER
  b) mindestens 12 Monaten seit Beginn der ersten AU derselben Krankheit
- Angearbeiteter erster Krankheitstag:
  zählt als normaler Arbeitstag, die 42-Tage-Frist startet am Folgetag

Wichtig:
- Fristen zählen in Kalendertagen.
- Die Höhe der Zahlung richtet sich nach ausgefallenen Arbeitstagen/Stunden.
"""

from datetime import date, timedelta
from typing import Optional, Sequence
import calendar
import re


def _safe_date(value, default: Optional[date] = None) -> Optional[date]:
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return default


def _add_months(d: date, months: int) -> date:
    month_index = (d.month - 1) + int(months)
    year = d.year + (month_index // 12)
    month = (month_index % 12) + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def _normalize_diagnose_key(value) -> Optional[str]:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    raw = re.sub(r"\s+", " ", raw)
    return raw or None


def _extract_episode_diagnose_key(episode: dict) -> Optional[str]:
    for key in (
        "diagnose",
        "diagnose_code",
        "diagnose_schluessel",
        "krankheitsfall_key",
        "icd10",
        "icd",
    ):
        val = _normalize_diagnose_key((episode or {}).get(key))
        if val:
            return val
    return None


def _normalize_episode(episode: dict) -> Optional[dict]:
    start = _safe_date((episode or {}).get("start_datum") or (episode or {}).get("beginn"))
    end = _safe_date((episode or {}).get("ende_datum") or (episode or {}).get("ende"), default=start)
    if start is None:
        return None
    if end is None or end < start:
        end = start
    return {
        "start": start,
        "end": end,
        "diagnose_key": _extract_episode_diagnose_key(episode),
        "erster_tag_teilgearbeitet": bool((episode or {}).get("erster_tag_teilgearbeitet")),
    }


def _build_active_same_diagnosis_chain(
    *,
    current_episode_start: date,
    current_episode_end: date,
    current_diagnose_key: Optional[str],
    current_partial_first_day: bool,
    history: Sequence[dict] | None,
) -> list[dict]:
    current = {
        "start": current_episode_start,
        "end": current_episode_end,
        "diagnose_key": _normalize_diagnose_key(current_diagnose_key),
        "erster_tag_teilgearbeitet": bool(current_partial_first_day),
    }
    episodes: list[dict] = []
    for ep in history or []:
        n = _normalize_episode(ep)
        if n is not None and n["start"] <= current_episode_end:
            episodes.append(n)
    episodes.append(current)
    episodes = sorted(episodes, key=lambda x: (x["start"], x["end"]))

    diagnose_key = current["diagnose_key"]
    if diagnose_key:
        episodes = [e for e in episodes if e.get("diagnose_key") == diagnose_key]
    else:
        # Ohne Diagnose-Key lässt sich §3 Abs.1 S.2 nicht belastbar anwenden.
        # Daher konservativ: nur aktuelle Episode als Krankheitsfall betrachten.
        return [current]

    if not episodes:
        return [current]

    chain: list[dict] = [episodes[0]]
    chain_anchor = episodes[0]["start"]
    for ep in episodes[1:]:
        prev = chain[-1]
        gesund_start = prev["end"] + timedelta(days=1)
        reset_by_6m = ep["start"] >= _add_months(gesund_start, 6)
        reset_by_12m = ep["start"] >= _add_months(chain_anchor, 12)
        if reset_by_6m or reset_by_12m:
            chain = [ep]
            chain_anchor = ep["start"]
        else:
            chain.append(ep)
    return chain


def _count_lfz_calendar_days_until(
    *,
    chain: Sequence[dict],
    target_day: date,
    sperrfrist_ende: date,
) -> int:
    counted = 0
    for ep in chain:
        start = ep["start"]
        end = min(ep["end"], target_day)
        if end < start:
            continue
        day = start
        while day <= end:
            # Wartezeit-Tage verbrauchen keine 42-Tage-LFZ.
            if day <= sperrfrist_ende:
                day += timedelta(days=1)
                continue
            # Angearbeiteter erster Krankheitstag zählt nicht in die 42 Tage.
            if bool(ep.get("erster_tag_teilgearbeitet")) and day == start:
                day += timedelta(days=1)
                continue
            counted += 1
            day += timedelta(days=1)
    return counted


def berechne_efzg_status(
    datum: date,
    eintrittsdatum: date,
    episode_beginn: date,
    episode_tag_nr: int,  # Kalendertag innerhalb der Episode (1-basiert)
    *,
    episode_ende: Optional[date] = None,
    diagnose_schluessel: Optional[str] = None,
    vorerkrankungen: Optional[Sequence[dict]] = None,
    erster_krankheitstag_teilgearbeitet: bool = False,
) -> str:
    """
    Bestimmt den Entgeltstatus eines Krankheitstages.

    Returns:
        'sperrfrist'          – < 4 Wochen Betriebszugehörigkeit (§3 Abs.3)
        'arbeitslohn_ersttag' – angearbeiteter erster Krankheitstag
        'lohnfortzahlung'     – innerhalb der 42 Kalendertage (§3 Abs.1)
        'krankengeld'         – ab Tag 43 derselben Anspruchskette
    """
    _ = episode_tag_nr  # bleibt aus API-Kompatibilität erhalten
    ep_start = _safe_date(episode_beginn, default=datum) or datum
    ep_end = _safe_date(episode_ende, default=max(ep_start, datum)) or max(ep_start, datum)
    target = _safe_date(datum, default=ep_start) or ep_start
    entry = _safe_date(eintrittsdatum, default=ep_start) or ep_start

    # §3 Abs.3 EntgFG: Anspruch erst nach 4 Wochen ununterbrochener Beschäftigung.
    sperrfrist_ende = entry + timedelta(days=27)
    if target <= sperrfrist_ende:
        return "sperrfrist"

    if erster_krankheitstag_teilgearbeitet and target == ep_start:
        return "arbeitslohn_ersttag"

    chain = _build_active_same_diagnosis_chain(
        current_episode_start=ep_start,
        current_episode_end=ep_end,
        current_diagnose_key=diagnose_schluessel,
        current_partial_first_day=bool(erster_krankheitstag_teilgearbeitet),
        history=vorerkrankungen,
    )
    lfz_days = _count_lfz_calendar_days_until(chain=chain, target_day=target, sperrfrist_ende=sperrfrist_ende)
    return "lohnfortzahlung" if lfz_days <= 42 else "krankengeld"


def berechne_lohnfortzahlung(
    soll_stunden_tag: float,
    stundenlohn: float,
    efzg_status: str,
) -> float:
    """
    Berechnet den Lohnfortzahlungsbetrag für einen Krankheitstag.

    Bei 'sperrfrist', 'arbeitslohn_ersttag' oder 'krankengeld': 0,00 €
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
    episode_ende: Optional[date] = None,
    diagnose_schluessel: Optional[str] = None,
    vorerkrankungen: Optional[Sequence[dict]] = None,
    erster_krankheitstag_teilgearbeitet: bool = False,
) -> dict:
    """
    Erstellt einen vollständigen Krankheitstag-Eintrag mit EFZG-Berechnung.
    Tagessatz = monatliche_soll_stunden / echte Arbeitstage (Mi-So) im Monat des Datums.
    Mo/Di = Ruhetage, erhalten 0h LFZ.
    """
    episode_tag_nr = berechne_episode_tag_nr(datum, episode_beginn)
    efzg_status = berechne_efzg_status(
        datum,
        eintrittsdatum,
        episode_beginn,
        episode_tag_nr,
        episode_ende=episode_ende,
        diagnose_schluessel=diagnose_schluessel,
        vorerkrankungen=vorerkrankungen,
        erster_krankheitstag_teilgearbeitet=erster_krankheitstag_teilgearbeitet,
    )

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
        'diagnose_schluessel': diagnose_schluessel,
        'erster_krankheitstag_teilgearbeitet': bool(erster_krankheitstag_teilgearbeitet),
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
    status = berechne_efzg_status(
        datum=datum,
        eintrittsdatum=episode_beginn - timedelta(days=120),  # simuliert erfüllte Wartezeit
        episode_beginn=episode_beginn,
        episode_tag_nr=berechne_episode_tag_nr(datum, episode_beginn),
        episode_ende=datum,
    )
    if status == "lohnfortzahlung":
        lfz_tag_nr = max(1, _count_lfz_calendar_days_until(
            chain=[{
                "start": episode_beginn,
                "end": datum,
                "diagnose_key": None,
                "erster_tag_teilgearbeitet": False,
            }],
            target_day=datum,
            sperrfrist_ende=episode_beginn - timedelta(days=1),
        ))
        verbleibend = max(0, 42 - lfz_tag_nr + 1)
        return status, verbleibend
    if status == "arbeitslohn_ersttag":
        return status, 42
    return "krankengeld", 0


def pruefe_wiederholungserkrankung_anspruch(
    *,
    aktuelle_episode_beginn: date,
    diagnose_schluessel: Optional[str],
    vorerkrankungen: Optional[Sequence[dict]] = None,
) -> bool:
    """
    Prüft, ob für eine Wiederholungserkrankung derselben Diagnose ein neuer
    42-Tage-Anspruch entstanden ist (§ 3 Abs. 1 S. 2 EntgFG).
    """
    chain = _build_active_same_diagnosis_chain(
        current_episode_start=aktuelle_episode_beginn,
        current_episode_end=aktuelle_episode_beginn,
        current_diagnose_key=diagnose_schluessel,
        current_partial_first_day=False,
        history=vorerkrankungen,
    )
    # Ohne belastbaren Diagnose-Key wird konservativ ein neuer Fall angenommen.
    if not diagnose_schluessel:
        return True
    # Wenn die Kette nur aus der aktuellen Episode besteht, wurde bereits
    # nach 6-/12-Monats-Regel getrennt und damit ein neuer Anspruch aufgebaut.
    return len(chain) == 1


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
