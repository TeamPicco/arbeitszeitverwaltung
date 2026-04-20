"""Gemeinsame Basis für alle Complio PDF-Generatoren."""
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
GREEN_TEXT = HexColor("#059669")
BLUE_BG = HexColor("#DBEAFE")
BLUE_TEXT = HexColor("#2563EB")

PAGE_W_P, PAGE_H_P = A4


def draw_complio_header(c, page_num, total_pages, title_right, subtitle_right, page_w=None, page_h=None, margin=15):
    """Standard-Header für alle Complio PDFs."""
    if page_w is None:
        page_w, page_h = A4
    margin_mm = margin * mm
    
    c.setFillColor(DARK)
    c.rect(0, page_h - 28*mm, page_w, 28*mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(margin_mm, page_h - 18*mm, "Complio")
    c.setFillColor(ORANGE)
    logo_width = stringWidth("Complio", "Helvetica-Bold", 22)
    c.drawString(margin_mm + logo_width, page_h - 18*mm, ".")
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 7)
    c.drawString(margin_mm, page_h - 23*mm, "RECHTSSICHER · ORGANISIERT · GESCHÜTZT")
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(page_w - margin_mm, page_h - 15*mm, title_right)
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 8)
    c.drawRightString(page_w - margin_mm, page_h - 20*mm, subtitle_right)
    if total_pages > 0:
        c.drawRightString(page_w - margin_mm, page_h - 24*mm, f"Seite {page_num} von {total_pages}")
    else:
        c.drawRightString(page_w - margin_mm, page_h - 24*mm, f"Seite {page_num}")


def draw_complio_footer(c, left_text="© 2026 Complio · getcomplio.de", right_text="", page_w=None, page_h=None, margin=15):
    """Standard-Footer für alle Complio PDFs."""
    if page_w is None:
        page_w, page_h = A4
    margin_mm = margin * mm
    
    c.setStrokeColor(GRAY_LIGHT)
    c.setLineWidth(0.5)
    c.line(margin_mm, 12*mm, page_w - margin_mm, 12*mm)
    c.setFillColor(GRAY_DARK)
    c.setFont("Helvetica", 7)
    c.drawString(margin_mm, 7*mm, left_text)
    c.drawRightString(page_w - margin_mm, 7*mm, right_text)


def new_pdf_buffer():
    """Erstellt einen neuen In-Memory-Buffer für PDF-Generierung."""
    return io.BytesIO()


def finalize_pdf(c, buffer):
    """Schließt das PDF ab und gibt die Bytes zurück."""
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
