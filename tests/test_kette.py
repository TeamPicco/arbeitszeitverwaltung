"""
test_kette.py – Validierungstest der Lohnberechnungs-Kette

Testet die gesamte Logik ohne echte Datenbankverbindung (Mock-Daten).
"""

import sys
import traceback
from unittest.mock import MagicMock, patch

PASS = []
FAIL = []

def test(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ✅ {name}")
    except Exception as e:
        FAIL.append((name, str(e)))
        print(f"  ❌ {name}: {e}")

# ─────────────────────────────────────────────────────────────────
# Modul importieren
# ─────────────────────────────────────────────────────────────────
print("\n=== IMPORT-TEST ===")

try:
    sys.path.insert(0, '/home/ubuntu/arbeitszeitverwaltung')
    import utils.lohnkern as lk
    print("  ✅ utils/lohnkern.py importiert")
    PASS.append("Import lohnkern")
except Exception as e:
    print(f"  ❌ Import lohnkern: {e}")
    FAIL.append(("Import lohnkern", str(e)))
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────
# TEST 1: Stunden-Summierung (Mock-DB)
# ─────────────────────────────────────────────────────────────────
print("\n=== TEST 1: Stunden-Summierung aus Zeiterfassung ===")

def test_stunden_summierung():
    mock_data = [
        {'start_zeit': '09:00:00', 'ende_zeit': '17:00:00', 'pause_minuten': 30, 'ist_sonntag': False, 'ist_feiertag': False},
        {'start_zeit': '10:00:00', 'ende_zeit': '18:00:00', 'pause_minuten': 45, 'ist_sonntag': True,  'ist_feiertag': False},
        {'start_zeit': '08:00:00', 'ende_zeit': '16:00:00', 'pause_minuten': 30, 'ist_sonntag': False, 'ist_feiertag': True},
        {'start_zeit': '09:00:00', 'ende_zeit': None,       'pause_minuten': 0,  'ist_sonntag': False, 'ist_feiertag': False},  # offen
    ]
    mock_resp = MagicMock()
    mock_resp.data = mock_data
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lt.return_value.execute.return_value = mock_resp

    with patch('utils.lohnkern.get_supabase_client', return_value=mock_supabase):
        result = lk.summiere_monatsstunden(1, 2, 2025)

    assert result['fehler'] is None, f"Unerwarteter Fehler: {result['fehler']}"
    assert result['anzahl_eintraege'] == 3, f"Erwartet 3 Einträge (1 offen ignoriert), got {result['anzahl_eintraege']}"

    # Eintrag 1: 8h - 30min = 7.5h
    # Eintrag 2: 8h - 45min = 7.25h (Sonntag)
    # Eintrag 3: 8h - 30min = 7.5h (Feiertag)
    expected_gesamt = round(7.5 + 7.25 + 7.5, 2)
    assert abs(result['gesamt_stunden'] - expected_gesamt) < 0.01, \
        f"Gesamt: erwartet {expected_gesamt}, got {result['gesamt_stunden']}"
    assert abs(result['sonntags_stunden'] - 7.25) < 0.01, \
        f"Sonntag: erwartet 7.25, got {result['sonntags_stunden']}"
    assert abs(result['feiertags_stunden'] - 7.5) < 0.01, \
        f"Feiertag: erwartet 7.5, got {result['feiertags_stunden']}"

test("Stunden-Summierung (3 Einträge, 1 offen ignoriert)", test_stunden_summierung)

# ─────────────────────────────────────────────────────────────────
# TEST 2: Brutto-Berechnung (Grundformel)
# ─────────────────────────────────────────────────────────────────
print("\n=== TEST 2: Brutto-Berechnung: Stunden × Stundensatz ===")

def test_brutto_berechnung():
    mock_ma = [{'id': 1, 'vorname': 'Silke', 'nachname': 'Test',
                'stundenlohn_brutto': 14.40, 'monatliche_soll_stunden': 100.0,
                'jahres_urlaubstage': 28, 'resturlaub_vorjahr': 5.0,
                'sonntagszuschlag_aktiv': False, 'feiertagszuschlag_aktiv': False}]
    mock_stunden = {'gesamt_stunden': 80.0, 'sonntags_stunden': 0.0,
                    'feiertags_stunden': 0.0, 'anzahl_eintraege': 10, 'fehler': None}

    with patch('utils.lohnkern.get_supabase_client') as mock_db, \
         patch('utils.lohnkern.summiere_monatsstunden', return_value=mock_stunden):
        mock_resp = MagicMock()
        mock_resp.data = mock_ma
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resp

        result = lk.berechneMonatslohn(1, 2, 2025)

    assert result['ok'], f"Fehler: {result.get('fehler')}"
    expected = round(80.0 * 14.40, 2)  # = 1152.00
    assert result['grundlohn'] == expected, f"Grundlohn: erwartet {expected}, got {result['grundlohn']}"
    assert result['gesamtbrutto'] == expected, f"Gesamtbrutto: erwartet {expected}, got {result['gesamtbrutto']}"
    assert result['sonntagszuschlag'] == 0.0
    assert result['feiertagszuschlag'] == 0.0
    print(f"      → {80.0} h × {14.40} € = {result['grundlohn']} € Brutto ✓")

test("Grundformel: 80h × 14,40€ = 1.152,00€", test_brutto_berechnung)

# ─────────────────────────────────────────────────────────────────
# TEST 3: Sonntagszuschlag 50%
# ─────────────────────────────────────────────────────────────────
print("\n=== TEST 3: Sonntagszuschlag 50% ===")

def test_sonntagszuschlag():
    mock_ma = [{'id': 1, 'vorname': 'Test', 'nachname': 'MA',
                'stundenlohn_brutto': 14.40, 'monatliche_soll_stunden': 160.0,
                'jahres_urlaubstage': 28, 'resturlaub_vorjahr': 0.0,
                'sonntagszuschlag_aktiv': True, 'feiertagszuschlag_aktiv': False}]
    mock_stunden = {'gesamt_stunden': 40.0, 'sonntags_stunden': 8.0,
                    'feiertags_stunden': 0.0, 'anzahl_eintraege': 5, 'fehler': None}

    with patch('utils.lohnkern.get_supabase_client') as mock_db, \
         patch('utils.lohnkern.summiere_monatsstunden', return_value=mock_stunden):
        mock_resp = MagicMock()
        mock_resp.data = mock_ma
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resp

        result = lk.berechneMonatslohn(1, 2, 2025)

    assert result['ok']
    expected_grundlohn = round(40.0 * 14.40, 2)   # 576.00
    expected_zuschlag  = round(8.0 * 14.40 * 0.5, 2)  # 57.60
    expected_gesamt    = round(expected_grundlohn + expected_zuschlag, 2)  # 633.60
    assert result['grundlohn'] == expected_grundlohn, f"Grundlohn: {result['grundlohn']}"
    assert result['sonntagszuschlag'] == expected_zuschlag, f"Zuschlag: {result['sonntagszuschlag']}"
    assert result['gesamtbrutto'] == expected_gesamt, f"Gesamt: {result['gesamtbrutto']}"
    print(f"      → Grundlohn {expected_grundlohn}€ + Sonntagszuschlag {expected_zuschlag}€ = {expected_gesamt}€ ✓")

test("Sonntagszuschlag 50% korrekt berechnet", test_sonntagszuschlag)

# ─────────────────────────────────────────────────────────────────
# TEST 4: Feiertagszuschlag 100%
# ─────────────────────────────────────────────────────────────────
print("\n=== TEST 4: Feiertagszuschlag 100% ===")

def test_feiertagszuschlag():
    mock_ma = [{'id': 1, 'vorname': 'Test', 'nachname': 'MA',
                'stundenlohn_brutto': 14.40, 'monatliche_soll_stunden': 160.0,
                'jahres_urlaubstage': 28, 'resturlaub_vorjahr': 0.0,
                'sonntagszuschlag_aktiv': False, 'feiertagszuschlag_aktiv': True}]
    mock_stunden = {'gesamt_stunden': 40.0, 'sonntags_stunden': 0.0,
                    'feiertags_stunden': 8.0, 'anzahl_eintraege': 5, 'fehler': None}

    with patch('utils.lohnkern.get_supabase_client') as mock_db, \
         patch('utils.lohnkern.summiere_monatsstunden', return_value=mock_stunden):
        mock_resp = MagicMock()
        mock_resp.data = mock_ma
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resp

        result = lk.berechneMonatslohn(1, 2, 2025)

    assert result['ok']
    expected_grundlohn = round(40.0 * 14.40, 2)   # 576.00
    expected_zuschlag  = round(8.0 * 14.40 * 1.0, 2)  # 115.20
    expected_gesamt    = round(expected_grundlohn + expected_zuschlag, 2)  # 691.20
    assert result['feiertagszuschlag'] == expected_zuschlag, f"Zuschlag: {result['feiertagszuschlag']}"
    assert result['gesamtbrutto'] == expected_gesamt, f"Gesamt: {result['gesamtbrutto']}"
    print(f"      → Grundlohn {expected_grundlohn}€ + Feiertagszuschlag {expected_zuschlag}€ = {expected_gesamt}€ ✓")

test("Feiertagszuschlag 100% korrekt berechnet", test_feiertagszuschlag)

# ─────────────────────────────────────────────────────────────────
# TEST 5: Fehlermeldung wenn Stundensatz fehlt
# ─────────────────────────────────────────────────────────────────
print("\n=== TEST 5: Fehlermeldung wenn Stundensatz fehlt ===")

def test_fehlermeldung_stundensatz():
    mock_ma = [{'id': 1, 'vorname': 'Silke', 'nachname': 'Test',
                'stundenlohn_brutto': None,  # FEHLT!
                'monatliche_soll_stunden': 100.0,
                'jahres_urlaubstage': 28, 'resturlaub_vorjahr': 0.0,
                'sonntagszuschlag_aktiv': False, 'feiertagszuschlag_aktiv': False}]

    with patch('utils.lohnkern.get_supabase_client') as mock_db:
        mock_resp = MagicMock()
        mock_resp.data = mock_ma
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resp

        result = lk.berechneMonatslohn(1, 2, 2025)

    assert not result['ok'], "Sollte fehlschlagen wenn Stundensatz None"
    assert result['fehler'] is not None, "Fehlermeldung muss vorhanden sein"
    assert 'Stundensatz' in result['fehler'], f"Fehlermeldung muss 'Stundensatz' enthalten: {result['fehler']}"
    print(f"      → Fehlermeldung: '{result['fehler']}'")

test("Klare Fehlermeldung bei fehlendem Stundensatz", test_fehlermeldung_stundensatz)

# ─────────────────────────────────────────────────────────────────
# TEST 6: Fehlermeldung wenn Mitarbeiter nicht gefunden
# ─────────────────────────────────────────────────────────────────
print("\n=== TEST 6: Fehlermeldung wenn Mitarbeiter nicht in DB ===")

def test_fehlermeldung_ma_nicht_gefunden():
    with patch('utils.lohnkern.get_supabase_client') as mock_db:
        mock_resp = MagicMock()
        mock_resp.data = []  # Leer!
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resp

        result = lk.berechneMonatslohn(99999, 2, 2025)

    assert not result['ok']
    assert result['fehler'] is not None
    assert '99999' in result['fehler'], f"ID muss in Fehlermeldung: {result['fehler']}"
    print(f"      → Fehlermeldung: '{result['fehler']}'")

test("Klare Fehlermeldung bei unbekannter Mitarbeiter-ID", test_fehlermeldung_ma_nicht_gefunden)

# ─────────────────────────────────────────────────────────────────
# TEST 7: Keine Zeiterfassungs-Einträge → 0 € Lohn, kein Fehler
# ─────────────────────────────────────────────────────────────────
print("\n=== TEST 7: Keine Zeiterfassungs-Einträge → 0 € (kein Fehler) ===")

def test_keine_eintraege():
    mock_ma = [{'id': 1, 'vorname': 'Test', 'nachname': 'MA',
                'stundenlohn_brutto': 14.40, 'monatliche_soll_stunden': 160.0,
                'jahres_urlaubstage': 28, 'resturlaub_vorjahr': 0.0,
                'sonntagszuschlag_aktiv': False, 'feiertagszuschlag_aktiv': False}]
    mock_stunden = {'gesamt_stunden': 0.0, 'sonntags_stunden': 0.0,
                    'feiertags_stunden': 0.0, 'anzahl_eintraege': 0, 'fehler': None}

    with patch('utils.lohnkern.get_supabase_client') as mock_db, \
         patch('utils.lohnkern.summiere_monatsstunden', return_value=mock_stunden):
        mock_resp = MagicMock()
        mock_resp.data = mock_ma
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_resp

        result = lk.berechneMonatslohn(1, 2, 2025)

    assert result['ok'], f"Sollte ok sein: {result.get('fehler')}"
    assert result['gesamtbrutto'] == 0.0
    assert result['grundlohn'] == 0.0
    print(f"      → 0 Einträge → 0,00 € Brutto (kein Fehler) ✓")

test("Keine Zeiteinträge → 0,00 € ohne Fehler", test_keine_eintraege)

# ─────────────────────────────────────────────────────────────────
# ERGEBNIS
# ─────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"ERGEBNIS: {len(PASS)} bestanden / {len(FAIL)} fehlgeschlagen")
print("="*60)

if FAIL:
    print("\nFEHLGESCHLAGENE TESTS:")
    for name, err in FAIL:
        print(f"  ❌ {name}: {err}")
    sys.exit(1)
else:
    print("\n✅ Alle Tests bestanden – Lohnberechnungs-Kette validiert!")
    sys.exit(0)
