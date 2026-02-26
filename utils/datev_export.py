"""
DATEV-CSV-Export für Steuerberater
Exportiert Lohnabrechnungsdaten im DATEV Lohn und Gehalt-kompatiblen Format.

DATEV-Format-Referenz:
- Trennzeichen: Semikolon (;)
- Dezimaltrennzeichen: Komma (,)
- Datumsformat: TTMMJJJJ
- Zeichensatz: UTF-8 mit BOM (für Excel-Kompatibilität)
- Erste Zeile: DATEV-Header mit Metadaten
- Zweite Zeile: Spaltenüberschriften
- Ab Zeile 3: Datensätze

Lohnarten-Schlüssel (DATEV-Standard):
    1000 = Grundlohn / Normalstunden
    1100 = Sonntagszuschlag (steuerfrei bis 25% des Grundlohns)
    1200 = Feiertagszuschlag (steuerfrei bis 125% des Grundlohns)
    2000 = Urlaubsvergütung
"""

import csv
import io
import os
from datetime import date, datetime
from typing import List, Dict, Any, Optional


# DATEV-Lohnarten-Schlüssel
LOHNART_GRUNDLOHN = "1000"
LOHNART_SONNTAGSZUSCHLAG = "1100"
LOHNART_FEIERTAGSZUSCHLAG = "1200"
LOHNART_URLAUBSVERGÜTUNG = "2000"


def _format_betrag(wert: float) -> str:
    """Formatiert einen Betrag für DATEV (Komma als Dezimaltrennzeichen, 2 Nachkommastellen)."""
    return f"{wert:.2f}".replace('.', ',')


def _format_stunden(stunden: float) -> str:
    """Formatiert Stunden für DATEV (Komma als Dezimaltrennzeichen, 2 Nachkommastellen)."""
    return f"{stunden:.2f}".replace('.', ',')


def _format_datum(d: date) -> str:
    """Formatiert Datum für DATEV: TTMMJJJJ."""
    return d.strftime('%d%m%Y')


def erstelle_datev_header(
    beraternummer: str = "0000000",
    mandantennummer: str = "00000",
    wirtschaftsjahr_beginn: int = None,
    sachkontenlaenge: int = 4
) -> str:
    """
    Erstellt den DATEV-Headerstring (erste Zeile der CSV-Datei).
    
    Args:
        beraternummer: DATEV-Beraternummer (7-stellig)
        mandantennummer: DATEV-Mandantennummer (5-stellig)
        wirtschaftsjahr_beginn: Beginn des Wirtschaftsjahres (Standard: aktuelles Jahr)
        sachkontenlaenge: Länge der Sachkontonummern
        
    Returns:
        str: DATEV-Headerzeile
    """
    heute = datetime.now()
    wj_beginn = wirtschaftsjahr_beginn or heute.year
    
    # DATEV-Header-Format für Lohn und Gehalt
    header = (
        f'"EXTF";510;21;"LohnBuchungsstapel";1;'
        f'{heute.strftime("%Y%m%d%H%M%S")}000;;"RE";;'
        f'{beraternummer};{mandantennummer};'
        f'{wj_beginn}0101;{sachkontenlaenge};;'
        f'"";"";"";"";;'
    )
    
    return header


def erstelle_datev_lohnexport(
    mitarbeiter_liste: List[Dict[str, Any]],
    lohnabrechnungen: List[Dict[str, Any]],
    monat: int,
    jahr: int,
    betrieb_info: Dict[str, Any] = None
) -> bytes:
    """
    Erstellt einen DATEV-kompatiblen CSV-Export der Lohnabrechnungen.
    
    Args:
        mitarbeiter_liste: Liste der Mitarbeiter-Dicts
        lohnabrechnungen: Liste der Lohnabrechnung-Dicts
        monat: Monat (1-12)
        jahr: Jahr
        betrieb_info: Betriebsinformationen (optional)
        
    Returns:
        bytes: CSV-Datei als Bytes (UTF-8 mit BOM)
    """
    output = io.StringIO()
    
    # Erstelle Mitarbeiter-Lookup
    ma_lookup = {ma['id']: ma for ma in mitarbeiter_liste}
    
    # Abrechnungszeitraum
    von_datum = date(jahr, monat, 1)
    if monat == 12:
        bis_datum = date(jahr + 1, 1, 1)
    else:
        bis_datum = date(jahr, monat + 1, 1)
    bis_datum_letzter = date(jahr, monat, _letzter_tag_des_monats(monat, jahr))
    
    # ============================================================
    # DATEV-HEADER (Zeile 1)
    # ============================================================
    beraternummer = betrieb_info.get('datev_beraternummer', '0000000') if betrieb_info else '0000000'
    mandantennummer = betrieb_info.get('datev_mandantennummer', '00000') if betrieb_info else '00000'
    
    output.write(erstelle_datev_header(beraternummer, mandantennummer, jahr))
    output.write('\n')
    
    # ============================================================
    # SPALTENÜBERSCHRIFTEN (Zeile 2)
    # ============================================================
    spalten = [
        'Umsatz (ohne Soll/Haben-Kz)',  # Betrag
        'Soll/Haben-Kennzeichen',         # S oder H
        'WKZ Umsatz',                     # Währungskennzeichen
        'Kurs',                           # Wechselkurs
        'Basis-Umsatz',                   # Basisumsatz
        'WKZ Basis-Umsatz',               # WKZ Basisumsatz
        'Konto',                          # Buchungskonto
        'Gegenkonto (ohne BU-Schlüssel)', # Gegenkonto
        'BU-Schlüssel',                   # Buchungsschlüssel
        'Belegdatum',                     # Datum
        'Belegfeld 1',                    # Belegnummer
        'Belegfeld 2',                    # Zusatzinfo
        'Skonto',                         # Skonto
        'Buchungstext',                   # Beschreibung
        'Postensperre',                   # Postensperre
        'Diverse Adressnummer',           # Adressnummer
        'Geschäftspartnerbank',           # Bankverbindung
        'Sachverhalt',                    # Sachverhalt
        'Zinssperre',                     # Zinssperre
        'Beleglink',                      # Link
        'Beleginfo - Art 1',              # Mitarbeitername
        'Beleginfo - Inhalt 1',           # Personalnummer
        'Beleginfo - Art 2',              # Lohnart
        'Beleginfo - Inhalt 2',           # Lohnart-Bezeichnung
        'Beleginfo - Art 3',              # Stunden
        'Beleginfo - Inhalt 3',           # Stundenzahl
        'Beleginfo - Art 4',              # Stundenlohn
        'Beleginfo - Inhalt 4',           # Stundenlohn-Betrag
        'Beleginfo - Art 5',              # Monat
        'Beleginfo - Inhalt 5',           # Monat-Wert
    ]
    
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(spalten)
    
    # ============================================================
    # DATENSÄTZE (ab Zeile 3)
    # ============================================================
    monate_de = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    monat_name = monate_de[monat]
    
    for abrechnung in lohnabrechnungen:
        ma_id = abrechnung.get('mitarbeiter_id')
        ma = ma_lookup.get(ma_id, {})
        
        if not ma:
            continue
        
        ma_name = f"{ma.get('vorname', '')} {ma.get('nachname', '')}".strip()
        personalnummer = ma.get('personalnummer', str(ma_id)[:8])
        stundenlohn = float(ma.get('stundenlohn_brutto', 0))
        
        grundlohn = float(abrechnung.get('grundlohn', 0))
        sonntagszuschlag = float(abrechnung.get('sonntagszuschlag', 0))
        feiertagszuschlag = float(abrechnung.get('feiertagszuschlag', 0))
        
        # Arbeitszeitkonto-Daten
        ist_stunden = float(abrechnung.get('ist_stunden', 0))
        sonntagsstunden = float(abrechnung.get('sonntagsstunden', 0))
        feiertagsstunden = float(abrechnung.get('feiertagsstunden', 0))
        
        belegdatum = _format_datum(bis_datum_letzter)
        belegnummer = f"LOHN-{personalnummer}-{monat:02d}{jahr}"
        
        # --- Zeile 1: Grundlohn ---
        if grundlohn > 0:
            writer.writerow([
                _format_betrag(grundlohn),  # Betrag
                'S',                         # Soll
                'EUR',                       # Währung
                '',                          # Kurs
                '',                          # Basis-Umsatz
                '',                          # WKZ Basis
                '4120',                      # Konto: Löhne und Gehälter
                '1200',                      # Gegenkonto: Verbindlichkeiten Lohn
                '',                          # BU-Schlüssel
                belegdatum,                  # Belegdatum
                belegnummer,                 # Belegfeld 1
                f"{monat:02d}/{jahr}",       # Belegfeld 2
                '',                          # Skonto
                f"Grundlohn {ma_name} {monat_name} {jahr}",  # Buchungstext
                '',                          # Postensperre
                '',                          # Adressnummer
                '',                          # Bank
                '',                          # Sachverhalt
                '',                          # Zinssperre
                '',                          # Beleglink
                'Mitarbeiter',               # Art 1
                ma_name,                     # Inhalt 1
                'Lohnart',                   # Art 2
                f"{LOHNART_GRUNDLOHN} Grundlohn",  # Inhalt 2
                'Stunden',                   # Art 3
                _format_stunden(ist_stunden - sonntagsstunden - feiertagsstunden),  # Inhalt 3
                'Stundenlohn',               # Art 4
                _format_betrag(stundenlohn), # Inhalt 4
                'Monat',                     # Art 5
                f"{monat:02d}/{jahr}",       # Inhalt 5
            ])
        
        # --- Zeile 2: Sonntagszuschlag ---
        if sonntagszuschlag > 0:
            writer.writerow([
                _format_betrag(sonntagszuschlag),
                'S',
                'EUR',
                '', '', '',
                '4125',   # Konto: Zuschläge (steuerfreie Lohnbestandteile)
                '1200',
                '',
                belegdatum,
                belegnummer,
                f"{monat:02d}/{jahr}",
                '',
                f"Sonntagszuschlag {ma_name} {monat_name} {jahr}",
                '', '', '', '', '', '',
                'Mitarbeiter', ma_name,
                'Lohnart', f"{LOHNART_SONNTAGSZUSCHLAG} Sonntagszuschlag 50%",
                'Stunden', _format_stunden(sonntagsstunden),
                'Stundenlohn', _format_betrag(stundenlohn * 0.5),
                'Monat', f"{monat:02d}/{jahr}",
            ])
        
        # --- Zeile 3: Feiertagszuschlag ---
        if feiertagszuschlag > 0:
            writer.writerow([
                _format_betrag(feiertagszuschlag),
                'S',
                'EUR',
                '', '', '',
                '4125',   # Konto: Zuschläge
                '1200',
                '',
                belegdatum,
                belegnummer,
                f"{monat:02d}/{jahr}",
                '',
                f"Feiertagszuschlag {ma_name} {monat_name} {jahr}",
                '', '', '', '', '', '',
                'Mitarbeiter', ma_name,
                'Lohnart', f"{LOHNART_FEIERTAGSZUSCHLAG} Feiertagszuschlag 100%",
                'Stunden', _format_stunden(feiertagsstunden),
                'Stundenlohn', _format_betrag(stundenlohn * 1.0),
                'Monat', f"{monat:02d}/{jahr}",
            ])
    
    csv_content = output.getvalue()
    output.close()
    
    # UTF-8 mit BOM (für Excel-Kompatibilität)
    return b'\xef\xbb\xbf' + csv_content.encode('utf-8')


def erstelle_lohnuebersicht_csv(
    mitarbeiter_liste: List[Dict[str, Any]],
    lohnabrechnungen: List[Dict[str, Any]],
    monat: int,
    jahr: int
) -> bytes:
    """
    Erstellt eine vereinfachte Lohnübersicht als CSV (für interne Verwendung oder
    als Alternative zum DATEV-Format).
    
    Args:
        mitarbeiter_liste: Liste der Mitarbeiter-Dicts
        lohnabrechnungen: Liste der Lohnabrechnung-Dicts
        monat: Monat (1-12)
        jahr: Jahr
        
    Returns:
        bytes: CSV-Datei als Bytes (UTF-8 mit BOM)
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    monate_de = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    
    # Header
    writer.writerow([f"Lohnübersicht {monate_de[monat]} {jahr}"])
    writer.writerow([f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}"])
    writer.writerow([])
    
    # Spaltenüberschriften
    writer.writerow([
        'Personalnummer',
        'Nachname',
        'Vorname',
        'Stundenlohn (€)',
        'Soll-Stunden',
        'Ist-Stunden',
        'Differenz',
        'Grundlohn (€)',
        'Sonntagsstunden',
        'Sonntagszuschlag (€)',
        'Feiertagsstunden',
        'Feiertagszuschlag (€)',
        'Gesamtbetrag Brutto (€)',
        'Urlaubstage genommen',
    ])
    
    ma_lookup = {ma['id']: ma for ma in mitarbeiter_liste}
    gesamt_grundlohn = 0
    gesamt_sonntagszuschlag = 0
    gesamt_feiertagszuschlag = 0
    gesamt_gesamtbetrag = 0
    
    for abrechnung in lohnabrechnungen:
        ma_id = abrechnung.get('mitarbeiter_id')
        ma = ma_lookup.get(ma_id, {})
        
        if not ma:
            continue
        
        grundlohn = float(abrechnung.get('grundlohn', 0))
        sonntagszuschlag = float(abrechnung.get('sonntagszuschlag', 0))
        feiertagszuschlag = float(abrechnung.get('feiertagszuschlag', 0))
        gesamtbetrag = float(abrechnung.get('gesamtbetrag', 0))
        ist_stunden = float(abrechnung.get('ist_stunden', 0))
        soll_stunden = float(ma.get('monatliche_soll_stunden', 0))
        sonntagsstunden = float(abrechnung.get('sonntagsstunden', 0))
        feiertagsstunden = float(abrechnung.get('feiertagsstunden', 0))
        urlaubstage = float(abrechnung.get('urlaubstage_genommen', 0))
        
        gesamt_grundlohn += grundlohn
        gesamt_sonntagszuschlag += sonntagszuschlag
        gesamt_feiertagszuschlag += feiertagszuschlag
        gesamt_gesamtbetrag += gesamtbetrag
        
        writer.writerow([
            ma.get('personalnummer', ''),
            ma.get('nachname', ''),
            ma.get('vorname', ''),
            _format_betrag(float(ma.get('stundenlohn_brutto', 0))),
            _format_stunden(soll_stunden),
            _format_stunden(ist_stunden),
            _format_stunden(ist_stunden - soll_stunden),
            _format_betrag(grundlohn),
            _format_stunden(sonntagsstunden),
            _format_betrag(sonntagszuschlag),
            _format_stunden(feiertagsstunden),
            _format_betrag(feiertagszuschlag),
            _format_betrag(gesamtbetrag),
            str(int(urlaubstage)),
        ])
    
    # Summenzeile
    writer.writerow([])
    writer.writerow([
        'GESAMT', '', '', '', '', '', '',
        _format_betrag(gesamt_grundlohn),
        '', _format_betrag(gesamt_sonntagszuschlag),
        '', _format_betrag(gesamt_feiertagszuschlag),
        _format_betrag(gesamt_gesamtbetrag),
        '',
    ])
    
    csv_content = output.getvalue()
    output.close()
    
    return b'\xef\xbb\xbf' + csv_content.encode('utf-8')


def _letzter_tag_des_monats(monat: int, jahr: int) -> int:
    """Gibt den letzten Tag des Monats zurück."""
    import calendar
    return calendar.monthrange(jahr, monat)[1]
