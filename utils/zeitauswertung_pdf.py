"""
PDF-Generator fuer monatliche Zeitauswertungen (AZK).
Erzeugt eine uebersichtliche, MiLoG-konforme Zeiterfassungs-PDF.
"""

from fpdf import FPDF
from datetime import date
import io
from utils.branding import BRAND_COMPANY_NAME


MONATSNAMEN = {
    1: 'Januar', 2: 'Februar', 3: 'Maerz', 4: 'April',
    5: 'Mai', 6: 'Juni', 7: 'Juli', 8: 'August',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Dezember'
}

# Farben
FARBE_HEADER = (30, 80, 140)       # Dunkelblau
FARBE_SUBHEADER = (60, 120, 180)   # Mittelblau
FARBE_HELLGRAU = (245, 245, 245)   # Tabellen-Zebrastreifen
FARBE_WEISS = (255, 255, 255)
FARBE_DUNKELGRAU = (80, 80, 80)
FARBE_SCHWARZ = (0, 0, 0)
FARBE_GRUEN = (34, 139, 34)
FARBE_ROT = (180, 30, 30)
FARBE_ORANGE = (200, 100, 0)
FARBE_BLAU_HELL = (220, 235, 255)


def h_zu_hhmm(stunden: float) -> str:
    """Konvertiert Dezimalstunden in HH:MM Format (auch negativ)."""
    if stunden is None:
        return '00:00'
    negativ = stunden < 0
    stunden_abs = abs(stunden)
    h = int(stunden_abs)
    m = round((stunden_abs - h) * 60)
    if m == 60:
        h += 1
        m = 0
    prefix = '-' if negativ else ''
    return f"{prefix}{h:02d}:{m:02d}"


def erstelle_azk_pdf(
    mitarbeiter: dict,
    monat: int,
    jahr: int,
    ergebnis: dict,
    saldo_kumuliert: float,
    urlaub: dict,
    betrieb_name: str = BRAND_COMPANY_NAME,
) -> bytes:
    """
    Erstellt eine uebersichtliche PDF-Zeitauswertung fuer einen Mitarbeiter.

    Args:
        mitarbeiter: Dict mit vorname, nachname, personalnummer, monatliche_soll_stunden
        monat: Monatsnummer (1-12)
        jahr: Jahr
        ergebnis: Rueckgabe von berechne_azk_monat()
        saldo_kumuliert: Kumulierter AZK-Saldo aus berechne_azk_kumuliert()
        urlaub: Rueckgabe von berechne_urlaubskonto()
        betrieb_name: Name des Betriebs

    Returns:
        PDF als bytes
    """
    pdf = FPDF(orientation='L', unit='mm', format='A4')  # Querformat fuer Tabelle
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(12, 12, 12)

    name = f"{mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}"
    personalnr = mitarbeiter.get('personalnummer', '-')
    monat_name = MONATSNAMEN.get(monat, str(monat))
    erstellt_am = date.today().strftime('%d.%m.%Y')

    # -- Kopfzeile ---------------------------------------------
    pdf.set_fill_color(*FARBE_HEADER)
    pdf.rect(12, 12, 273, 18, 'F')

    def safe(text):
        """Ersetzt Sonderzeichen durch latin-1-kompatible Aequivalente."""
        if not text:
            return ''
        repl = {
            '\u2013': '-', '\u2014': '-', '\u2019': "'",
            '\u201c': '"', '\u201d': '"', '\u2026': '...',
            '\u00e4': 'ae', '\u00f6': 'oe', '\u00fc': 'ue',
            '\u00c4': 'Ae', '\u00d6': 'Oe', '\u00dc': 'Ue',
            '\u00df': 'ss', '\u00e9': 'e', '\u00e8': 'e',
            '\u00e0': 'a', '\u00e1': 'a', '\u00fa': 'u',
            '\u00f3': 'o', '\u00ed': 'i', '\u00fc': 'ue',
        }
        for k, v in repl.items():
            text = text.replace(k, v)
        return text.encode('latin-1', errors='replace').decode('latin-1')

    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*FARBE_WEISS)
    pdf.set_xy(15, 14)
    pdf.cell(180, 8, safe(f'Arbeitszeitkonto (AZK) - {monat_name} {jahr}'), ln=0)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(195, 14)
    pdf.cell(88, 4, safe(betrieb_name), ln=0, align='R')
    pdf.set_xy(195, 19)
    pdf.cell(88, 4, f'Erstellt: {erstellt_am}', ln=0, align='R')

    # -- Mitarbeiter-Info --------------------------------------
    pdf.set_fill_color(*FARBE_BLAU_HELL)
    pdf.rect(12, 32, 273, 14, 'F')
    pdf.set_text_color(*FARBE_SCHWARZ)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_xy(15, 34)
    pdf.cell(100, 6, safe(f'Mitarbeiter: {name}'), ln=0)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_xy(120, 34)
    pdf.cell(80, 6, f'Personal-Nr.: {personalnr}', ln=0)
    pdf.set_xy(210, 34)
    pdf.cell(73, 6, safe(f'Abrechnungsmonat: {monat_name} {jahr}'), ln=0, align='R')

    # -- Kennzahlen-Box ----------------------------------------
    pdf.set_xy(12, 48)
    box_y = 48
    box_h = 22
    box_w = 60

    kennzahlen = [
        ('Ist-Stunden', h_zu_hhmm(ergebnis.get('ist_stunden', 0))),
        ('Soll-Stunden', h_zu_hhmm(ergebnis.get('soll_stunden', 0))),
        ('Monatssaldo', h_zu_hhmm(ergebnis.get('differenz', 0))),
        ('Kum. AZK-Saldo', h_zu_hhmm(saldo_kumuliert)),
    ]

    for i, (label, wert) in enumerate(kennzahlen):
        x = 12 + i * (box_w + 3)
        diff_val = ergebnis.get('differenz', 0)
        kum_val = saldo_kumuliert

        # Farbe fuer Saldo
        if label == 'Monatssaldo':
            fill = FARBE_GRUEN if diff_val >= 0 else FARBE_ROT
            text_col = FARBE_WEISS
        elif label == 'Kum. AZK-Saldo':
            fill = FARBE_GRUEN if kum_val >= 0 else FARBE_ROT
            text_col = FARBE_WEISS
        else:
            fill = FARBE_SUBHEADER
            text_col = FARBE_WEISS

        pdf.set_fill_color(*fill)
        pdf.rect(x, box_y, box_w, box_h, 'F')
        pdf.set_text_color(*text_col)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_xy(x + 2, box_y + 3)
        pdf.cell(box_w - 4, 5, label, align='C')
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_xy(x + 2, box_y + 9)
        pdf.cell(box_w - 4, 9, wert, align='C')

    # Abwesenheiten rechts
    krank_h = ergebnis.get('krank_stunden', 0)
    urlaub_h = ergebnis.get('urlaub_stunden', 0)
    urlaub_tage = ergebnis.get('urlaub_genommen', 0)

    pdf.set_text_color(*FARBE_DUNKELGRAU)
    pdf.set_font('Helvetica', '', 9)
    info_x = 12 + 4 * (box_w + 3) + 3
    pdf.set_xy(info_x, box_y + 2)

    if krank_h > 0:
        pdf.set_text_color(*FARBE_ORANGE)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(50, 5, f'Krank (LFZ): {h_zu_hhmm(krank_h)}', ln=1)
        pdf.set_xy(info_x, pdf.get_y())
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*FARBE_DUNKELGRAU)
        pdf.cell(50, 4, 'Saldo neutralisiert (EFZG S.4)', ln=1)

    if urlaub_h > 0:
        pdf.set_xy(info_x, pdf.get_y() + 1)
        pdf.set_text_color(*FARBE_SUBHEADER)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(50, 5, f'Urlaub: {urlaub_tage} Tage / {h_zu_hhmm(urlaub_h)}', ln=1)

    # Urlaubskonto
    pdf.set_xy(info_x, box_y + 13)
    pdf.set_text_color(*FARBE_DUNKELGRAU)
    pdf.set_font('Helvetica', '', 8)
    u_gesamt = urlaub.get('gesamt_anspruch', 0)
    u_genommen = urlaub.get('genommen', 0)
    u_offen = urlaub.get('offen', 0)
    pdf.cell(70, 4, f'Urlaub: {u_gesamt} Tage Anspruch | {u_genommen} genommen | {u_offen} offen', ln=1)

    # -- Tagesdetails-Tabelle ----------------------------------
    pdf.set_text_color(*FARBE_SCHWARZ)
    pdf.set_xy(12, 73)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(*FARBE_HEADER)
    pdf.set_text_color(*FARBE_WEISS)

    # Spaltenbreiten (Querformat A4 = 297mm - 24mm Rand = 273mm)
    cols = [
        ('Datum',    28),
        ('WT',       12),
        ('Typ',      22),
        ('Start',    18),
        ('Ende',     18),
        ('Pause',    18),
        ('Ist',      20),
        ('Soll',     20),
        ('Differenz',22),
        ('Kum. Saldo',22),
        ('Kommentar', 73),
    ]

    row_h = 6
    for col_name, col_w in cols:
        pdf.cell(col_w, row_h, col_name, border=0, align='C', fill=True)
    pdf.ln()

    # Tageszeilen
    tage = ergebnis.get('tage', [])
    pdf.set_font('Helvetica', '', 8)

    for i, t in enumerate(tage):
        # Zebrastreifen
        if i % 2 == 0:
            pdf.set_fill_color(*FARBE_HELLGRAU)
        else:
            pdf.set_fill_color(*FARBE_WEISS)

        typ = t.get('typ', 'arbeit')
        diff_h = t.get('diff_h', 0)

        # Textfarbe nach Typ
        if typ == 'krank':
            pdf.set_text_color(*FARBE_ORANGE)
        elif typ == 'urlaub':
            pdf.set_text_color(*FARBE_SUBHEADER)
        elif diff_h < -0.01:
            pdf.set_text_color(*FARBE_ROT)
        elif diff_h > 0.01:
            pdf.set_text_color(*FARBE_GRUEN)
        else:
            pdf.set_text_color(*FARBE_SCHWARZ)

        typ_label = {
            'arbeit': 'Arbeit',
            'krank': 'Krank LFZ',
            'urlaub': 'Urlaub',
            'frei': 'Frei',
        }.get(typ, typ)

        kommentar = t.get('kommentar', '') or ''
        if len(kommentar) > 40:
            kommentar = kommentar[:38] + '...'
        kommentar = safe(kommentar)

        pause_str = f"{t.get('pause_min', 0)} min" if t.get('pause_min', 0) > 0 else '-'

        zeile = [
            (safe(t.get('datum_fmt', '')),      28),
            (safe(t.get('wochentag', '')),       12),
            (safe(typ_label),                    22),
            (safe(t.get('start', '-')),          18),
            (safe(t.get('ende', '-')),           18),
            (pause_str,                          18),
            (safe(t.get('ist_hhmm', '00:00')),   20),
            (safe(t.get('soll_hhmm', '00:00')),  20),
            (safe(t.get('diff_hhmm', '00:00')),  22),
            (safe(t.get('kum_saldo_hhmm', '00:00')), 22),
            (kommentar,                          73),
        ]

        for val, w in zeile:
            pdf.cell(w, row_h, str(val), border=0, align='C', fill=True)
        pdf.ln()

        # Neue Seite wenn noetig
        if pdf.get_y() > 185:
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(*FARBE_HEADER)
            pdf.set_text_color(*FARBE_WEISS)
            for col_name, col_w in cols:
                pdf.cell(col_w, row_h, col_name, border=0, align='C', fill=True)
            pdf.ln()
            pdf.set_font('Helvetica', '', 8)

    # -- Fusszeile ----------------------------------------------
    pdf.set_text_color(*FARBE_DUNKELGRAU)
    pdf.set_font('Helvetica', 'I', 7)
    pdf.set_xy(12, pdf.get_y() + 4)
    pdf.cell(273, 4,
             safe(f'Dokument erstellt am {erstellt_am} | MiLoG-konforme Zeiterfassung | {betrieb_name} | '
             f'Mitarbeiter: {name} (Nr. {personalnr}) | {monat_name} {jahr}'),
             align='C')

    # -- Unterschriften-Zeile ----------------------------------
    pdf.set_xy(12, pdf.get_y() + 8)
    pdf.set_text_color(*FARBE_SCHWARZ)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(100, 4, '________________________________', ln=0)
    pdf.cell(73, 4, '', ln=0)
    pdf.cell(100, 4, '________________________________', ln=1)
    pdf.set_xy(12, pdf.get_y())
    pdf.cell(100, 4, f'Datum, Unterschrift Mitarbeiter', ln=0)
    pdf.cell(73, 4, '', ln=0)
    pdf.cell(100, 4, 'Datum, Unterschrift Arbeitgeber', ln=1)

    output = pdf.output(dest='S')
    if isinstance(output, str):
        return output.encode('latin-1')
    return bytes(output)
