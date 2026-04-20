"""
Complio Template-Generatoren: 8 professionelle Formulare & Nachweise.
Alle generieren PDFs in-memory und geben Bytes zurück.
"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase.pdfmetrics import stringWidth
import io

ORANGE = HexColor("#F97316")
DARK = HexColor("#0a0a0a")
GRAY_LIGHT = HexColor("#E5E5E5")
GRAY_DARK = HexColor("#666666")
GRAY_VERY_LIGHT = HexColor("#F5F5F5")
YELLOW_BG = HexColor("#FFF4E6")
RED_BG = HexColor("#FEE2E2")
RED_TEXT = HexColor("#DC2626")
GREEN_BG = HexColor("#D1FAE5")
BLUE_BG = HexColor("#DBEAFE")

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm


def _header(c, title_right, subtitle_right, page_num=1, page_w=None, page_h=None, margin_val=None):
    pw = page_w or PAGE_W
    ph = page_h or PAGE_H
    m = margin_val or MARGIN
    c.setFillColor(DARK)
    c.rect(0, ph - 28*mm, pw, 28*mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(m, ph - 18*mm, "Complio")
    c.setFillColor(ORANGE)
    c.drawString(m + stringWidth("Complio", "Helvetica-Bold", 22), ph - 18*mm, ".")
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 7)
    c.drawString(m, ph - 23*mm, "RECHTSSICHER · ORGANISIERT · GESCHÜTZT")
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(pw - m, ph - 15*mm, title_right)
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 8)
    c.drawRightString(pw - m, ph - 20*mm, subtitle_right)
    c.drawRightString(pw - m, ph - 24*mm, f"Seite {page_num}")


def _footer(c, left_text="© 2026 Complio · getcomplio.de", right_text="", page_w=None, page_h=None, margin_val=None):
    pw = page_w or PAGE_W
    ph = page_h or PAGE_H
    m = margin_val or MARGIN
    c.setStrokeColor(GRAY_LIGHT)
    c.setLineWidth(0.5)
    c.line(m, 12*mm, pw - m, 12*mm)
    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica", 7)
    c.drawString(m, 7*mm, left_text)
    c.drawRightString(pw - m, 7*mm, right_text)


def _field(c, x, y, width, label, height=7*mm):
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY_DARK)
    c.drawString(x, y, label)
    c.setStrokeColor(HexColor("#CCCCCC"))
    c.setLineWidth(0.5)
    c.rect(x, y - height, width, height - 1*mm, fill=0, stroke=1)


def _section_title(c, y, title, right=""):
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, y, title)
    if right:
        c.setFillColor(ORANGE)
        c.setFont("Helvetica", 7)
        c.drawRightString(PAGE_W - MARGIN, y, right)
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1)
    c.line(MARGIN, y - 2*mm, PAGE_W - MARGIN, y - 2*mm)


def _new_canvas(landscape_mode=False):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4) if landscape_mode else A4)
    c.setAuthor("Complio")
    return c, buf


def _finalize(c, buf):
    c.save()
    buf.seek(0)
    return buf.getvalue()


CHECKLISTE_DATA = [
    {"kategorie": "GRUNDPFLICHTEN DES ARBEITGEBERS", "rechtsgrundlage": "§ 3 ArbSchG · DGUV V1",
     "items": [
        ("Gefährdungsbeurteilung aktuell und dokumentiert", "§ 5 ArbSchG", "30.000 €"),
        ("Selbsterklärung zur Gefährdungsbeurteilung (ab 2026)", "DGUV V2 2026", "Pflicht"),
        ("Arbeitsmedizinische Betreuung organisiert", "ASiG, DGUV V2", "10.000 €"),
        ("Schriftliche Bestellung Sifa/Betriebsarzt", "§ 5 ASiG", "Pflicht"),
        ("Fortbildung Inhaber bei alt. Betreuung (ab 2026)", "DGUV V2 2026", "Pflicht"),
     ]},
    {"kategorie": "UNTERWEISUNGEN & SCHULUNGEN", "rechtsgrundlage": "§ 12 ArbSchG · § 4 DGUV V1",
     "items": [
        ("Erstunterweisung neuer Mitarbeiter", "§ 12 ArbSchG", "5.000 €"),
        ("Jährliche Wiederholungsunterweisung", "§ 4 DGUV V1", "5.000 €"),
        ("Unterweisung Gefahrstoffe", "§ 14 GefStoffV", "5.000 €"),
        ("IfSG § 43 Belehrung Erstbelehrung (Gesundheitsamt)", "§ 43 IfSG", "25.000 €"),
        ("IfSG § 43 Folgebelehrung jährlich", "§ 43 IfSG", "25.000 €"),
        ("HACCP-Schulung Lebensmittelhygiene", "VO 852/2004", "50.000 €"),
        ("Brandschutz-Unterweisung jährlich", "ASR A2.2", "5.000 €"),
        ("Erste-Hilfe-Ausbildung Ersthelfer", "§ 26 DGUV V1", "5.000 €"),
     ]},
    {"kategorie": "DOKUMENTATION & NACHWEISE", "rechtsgrundlage": "ArbSchG, ArbStättV",
     "items": [
        ("Gefährdungsbeurteilung schriftlich dokumentiert", "§ 6 ArbSchG", "30.000 €"),
        ("Unterweisungsnachweise mit Unterschrift", "§ 4 DGUV V1", "5.000 €"),
        ("Verbandbuch / Erste-Hilfe-Meldeblock", "§ 24 DGUV V1", "5.000 €"),
        ("Betriebsanweisungen für Gefahrstoffe", "§ 14 GefStoffV", "5.000 €"),
        ("HACCP-Konzept schriftlich", "VO 852/2004", "50.000 €"),
        ("Temperaturkontroll-Listen", "LMHV", "25.000 €"),
        ("Reinigungs- und Desinfektionsplan", "LMHV § 3", "25.000 €"),
        ("Schädlingsbekämpfungs-Nachweise", "LMHV § 3", "25.000 €"),
     ]},
    {"kategorie": "ARBEITSZEIT & PERSONAL", "rechtsgrundlage": "ArbZG, JArbSchG, MuSchG",
     "items": [
        ("Arbeitszeiterfassung elektronisch", "§ 16 ArbZG, EuGH", "15.000 €"),
        ("Pausenregelung dokumentiert", "§ 4 ArbZG", "15.000 €"),
        ("Ruhezeiten 11 Std. zwischen Schichten", "§ 5 ArbZG", "15.000 €"),
        ("Max. 10 Std./Tag, 48 Std./Woche", "§ 3 ArbZG", "15.000 €"),
        ("Spezielle Regelungen Jugendliche", "JArbSchG", "20.000 €"),
        ("Gefährdungsbeurteilung für Schwangere", "§ 10 MuSchG", "30.000 €"),
        ("Arbeitsverträge schriftlich", "NachwG", "5.000 €"),
        ("Mindestlohn-Dokumentation", "MiLoG", "500.000 €"),
     ]},
    {"kategorie": "TECHNISCHE PRÜFUNGEN", "rechtsgrundlage": "BetrSichV, DGUV V3",
     "items": [
        ("Ortsveränderliche Elektrogeräte jährlich prüfen", "DGUV V3", "10.000 €"),
        ("Ortsfeste Anlagen prüfen", "DGUV V3", "10.000 €"),
        ("Gasanlagen jährlich durch Fachbetrieb", "TRGI, DGUV V49", "50.000 €"),
        ("Feuerlöscher-Prüfung alle 2 Jahre", "ASR A2.2", "5.000 €"),
        ("Dunstabzugshauben regelmäßig reinigen", "VDI 2052", "Pflicht"),
     ]},
    {"kategorie": "ARBEITSSTÄTTE", "rechtsgrundlage": "ArbStättV, ASR",
     "items": [
        ("Fluchtwege frei und beleuchtet", "ASR A1.3, A2.3", "5.000 €"),
        ("Fluchtwege gekennzeichnet", "ASR A1.3", "5.000 €"),
        ("Rutschhemmender Bodenbelag in Nassbereichen", "DGUV 208-050", "5.000 €"),
        ("Getrennte Umkleide/Toilette für Personal", "ASR A4.1", "2.500 €"),
        ("Pausenraum / Aufenthaltsraum", "ASR A4.2", "2.500 €"),
     ]},
    {"kategorie": "LEBENSMITTELRECHT & HYGIENE", "rechtsgrundlage": "LFGB, LMHV",
     "items": [
        ("HACCP-Konzept implementiert und gelebt", "VO 852/2004", "50.000 €"),
        ("Allergenkennzeichnung (14 Hauptallergene)", "LMIV Art. 21", "50.000 €"),
        ("Rückstellproben (bei Caterern)", "LMHV", "Empfohlen"),
        ("Lieferantennachweise / Herkunftsnachweise", "LMHV", "25.000 €"),
        ("Kühlkettendokumentation", "VO 853/2004", "25.000 €"),
     ]},
    {"kategorie": "DATENSCHUTZ (DSGVO)", "rechtsgrundlage": "DSGVO, BDSG",
     "items": [
        ("Verzeichnis der Verarbeitungstätigkeiten", "Art. 30 DSGVO", "20 Mio €"),
        ("Datenschutzerklärung für Website", "Art. 13 DSGVO", "20 Mio €"),
        ("Einwilligungen dokumentiert", "Art. 7 DSGVO", "20 Mio €"),
        ("Mitarbeiterdaten DSGVO-konform", "§ 26 BDSG", "20 Mio €"),
        ("Löschkonzept für personenbezogene Daten", "Art. 17 DSGVO", "20 Mio €"),
        ("Auftragsverarbeitungsverträge", "Art. 28 DSGVO", "20 Mio €"),
     ]},
]


def generate_checkliste():
    c, buf = _new_canvas()
    _header(c, "Pflichten-Checkliste", "Rechtsstand 2026 · DGUV V2 NEU", 1)
    _footer(c, right_text="Rechtshinweis: Diese Checkliste ersetzt keine individuelle Rechtsberatung")
    
    y = PAGE_H - 38*mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN, y, "Arbeitsschutz & Compliance")
    y -= 8*mm
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN, y, "Was dein Betrieb WIRKLICH erfüllen muss")
    y -= 12*mm
    
    c.setFillColor(YELLOW_BG)
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    c.rect(MARGIN, y - 35*mm, PAGE_W - 2*MARGIN, 35*mm, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN + 4*mm, y - 6*mm, "⚠ Wichtig zu wissen")
    c.setFont("Helvetica", 9)
    t = c.beginText(MARGIN + 4*mm, y - 12*mm)
    t.setLeading(11)
    for line in ["• Rechtsstand 2026 inkl. neue DGUV Vorschrift 2",
                 "• Bußgelder bis 50.000 € (LFGB) und bis 20 Mio € (DSGVO)",
                 "• Fehlende Gefährdungsbeurteilung: bis 30.000 €",
                 "• NEU ab 2026: Selbsterklärung bei alternativer Betreuung",
                 "• Kontrollen durch Gewerbeaufsicht, BGN, Gesundheitsamt, Zoll"]:
        t.textLine(line)
    c.drawText(t)
    
    c.showPage()
    
    page_num = 2
    _header(c, "Pflichten-Checkliste", "Rechtsstand 2026", page_num)
    _footer(c, right_text="Druckbare Vorlage")
    y = PAGE_H - 35*mm
    
    for kat in CHECKLISTE_DATA:
        if y - 20*mm < 20*mm:
            c.showPage()
            page_num += 1
            _header(c, "Pflichten-Checkliste", "Rechtsstand 2026", page_num)
            _footer(c, right_text="Druckbare Vorlage")
            y = PAGE_H - 35*mm
        
        c.setFillColor(DARK)
        c.rect(MARGIN, y - 7*mm, PAGE_W - 2*MARGIN, 7*mm, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN + 3*mm, y - 5*mm, kat["kategorie"])
        c.setFillColor(ORANGE)
        c.setFont("Helvetica", 7)
        c.drawRightString(PAGE_W - MARGIN - 3*mm, y - 5*mm, kat["rechtsgrundlage"])
        y -= 10*mm
        
        for item, rg, bg in kat["items"]:
            if y < 25*mm:
                c.showPage()
                page_num += 1
                _header(c, "Pflichten-Checkliste", "Rechtsstand 2026", page_num)
                _footer(c, right_text="Druckbare Vorlage")
                y = PAGE_H - 35*mm
            
            c.setStrokeColor(GRAY_LIGHT)
            c.setLineWidth(0.3)
            c.line(MARGIN, y - 2*mm, PAGE_W - MARGIN, y - 2*mm)
            c.setStrokeColor(HexColor("#999999"))
            c.setLineWidth(1)
            c.rect(MARGIN + 2*mm, y - 5*mm, 4*mm, 4*mm, fill=0, stroke=1)
            c.setFillColor(DARK)
            c.setFont("Helvetica", 9)
            display = item[:70] if len(item) > 70 else item
            c.drawString(MARGIN + 9*mm, y - 4*mm, display)
            c.setFont("Helvetica", 7)
            c.setFillColor(GRAY_DARK)
            c.drawString(MARGIN + 125*mm, y - 4*mm, rg[:25])
            if "€" in bg or "Mio" in bg:
                c.setFillColor(RED_TEXT)
            elif bg == "Pflicht":
                c.setFillColor(ORANGE)
            else:
                c.setFillColor(GRAY_DARK)
            c.setFont("Helvetica-Bold", 8)
            c.drawRightString(PAGE_W - MARGIN - 2*mm, y - 4*mm, bg)
            y -= 8*mm
        y -= 4*mm
    
    return _finalize(c, buf)


def generate_verbandbuch():
    c, buf = _new_canvas()
    _header(c, "Verbandbuch / Erste-Hilfe-Meldeblock", "DGUV V1 § 24 · 5 Jahre", 1)
    _footer(c, right_text="Vertraulich behandeln")
    
    y = PAGE_H - 35*mm
    c.setFillColor(YELLOW_BG)
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    c.rect(MARGIN, y - 32*mm, PAGE_W - 2*MARGIN, 32*mm, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 4*mm, y - 6*mm, "Hinweise zur Verwendung")
    c.setFont("Helvetica", 8)
    t = c.beginText(MARGIN + 4*mm, y - 11*mm)
    t.setLeading(10)
    for line in ["• Jeder Unfall ist unverzüglich einzutragen",
                 "• Unlesbare oder nachträgliche Änderungen sind unzulässig",
                 "• Bei Wegeunfällen auch Weg zum/vom Betrieb dokumentieren",
                 "• Aufbewahrung: 5 Jahre nach letztem Eintrag",
                 "• Auskunftspflicht gegenüber Berufsgenossenschaft",
                 "• Datenschutz beachten: Zugriff nur durch berechtigte Personen"]:
        t.textLine(line)
    c.drawText(t)
    y -= 38*mm
    
    _section_title(c, y, "BETRIEBSDATEN")
    y -= 8*mm
    for label, w in [("Name des Betriebs", 165), ("Anschrift", 165), 
                     ("BGN-Mitgliedsnummer", 85), ("Betriebsinhaber", 80)]:
        _field(c, MARGIN, y, w*mm, label)
        y -= 12*mm
    
    c.showPage()
    
    for page in range(2, 7):
        _header(c, "Verbandbuch", f"Eintrag {page-1}", page)
        _footer(c, right_text="Vertraulich")
        y = PAGE_H - 35*mm
        
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGIN, y - 5*mm, "Unfallmeldung Nr.:")
        c.setStrokeColor(HexColor("#CCCCCC"))
        c.rect(MARGIN + 35*mm, y - 7*mm, 25*mm, 6*mm, fill=0, stroke=1)
        c.drawString(MARGIN + 70*mm, y - 5*mm, "Datum:")
        c.rect(MARGIN + 85*mm, y - 7*mm, 35*mm, 6*mm, fill=0, stroke=1)
        c.drawString(MARGIN + 125*mm, y - 5*mm, "Uhrzeit:")
        c.rect(MARGIN + 145*mm, y - 7*mm, 35*mm, 6*mm, fill=0, stroke=1)
        y -= 15*mm
        
        sections = [
            ("ANGABEN ZUR PERSON", [("Name, Vorname", 85), ("Geburtsdatum", 80),
                                     ("Tätigkeit/Funktion", 85), ("Abteilung", 80)]),
            ("ANGABEN ZUM UNFALL", [("Datum", 40), ("Uhrzeit", 40), ("Ort/Raum", 85),
                                     ("Tätigkeit zum Zeitpunkt", 165)]),
            ("HERGANG DES UNFALLS", [("Was ist passiert?", 165), ("", 165), ("", 165)]),
            ("ART DER VERLETZUNG", [("Welche Verletzung / Körperteil", 165)]),
            ("ERSTE-HILFE-LEISTUNG", [("Durchgeführte Maßnahmen", 165), ("", 165)]),
            ("WEITERE VERSORGUNG", [("Ersthelfer", 85), ("Arzt/Krankenhaus", 80)]),
            ("UNTERSCHRIFTEN", [("Verletzte/r", 80), ("Ersthelfer/in", 85)]),
        ]
        
        for section, fields in sections:
            _section_title(c, y, section)
            y -= 6*mm
            x_pos = MARGIN
            field_y = y
            for label, w in fields:
                if x_pos + w*mm > PAGE_W - MARGIN:
                    x_pos = MARGIN
                    field_y -= 11*mm
                _field(c, x_pos, field_y, w*mm - 2*mm, label)
                x_pos += w*mm
            y = field_y - 10*mm
        
        if page < 6:
            c.showPage()
    
    return _finalize(c, buf)


def generate_unterweisung():
    c, buf = _new_canvas()
    _header(c, "Unterweisungsnachweis", "§ 12 ArbSchG · § 4 DGUV V1", 1)
    _footer(c, right_text="Vor Tätigkeitsbeginn + jährlich")
    
    y = PAGE_H - 35*mm
    c.setFillColor(YELLOW_BG)
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    c.rect(MARGIN, y - 28*mm, PAGE_W - 2*MARGIN, 28*mm, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 4*mm, y - 6*mm, "⚠ Pflichten nach § 12 ArbSchG / § 4 DGUV V1")
    c.setFont("Helvetica", 8)
    t = c.beginText(MARGIN + 4*mm, y - 11*mm)
    t.setLeading(10)
    for line in ["• VOR Aufnahme der Tätigkeit: Erstunterweisung",
                 "• MINDESTENS JÄHRLICH: Wiederholungsunterweisung",
                 "• BEI ÄNDERUNGEN: Anlassbezogene Unterweisung",
                 "• BEI JUGENDLICHEN: Halbjährliche Unterweisung",
                 "• DOKUMENTATION: Schriftlich - 5 Jahre aufbewahren"]:
        t.textLine(line)
    c.drawText(t)
    y -= 34*mm
    
    _section_title(c, y, "ANGABEN ZUM BETRIEB")
    y -= 8*mm
    _field(c, MARGIN, y, 100*mm, "Betrieb / Firma")
    _field(c, MARGIN + 102*mm, y, 63*mm, "Abteilung")
    y -= 11*mm
    _field(c, MARGIN, y, 100*mm, "Unterweiser (Name)")
    _field(c, MARGIN + 102*mm, y, 63*mm, "Funktion")
    y -= 15*mm
    
    _section_title(c, y, "ART DER UNTERWEISUNG")
    y -= 8*mm
    for opt in ["Erstunterweisung (vor Tätigkeitsbeginn)",
                "Wiederholungsunterweisung (jährlich)",
                "Anlassbezogene Unterweisung",
                "Halbjährliche Unterweisung (Jugendliche)"]:
        c.setStrokeColor(HexColor("#999999"))
        c.rect(MARGIN + 2*mm, y - 4*mm, 4*mm, 4*mm, fill=0, stroke=1)
        c.setFillColor(DARK)
        c.setFont("Helvetica", 9)
        c.drawString(MARGIN + 9*mm, y - 3.5*mm, opt)
        y -= 6*mm
    y -= 4*mm
    
    _section_title(c, y, "ZEITPUNKT")
    y -= 8*mm
    _field(c, MARGIN, y, 50*mm, "Datum")
    _field(c, MARGIN + 53*mm, y, 45*mm, "Uhrzeit")
    _field(c, MARGIN + 101*mm, y, 64*mm, "Dauer (Min)")
    y -= 15*mm
    
    _section_title(c, y, "UNTERWEISUNGSINHALTE")
    y -= 8*mm
    
    links = ["Allgemeine Gefahren", "Notfall/Brandfall", "Erste Hilfe", 
             "Flucht-/Rettungswege", "Feuerlöscher/Verbandkasten", "Verbandbuch",
             "Rutschgefahr", "PSA", "Heben/Tragen"]
    rechts = ["Gefahrstoffe", "Elektrische Sicherheit", "Messer/Schneidegeräte",
              "Heißgeräte", "HACCP", "IfSG § 43", "Arbeitszeit/Pausen",
              "Mobbing/Belästigung", "Datenschutz DSGVO"]
    
    y_start = y
    for item in links:
        c.setStrokeColor(HexColor("#999999"))
        c.rect(MARGIN + 2*mm, y - 4*mm, 3.5*mm, 3.5*mm, fill=0, stroke=1)
        c.setFont("Helvetica", 8)
        c.setFillColor(DARK)
        c.drawString(MARGIN + 7*mm, y - 3.5*mm, item)
        y -= 5*mm
    y = y_start
    for item in rechts:
        c.setStrokeColor(HexColor("#999999"))
        c.rect(MARGIN + 92*mm, y - 4*mm, 3.5*mm, 3.5*mm, fill=0, stroke=1)
        c.setFont("Helvetica", 8)
        c.setFillColor(DARK)
        c.drawString(MARGIN + 97*mm, y - 3.5*mm, item)
        y -= 5*mm
    
    y -= 4*mm
    _field(c, MARGIN, y, 75*mm, "Datum / Unterschrift Unterweiser")
    _field(c, MARGIN + 78*mm, y, 87*mm, "Name in Druckschrift")
    
    c.showPage()
    
    _header(c, "Unterweisungsnachweis", "Teilnehmerliste", 2)
    _footer(c, right_text="Aufbewahrung 5 Jahre")
    y = PAGE_H - 35*mm
    _section_title(c, y, "TEILNEHMER DER UNTERWEISUNG")
    y -= 10*mm
    
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 8)
    for x, label in [(MARGIN + 2*mm, "Nr."), (MARGIN + 10*mm, "Name"),
                      (MARGIN + 70*mm, "Personalnr."), (MARGIN + 90*mm, "Tätigkeit"),
                      (MARGIN + 130*mm, "Unterschrift")]:
        c.drawString(x, y, label)
    c.setStrokeColor(ORANGE)
    c.line(MARGIN, y - 2*mm, PAGE_W - MARGIN, y - 2*mm)
    y -= 6*mm
    
    for i in range(1, 22):
        row_h = 10*mm
        c.setStrokeColor(GRAY_LIGHT)
        c.line(MARGIN, y - row_h + 1*mm, PAGE_W - MARGIN, y - row_h + 1*mm)
        c.setFillColor(GRAY_DARK)
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN + 2*mm, y - 4*mm, str(i))
        for x in [MARGIN + 8*mm, MARGIN + 68*mm, MARGIN + 88*mm, MARGIN + 128*mm]:
            c.line(x, y, x, y - row_h + 1*mm)
        y -= row_h
    
    return _finalize(c, buf)


def generate_haccp_nachweis():
    c, buf = _new_canvas()
    _header(c, "HACCP-Schulungsnachweis", "VO (EG) 852/2004 · LMHV", 1)
    _footer(c, right_text="Jährliche Empfehlung")
    
    y = PAGE_H - 35*mm
    c.setFillColor(RED_BG)
    c.setStrokeColor(HexColor("#DC2626"))
    c.setLineWidth(1.5)
    c.rect(MARGIN, y - 28*mm, PAGE_W - 2*MARGIN, 28*mm, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 4*mm, y - 6*mm, "⚠ HACCP-Pflicht für Lebensmittelbetriebe")
    c.setFont("Helvetica", 8)
    t = c.beginText(MARGIN + 4*mm, y - 11*mm)
    t.setLeading(10)
    for line in ["• VO (EG) 852/2004 Art. 5: HACCP-Konzept-Pflicht",
                 "• LMHV § 4: Schulung der Mitarbeiter erforderlich",
                 "• EMPFEHLUNG: Erstschulung + jährliche Auffrischung",
                 "• BUSSGELD: bis 50.000 € (§ 60 LFGB)"]:
        t.textLine(line)
    c.drawText(t)
    y -= 34*mm
    
    _section_title(c, y, "ANGABEN ZUM BETRIEB")
    y -= 8*mm
    _field(c, MARGIN, y, 100*mm, "Betrieb")
    _field(c, MARGIN + 102*mm, y, 63*mm, "Betriebsart")
    y -= 11*mm
    _field(c, MARGIN, y, 100*mm, "Schulungsleiter")
    _field(c, MARGIN + 102*mm, y, 63*mm, "Qualifikation")
    y -= 15*mm
    
    _section_title(c, y, "SCHULUNGSINHALTE")
    y -= 8*mm
    
    kategorien = [
        ("1. Grundlagen HACCP", ["HACCP-Prinzip", "7 Grundsätze", "Gefahrenanalyse", "CCPs"]),
        ("2. Personalhygiene", ["Händewaschen", "Arbeitskleidung", "Krankheit Meldepflicht"]),
        ("3. Lebensmittelhygiene", ["Getrennte Verarbeitung", "Lagerung", "Kühlkette", "Kerntemperaturen"]),
        ("4. Reinigung", ["Reinigungsplan", "Dosierung/Einwirkzeit"]),
        ("5. Dokumentation", ["Temperaturen", "Reinigung", "Schädlinge", "Rückstellproben"]),
        ("6. Allergene", ["14 Hauptallergene", "Kennzeichnung", "Kreuzkontamination"]),
    ]
    
    for kat_title, items in kategorien:
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN, y, kat_title)
        y -= 5*mm
        for item in items:
            c.setStrokeColor(HexColor("#999999"))
            c.rect(MARGIN + 4*mm, y - 3.5*mm, 3.5*mm, 3.5*mm, fill=0, stroke=1)
            c.setFont("Helvetica", 8)
            c.drawString(MARGIN + 10*mm, y - 3*mm, item)
            y -= 4.5*mm
        y -= 2*mm
    
    c.showPage()
    _header(c, "HACCP-Nachweis", "Teilnehmer", 2)
    _footer(c)
    y = PAGE_H - 35*mm
    _section_title(c, y, "TEILNEHMER DER SCHULUNG")
    y -= 10*mm
    
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN + 2*mm, y, "Nr.")
    c.drawString(MARGIN + 10*mm, y, "Name")
    c.drawString(MARGIN + 70*mm, y, "IfSG §43?")
    c.drawString(MARGIN + 98*mm, y, "Tätigkeit")
    c.drawString(MARGIN + 130*mm, y, "Unterschrift")
    c.setStrokeColor(ORANGE)
    c.line(MARGIN, y - 2*mm, PAGE_W - MARGIN, y - 2*mm)
    y -= 6*mm
    
    for i in range(1, 20):
        row_h = 10*mm
        c.setStrokeColor(GRAY_LIGHT)
        c.line(MARGIN, y - row_h + 1*mm, PAGE_W - MARGIN, y - row_h + 1*mm)
        c.setFillColor(GRAY_DARK)
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN + 2*mm, y - 4*mm, str(i))
        for x in [MARGIN + 8*mm, MARGIN + 68*mm, MARGIN + 96*mm, MARGIN + 128*mm]:
            c.line(x, y, x, y - row_h + 1*mm)
        y -= row_h
    
    return _finalize(c, buf)


def generate_ifsg_belehrung():
    c, buf = _new_canvas()
    _header(c, "IfSG § 43 Folgebelehrung", "Infektionsschutzgesetz", 1)
    _footer(c, right_text="Alle 24 Monate")
    
    y = PAGE_H - 35*mm
    c.setFillColor(RED_BG)
    c.setStrokeColor(HexColor("#DC2626"))
    c.setLineWidth(1.5)
    c.rect(MARGIN, y - 32*mm, PAGE_W - 2*MARGIN, 32*mm, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 4*mm, y - 6*mm, "⚠ IfSG § 43 - Zwei Belehrungen!")
    c.setFont("Helvetica", 8)
    t = c.beginText(MARGIN + 4*mm, y - 12*mm)
    t.setLeading(10)
    for line in ["1. ERSTBELEHRUNG: Durch Gesundheitsamt (kostenpflichtig)",
                 "   → Gelbes Gesundheitszeugnis - lebenslang gueltig",
                 "2. FOLGEBELEHRUNG: Durch Arbeitgeber, alle 24 Monate",
                 "BETRIFFT: Alle die mit Lebensmitteln arbeiten (§ 42 IfSG)"]:
        t.textLine(line)
    c.drawText(t)
    y -= 38*mm
    
    _section_title(c, y, "ANGABEN")
    y -= 8*mm
    _field(c, MARGIN, y, 100*mm, "Betrieb")
    _field(c, MARGIN + 102*mm, y, 63*mm, "Datum")
    y -= 11*mm
    _field(c, MARGIN, y, 100*mm, "Belehrender")
    _field(c, MARGIN + 102*mm, y, 63*mm, "Nächste Belehrung")
    y -= 15*mm
    
    _section_title(c, y, "INHALTE: Tätigkeitsverbote bei")
    y -= 8*mm
    
    for erk in ["Akute infektiöse Gastroenteritis (Durchfall, Erbrechen)",
                "Typhus abdominalis / Paratyphus", "Shigellose (Bakterienruhr)",
                "Cholera", "Hepatitis A oder E (Gelbsucht)",
                "Verdacht einer dieser Erkrankungen",
                "Salmonellose", "EHEC (Escherichia coli)",
                "Infizierte Wunden / Hautkrankheiten"]:
        c.setStrokeColor(HexColor("#999999"))
        c.rect(MARGIN + 2*mm, y - 3.5*mm, 3.5*mm, 3.5*mm, fill=0, stroke=1)
        c.setFont("Helvetica", 8)
        c.setFillColor(DARK)
        c.drawString(MARGIN + 9*mm, y - 3*mm, erk)
        y -= 5*mm
    y -= 3*mm
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, "Weitere Pflichten:")
    y -= 6*mm
    for w in ["Meldepflicht bei Krankheit (sofort Arbeitgeber)",
              "Tätigkeitsverbot bis ärztliche Freigabe",
              "Händewaschen, saubere Arbeitskleidung, Handschuhe",
              "Beschäftigungsverbot auch bei Kontakt zu Erkrankten"]:
        c.setStrokeColor(HexColor("#999999"))
        c.rect(MARGIN + 2*mm, y - 3.5*mm, 3.5*mm, 3.5*mm, fill=0, stroke=1)
        c.setFont("Helvetica", 8)
        c.setFillColor(DARK)
        c.drawString(MARGIN + 9*mm, y - 3*mm, w)
        y -= 5*mm
    
    c.showPage()
    _header(c, "IfSG Folgebelehrung", "Teilnehmer", 2)
    _footer(c)
    y = PAGE_H - 35*mm
    
    c.setFillColor(YELLOW_BG)
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    c.rect(MARGIN, y - 25*mm, PAGE_W - 2*MARGIN, 25*mm, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 4*mm, y - 6*mm, "Erklärung der Teilnehmer")
    c.setFont("Helvetica", 8)
    t = c.beginText(MARGIN + 4*mm, y - 12*mm)
    t.setLeading(10)
    for line in ["• Belehrung erhalten und verstanden",
                 "• Keine Tätigkeitsverbote nach § 42 IfSG",
                 "• Bei Symptomen Arbeitgeber unverzüglich informieren",
                 "• Gültige Erstbelehrung vorhanden"]:
        t.textLine(line)
    c.drawText(t)
    y -= 32*mm
    
    _section_title(c, y, "TEILNEHMER")
    y -= 10*mm
    
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 8)
    for x, label in [(MARGIN + 2*mm, "Nr."), (MARGIN + 10*mm, "Name"),
                      (MARGIN + 58*mm, "Geburtsdatum"), (MARGIN + 85*mm, "Erstbel."),
                      (MARGIN + 108*mm, "Tätigkeit"), (MARGIN + 135*mm, "Unterschrift")]:
        c.drawString(x, y, label)
    c.setStrokeColor(ORANGE)
    c.line(MARGIN, y - 2*mm, PAGE_W - MARGIN, y - 2*mm)
    y -= 6*mm
    
    for i in range(1, 22):
        row_h = 9*mm
        c.setStrokeColor(GRAY_LIGHT)
        c.line(MARGIN, y - row_h + 1*mm, PAGE_W - MARGIN, y - row_h + 1*mm)
        c.setFillColor(GRAY_DARK)
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN + 2*mm, y - 4*mm, str(i))
        for x in [MARGIN + 8*mm, MARGIN + 56*mm, MARGIN + 83*mm, MARGIN + 106*mm, MARGIN + 133*mm]:
            c.line(x, y, x, y - row_h + 1*mm)
        y -= row_h
    
    return _finalize(c, buf)


def generate_reinigungsplan():
    c, buf = _new_canvas()
    _header(c, "Reinigungs- & Desinfektionsplan", "LMHV § 3 · VO 852/2004", 1)
    _footer(c, right_text="Monatlich führen · 2 Jahre aufbewahren")
    
    y = PAGE_H - 33*mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, y, "Betrieb:")
    c.setStrokeColor(HexColor("#CCCCCC"))
    c.rect(MARGIN + 18*mm, y - 5*mm, 80*mm, 5*mm, fill=0, stroke=1)
    c.drawString(MARGIN + 102*mm, y, "Monat/Jahr:")
    c.rect(MARGIN + 128*mm, y - 5*mm, 55*mm, 5*mm, fill=0, stroke=1)
    y -= 12*mm
    
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN, y, "Reinigungs- und Desinfektionsplan")
    y -= 6*mm
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY_DARK)
    c.drawString(MARGIN, y, "Was · Wann · Womit · Wie · Wer")
    y -= 8*mm
    
    col_widths = [40*mm, 22*mm, 28*mm, 38*mm, 25*mm, 32*mm]
    headers = ["Was", "Wann", "Womit", "Wie", "Einwirkzeit", "Wer"]
    
    c.setFillColor(DARK)
    c.rect(MARGIN, y - 7*mm, PAGE_W - 2*MARGIN, 7*mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    x = MARGIN + 2*mm
    for h, w in zip(headers, col_widths):
        c.drawString(x, y - 5*mm, h)
        x += w
    y -= 7*mm
    
    eintraege = [
        ("KÜCHE", None, None, None, None, None),
        ("Arbeitsflächen", "Nach Nutzung", "Allzweckreiniger", "Absprühen, abwischen", "-", ""),
        ("Schneidbretter", "Nach Nutzung", "Heißes Spülwasser", "Spülmaschine 65°C+", "-", ""),
        ("Messer", "Nach Nutzung", "Desinfektion", "Tauchen", "5 Min", ""),
        ("Herd", "Täglich", "Backofenreiniger", "Einsprühen, abwischen", "10 Min", ""),
        ("Backofen innen", "Wöchentlich", "Backofenreiniger", "Einsprühen", "30 Min", ""),
        ("Fritteuse", "Fettwechsel", "Spezialreiniger", "Einkochen", "-", ""),
        ("Dunstabzug Filter", "Monatlich", "Fettlöser", "Einweichen", "2 Std", ""),
        ("Kühlschrank innen", "Wöchentlich", "Lebensmittelsicher", "Auswischen", "-", ""),
        ("Böden Küche", "Schichtende", "Desinf. Reiniger", "Wischen", "5 Min", ""),
        ("Abfluss", "Wöchentlich", "Abflussreiniger", "Einfüllen", "30 Min", ""),
        ("SERVICE", None, None, None, None, None),
        ("Tische", "Nach Gast", "Allzweckreiniger", "Abwischen", "-", ""),
        ("Theke/Bar", "Mehrfach tägl.", "Allzweckreiniger", "Abwischen", "-", ""),
        ("Zapfanlage", "Täglich", "Hersteller-Mittel", "Spülen", "n. Anl.", ""),
        ("Gläser", "Nach Nutzung", "Spülmaschine", "65°C+ Klarspüler", "-", ""),
        ("Böden Gastraum", "Täglich", "Bodenreiniger", "Wischen", "-", ""),
        ("SANITÄR", None, None, None, None, None),
        ("Toilettenbecken", "Täglich", "WC-Reiniger", "Bürsten", "-", ""),
        ("Waschbecken", "Täglich", "Sanitärreiniger", "Abwischen", "-", ""),
        ("Böden Toiletten", "Täglich", "Desinf. Reiniger", "Wischen", "5 Min", ""),
        ("LAGER", None, None, None, None, None),
        ("Regale", "Monatlich", "Allzweckreiniger", "Abwischen", "-", ""),
        ("Müllbereich", "Leerung", "Desinfektion", "Ausspülen", "5 Min", ""),
    ]
    
    for e in eintraege:
        if e[1] is None:
            c.setFillColor(ORANGE)
            c.rect(MARGIN, y - 5*mm, PAGE_W - 2*MARGIN, 5*mm, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(MARGIN + 2*mm, y - 3.5*mm, e[0])
            y -= 5*mm
            continue
        if y < 20*mm:
            c.showPage()
            _header(c, "Reinigungsplan", "Fortsetzung", 2)
            _footer(c)
            y = PAGE_H - 33*mm
        c.setStrokeColor(GRAY_LIGHT)
        c.line(MARGIN, y - 6*mm, PAGE_W - MARGIN, y - 6*mm)
        c.setFillColor(DARK)
        c.setFont("Helvetica", 8)
        x = MARGIN + 2*mm
        for text, w in zip(e, col_widths):
            max_chars = int((w - 4*mm) / (1.5*mm))
            display = text[:max_chars] if len(text) > max_chars else text
            c.drawString(x, y - 4*mm, display)
            x += w
        y -= 6*mm
    
    return _finalize(c, buf)


def generate_temperaturkontrolle():
    c, buf = _new_canvas(landscape_mode=True)
    pw, ph = landscape(A4)
    m = 12 * mm
    _header(c, "Temperaturkontroll-Liste", "HACCP · VO 852/2004", 1, pw, ph, m)
    _footer(c, right_text="Täglich führen", page_w=pw, page_h=ph, margin_val=m)
    
    y = ph - 28*mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(m, y, "Betrieb:")
    c.setStrokeColor(HexColor("#CCCCCC"))
    c.rect(m + 15*mm, y - 5*mm, 80*mm, 5*mm, fill=0, stroke=1)
    c.drawString(m + 102*mm, y, "Monat:")
    c.rect(m + 120*mm, y - 5*mm, 60*mm, 5*mm, fill=0, stroke=1)
    c.drawString(m + 188*mm, y, "Verantw:")
    c.rect(m + 210*mm, y - 5*mm, 60*mm, 5*mm, fill=0, stroke=1)
    y -= 12*mm
    
    c.setFillColor(RED_BG)
    c.setStrokeColor(HexColor("#DC2626"))
    c.setLineWidth(1.2)
    c.rect(m, y - 16*mm, pw - 2*m, 16*mm, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(m + 3*mm, y - 4*mm, "⚠ Sollwerte")
    c.setFont("Helvetica", 8)
    werte_text = "TK: -18°C · Fleisch/Fisch frisch: max +4°C · Hackfleisch: max +2°C · Milch: max +7°C · Warmhaltung: min +65°C"
    c.drawString(m + 3*mm, y - 10*mm, werte_text)
    y -= 22*mm
    
    geraete = ["Kühlschrank 1", "Kühlschrank 2", "Kühlschrank Theke",
               "Kühlschrank Getränke", "Tiefkühltruhe 1", "Tiefkühltruhe 2",
               "Kühlhaus", "Salatkühlung"]
    
    day_col_w = (pw - 2*m - 55*mm) / 31
    c.setFillColor(DARK)
    c.rect(m, y - 7*mm, pw - 2*m, 7*mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(m + 2*mm, y - 5*mm, "Gerät \\ Tag")
    c.setFont("Helvetica-Bold", 7)
    for day in range(1, 32):
        x = m + 55*mm + (day - 1) * day_col_w
        c.drawString(x + 0.5*mm, y - 5*mm, str(day))
    y -= 7*mm
    
    for i, geraet in enumerate(geraete):
        total_row = 11*mm
        if i % 2 == 0:
            c.setFillColor(GRAY_VERY_LIGHT)
            c.rect(m, y - total_row, pw - 2*m, total_row, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(m + 2*mm, y - 4*mm, geraet)
        c.setFont("Helvetica", 7)
        c.setFillColor(GRAY_DARK)
        c.drawString(m + 2*mm, y - 4*mm - 6*mm + 1*mm, "°C | Kürzel")
        c.setStrokeColor(HexColor("#CCCCCC"))
        for day in range(32):
            x = m + 55*mm + day * day_col_w
            c.line(x, y, x, y - total_row)
        c.line(m, y - 6*mm, pw - m, y - 6*mm)
        y -= total_row
    
    c.setStrokeColor(HexColor("#CCCCCC"))
    c.line(m, y, pw - m, y)
    
    return _finalize(c, buf)


def _anweisung_seite(c, name, hersteller, gefahren, schutz, erste_hilfe, entsorgung, page_num):
    _header(c, "Betriebsanweisung Gefahrstoffe", "§ 14 GefStoffV", page_num)
    _footer(c, right_text="Muss am Arbeitsplatz aushängen")
    
    y = PAGE_H - 33*mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN, y, name.upper())
    y -= 6*mm
    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN, y, f"Hersteller: {hersteller}")
    y -= 3*mm
    c.setStrokeColor(ORANGE)
    c.setLineWidth(2)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 8*mm
    
    def box(title, color_bg, color_border, lines):
        nonlocal y
        h = 8*mm + len(lines) * 4*mm + 2*mm
        c.setFillColor(color_bg)
        c.setStrokeColor(color_border)
        c.setLineWidth(1.2)
        c.rect(MARGIN, y - h, PAGE_W - 2*MARGIN, h, fill=1, stroke=1)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN + 4*mm, y - 6*mm, title)
        c.setFont("Helvetica", 9)
        yt = y - 11*mm
        for line in lines:
            c.drawString(MARGIN + 4*mm, yt, line)
            yt -= 4*mm
        y -= h + 3*mm
    
    box("1. Anwendungsbereich", BLUE_BG, HexColor("#2563EB"),
        [f"• {name} ist ein Reinigungsmittel für die Gastronomie",
         "• Nur für beschriebene Anwendungen einsetzen",
         "• Nur von unterwiesenem Personal verwenden"])
    box("⚠ 2. Gefahren", RED_BG, RED_TEXT, gefahren)
    box("✓ 3. Schutzmaßnahmen", GREEN_BG, HexColor("#059669"), schutz)
    box("🚨 4. Verhalten im Gefahrfall", YELLOW_BG, ORANGE,
        ["• Augenkontakt: 15 Min mit Wasser spülen, Arzt!",
         "• Hautkontakt: Kleidung entfernen, mit Wasser spülen",
         "• Verschlucken: KEIN Erbrechen, sofort Notarzt 112",
         "• Einatmen: An frische Luft",
         "• Giftnotruf Berlin: 030 19240"])
    box("+ 5. Erste Hilfe", HexColor("#F5F5F5"), GRAY_DARK, erste_hilfe)
    box("♻ 6. Entsorgung", HexColor("#F5F5F5"), GRAY_DARK, entsorgung)


def generate_betriebsanweisung():
    c, buf = _new_canvas()
    _header(c, "Betriebsanweisung Gefahrstoffe", "§ 14 GefStoffV", 1)
    _footer(c)
    y = PAGE_H - 45*mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(MARGIN, y, "Betriebsanweisung")
    y -= 10*mm
    c.setFillColor(ORANGE)
    c.drawString(MARGIN, y, "Gefahrstoffe")
    y -= 15*mm
    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica", 12)
    c.drawString(MARGIN, y, "Muster-Betriebsanweisungen für typische Reinigungsmittel")
    y -= 6*mm
    c.drawString(MARGIN, y, "in der Gastronomie nach § 14 GefStoffV")
    y -= 15*mm
    
    c.setFillColor(RED_BG)
    c.setStrokeColor(RED_TEXT)
    c.setLineWidth(1.5)
    c.rect(MARGIN, y - 40*mm, PAGE_W - 2*MARGIN, 40*mm, fill=1, stroke=1)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN + 4*mm, y - 6*mm, "⚠ Rechtliche Pflicht nach § 14 GefStoffV")
    c.setFont("Helvetica", 9)
    t = c.beginText(MARGIN + 4*mm, y - 12*mm)
    t.setLeading(11)
    for line in ["Schriftliche Betriebsanweisung für jeden Gefahrstoff erforderlich.",
                 "Bei Missachtung: Bußgeld bis 25.000 €.",
                 "",
                 "• Am Arbeitsplatz aushängen",
                 "• Mitarbeiter mind. 1x jährlich unterweisen",
                 "• In verständlicher Sprache",
                 "• Bei neuen Produkten: vor erster Verwendung"]:
        t.textLine(line)
    c.drawText(t)
    
    c.showPage()
    
    _anweisung_seite(c, "Fettlöser / Grillreiniger", "Nach Sicherheitsdatenblatt",
        ["• Stark alkalisch (pH > 11)", "• Schwere Verätzungen Haut/Augen",
         "• Giftig bei Verschlucken", "• Dämpfe reizen Atemwege"],
        ["• Nitril-Handschuhe", "• Schutzbrille mit Seitenschutz",
         "• FFP2-Maske beim Sprühen", "• Langärmelige Kleidung",
         "• Gut lüften", "• NIE mit anderen Reinigern mischen"],
        ["• Hautkontakt: 15 Min Wasser+Seife", "• Augen: 15 Min spülen, Notarzt",
         "• Verschlucken: Mund spülen, NICHT erbrechen, Notarzt",
         "• Einatmen: Frische Luft, Arzt bei Beschwerden"],
        ["• Reste: Sondermüll", "• Leere Gebinde: Nach Absprache Entsorger",
         "• Verschüttetes: Lappen, viel Wasser"],
        2)
    c.showPage()
    
    _anweisung_seite(c, "Flächendesinfektion", "Nach Sicherheitsdatenblatt",
        ["• Leicht entzündbar - Brandgefahr!", "• Dämpfe reizen Schleimhäute",
         "• Entzündet sich bei Zündquellen", "• Hautkontakt trocknet aus"],
        ["• Keine offenen Flammen!", "• Keine Zündquellen beim Sprühen",
         "• Gut lüften", "• Nicht auf heiße Flächen",
         "• Handschuhe", "• 1 m Abstand zu Lebensmitteln"],
        ["• Hautkontakt: Wasser, Hautpflege", "• Augen: 15 Min spülen",
         "• Verschlucken: Viel Wasser trinken, Arzt",
         "• Einatmen: Frische Luft"],
        ["• Kleine Mengen: Wasser nachspülen",
         "• Leere Flaschen: Gelber Sack",
         "• Verschüttetes: Saugfähiges Material"],
        3)
    c.showPage()
    
    _anweisung_seite(c, "Sanitärreiniger (säurehaltig)", "Nach Sicherheitsdatenblatt",
        ["• Säure (pH < 4)", "• Reizt Haut/Augen/Atemwege",
         "• Verätzungen bei Kontakt",
         "• LEBENSGEFAHR bei Mischung mit Chlor!"],
        ["• Gummihandschuhe", "• Schutzbrille empfohlen",
         "• NIEMALS mit anderen Reinigern mischen!",
         "• Gut lüften", "• Einwirkzeit einhalten",
         "• Gründlich nachspülen"],
        ["• Haut: 10 Min Wasser spülen", "• Augen: 15 Min spülen, Arzt",
         "• Verschlucken: Wasser, NICHT erbrechen, Notarzt",
         "• Einatmen: Frische Luft, bei Atemnot Notarzt"],
        ["• Nicht konzentriert in Ausguss",
         "• Mit viel Wasser verdünnen",
         "• Gebinde: Wertstoffhof"],
        4)
    c.showPage()
    
    _anweisung_seite(c, "Backofenreiniger", "Nach Sicherheitsdatenblatt",
        ["• STARK ätzend (Natriumhydroxid)",
         "• Schwere Verätzungen", "• Augen: Erblindungsgefahr!",
         "• Aerosol sehr reizend"],
        ["• Lange Chemikalien-Handschuhe",
         "• Schutzbrille/Gesichtsschutz", "• FFP2-Maske beim Sprühen",
         "• Langärmelige Kleidung", "• Nur bei kaltem Ofen",
         "• Fenster öffnen"],
        ["• Haut: Kleidung weg, 15 Min Wasser",
         "• Augen: 20 Min spülen, Notarzt (Erblindung!)",
         "• Verschlucken: Wasser, Notarzt 112",
         "• Einatmen: Frische Luft, bei Atemnot Notarzt"],
        ["• Sondermüll", "• Gebinde: Nach Absprache Entsorger",
         "• Verschüttetes: Saugfähiges Material"],
        5)
    c.showPage()
    
    _anweisung_seite(c, "Spülmaschinen-Reiniger", "Nach Sicherheitsdatenblatt",
        ["• Stark alkalisch (pH > 11)", "• Ätzend für Haut/Augen",
         "• Giftig bei Verschlucken", "• Dämpfe reizen"],
        ["• Handschuhe beim Befüllen",
         "• Schutzbrille bei Konzentrat",
         "• Dosierpumpe nutzen",
         "• Nicht mit bloßen Händen",
         "• Maschine aus beim Befüllen"],
        ["• Haut: 15 Min Wasser", "• Augen: 15 Min, Arzt",
         "• Verschlucken: Wasser, Notarzt",
         "• Einatmen: Frische Luft"],
        ["• Reste nicht in Ausguss",
         "• Gebinde: Nach Absprache",
         "• Verschüttetes: Wasser verdünnen"],
        6)
    
    return _finalize(c, buf)


TEMPLATES = {
    "checkliste": {
        "generator": generate_checkliste,
        "name": "Pflichten-Checkliste Gastronomie",
        "beschreibung": "Alle Compliance-Pflichten auf einen Blick - Rechtsstand 2026",
        "dateiname": "complio_pflichten_checkliste.pdf",
        "kategorie": "Checklisten",
    },
    "verbandbuch": {
        "generator": generate_verbandbuch,
        "name": "Verbandbuch / Erste-Hilfe-Meldeblock",
        "beschreibung": "Nach DGUV V1 § 24 - 5 Jahre Aufbewahrung",
        "dateiname": "complio_verbandbuch.pdf",
        "kategorie": "Formulare",
    },
    "unterweisung": {
        "generator": generate_unterweisung,
        "name": "Unterweisungsnachweis",
        "beschreibung": "Jährliche Pflicht nach § 12 ArbSchG",
        "dateiname": "complio_unterweisungsnachweis.pdf",
        "kategorie": "Nachweise",
    },
    "haccp_nachweis": {
        "generator": generate_haccp_nachweis,
        "name": "HACCP-Schulungsnachweis",
        "beschreibung": "VO (EG) 852/2004 - Lebensmittelhygiene-Schulung",
        "dateiname": "complio_haccp_nachweis.pdf",
        "kategorie": "Nachweise",
    },
    "ifsg": {
        "generator": generate_ifsg_belehrung,
        "name": "IfSG § 43 Folgebelehrung",
        "beschreibung": "Infektionsschutz - alle 24 Monate",
        "dateiname": "complio_ifsg_belehrung.pdf",
        "kategorie": "Nachweise",
    },
    "reinigungsplan": {
        "generator": generate_reinigungsplan,
        "name": "Reinigungs- & Desinfektionsplan",
        "beschreibung": "Monatlicher HACCP-Nachweis - LMHV § 3",
        "dateiname": "complio_reinigungsplan.pdf",
        "kategorie": "Formulare",
    },
    "temperatur": {
        "generator": generate_temperaturkontrolle,
        "name": "Temperaturkontroll-Liste",
        "beschreibung": "Täglicher Kühlkettennachweis - HACCP Pflicht",
        "dateiname": "complio_temperaturkontrolle.pdf",
        "kategorie": "Formulare",
    },
    "gefahrstoffe": {
        "generator": generate_betriebsanweisung,
        "name": "Betriebsanweisung Gefahrstoffe",
        "beschreibung": "5 Muster nach § 14 GefStoffV",
        "dateiname": "complio_gefahrstoffe.pdf",
        "kategorie": "Betriebsanweisungen",
    },
}
