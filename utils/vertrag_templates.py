"""
Editierbare Arbeitsvertrags-/Aenderungsvertrags-Templates mit PDF-Export.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from utils.branding import BRAND_APP_NAME, BRAND_COMPANY_NAME


VERTRAG_TEMPLATE_OPTIONS = {
    "arbeitsvertrag_standard": "Arbeitsvertrag (Standard)",
    "aenderungsvertrag": "Aenderungsvertrag",
}


def _safe(text: Any) -> str:
    return str(text or "").strip().replace("\n", " ")


def _format_date(value: Any) -> str:
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    s = _safe(value)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[8:10]}.{s[5:7]}.{s[0:4]}"
    return s


def _to_date(value: Any, fallback: date | None = None) -> date:
    """Normalisiert verschiedene Datumsformate auf ein date-Objekt für Streamlit."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    s = _safe(value)
    if not s:
        return fallback or date.today()

    # ISO-Format: YYYY-MM-DD
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            pass

    # DE-Format: DD.MM.YYYY
    if len(s) >= 10 and s[2] == "." and s[5] == ".":
        try:
            d = int(s[0:2])
            m = int(s[3:5])
            y = int(s[6:10])
            return date(y, m, d)
        except Exception:
            pass

    return fallback or date.today()


def coerce_to_date(value: Any, fallback: date | None = None) -> date:
    """Öffentlicher Helper für Streamlit date_input-Kompatibilität."""
    return _to_date(value, fallback=fallback)


def build_default_contract_payload(mitarbeiter: dict, template_key: str = "arbeitsvertrag_standard") -> dict:
    today = date.today()
    vorname = _safe(mitarbeiter.get("vorname"))
    nachname = _safe(mitarbeiter.get("nachname"))
    arbeitnehmer_name = f"{vorname} {nachname}".strip()
    strasse = _safe(mitarbeiter.get("strasse"))
    plz = _safe(mitarbeiter.get("plz"))
    ort = _safe(mitarbeiter.get("ort"))
    anschrift = " ".join(part for part in [strasse, f"{plz} {ort}".strip()] if part).strip()

    return {
        "template_key": template_key,
        "template_name": VERTRAG_TEMPLATE_OPTIONS.get(template_key, template_key),
        "arbeitgeber_name": BRAND_COMPANY_NAME,
        "arbeitgeber_vertreten_durch": "",
        "arbeitgeber_strasse": "",
        "arbeitgeber_plz_ort": "",
        "arbeitnehmer_name": arbeitnehmer_name,
        "arbeitnehmer_geburtsdatum": _to_date(mitarbeiter.get("geburtsdatum"), fallback=today),
        "arbeitnehmer_anschrift": anschrift,
        "persoenliche_daten": "",
        "vertragsdatum": today,
        "eintrittsdatum": _to_date(mitarbeiter.get("eintrittsdatum"), fallback=today),
        "gueltig_ab": today,
        "monatliche_arbeitszeit": float(mitarbeiter.get("monatliche_soll_stunden") or 160.0),
        "probezeit_monate": 6,
        "wochenarbeitstage": "5",
        "stundenlohn_brutto": float(mitarbeiter.get("stundenlohn_brutto") or 0.0),
        "zuschlaege": "",
        "zusatzvereinbarungen": "",
    }


def generate_contract_pdf(payload: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=20, spaceAfter=8)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, leading=15, spaceBefore=6, spaceAfter=4)
    p = ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=14)
    foot = ParagraphStyle("foot", fontName="Helvetica", fontSize=8, leading=10)

    arbeitgeber_name = _safe(payload.get("arbeitgeber_name"))
    arbeitgeber_vertreten_durch = _safe(payload.get("arbeitgeber_vertreten_durch"))
    arbeitgeber_strasse = _safe(payload.get("arbeitgeber_strasse"))
    arbeitgeber_plz_ort = _safe(payload.get("arbeitgeber_plz_ort"))
    arbeitnehmer_name = _safe(payload.get("arbeitnehmer_name"))
    arbeitnehmer_geburtsdatum = _format_date(payload.get("arbeitnehmer_geburtsdatum"))
    arbeitnehmer_anschrift = _safe(payload.get("arbeitnehmer_anschrift"))
    persoenliche_daten = _safe(payload.get("persoenliche_daten"))
    vertragsdatum = _format_date(payload.get("vertragsdatum"))
    eintrittsdatum = _format_date(payload.get("eintrittsdatum"))
    gueltig_ab = _format_date(payload.get("gueltig_ab"))
    monatliche_arbeitszeit = float(payload.get("monatliche_arbeitszeit") or 0.0)
    probezeit_monate = int(payload.get("probezeit_monate") or 0)
    wochenarbeitstage = _safe(payload.get("wochenarbeitstage"))
    stundenlohn_brutto = float(payload.get("stundenlohn_brutto") or 0.0)
    zuschlaege = _safe(payload.get("zuschlaege"))
    zusatzvereinbarungen = _safe(payload.get("zusatzvereinbarungen"))
    template_name = _safe(payload.get("template_name")) or "Arbeitsvertrag"

    story = [
        Paragraph(template_name, h1),
        Paragraph("A R B E I T G E B E R", h2),
        Paragraph(
            f"{arbeitgeber_name or '-'}<br/>"
            f"vertreten durch {arbeitgeber_vertreten_durch or '-'}<br/>"
            f"{arbeitgeber_strasse or '-'}<br/>"
            f"{arbeitgeber_plz_ort or '-'}",
            p,
        ),
        Spacer(1, 0.2 * cm),
        Paragraph("A R B E I T N E H M E R", h2),
        Paragraph(
            f"{arbeitnehmer_name or '-'}<br/>"
            f"geb. {arbeitnehmer_geburtsdatum or '-'}<br/>"
            f"{arbeitnehmer_anschrift or '-'}<br/>"
            f"{persoenliche_daten or ''}",
            p,
        ),
        Spacer(1, 0.25 * cm),
        Paragraph("§ 1 Beginn und Gueltigkeit", h2),
        Paragraph(
            f"Das Arbeitsverhaeltnis beginnt am {eintrittsdatum or '-'} und gilt in dieser Fassung ab {gueltig_ab or '-'}.",
            p,
        ),
        Paragraph("§ 2 Arbeitszeit", h2),
        Paragraph(
            f"Die monatliche Arbeitszeit betraegt {monatliche_arbeitszeit:.2f} Stunden "
            f"bei einer regelmaessigen Verteilung auf {wochenarbeitstage or '-'} Arbeitstage pro Woche.",
            p,
        ),
        Paragraph("§ 3 Probezeit", h2),
        Paragraph(f"Die Probezeit betraegt {probezeit_monate} Monat(e).", p),
        Paragraph("§ 4 Verguetung", h2),
        Paragraph(
            f"Der Stundenlohn betraegt {stundenlohn_brutto:.2f} EUR brutto."
            + (f"<br/>Zuschlaege/Details: {zuschlaege}" if zuschlaege else ""),
            p,
        ),
        Paragraph("§ 5 Zusatzvereinbarungen", h2),
        Paragraph(zusatzvereinbarungen or "-", p),
        Spacer(1, 0.6 * cm),
        Paragraph(f"Ort/Datum: ____________________ , den {vertragsdatum or '-'}", p),
        Spacer(1, 0.8 * cm),
        Paragraph("______________________________", p),
        Paragraph(f"{arbeitgeber_name or '-'} (Arbeitgeber)", p),
        Spacer(1, 0.4 * cm),
        Paragraph("______________________________", p),
        Paragraph(f"{arbeitnehmer_name or '-'} (Arbeitnehmer)", p),
        Spacer(1, 0.6 * cm),
        Paragraph(f"Erstellt mit {BRAND_APP_NAME}", foot),
    ]

    doc.build(story)
    return buffer.getvalue()
