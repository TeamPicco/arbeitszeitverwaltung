"""
Complio Vertrags-Generator Basis.
Professionelle Arbeitsverträge nach BGB, NachwG, MiLoG 2026.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime
import io


DARK = HexColor("#1a1a1a")
GRAY_DARK = HexColor("#4a4a4a")
GRAY_MED = HexColor("#767676")
GRAY_LIGHT = HexColor("#cccccc")
GRAY_BG = HexColor("#f5f5f5")
ACCENT = HexColor("#2c3e50")
ORANGE = HexColor("#F97316")

PAGE_W, PAGE_H = A4
MARGIN_L = 25 * mm
MARGIN_R = 25 * mm
MARGIN_T = 25 * mm
MARGIN_B = 25 * mm

CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R


class VertragPDF:
    def __init__(self, vertragstyp, betriebsdaten, mitarbeiterdaten, vertragsdaten, logo_bytes=None):
        self.vertragstyp = vertragstyp
        self.betrieb = betriebsdaten or {}
        self.arbeitnehmer = mitarbeiterdaten or {}
        self.daten = vertragsdaten or {}
        self.logo_bytes = logo_bytes

        self.buf = io.BytesIO()
        self.c = canvas.Canvas(self.buf, pagesize=A4)
        self.c.setAuthor("Complio")
        self.c.setTitle(self._get_title())

        self.page_num = 1
        self.y = PAGE_H - MARGIN_T

    def _get_title(self):
        titles = {
            "vollzeit": "Arbeitsvertrag",
            "teilzeit": "Arbeitsvertrag (Teilzeit)",
            "minijob": "Arbeitsvertrag (Minijob)",
            "aenderungsvertrag": "Änderungsvertrag"
        }
        return titles.get(self.vertragstyp, "Arbeitsvertrag")

    def _check_page(self, needed_space_mm):
        if self.y - needed_space_mm * mm < MARGIN_B + 15 * mm:
            self.new_page()

    def new_page(self):
        self._footer()
        self.c.showPage()
        self.page_num += 1
        self.y = PAGE_H - MARGIN_T

    def _footer(self):
        self.c.setFillColor(GRAY_MED)
        self.c.setFont("Helvetica", 8)
        self.c.drawRightString(PAGE_W - MARGIN_R, 15 * mm, f"Seite {self.page_num}")
        self.c.drawString(MARGIN_L, 15 * mm, "Erstellt mit Complio · getcomplio.de")

    def draw_cover(self):
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica-Bold", 28)
        self.c.drawString(MARGIN_L, self.y, self._get_title())

        untertitel = self.daten.get("untertitel", self._get_default_untertitel())
        if untertitel:
            self.c.setFillColor(GRAY_DARK)
            self.c.setFont("Helvetica", 10)
            self.c.drawString(MARGIN_L, self.y - 7 * mm, untertitel)

        if self.logo_bytes:
            try:
                from reportlab.lib.utils import ImageReader
                img = ImageReader(io.BytesIO(self.logo_bytes))
                img_w = 35 * mm
                img_h = 25 * mm
                self.c.drawImage(img, PAGE_W - MARGIN_R - img_w, self.y - 8 * mm,
                                 width=img_w, height=img_h, mask='auto',
                                 preserveAspectRatio=True, anchor='ne')
            except Exception:
                pass

        self.y -= 20 * mm
        self._draw_intro_box()
        self.y -= 8 * mm
        self._draw_parties_table()
        self.y -= 10 * mm

    def _get_default_untertitel(self):
        if self.vertragstyp == "aenderungsvertrag":
            beginn = self.daten.get("urspruenglicher_vertrag_datum", "")
            return f"zum bestehenden Arbeitsvertrag vom {beginn}" if beginn else ""
        return ""

    def _draw_intro_box(self):
        intro = self.daten.get("intro_text", self._get_default_intro())
        if not intro:
            return
        lines = self._wrap_text(intro, CONTENT_W - 10 * mm, "Helvetica", 9)
        box_height = len(lines) * 4.5 * mm + 6 * mm

        self.c.setFillColor(ACCENT)
        self.c.rect(MARGIN_L, self.y - box_height, 1.5, box_height, fill=1, stroke=0)

        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 9)
        text_y = self.y - 4 * mm
        for line in lines:
            self.c.drawString(MARGIN_L + 5 * mm, text_y, line)
            text_y -= 4.5 * mm
        self.y -= box_height

    def _get_default_intro(self):
        if self.vertragstyp == "aenderungsvertrag":
            datum = self.daten.get("urspruenglicher_vertrag_datum", "")
            return (f"Die nachfolgenden Regelungen treten ergänzend und abändernd zum "
                    f"bestehenden Arbeitsvertrag vom {datum} in Kraft. Alle nicht ausdrücklich "
                    f"geänderten Bestimmungen des ursprünglichen Arbeitsvertrages behalten ihre Gültigkeit.")
        if self.vertragstyp == "minijob":
            return ("Dieser Arbeitsvertrag regelt die Bedingungen einer geringfügig entlohnten "
                    "Beschäftigung (Minijob) gemäß § 8 Abs. 1 Nr. 1 SGB IV.")
        return ("Dieser Arbeitsvertrag regelt die Bedingungen des Arbeitsverhältnisses zwischen "
                "den unten genannten Parteien unter Berücksichtigung der gesetzlichen Bestimmungen "
                "(BGB, NachwG, ArbZG, MiLoG, BUrlG).")

    def _draw_parties_table(self):
        col_w = (CONTENT_W - 10 * mm) / 2

        self.c.setFillColor(GRAY_MED)
        self.c.setFont("Helvetica", 7.5)
        self.c.drawString(MARGIN_L, self.y, "A R B E I T G E B E R")
        self.c.drawString(MARGIN_L + col_w + 10 * mm, self.y, "A R B E I T N E H M E R I N")
        self.y -= 5 * mm

        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica-Bold", 11)
        firma = self.betrieb.get("firmenname", "Firma")
        an_name = f"{self.arbeitnehmer.get('vorname', '')} {self.arbeitnehmer.get('nachname', '')}".strip()
        self.c.drawString(MARGIN_L, self.y, firma)
        self.c.drawString(MARGIN_L + col_w + 10 * mm, self.y, an_name or "Name Arbeitnehmer/in")
        self.y -= 5 * mm

        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 9)

        ag_lines = []
        if self.betrieb.get("vertreten_durch"):
            ag_lines.append(f"vertreten durch {self.betrieb['vertreten_durch']}")
        if self.betrieb.get("anschrift_strasse"):
            ag_lines.append(self.betrieb["anschrift_strasse"])
        plz_ort = f"{self.betrieb.get('anschrift_plz', '')} {self.betrieb.get('anschrift_ort', '')}".strip()
        if plz_ort:
            ag_lines.append(plz_ort)

        an_lines = []
        if self.arbeitnehmer.get("strasse"):
            an_lines.append(self.arbeitnehmer["strasse"])
        an_plz_ort = f"{self.arbeitnehmer.get('plz', '')} {self.arbeitnehmer.get('ort', '')}".strip()
        if an_plz_ort:
            an_lines.append(an_plz_ort)

        max_lines = max(len(ag_lines), len(an_lines))
        for i in range(max_lines):
            if i < len(ag_lines):
                self.c.drawString(MARGIN_L, self.y, ag_lines[i])
            if i < len(an_lines):
                self.c.drawString(MARGIN_L + col_w + 10 * mm, self.y, an_lines[i])
            self.y -= 4.5 * mm

        self.y -= 2 * mm

        self.c.setFillColor(GRAY_MED)
        self.c.setFont("Helvetica-Oblique", 8.5)
        self.c.drawString(MARGIN_L, self.y, "— nachfolgend „Arbeitgeber\" —")
        self.c.drawString(MARGIN_L + col_w + 10 * mm, self.y, "— nachfolgend „Arbeitnehmerin\" —")
        self.y -= 4 * mm

    def paragraph(self, number, title, body_lines, space_before=6):
        total_h = 10 * mm
        for line in body_lines:
            total_h += 5 * mm
        self._check_page(total_h / mm + space_before)

        self.y -= space_before * mm

        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica-Bold", 10.5)
        self.c.drawString(MARGIN_L, self.y, f"§ {number}  {title}")

        self.c.setStrokeColor(GRAY_LIGHT)
        self.c.setLineWidth(0.5)
        self.c.line(MARGIN_L, self.y - 1.5 * mm, PAGE_W - MARGIN_R, self.y - 1.5 * mm)

        self.y -= 6 * mm

        self.c.setFillColor(DARK)

        for item in body_lines:
            if isinstance(item, tuple):
                typ, text = item
            else:
                typ, text = "p", item

            if typ == "sub":
                self._render_numbered_para(text)
            elif typ == "bullet":
                self._render_bullet(text)
            elif typ == "bold_line":
                self._render_bold_line(text)
            else:
                self._render_para(text)
            self.y -= 1.5 * mm

    def _render_para(self, text):
        lines = self._wrap_text(text, CONTENT_W, "Helvetica", 9.5)
        self.c.setFont("Helvetica", 9.5)
        for line in lines:
            self._check_page(5)
            self.c.drawString(MARGIN_L, self.y, line)
            self.y -= 4.5 * mm

    def _render_numbered_para(self, item):
        if isinstance(item, tuple):
            nummer, text = item
        else:
            import re
            m = re.match(r'^\((\d+)\)\s*(.*)', item, re.DOTALL)
            if m:
                nummer = m.group(1)
                text = m.group(2)
            else:
                nummer = ""
                text = item

        nummer_str = f"({nummer})" if nummer else ""
        indent = 8 * mm
        self.c.setFont("Helvetica", 9.5)

        if nummer_str:
            self.c.setFillColor(DARK)
            self.c.drawString(MARGIN_L, self.y, nummer_str)

        lines = self._wrap_text(text, CONTENT_W - indent, "Helvetica", 9.5)
        for line in lines:
            self._check_page(5)
            self.c.drawString(MARGIN_L + indent, self.y, line)
            self.y -= 4.5 * mm

    def _render_bullet(self, text):
        indent = 5 * mm
        self.c.setFont("Helvetica", 9.5)
        self.c.setFillColor(DARK)
        self.c.drawString(MARGIN_L + 2 * mm, self.y, "•")
        lines = self._wrap_text(text, CONTENT_W - indent, "Helvetica", 9.5)
        for line in lines:
            self._check_page(5)
            self.c.drawString(MARGIN_L + indent, self.y, line)
            self.y -= 4.5 * mm

    def _render_bold_line(self, text):
        self.c.setFont("Helvetica-Bold", 9.5)
        self.c.setFillColor(DARK)
        lines = self._wrap_text(text, CONTENT_W, "Helvetica-Bold", 9.5)
        for line in lines:
            self._check_page(5)
            self.c.drawString(MARGIN_L, self.y, line)
            self.y -= 4.5 * mm

    def _wrap_text(self, text, max_width, font, size):
        if not text:
            return [""]
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if stringWidth(test, font, size) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def signature_section(self):
        self._check_page(50)
        self.y -= 10 * mm

        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 9.5)
        ort = self.betrieb.get("anschrift_ort", "Leipzig")
        self.c.drawString(MARGIN_L, self.y, f"{ort}, den")

        self.y -= 25 * mm

        line_w = (CONTENT_W - 10 * mm) / 2
        self.c.setStrokeColor(DARK)
        self.c.setLineWidth(0.5)
        self.c.line(MARGIN_L, self.y, MARGIN_L + line_w, self.y)
        self.c.line(MARGIN_L + line_w + 10 * mm, self.y, PAGE_W - MARGIN_R, self.y)

        self.y -= 5 * mm

        self.c.setFont("Helvetica-Bold", 9)
        vertreter = self.betrieb.get("vertreten_durch", "")
        if vertreter:
            self.c.drawString(MARGIN_L, self.y, vertreter)
            self.y -= 4 * mm

        self.c.setFont("Helvetica", 8.5)
        self.c.setFillColor(GRAY_DARK)
        firma = self.betrieb.get("firmenname", "Firma")
        self.c.drawString(MARGIN_L, self.y, f"{firma} (Arbeitgeber)")

        if vertreter:
            self.y += 4 * mm

        an_name = f"{self.arbeitnehmer.get('vorname', '')} {self.arbeitnehmer.get('nachname', '')}".strip()
        self.c.setFont("Helvetica-Bold", 9)
        self.c.setFillColor(DARK)
        if an_name:
            self.c.drawString(MARGIN_L + line_w + 10 * mm, self.y, an_name)
            self.y -= 4 * mm
        self.c.setFont("Helvetica", 8.5)
        self.c.setFillColor(GRAY_DARK)
        self.c.drawString(MARGIN_L + line_w + 10 * mm, self.y, "(Arbeitnehmerin)")

    def save(self):
        self._footer()
        self.c.save()
        self.buf.seek(0)
        return self.buf.getvalue()
