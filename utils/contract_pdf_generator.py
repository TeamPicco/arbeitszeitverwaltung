"""
PDF-Vertragsgenerator auf Basis fpdf2.
Layout orientiert sich am Muster "Aenderungsvertrag_Franke_ab_01022026.pdf".
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

from fpdf import FPDF


@dataclass
class ContractData:
    contract_title: str
    prior_contract_date: str
    employer_name: str
    employer_represented_by: str
    employer_street: str
    employer_city_line: str
    employee_name: str
    employee_birth_date: date
    employee_street: str
    employee_city_line: str
    effective_date: date
    start_of_employment: date
    probation_months: int
    monthly_target_hours: float
    gross_hourly_wage: float
    annual_vacation_days: float
    additional_agreements: str = ""


def _to_payload(data: ContractData | dict[str, Any]) -> dict[str, Any]:
    if isinstance(data, ContractData):
        base = asdict(data)
        return {
            "vertragstitel": base["contract_title"],
            "altvertrag_vom": base["prior_contract_date"],
            "arbeitgeber_name": base["employer_name"],
            "arbeitgeber_vertreten_durch": base["employer_represented_by"],
            "arbeitgeber_strasse": base["employer_street"],
            "arbeitgeber_plz_ort": base["employer_city_line"],
            "arbeitnehmer_name": base["employee_name"],
            "arbeitnehmer_geburtsdatum": base["employee_birth_date"],
            "arbeitnehmer_strasse": base["employee_street"],
            "arbeitnehmer_plz_ort": base["employee_city_line"],
            "beginn_av": base["effective_date"],
            "probezeit_monate": base["probation_months"],
            "monatliche_sollarbeitszeit": base["monthly_target_hours"],
            "brutto_verguetung": base["gross_hourly_wage"],
            "urlaubsanspruch": base["annual_vacation_days"],
            "sonstige_vereinbarungen": base["additional_agreements"],
        }
    return dict(data)


def as_download_filename(employee_name: str, effective_date: date) -> str:
    safe_name = "_".join(_safe(employee_name).split()) or "Mitarbeiter"
    return f"Aenderungsvertrag_{safe_name}_{effective_date.strftime('%Y%m%d')}.pdf"


def preview_pdf_html(pdf_bytes: bytes) -> str:
    encoded = base64.b64encode(pdf_bytes).decode("ascii")
    return (
        "<iframe "
        "src='data:application/pdf;base64,"
        + encoded
        + "' width='100%' height='960' style='border:1px solid #E2E8F0; border-radius:8px;'></iframe>"
    )


def _safe(value: Any) -> str:
    return str(value or "").strip()


def _pdf_safe_text(value: Any) -> str:
    text = _safe(value)
    replacements = {
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2011": "-",   # non-breaking hyphen
        "\u00ad": "-",   # soft hyphen
        "\u201c": "\"",
        "\u201d": "\"",
        "\u201e": "\"",
        "\u201f": "\"",
        "\u2018": "'",
        "\u2019": "'",
        "\u2026": "...",
        "\u202f": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


def _as_date(value: Any, fallback: date | None = None) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = _safe(value)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            pass
    if len(s) >= 10 and s[2] == "." and s[5] == ".":
        try:
            d = int(s[0:2])
            m = int(s[3:5])
            y = int(s[6:10])
            return date(y, m, d)
        except Exception:
            pass
    return fallback or date.today()


def _fmt_date(value: Any) -> str:
    return _as_date(value).strftime("%d.%m.%Y")


def _as_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value if value is not None else fallback)
    except Exception:
        return fallback


def _add_section_title(pdf: FPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.ln(2)
    pdf.multi_cell(0, 6.5, _pdf_safe_text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)


def _add_paragraph(pdf: FPDF, text: str, *, line_height: float = 6.0) -> None:
    pdf.multi_cell(0, line_height, _pdf_safe_text(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.8)


def generate_contract_pdf(data: ContractData | dict[str, Any]) -> bytes:
    """
    Erzeugt ein Vertrags-PDF (Änderungsvertrag/Arbeitsvertrag) im seriösen Drucklayout.
    """
    payload = _to_payload(data)

    arbeitnehmer_name = _safe(payload.get("arbeitnehmer_name"))
    arbeitnehmer_geburtsdatum = _fmt_date(payload.get("arbeitnehmer_geburtsdatum"))
    arbeitnehmer_strasse = _safe(payload.get("arbeitnehmer_strasse"))
    arbeitnehmer_plz_ort = _safe(payload.get("arbeitnehmer_plz_ort"))

    beginn_av = _as_date(payload.get("beginn_av"))
    vertrag_ab = _fmt_date(beginn_av)
    probezeit_monate = int(payload.get("probezeit_monate") or 6)
    monatliche_sollarbeitszeit = _as_float(payload.get("monatliche_sollarbeitszeit"), 130.0)
    brutto_verguetung = _as_float(payload.get("brutto_verguetung"), 15.0)
    urlaubsanspruch = _as_float(payload.get("urlaubsanspruch"), 20.0)
    sonstige_vereinbarungen = _safe(payload.get("sonstige_vereinbarungen")) or "Keine zusätzlichen Vereinbarungen."

    vertragstitel = _safe(payload.get("vertragstitel")) or "Änderungsvertrag"
    altvertrag_vom = _safe(payload.get("altvertrag_vom")) or "15. Oktober 2025"
    ort_unterschrift = _safe(payload.get("ort_unterschrift")) or "Leipzig"
    datum_unterschrift = _fmt_date(payload.get("datum_unterschrift") or date.today())

    arbeitgeber_name = _safe(payload.get("arbeitgeber_name")) or "Steakhouse Piccolo"
    arbeitgeber_vertreten = _safe(payload.get("arbeitgeber_vertreten_durch")) or "Silvana Lasinski"
    arbeitgeber_strasse = _safe(payload.get("arbeitgeber_strasse")) or "Gustav-Adolf-Straße 17"
    arbeitgeber_plz_ort = _safe(payload.get("arbeitgeber_plz_ort")) or "04105 Leipzig"

    taetigkeiten = payload.get("taetigkeiten") or [
        "Beikoch und Koch",
        "Küchenhilfe",
        "Reinigung der Betriebsräume und des Inventars",
        "Logistik",
    ]

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # Header
    pdf.set_font("Helvetica", "B", 17)
    pdf.cell(0, 10, _pdf_safe_text(vertragstitel), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0,
        6.5,
        _pdf_safe_text(f"zum bestehenden Arbeitsvertrag vom {altvertrag_vom}"),
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(2)
    _add_paragraph(
        pdf,
        "Die nachfolgenden Regelungen treten ergänzend und abändernd zum bestehenden Arbeitsvertrag in Kraft. "
        "Alle nicht ausdrücklich geänderten Bestimmungen des ursprünglichen Arbeitsvertrages behalten ihre Gültigkeit.",
    )

    # Parteienblock
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, _pdf_safe_text("A R B E I T G E B E R"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    _add_paragraph(
        pdf,
        f"{arbeitgeber_name}\n"
        f"vertreten durch {arbeitgeber_vertreten}\n"
        f"{arbeitgeber_strasse}\n"
        f"{arbeitgeber_plz_ort}\n"
        "– nachfolgend „Arbeitgeber“ –",
        line_height=5.8,
    )

    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, _pdf_safe_text("A R B E I T N E H M E R"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    _add_paragraph(
        pdf,
        f"{arbeitnehmer_name}\n"
        f"geb. {arbeitnehmer_geburtsdatum}\n"
        f"{arbeitnehmer_strasse}\n"
        f"{arbeitnehmer_plz_ort}\n"
        "– nachfolgend „Arbeitnehmer“ –",
        line_height=5.8,
    )

    # Paragraphenstruktur aus dem Muster
    _add_section_title(pdf, "§ 1 Inkrafttreten der Änderungen")
    _add_paragraph(
        pdf,
        f"Die nachfolgenden Änderungen treten mit Wirkung zum {vertrag_ab} in Kraft und ersetzen die bisherigen "
        f"Regelungen der entsprechenden Paragrafen des Arbeitsvertrages vom {altvertrag_vom}.",
    )

    _add_section_title(pdf, "§ 2 Probezeit")
    _add_paragraph(
        pdf,
        f"Die ersten {probezeit_monate} Monate des Arbeitsverhältnisses gelten als Probezeit gemäß § 622 Abs. 3 BGB. "
        "Während der Probezeit kann das Arbeitsverhältnis von beiden Parteien mit einer Frist von zwei Wochen zu "
        "jedem beliebigen Tag gekündigt werden.",
    )

    _add_section_title(pdf, "§ 3 Arbeitszeit")
    _add_paragraph(
        pdf,
        f"(1) Die monatliche Sollarbeitszeit beträgt {monatliche_sollarbeitszeit:.0f} Stunden. "
        "Die Verteilung erfolgt auf 4–5 Arbeitstage pro Woche."
    )
    _add_paragraph(
        pdf,
        "(2) Montag und Dienstag sind betriebliche Ruhetage; eine Einplanung an diesen Tagen erfolgt grundsätzlich nicht. "
        "Da es sich um einen gastronomischen Betrieb handelt, kann die Arbeitsleistung an allen übrigen Wochentagen "
        "einschließlich Sonn- und Feiertagen erbracht werden, sofern die gesetzlichen Vorgaben des ArbZG eingehalten werden."
    )
    _add_paragraph(
        pdf,
        "(3) Die Lage der Arbeitszeit wird vom Arbeitgeber entsprechend dem Arbeitsanfall festgelegt. "
        "Der Arbeitgeber teilt dem Arbeitnehmer die Lage seiner Arbeitszeit jeweils mindestens 4 Tage im Voraus mit. "
        "In Krankheitsfällen oder anderen betrieblichen Notfällen kann eine kurzfristige Änderung des Dienstes erfolgen."
    )
    _add_paragraph(
        pdf,
        "(4) Gesetzliche Ruhepausen werden gewährt: bei einer Arbeitszeit von mehr als 6 Stunden mindestens 30 Minuten, "
        "bei mehr als 9 Stunden mindestens 45 Minuten (§ 4 ArbZG). Nach Beendigung der täglichen Arbeitszeit wird eine "
        "Ruhezeit von mindestens 11 Stunden gewährleistet (§ 5 ArbZG)."
    )
    _add_paragraph(
        pdf,
        "(5) Die monatliche Sollarbeitszeit kann bei betrieblicher Notwendigkeit überschritten werden. "
        "Mehrarbeitsstunden werden dem Arbeitszeitkonto gutgeschrieben und nach den Bestimmungen des § 7 abgerechnet oder ausgeglichen."
    )

    _add_section_title(pdf, "§ 4 Tätigkeit")
    _add_paragraph(pdf, "Der Arbeitnehmer wird mit folgenden Aufgaben betraut:")
    for task in taetigkeiten:
        _add_paragraph(pdf, f"- {_safe(task)}", line_height=5.5)

    _add_section_title(pdf, "§ 5 Vergütung")
    _add_paragraph(
        pdf,
        f"(1) Die Vergütung beträgt {brutto_verguetung:.2f} € brutto pro Stunde. "
        f"Der monatliche Bruttolohn ergibt sich aus dem Stundenlohn multipliziert mit den tatsächlich geleisteten "
        f"Arbeitsstunden entsprechend der vereinbarten monatlichen Sollarbeitszeit von {monatliche_sollarbeitszeit:.0f} Stunden."
    )
    _add_paragraph(
        pdf,
        "(2) Zusätzlich zum Grundstundenlohn werden folgende freiwillige Zuschläge gewährt: "
        "Feiertagszuschlag 100 % des Stundenlohns, Sonntagszuschlag 50 % des Stundenlohns."
    )
    _add_paragraph(
        pdf,
        "(3) Die Zuschläge sind freiwillige Leistungen, auf die kein dauerhafter Rechtsanspruch für die Zukunft besteht. "
        "Der Arbeitgeber behält sich den Widerruf aus sachlichen Gründen vor."
    )
    _add_paragraph(
        pdf,
        "(4) Die Auszahlung der Vergütung erfolgt jeweils zum 15. des Monats, spätestens jedoch bis zum nächsten Werktag."
    )
    _add_paragraph(
        pdf,
        "(5) Angeordnete Überstunden werden dem Arbeitszeitkonto gutgeschrieben oder mit dem regulären Stundensatz vergütet."
    )

    _add_section_title(pdf, "§ 6 Urlaub")
    _add_paragraph(
        pdf,
        f"Der Arbeitnehmer hat Anspruch auf einen jährlichen Erholungsurlaub von {urlaubsanspruch:.0f} Arbeitstagen. "
        "Im Übrigen gelten die Bestimmungen des Bundesurlaubsgesetzes (BUrlG)."
    )

    _add_section_title(pdf, "§ 7 Arbeitszeitkonto")
    _add_paragraph(
        pdf,
        f"(1) Für den Arbeitnehmer wird ein Arbeitszeitkonto geführt, auf dem die Differenz zwischen geleisteter Arbeitszeit "
        f"und der monatlichen Sollarbeitszeit von {monatliche_sollarbeitszeit:.0f} Stunden als Plus- oder Minusstunden erfasst wird."
    )
    _add_paragraph(
        pdf,
        "(2) Plusstunden entstehen bei Überschreitung der Sollarbeitszeit. Nach § 2 Abs. 2 MiLoG dürfen monatlich höchstens "
        "50 % der vereinbarten Sollarbeitszeit auf dem Konto eingestellt werden."
    )
    _add_paragraph(
        pdf,
        "(3) Minusstunden können entstehen, wenn die geleistete Arbeitszeit die Sollarbeitszeit unterschreitet und dies "
        "auf betriebliche Gründe oder auf Wunsch des Arbeitnehmers zurückzuführen ist."
    )
    _add_paragraph(
        pdf,
        "(4) Der Ausgleichszeitraum beträgt 12 Monate (Kalenderjahr). Ein Ausgleich erfolgt durch Freizeit oder Vergütung."
    )
    _add_paragraph(
        pdf,
        f"(5) Bei Beendigung des Arbeitsverhältnisses werden Plusstunden mit dem regulären Stundensatz von "
        f"{brutto_verguetung:.2f} € brutto ausgezahlt."
    )
    _add_paragraph(
        pdf,
        "(6) Der Arbeitnehmer hat das Recht, jederzeit Einsicht in seinen Kontostand zu nehmen."
    )

    _add_section_title(pdf, "§ 8 Verschwiegenheitspflicht")
    _add_paragraph(
        pdf,
        "Der Arbeitnehmer ist verpflichtet, über alle im Rahmen der Tätigkeit bekannt gewordenen Betriebs- und "
        "Geschäftsgeheimnisse sowie vertraulichen betriebsinternen Angelegenheiten gegenüber Dritten Stillschweigen zu bewahren."
    )

    _add_section_title(pdf, "§ 9 Schlussbestimmungen")
    _add_paragraph(
        pdf,
        "(1) Alle nicht durch diesen Vertrag ausdrücklich geänderten Bestimmungen des bisherigen Arbeitsvertrages "
        "bleiben unverändert in Kraft."
    )
    _add_paragraph(
        pdf,
        "(2) Mündliche Nebenabreden bestehen nicht. Änderungen und Ergänzungen dieses Vertrages bedürfen der Textform."
    )
    _add_paragraph(
        pdf,
        "(3) Sollten einzelne Bestimmungen unwirksam sein oder werden, bleibt die Wirksamkeit der übrigen Bestimmungen unberührt."
    )

    _add_section_title(pdf, "§ 10 Sonstige Vereinbarungen")
    _add_paragraph(pdf, sonstige_vereinbarungen)

    # Unterschriftenblock
    pdf.ln(4)
    pdf.multi_cell(0, 6, _pdf_safe_text(f"{ort_unterschrift}, den {datum_unterschrift}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = (available_width - 10) / 2
    left_x = pdf.l_margin
    right_x = left_x + col_width + 10
    y = pdf.get_y()

    pdf.set_xy(left_x, y)
    pdf.cell(col_width, 6, "______________________________", align="C")
    pdf.set_xy(right_x, y)
    pdf.cell(col_width, 6, "______________________________", align="C")
    pdf.ln(7)

    pdf.set_xy(left_x, pdf.get_y())
    pdf.cell(col_width, 6, _pdf_safe_text(f"{arbeitgeber_name} (Arbeitgeber)"), align="C")
    pdf.set_xy(right_x, pdf.get_y())
    pdf.cell(col_width, 6, _pdf_safe_text(f"{arbeitnehmer_name} (Arbeitnehmer)"), align="C")

    # latin-1 kompatibles Byte-Output für Browser/Download
    return bytes(pdf.output())
