"""
Selbsttest für alle Module der CrewBase-App
Testet alle kritischen Funktionen ohne Datenbankverbindung
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, time, datetime
from typing import Dict, Any

TESTS_BESTANDEN = 0
TESTS_FEHLGESCHLAGEN = 0

def test(name: str, bedingung: bool, details: str = ""):
    global TESTS_BESTANDEN, TESTS_FEHLGESCHLAGEN
    if bedingung:
        print(f"  ✅ {name}")
        TESTS_BESTANDEN += 1
    else:
        print(f"  ❌ {name} {f'({details})' if details else ''}")
        TESTS_FEHLGESCHLAGEN += 1


print("=" * 60)
print("CREWBASE SELBSTTEST")
print("=" * 60)


# ============================================================
# TEST 1: calculations.py
# ============================================================
print("\n📐 TEST: calculations.py")

try:
    from utils.calculations import (
        berechne_arbeitsstunden,
        berechne_arbeitsstunden_mit_pause,
        berechne_grundlohn,
        berechne_sonntagszuschlag,
        berechne_feiertagszuschlag,
        berechne_gesamtlohn,
        berechne_urlaubstage,
        is_feiertag,
        is_sonntag,
        get_german_holidays
    )
    
    # Test: Arbeitsstunden berechnen (8h - 30min Pause = 7.5h)
    start = time(8, 0)
    ende = time(16, 0)
    stunden = berechne_arbeitsstunden(start, ende, 30)
    test("Arbeitsstunden 8:00-16:00 mit 30min Pause = 7.5h", abs(stunden - 7.5) < 0.01, f"Ergebnis: {stunden}")
    
    # Test: Gesetzliche Pause nach ArbZG
    brutto, pause = berechne_arbeitsstunden_mit_pause(time(8, 0), time(16, 0))
    test("Gesetzliche Pause bei 8h Brutto = 30min", pause == 30, f"Pause: {pause}")
    
    brutto2, pause2 = berechne_arbeitsstunden_mit_pause(time(8, 0), time(18, 30))
    test("Gesetzliche Pause bei >9h Brutto = 45min", pause2 == 45, f"Pause: {pause2}")
    
    # Test: Grundlohn
    grundlohn = berechne_grundlohn(15.0, 160.0)
    test("Grundlohn 15€/h × 160h = 2400€", abs(grundlohn - 2400.0) < 0.01, f"Ergebnis: {grundlohn}")
    
    # Test: Sonntagszuschlag 50%
    sonntagszuschlag = berechne_sonntagszuschlag(15.0, 8.0)
    test("Sonntagszuschlag 50%: 15€ × 8h × 0.5 = 60€", abs(sonntagszuschlag - 60.0) < 0.01, f"Ergebnis: {sonntagszuschlag}")
    
    # Test: Feiertagszuschlag 100%
    feiertagszuschlag = berechne_feiertagszuschlag(15.0, 8.0)
    test("Feiertagszuschlag 100%: 15€ × 8h × 1.0 = 120€", abs(feiertagszuschlag - 120.0) < 0.01, f"Ergebnis: {feiertagszuschlag}")
    
    # Test: Urlaubstage - Mo/Di werden nicht gezählt
    # Montag 2025-03-10 bis Freitag 2025-03-14 (Mo, Di, Mi, Do, Fr)
    # Nur Mi, Do, Fr = 3 Tage
    von = date(2025, 3, 10)  # Montag
    bis = date(2025, 3, 14)  # Freitag
    urlaubstage = berechne_urlaubstage(von, bis)
    test("Urlaubstage Mo-Fr: nur Mi,Do,Fr = 3 Tage (Mo/Di Ruhetage)", abs(urlaubstage - 3.0) < 0.01, f"Ergebnis: {urlaubstage}")
    
    # Test: Urlaubstage Mi-So = 5 Tage
    von2 = date(2025, 3, 12)  # Mittwoch
    bis2 = date(2025, 3, 16)  # Sonntag
    urlaubstage2 = berechne_urlaubstage(von2, bis2)
    test("Urlaubstage Mi-So = 5 Tage", abs(urlaubstage2 - 5.0) < 0.01, f"Ergebnis: {urlaubstage2}")
    
    # Test: Feiertag an Montag wird NICHT als Feiertag gezählt
    # Ostermontag 2025: 21. April (Montag)
    ostermontag_2025 = date(2025, 4, 21)
    test("Ostermontag (Mo) ist Ruhetag → kein Feiertagszuschlag", 
         not is_feiertag(ostermontag_2025), 
         f"Weekday: {ostermontag_2025.weekday()}")
    
    # Test: Feiertag an Mittwoch wird als Feiertag gezählt
    # Tag der Deutschen Einheit 2025: 3. Oktober (Freitag)
    tag_der_einheit_2025 = date(2025, 10, 3)
    test("Tag der Deutschen Einheit (Fr) = Feiertag", 
         is_feiertag(tag_der_einheit_2025),
         f"Weekday: {tag_der_einheit_2025.weekday()}")
    
    # Test: Sonntag
    sonntag = date(2025, 3, 16)  # Sonntag
    test("Sonntag erkannt", is_sonntag(sonntag))
    
    montag = date(2025, 3, 17)  # Montag
    test("Montag ist kein Sonntag", not is_sonntag(montag))

except Exception as e:
    print(f"  ❌ FEHLER beim Import/Test calculations.py: {e}")
    import traceback
    traceback.print_exc()
    TESTS_FEHLGESCHLAGEN += 1


# ============================================================
# TEST 2: lohnabrechnung.py (ohne DB)
# ============================================================
print("\n💰 TEST: lohnabrechnung.py (Import-Test)")

try:
    from utils.lohnabrechnung import berechne_arbeitszeitkonto, erstelle_lohnabrechnung
    test("lohnabrechnung.py importierbar", True)
except Exception as e:
    test("lohnabrechnung.py importierbar", False, str(e))


# ============================================================
# TEST 3: QR-Code
# ============================================================
print("\n📱 TEST: qr_code.py")

try:
    from utils.qr_code import generiere_aktivierungs_qr, qr_zu_base64, zeige_qr_code_html
    
    # Test: QR-Code generieren
    qr_bytes = generiere_aktivierungs_qr("ABCD1234", "Terminal Eingang", "https://example.com")
    test("QR-Code generiert (mit URL)", qr_bytes is not None and len(qr_bytes) > 0)
    
    # Test: QR-Code ohne URL
    qr_bytes2 = generiere_aktivierungs_qr("EFGH5678", "Terminal 2")
    test("QR-Code generiert (ohne URL)", qr_bytes2 is not None and len(qr_bytes2) > 0)
    
    # Test: Base64-Konvertierung
    if qr_bytes:
        b64 = qr_zu_base64(qr_bytes)
        test("QR-Code zu Base64 konvertiert", b64 is not None and len(b64) > 100)
    
    # Test: HTML-Darstellung
    html = zeige_qr_code_html("TEST1234", "Test-Gerät", "https://example.com")
    test("QR-Code HTML enthält Bild", "data:image/png;base64," in html)
    test("QR-Code HTML enthält Code", "TEST1234" in html)

except Exception as e:
    test("qr_code.py importierbar", False, str(e))
    import traceback
    traceback.print_exc()


# ============================================================
# TEST 4: email_service.py
# ============================================================
print("\n📧 TEST: email_service.py")

try:
    from utils.email_service import (
        ist_email_konfiguriert,
        send_urlaubsantrag_email,
        send_urlaubsgenehmigung_email,
        send_dienstplan_email,
        send_lohnabrechnung_email,
        _erstelle_html_template
    )
    
    test("email_service.py importierbar", True)
    
    # Test: HTML-Template
    html = _erstelle_html_template("Test-Titel", "<p>Test-Inhalt</p>")
    test("HTML-Template enthält Titel", "Test-Titel" in html)
    test("HTML-Template enthält Inhalt", "Test-Inhalt" in html)
    test("HTML-Template ist valides HTML", "<html>" in html and "</html>" in html)
    
    # Test: Konfigurationsprüfung (ohne echte Credentials)
    konfiguriert = ist_email_konfiguriert()
    test("E-Mail-Konfiguration prüfbar", isinstance(konfiguriert, bool))

except Exception as e:
    test("email_service.py importierbar", False, str(e))
    import traceback
    traceback.print_exc()


# ============================================================
# TEST 5: datev_export.py
# ============================================================
print("\n📊 TEST: datev_export.py")

try:
    from utils.datev_export import (
        erstelle_datev_lohnexport,
        erstelle_lohnuebersicht_csv,
        erstelle_datev_header,
        _format_betrag,
        _format_stunden,
        _format_datum
    )
    
    test("datev_export.py importierbar", True)
    
    # Test: Formatierungsfunktionen
    test("Betrag formatiert (1234.56 → 1234,56)", _format_betrag(1234.56) == "1234,56")
    test("Stunden formatiert (7.5 → 7,50)", _format_stunden(7.5) == "7,50")
    test("Datum formatiert (2025-03-15 → 15032025)", _format_datum(date(2025, 3, 15)) == "15032025")
    
    # Test: DATEV-Header
    header = erstelle_datev_header("1234567", "12345", 2025)
    test("DATEV-Header enthält EXTF", "EXTF" in header)
    
    # Test: Lohnübersicht mit Testdaten
    test_mitarbeiter = [
        {
            'id': 'ma1',
            'personalnummer': '001',
            'vorname': 'Max',
            'nachname': 'Mustermann',
            'stundenlohn_brutto': 15.0,
            'monatliche_soll_stunden': 160.0
        }
    ]
    
    test_abrechnungen = [
        {
            'mitarbeiter_id': 'ma1',
            'grundlohn': 2400.0,
            'sonntagszuschlag': 60.0,
            'feiertagszuschlag': 0.0,
            'gesamtbetrag': 2460.0,
            'ist_stunden': 160.0,
            'soll_stunden': 160.0,
            'sonntagsstunden': 8.0,
            'feiertagsstunden': 0.0,
            'urlaubstage_genommen': 0
        }
    ]
    
    # Test: DATEV-Export
    datev_bytes = erstelle_datev_lohnexport(test_mitarbeiter, test_abrechnungen, 3, 2025)
    test("DATEV-Export generiert", datev_bytes is not None and len(datev_bytes) > 0)
    test("DATEV-Export hat UTF-8 BOM", datev_bytes[:3] == b'\xef\xbb\xbf')
    
    datev_content = datev_bytes.decode('utf-8-sig')
    test("DATEV-Export enthält Mitarbeitername", "Mustermann" in datev_content)
    test("DATEV-Export enthält Grundlohn", "2400,00" in datev_content)
    
    # Test: Lohnübersicht
    uebersicht_bytes = erstelle_lohnuebersicht_csv(test_mitarbeiter, test_abrechnungen, 3, 2025)
    test("Lohnübersicht-CSV generiert", uebersicht_bytes is not None and len(uebersicht_bytes) > 0)
    
    uebersicht_content = uebersicht_bytes.decode('utf-8-sig')
    test("Lohnübersicht enthält Mitarbeitername", "Mustermann" in uebersicht_content)
    test("Lohnübersicht enthält Gesamtbetrag", "2460,00" in uebersicht_content)

except Exception as e:
    test("datev_export.py importierbar", False, str(e))
    import traceback
    traceback.print_exc()


# ============================================================
# TEST 6: device_management.py
# ============================================================
print("\n🖥️ TEST: device_management.py")

try:
    from utils.device_management import activate_device_with_code, is_device_activated
    test("device_management.py importierbar", True)
except Exception as e:
    test("device_management.py importierbar", False, str(e))


# ============================================================
# ZUSAMMENFASSUNG
# ============================================================
print("\n" + "=" * 60)
print(f"ERGEBNIS: {TESTS_BESTANDEN} bestanden, {TESTS_FEHLGESCHLAGEN} fehlgeschlagen")
print("=" * 60)

if TESTS_FEHLGESCHLAGEN == 0:
    print("🎉 Alle Tests bestanden!")
    sys.exit(0)
else:
    print(f"⚠️  {TESTS_FEHLGESCHLAGEN} Test(s) fehlgeschlagen!")
    sys.exit(1)
