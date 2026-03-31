"""
historischer_import.py
======================
Import-Logik für historische Arbeitszeitdaten aus dem Altsystem.

Dateiformat (Excel .xlsx):
  Zeile 2: "Arbeitszeitauswertung"
  Zeile 3: Zeitraum "DD.MM.YYYY - DD.MM.YYYY"
  Zeile 5: "Vorname Nachname - Personalnummer"
  Zeile 6: Spaltenköpfe: Datum | Tag | Soll | Plan | Ist | Abwesend | Saldo |
                          Korrektur | Korrektur Notiz | Lauf. Saldo | Std. Konto | Lohn
  Zeile 8+: Tagesdaten
  Letzte Zeile: Summenzeile

Mapping:
  Datum         → zeiterfassung.datum
  Ist           → zeiterfassung.arbeitsstunden
  Saldo         → wird gespeichert als tages_saldo
  Lauf. Saldo   → arbeitszeitkonto.laufender_saldo (letzter Wert = Startsaldo)
  Std. Konto    → arbeitszeitkonto.std_konto
  Lohn          → zeiterfassung.lohn_betrag (historisch)
  Korrektur     → zeiterfassung.korrektur_betrag
  Korrektur Notiz → zeiterfassung.manuell_kommentar
"""

import csv
from datetime import date, datetime, time
from typing import Optional
import re
import tempfile
from pathlib import Path

try:
    import openpyxl
except ImportError:
    openpyxl = None

from utils.work_accounts import sync_work_account_range


# ─────────────────────────────────────────────────────────────
# PARSE-FUNKTIONEN
# ─────────────────────────────────────────────────────────────

def parse_datum(wert) -> Optional[date]:
    """Konvertiert DD.MM.YYYY-String oder datetime-Objekt in date."""
    if wert is None:
        return None
    if isinstance(wert, (date, datetime)):
        return wert.date() if isinstance(wert, datetime) else wert
    s = str(wert).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, '%d.%m.%Y').date()
    except ValueError:
        return None


def safe_float(wert, default: float = 0.0) -> float:
    """Konvertiert Wert sicher in float, gibt default bei Fehler zurück."""
    if wert is None or wert == '':
        return default
    try:
        return float(wert)
    except (ValueError, TypeError):
        return default


def parse_mitarbeiter_info(zelle_wert: str) -> dict:
    """
    Parst 'Fernando Marrero - 10' in {vorname, nachname, personalnummer}.
    Unterstützt auch 'Vorname Nachname - Nr' und 'Vorname Nachname'.
    """
    if not zelle_wert:
        return {}
    s = str(zelle_wert).strip()
    # Trenne bei ' - ' (Personalnummer)
    if ' - ' in s:
        name_teil, nr_teil = s.rsplit(' - ', 1)
        personalnummer = nr_teil.strip()
    else:
        name_teil = s
        personalnummer = None
    # Trenne Name in Vorname / Nachname
    teile = name_teil.strip().split(' ', 1)
    vorname = teile[0] if teile else ''
    nachname = teile[1] if len(teile) > 1 else ''
    return {
        'vorname': vorname,
        'nachname': nachname,
        'personalnummer': personalnummer,
        'vollname': name_teil.strip()
    }


def parse_zeitraum(zelle_wert: str) -> dict:
    """Parst '01.01.2026 - 31.01.2026' in {von, bis, monat, jahr}."""
    if not zelle_wert:
        return {}
    s = str(zelle_wert).strip()
    match = re.match(r'(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})', s)
    if not match:
        return {}
    von = datetime.strptime(match.group(1), '%d.%m.%Y').date()
    bis = datetime.strptime(match.group(2), '%d.%m.%Y').date()
    return {
        'von': von,
        'bis': bis,
        'monat': von.month,
        'jahr': von.year
    }


# ─────────────────────────────────────────────────────────────
# DATEI-EINLESEN (XLSX/CSV)
# ─────────────────────────────────────────────────────────────

def _parse_planovo_rows(rows: list) -> dict:
    """Parst bereits geladene Planovo-Zeilen in das Standard-Importformat."""
    result = {
        'mitarbeiter': {},
        'zeitraum': {},
        'tage': [],
        'summen': {},
        'startsaldo': 0.0,
        'fehler': []
    }

    # ── Metadaten robust erkennen (XLSX/CSV-Varianten) ────────
    header_row_index = None
    for i, row in enumerate(rows):
        first_cell = row[0] if row and len(row) > 0 else None
        first_text = str(first_cell).strip() if first_cell is not None else ""

        if not result['zeitraum'] and first_text:
            parsed_zeitraum = parse_zeitraum(first_text)
            if parsed_zeitraum:
                result['zeitraum'] = parsed_zeitraum

        if not result['mitarbeiter'] and first_text and " - " in first_text:
            if not parse_zeitraum(first_text):
                info = parse_mitarbeiter_info(first_text)
                if info.get("vorname") and info.get("vorname", "").lower() != "datum":
                    result['mitarbeiter'] = info

        normalized = [str(h).strip().lower() if h is not None else '' for h in row]
        has_datum = any("datum" == h or "datum" in h for h in normalized)
        has_ist = any(h in ("ist", "ist-stunden", "ist stunden") for h in normalized)
        if has_datum and has_ist:
            header_row_index = i
            break

    if header_row_index is None:
        if len(rows) > 5:
            header_row_index = 5
        else:
            result['fehler'].append("Spaltenköpfe nicht gefunden.")
            return result

    header = [str(h).strip() if h else '' for h in rows[header_row_index]]
    col_map = {}
    for idx, h in enumerate(header):
        h_lower = h.lower()
        if 'datum' in h_lower:
            col_map['datum'] = idx
        elif h_lower == 'tag':
            col_map['tag'] = idx
        elif h_lower == 'soll':
            col_map['soll'] = idx
        elif h_lower == 'plan':
            col_map['plan'] = idx
        elif h_lower in ('ist', 'ist-stunden', 'ist stunden'):
            col_map['ist'] = idx
        elif 'abwesend' in h_lower:
            col_map['abwesend'] = idx
        elif h_lower == 'saldo':
            col_map['saldo'] = idx
        elif h_lower == 'korrektur' and 'notiz' not in h_lower:
            col_map['korrektur'] = idx
        elif 'korrektur' in h_lower and 'notiz' in h_lower:
            col_map['korrektur_notiz'] = idx
        elif 'lauf' in h_lower and 'saldo' in h_lower:
            col_map['laufender_saldo'] = idx
        elif 'std' in h_lower and 'konto' in h_lower:
            col_map['std_konto'] = idx
        elif h_lower == 'lohn':
            col_map['lohn'] = idx

    letzter_saldo = 0.0
    letzter_std_konto = 0.0

    for i in range(header_row_index + 1, len(rows)):
        row = rows[i]
        if not row or not any(row):
            continue

        datum_idx = col_map.get('datum')
        datum_wert = row[datum_idx] if datum_idx is not None and datum_idx < len(row) else None
        datum_str = str(datum_wert).strip() if datum_wert else ''

        if datum_str.lower() == 'summe' or datum_str == '':
            if datum_str.lower() == 'summe':
                result['summen'] = {
                    'soll': safe_float(row[col_map['soll']] if 'soll' in col_map and col_map['soll'] < len(row) else None),
                    'plan': safe_float(row[col_map['plan']] if 'plan' in col_map and col_map['plan'] < len(row) else None),
                    'ist': safe_float(row[col_map['ist']] if 'ist' in col_map and col_map['ist'] < len(row) else None),
                    'abwesend': safe_float(row[col_map['abwesend']] if 'abwesend' in col_map and col_map['abwesend'] < len(row) else None),
                    'korrektur': safe_float(row[col_map['korrektur']] if 'korrektur' in col_map and col_map['korrektur'] < len(row) else None),
                    'laufender_saldo': safe_float(row[col_map['laufender_saldo']] if 'laufender_saldo' in col_map and col_map['laufender_saldo'] < len(row) else None),
                    'std_konto': safe_float(row[col_map['std_konto']] if 'std_konto' in col_map and col_map['std_konto'] < len(row) else None),
                    'lohn': safe_float(row[col_map['lohn']] if 'lohn' in col_map and col_map['lohn'] < len(row) else None),
                }
            continue

        datum = parse_datum(datum_wert)
        if datum is None:
            continue

        def _row_val(col_name):
            idx = col_map.get(col_name)
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        wochentag = str(_row_val('tag')).strip() if _row_val('tag') else ''
        ist = safe_float(_row_val('ist'))
        soll = safe_float(_row_val('soll'))
        plan = safe_float(_row_val('plan'))
        abwesend = safe_float(_row_val('abwesend'))
        saldo = safe_float(_row_val('saldo'))
        korrektur = safe_float(_row_val('korrektur'))
        korrektur_notiz = str(_row_val('korrektur_notiz')).strip() if _row_val('korrektur_notiz') else ''
        laufender_saldo = safe_float(_row_val('laufender_saldo'))
        std_konto = safe_float(_row_val('std_konto'))
        lohn = safe_float(_row_val('lohn'))

        ist_ruhetag = (wochentag in ('Mo', 'Di') and soll == 0.0 and ist == 0.0)
        ist_korrekturzeile = bool(korrektur_notiz and korrektur != 0.0)
        ist_krank = (
            soll > 0 and ist == 0.0 and abwesend > 0
        ) or (
            'krank' in korrektur_notiz.lower() or
            'au ' in korrektur_notiz.lower() or
            'arbeitsunfähig' in korrektur_notiz.lower()
        )

        if laufender_saldo != 0.0:
            letzter_saldo = laufender_saldo
        if std_konto != 0.0:
            letzter_std_konto = std_konto

        result['tage'].append({
            'datum': datum,
            'wochentag': wochentag,
            'soll': soll,
            'plan': plan,
            'ist': ist,
            'abwesend': abwesend,
            'saldo': saldo,
            'korrektur': korrektur,
            'korrektur_notiz': korrektur_notiz,
            'laufender_saldo': laufender_saldo,
            'std_konto': std_konto,
            'lohn': lohn,
            'ist_ruhetag': ist_ruhetag,
            'ist_korrekturzeile': ist_korrekturzeile,
            'ist_krank': ist_krank,
        })

    result['startsaldo'] = letzter_saldo if letzter_saldo != 0.0 else letzter_std_konto
    return result


def lese_excel_datei(dateipfad: str) -> dict:
    """Liest eine Planovo-Excel-Datei (.xlsx)."""
    if openpyxl is None:
        return {
            'mitarbeiter': {},
            'zeitraum': {},
            'tage': [],
            'summen': {},
            'startsaldo': 0.0,
            'fehler': ["openpyxl ist nicht installiert. Bitte requirements.txt prüfen."],
        }
    try:
        wb = openpyxl.load_workbook(dateipfad, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        return _parse_planovo_rows(rows)
    except Exception as e:
        return {
            'mitarbeiter': {},
            'zeitraum': {},
            'tage': [],
            'summen': {},
            'startsaldo': 0.0,
            'fehler': [f"Datei konnte nicht geöffnet werden: {e}"],
        }


def lese_csv_datei(dateipfad: str) -> dict:
    """Liest eine Planovo-CSV-Datei und mappt sie auf das gleiche Importformat wie XLSX."""
    encodings = ("utf-8-sig", "cp1252", "latin-1")
    content = None
    for enc in encodings:
        try:
            content = Path(dateipfad).read_text(encoding=enc)
            break
        except Exception:
            continue

    if content is None:
        return {
            'mitarbeiter': {},
            'zeitraum': {},
            'tage': [],
            'summen': {},
            'startsaldo': 0.0,
            'fehler': ["CSV-Datei konnte nicht gelesen werden."],
        }

    try:
        sample = content[:2048]
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ";"

    rows = []
    for row in csv.reader(content.splitlines(), delimiter=delimiter):
        rows.append(row)

    return _parse_planovo_rows(rows)


# ─────────────────────────────────────────────────────────────
# IMPORT-HILFSFUNKTIONEN
# ─────────────────────────────────────────────────────────────

def _resolve_import_range(daten: dict, monat: int, jahr: int) -> tuple[date, date]:
    zeitraum = daten.get('zeitraum', {})
    range_start = zeitraum.get('von')
    range_end = zeitraum.get('bis')
    if not isinstance(range_start, date):
        range_start = date(int(jahr), int(monat), 1)
    if not isinstance(range_end, date):
        range_end = date(int(jahr), int(monat), 28)
    return range_start, range_end


def _count_range_rows(supabase_client, table_name: str, mitarbeiter_id, range_start: date, range_end: date) -> int:
    try:
        res = supabase_client.table(table_name).select('id').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).gte('datum', range_start.isoformat()).lte('datum', range_end.isoformat()).execute()
        return len(res.data or [])
    except Exception:
        return 0


def _cleanup_import_month(
    supabase_client,
    *,
    mitarbeiter_id,
    monat: int,
    jahr: int,
    range_start: date,
    range_end: date,
) -> list[str]:
    errors: list[str] = []
    try:
        supabase_client.table('zeiterfassung').delete().eq(
            'mitarbeiter_id', mitarbeiter_id
        ).gte('datum', range_start.isoformat()).lte('datum', range_end.isoformat()).execute()
    except Exception as e:
        errors.append(f"Fehler beim Monats-Reset (zeiterfassung): {str(e)}")

    try:
        supabase_client.table('krankheitstage').delete().eq(
            'mitarbeiter_id', mitarbeiter_id
        ).gte('datum', range_start.isoformat()).lte('datum', range_end.isoformat()).execute()
    except Exception:
        pass

    try:
        supabase_client.table('arbeitszeitkonto').delete().eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('monat', monat).eq('jahr', jahr).execute()
    except Exception:
        pass

    return errors


def dry_run_import_summary(
    daten: dict,
    *,
    mitarbeiter_id: str | int,
    supabase_client,
) -> dict:
    """
    Trockenlauf vor Import:
    - zeigt geplanten Zeitraum
    - Anzahl Datensätze, die beim Überschreiben gelöscht würden
    - Anzahl Datensätze, die importiert würden
    """
    monat = daten.get('zeitraum', {}).get('monat')
    jahr = daten.get('zeitraum', {}).get('jahr')
    tage = daten.get('tage') or []
    if not monat or not jahr:
        return {
            "ok": False,
            "fehler": ["Zeitraum konnte nicht ermittelt werden."],
        }

    range_start, range_end = _resolve_import_range(daten, int(monat), int(jahr))
    importierbar = sum(1 for t in tage if float(t.get('ist') or 0.0) > 0 or bool(t.get('ist_korrekturzeile')))

    delete_zeiterfassung = _count_range_rows(
        supabase_client, 'zeiterfassung', mitarbeiter_id, range_start, range_end
    )
    delete_krankheitstage = _count_range_rows(
        supabase_client, 'krankheitstage', mitarbeiter_id, range_start, range_end
    )
    try:
        konto_res = supabase_client.table('arbeitszeitkonto').select('id').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('monat', int(monat)).eq('jahr', int(jahr)).execute()
        delete_konto = len(konto_res.data or [])
    except Exception:
        delete_konto = 0

    return {
        "ok": True,
        "monat": int(monat),
        "jahr": int(jahr),
        "range_start": range_start.isoformat(),
        "range_end": range_end.isoformat(),
        "would_import": int(importierbar),
        "would_skip": max(0, len(tage) - int(importierbar)),
        "would_delete_zeiterfassung": int(delete_zeiterfassung),
        "would_delete_krankheitstage": int(delete_krankheitstage),
        "would_delete_arbeitszeitkonto": int(delete_konto),
    }


def _build_import_result_template(daten: dict) -> dict:
    return {
        'ok': False,
        'importiert': 0,
        'uebersprungen': 0,
        'fehler': [],
        'startsaldo': daten.get('startsaldo', 0.0),
        'monat': daten.get('zeitraum', {}).get('monat'),
        'jahr': daten.get('zeitraum', {}).get('jahr'),
    }


def importiere_csv_in_crewbase(
    dateipfad: str,
    *,
    mitarbeiter_id: str | int,
    betrieb_id: str | int,
    supabase_client,
    ueberschreiben: bool = False,
) -> dict:
    daten = lese_csv_datei(dateipfad)
    if daten.get('fehler'):
        result = _build_import_result_template(daten)
        result['fehler'].extend(daten.get('fehler') or [])
        return result
    return importiere_in_crewbase(
        daten,
        mitarbeiter_id=str(mitarbeiter_id),
        betrieb_id=str(betrieb_id),
        supabase_client=supabase_client,
        ueberschreiben=ueberschreiben,
    )


# ─────────────────────────────────────────────────────────────
# IMPORT IN CREWBASE-DATENBANK
# ─────────────────────────────────────────────────────────────

def importiere_in_crewbase(
    daten: dict,
    mitarbeiter_id: str,
    betrieb_id: str,
    supabase_client,
    ueberschreiben: bool = False
) -> dict:
    """
    Importiert die geparsten Daten in die CrewBase-Datenbank.

    Felder:
    - zeiterfassung: Tagesbuchungen (nur Arbeitstage mit ist > 0)
    - arbeitszeitkonto: Monatssaldo
    - historischer_saldo: Startsaldo-Übertrag

    Rückgabe: {ok, importiert, uebersprungen, fehler, startsaldo}
    """
    result = {
        'ok': False,
        'importiert': 0,
        'uebersprungen': 0,
        'fehler': [],
        'startsaldo': daten.get('startsaldo', 0.0),
        'monat': daten.get('zeitraum', {}).get('monat'),
        'jahr': daten.get('zeitraum', {}).get('jahr'),
    }

    if not daten.get('tage'):
        result['fehler'].append("Keine Tagesdaten gefunden.")
        return result

    monat = daten.get('zeitraum', {}).get('monat')
    jahr = daten.get('zeitraum', {}).get('jahr')

    if not monat or not jahr:
        result['fehler'].append("Zeitraum konnte nicht ermittelt werden.")
        return result

    # ── 0. Import-Zeitraum vorbereiten (Monat überschreiben) ────────────────
    range_start, range_end = _resolve_import_range(daten, int(monat), int(jahr))

    if ueberschreiben:
        result['fehler'].extend(
            _cleanup_import_month(
                supabase_client,
                mitarbeiter_id=mitarbeiter_id,
                monat=int(monat),
                jahr=int(jahr),
                range_start=range_start,
                range_end=range_end,
            )
        )

    # ── 1. Zeiterfassung: Tagesbuchungen importieren ──────────
    for tag in daten['tage']:
        datum = tag['datum']
        ist = tag['ist']
        korrektur_notiz = tag.get('korrektur_notiz', '')

        # Nur Tage mit tatsächlichen Stunden importieren (keine Ruhetage, keine reinen Korrekturen)
        if ist <= 0 and not tag['ist_korrekturzeile']:
            result['uebersprungen'] += 1
            continue

        # Sonntag/Feiertag erkennen
        from utils.calculations import is_sonntag, is_feiertag
        ist_so = is_sonntag(datum)
        ist_ft = is_feiertag(datum)

        # Startzeit und Endzeit schätzen (historisch: keine genauen Zeiten vorhanden)
        # Wir setzen 08:00 als Start und berechnen Ende aus Ist-Stunden
        start_h = 8
        start_m = 0
        ende_minuten = int(ist * 60)
        ende_h = start_h + ende_minuten // 60
        ende_m = ende_minuten % 60

        # Pause nach gesetzlicher Regelung
        if ist >= 9:
            pause = 45
        elif ist >= 6:
            pause = 30
        else:
            pause = 0

        # Endzeit mit Pause anpassen
        ende_gesamt_min = start_h * 60 + start_m + int(ist * 60) + pause
        ende_h = ende_gesamt_min // 60
        ende_m = ende_gesamt_min % 60

        kommentar = f"Historischer Import (Altsystem) | Lohn: {tag['lohn']:.2f}€ | Saldo: {tag['saldo']:+.2f}h"
        if korrektur_notiz:
            kommentar += f" | {korrektur_notiz}"

        eintrag = {
            'mitarbeiter_id': mitarbeiter_id,
            'betrieb_id': betrieb_id,
            'datum': datum.isoformat(),
            'start_zeit': f'{start_h:02d}:{start_m:02d}:00',
            'ende_zeit': f'{min(ende_h, 23):02d}:{ende_m:02d}:00',
            'pause_minuten': pause,
            'arbeitsstunden': round(ist, 4),
            'ist_sonntag': ist_so,
            'ist_feiertag': ist_ft,
            'quelle': 'historischer_import',
            'manuell_kommentar': kommentar,
            'korrigiert_von_admin': True,

        }

        try:
            # Prüfen ob bereits vorhanden (nicht überschreiben)
            if not ueberschreiben:
                existing = supabase_client.table('zeiterfassung').select('id').eq(
                    'mitarbeiter_id', mitarbeiter_id
                ).eq('datum', datum.isoformat()).execute()
                if existing.data:
                    result['uebersprungen'] += 1
                    continue

            supabase_client.table('zeiterfassung').insert(eintrag).execute()
            result['importiert'] += 1

        except Exception as e:
            result['fehler'].append(f"Fehler bei {datum}: {str(e)}")
    # ── 1b. Krankheitstage importieren (EFZG) ─────────────────────────────
    kranke_tage = [t for t in daten['tage'] if t.get('ist_krank')]
    if kranke_tage:
        try:
            from utils.efzg import erstelle_krankheitstag_eintrag, berechne_episode_zusammenfassung
            # Eintrittsdatum und Stammdaten aus Mitarbeiter-Tabelle holen
            ma_res = supabase_client.table('mitarbeiter').select(
                'eintrittsdatum, monatliche_soll_stunden, stundenlohn_brutto'
            ).eq('id', mitarbeiter_id).execute()
            ma_data = ma_res.data[0] if ma_res.data else {}
            from datetime import date as _date
            eintrittsdatum = _date.fromisoformat(ma_data.get('eintrittsdatum', '2020-01-01'))
            soll_stunden = float(ma_data.get('monatliche_soll_stunden') or 0)
            stundenlohn = float(ma_data.get('stundenlohn_brutto') or 0)

            # Episode für diesen Import-Block anlegen
            ep_res = supabase_client.table('krankheit_episoden').insert({
                'mitarbeiter_id': mitarbeiter_id,
                'beginn_datum': kranke_tage[0]['datum'].isoformat(),
            }).execute()
            episode_id = ep_res.data[0]['id'] if ep_res.data else None
            episode_beginn = kranke_tage[0]['datum']

            importierte_kranktage = []
            for kt in kranke_tage:
                eintrag = erstelle_krankheitstag_eintrag(
                    mitarbeiter_id=mitarbeiter_id,
                    datum=kt['datum'],
                    eintrittsdatum=eintrittsdatum,
                    episode_beginn=episode_beginn,
                    episode_id=episode_id,
                    monatliche_soll_stunden=soll_stunden,
                    stundenlohn=stundenlohn,
                    arbeitstage_im_monat=23,
                    notiz=kt.get('korrektur_notiz', ''),
                    quelle='historischer_import',
                )
                # Duplikat-Prüfung
                ex = supabase_client.table('krankheitstage').select('id').eq(
                    'mitarbeiter_id', mitarbeiter_id
                ).eq('datum', kt['datum'].isoformat()).execute()
                if not ex.data:
                    supabase_client.table('krankheitstage').insert(eintrag).execute()
                    importierte_kranktage.append(eintrag)

            # Episode aktualisieren
            if episode_id and importierte_kranktage:
                zusammenfassung = berechne_episode_zusammenfassung(importierte_kranktage)
                supabase_client.table('krankheit_episoden').update({
                    'ende_datum': kranke_tage[-1]['datum'].isoformat(),
                    'gesamt_tage': zusammenfassung.get('gesamt_tage', 0),
                    'arbeitstage_krank': zusammenfassung.get('arbeitstage_krank', 0),
                    'lohnfortzahlung_tage': zusammenfassung.get('lohnfortzahlung_tage', 0),
                    'krankengeld_tage': zusammenfassung.get('krankengeld_tage', 0),
                    'gesamt_lohnfortzahlung': zusammenfassung.get('gesamt_lohnfortzahlung', 0),
                }).eq('id', episode_id).execute()

            result['kranktage_importiert'] = len(importierte_kranktage)
        except Exception as e:
            result['fehler'].append(f"Fehler beim Krankheitstage-Import: {str(e)}")

    # ── 2. Arbeitszeitkonto: Monatssaldo speichern ────────────────────────
    try:
        # Summenwerte aus den Tagesdaten berechnen
        arbeitstage = [t for t in daten['tage'] if not t['ist_ruhetag'] and t['ist'] > 0]
        gesamt_ist = sum(t['ist'] for t in arbeitstage)
        gesamt_soll = sum(t['soll'] for t in daten['tage'] if not t['ist_ruhetag'])
        gesamt_so = sum(t['ist'] for t in arbeitstage if t['wochentag'] == 'So')
        gesamt_lohn = sum(t['lohn'] for t in arbeitstage)

        konto_eintrag = {
            'mitarbeiter_id': mitarbeiter_id,
            'monat': monat,
            'jahr': jahr,
            'soll_stunden': round(gesamt_soll, 2),
            'ist_stunden': round(gesamt_ist, 2),
            'sonntagsstunden': round(gesamt_so, 2),
            'feiertagsstunden': 0.0,
            'urlaubstage_genommen': 0,
        }

        # Upsert (einfügen oder aktualisieren)
        existing_konto = supabase_client.table('arbeitszeitkonto').select('id').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('monat', monat).eq('jahr', jahr).execute()

        if existing_konto.data:
            if ueberschreiben:
                supabase_client.table('arbeitszeitkonto').update(konto_eintrag).eq(
                    'id', existing_konto.data[0]['id']
                ).execute()
        else:
            supabase_client.table('arbeitszeitkonto').insert(konto_eintrag).execute()

    except Exception as e:
        result['fehler'].append(f"Fehler beim Arbeitszeitkonto: {str(e)}")

    # ── 3. Historischer Saldo als Übertrag speichern ──────────
    try:
        startsaldo = daten.get('startsaldo', 0.0)
        if startsaldo != 0.0:
            # Saldo als Korrektur-Eintrag in zeiterfassung speichern
            # (mit Datum = letzter Tag des Monats + Notiz)
            letzter_tag = daten['zeitraum'].get('bis')
            if letzter_tag:
                saldo_eintrag = {
                    'mitarbeiter_id': mitarbeiter_id,
                    'betrieb_id': betrieb_id,
                    'datum': letzter_tag.isoformat(),
                    'start_zeit': '00:00:00',
                    'ende_zeit': '00:00:00',
                    'pause_minuten': 0,
                    'arbeitsstunden': 0.0,
                    'ist_sonntag': False,
                    'ist_feiertag': False,
                    'quelle': 'historischer_saldo',
                    'manuell_kommentar': f'Startsaldo-Übertrag aus Altsystem: {startsaldo:+.4f} h (Std. Konto per {letzter_tag.strftime("%d.%m.%Y")})',
                    'korrigiert_von_admin': True,

                }
                # Nur einfügen wenn noch kein Saldo-Eintrag vorhanden
                existing_saldo = supabase_client.table('zeiterfassung').select('id').eq(
                    'mitarbeiter_id', mitarbeiter_id
                ).eq('datum', letzter_tag.isoformat()).eq('quelle', 'historischer_saldo').execute()

                if not existing_saldo.data or ueberschreiben:
                    if existing_saldo.data and ueberschreiben:
                        supabase_client.table('zeiterfassung').delete().eq(
                            'id', existing_saldo.data[0]['id']
                        ).execute()
                    supabase_client.table('zeiterfassung').insert(saldo_eintrag).execute()

    except Exception as e:
        result['fehler'].append(f"Fehler beim Saldo-Übertrag: {str(e)}")

    # ── 4. Laufendes Arbeitszeitkonto automatisch neu berechnen ─────────────
    try:
        zeitraum = daten.get('zeitraum', {})
        start_monat = int(zeitraum.get('monat') or monat)
        start_jahr = int(zeitraum.get('jahr') or jahr)
        heute = date.today()
        snapshots = sync_work_account_range(
            supabase_client,
            betrieb_id=int(betrieb_id),
            mitarbeiter_id=int(mitarbeiter_id),
            start_monat=start_monat,
            start_jahr=start_jahr,
            end_monat=heute.month,
            end_jahr=heute.year,
        )
        result['azk_sync_monate'] = len(snapshots)
    except Exception as e:
        result['fehler'].append(f"Fehler beim automatischen Arbeitszeitkonto-Sync: {str(e)}")

    result['ok'] = len(result['fehler']) == 0 or result['importiert'] > 0
    return result


def lese_upload_datei(uploaded_file) -> dict:
    """
    Liest eine hochgeladene Importdatei (XLSX/CSV) ein.
    """
    suffix = (Path(getattr(uploaded_file, "name", "import.xlsx")).suffix or ".xlsx").lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    try:
        if suffix == ".csv":
            return lese_csv_datei(tmp_path)
        return lese_excel_datei(tmp_path)
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


def lese_excel_upload(uploaded_file) -> dict:
    """
    Rückwärtskompatibler Alias für ältere Aufrufe.
    """
    return lese_upload_datei(uploaded_file)
