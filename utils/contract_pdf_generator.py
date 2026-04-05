"""
Rechtssicherer Vertragsgenerator (fpdf2) für Steakhouse Piccolo.
Layout und Paragraphen orientieren sich eng am Mustervertrag.
"""

from __future__ import annotations

import base64
import calendar
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from utils.branding import BRAND_LOGO_IMAGE


@dataclass
class ContractData:
    contract_title: str = "Änderungsvertrag"
    prior_contract_date_text: str = "15. Oktober 2025"
    employer_name: str = "Steakhouse Piccolo"
    employer_represented_by: str = "Silvana Lasinski"
    employer_street: str = "Gustav-Adolf-Straße 17"
    employer_city_line: str = "04105 Leipzig"
    employee_name: str = ""
    employee_birth_date: date = field(default_factory=date.today)
    employee_street: str = ""
    employee_city_line: str = ""
    employment_start_date: date = field(default_factory=date.today)
    amendment_effective_date: date = field(default_factory=date.today)
    monthly_target_hours: float = 130.0
    monthly_gross_salary: float = 0.0
    annual_vacation_days: float = 20.0
    additional_agreements: str = ""
    employer_signatory: str = "Silvana Lasinski"
    signing_city: str = "Leipzig"
    signing_date: date = field(default_factory=date.today)
    logo_path: str = ""


def _safe(value: Any) -> str:
    return str(value or "").strip()


def _pdf_safe(value: Any) -> str:
    text = _safe(value)
    repl = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2011": "-",
        "\u00ad": "-",
        "\u201c": "\"",
        "\u201d": "\"",
        "\u201e": "\"",
        "\u201f": "\"",
        "\u2018": "'",
        "\u2019": "'",
        "\u2026": "...",
        "\u202f": " ",
    }
    for old, new in repl.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def _to_date(value: Any, fallback: date | None = None) -> date:
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
            return date(int(s[6:10]), int(s[3:5]), int(s[0:2]))
        except Exception:
            pass
    return fallback or date.today()


def _fmt_date(value: Any) -> str:
    return _to_date(value).strftime("%d.%m.%Y")


def _fmt_date_long(value: Any) -> str:
    d = _to_date(value)
    months = [
        "",
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ]
    return f"{d.day:02d}. {months[d.month]} {d.year}"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


def _plus_months(src: date, months: int) -> date:
    month_idx = src.month - 1 + months
    year = src.year + month_idx // 12
    month = month_idx % 12 + 1
    day = min(src.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _default_logo_path() -> str:
    # Priorität: expliziter Name aus User-Anforderung, dann Branding-Fallback.
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "assets" / "Piccolo Logo.jpeg",
        root / "assets" / "Piccolo Logo.jpg",
        root / "assets" / "piccolo_logo.jpeg",
        root / "assets" / "piccolo_logo.jpg",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return BRAND_LOGO_IMAGE or ""


def _to_payload(data: ContractData | dict[str, Any]) -> dict[str, Any]:
    if isinstance(data, ContractData):
        b = asdict(data)
        return {
            "contract_title": b["contract_title"],
            "prior_contract_date_text": b["prior_contract_date_text"],
            "employer_name": b["employer_name"],
            "employer_represented_by": b["employer_represented_by"],
            "employer_street": b["employer_street"],
            "employer_city_line": b["employer_city_line"],
            "employee_name": b["employee_name"],
            "employee_birth_date": b["employee_birth_date"],
            "employee_street": b["employee_street"],
            "employee_city_line": b["employee_city_line"],
            "employment_start_date": b["employment_start_date"],
            "amendment_effective_date": b["amendment_effective_date"],
            "monthly_target_hours": b["monthly_target_hours"],
            "monthly_gross_salary": b["monthly_gross_salary"],
            "annual_vacation_days": b["annual_vacation_days"],
            "additional_agreements": b["additional_agreements"],
            "employer_signatory": b["employer_signatory"],
            "signing_city": b["signing_city"],
            "signing_date": b["signing_date"],
            "logo_path": b.get("logo_path") or _default_logo_path(),
        }
    payload = dict(data)
    payload["logo_path"] = _safe(payload.get("logo_path")) or _default_logo_path()
    return payload


def as_download_filename(employee_name: str, effective_date: date) -> str:
    name = _safe(employee_name)
    last = (name.split()[-1] if name else "Mitarbeiter").strip() or "Mitarbeiter"
    return f"Vertrag_{'_'.join(last.split())}_{effective_date.strftime('%Y%m%d')}.pdf"


def preview_pdf_html(pdf_bytes: bytes) -> str:
    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    return (
        "<iframe src='data:application/pdf;base64,"
        + b64
        + "' width='100%' height='980' style='border:1px solid #E2E8F0;border-radius:8px;'></iframe>"
    )


def _title(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6.2, _pdf_safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10.5)


def _para(pdf: FPDF, text: str, *, lh: float = 5.6) -> None:
    pdf.multi_cell(0, lh, _pdf_safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.4)


def _add_header(pdf: FPDF, payload: dict[str, Any]) -> None:
    logo_path = _safe(payload.get("logo_path"))
    company = _safe(payload.get("employer_name")) or "Steakhouse Piccolo"
    street = _safe(payload.get("employer_street")) or "Gustav-Adolf-Straße 17"
    city = _safe(payload.get("employer_city_line")) or "04105 Leipzig"

    top_y = 14.0
    left_x = pdf.l_margin

    # Briefkopf links
    pdf.set_xy(left_x, top_y)
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(105, 6, _pdf_safe(company), new_x="LEFT", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(left_x)
    pdf.multi_cell(105, 5.0, _pdf_safe(f"{street}\n{city}"), new_x="LEFT", new_y="NEXT")

    # Logo rechts (ca. 45 mm)
    if logo_path and Path(logo_path).exists():
        logo_w_mm = 45.0
        x_logo = pdf.w - pdf.r_margin - logo_w_mm
        pdf.image(logo_path, x=x_logo, y=top_y, w=logo_w_mm)

    pdf.set_y(44)
    pdf.set_draw_color(160, 160, 160)
    pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)


def generate_contract_pdf(data: ContractData | dict[str, Any]) -> bytes:
    # Lazy-Import: fpdf2 wird erst bei tatsächlicher PDF-Erzeugung geladen.
    from fpdf import FPDF

    payload = _to_payload(data)

    title = _safe(payload.get("contract_title")) or "Änderungsvertrag"
    prior_contract_date_text = _safe(payload.get("prior_contract_date_text")) or "15. Oktober 2025"

    employer_name = _safe(payload.get("employer_name")) or "Steakhouse Piccolo"
    employer_represented = _safe(payload.get("employer_represented_by")) or "Silvana Lasinski"
    employer_street = _safe(payload.get("employer_street")) or "Gustav-Adolf-Straße 17"
    employer_city = _safe(payload.get("employer_city_line")) or "04105 Leipzig"

    employee_name = _safe(payload.get("employee_name"))
    employee_birth = _to_date(payload.get("employee_birth_date"))
    employee_street = _safe(payload.get("employee_street"))
    employee_city = _safe(payload.get("employee_city_line"))

    employment_start = _to_date(payload.get("employment_start_date"))
    amendment_effective = _to_date(payload.get("amendment_effective_date"))
    probe_start = employment_start
    probe_end = _plus_months(employment_start, 6) - date.resolution

    monthly_hours = _to_float(payload.get("monthly_target_hours"), 130.0)
    monthly_gross = _to_float(payload.get("monthly_gross_salary"), 0.0)
    annual_vacation = _to_float(payload.get("annual_vacation_days"), 20.0)
    additional = _safe(payload.get("additional_agreements")) or "Keine."
    signing_city = _safe(payload.get("signing_city")) or "Leipzig"
    signing_date = _to_date(payload.get("signing_date"), fallback=date.today())
    employer_signatory = _safe(payload.get("employer_signatory")) or "Silvana Lasinski"

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(20, 16, 20)
    pdf.set_font("Helvetica", "", 10.5)

    _add_header(pdf, payload)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8.5, _pdf_safe(title), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10.5)
    pdf.cell(
        0,
        6.2,
        _pdf_safe(f"zum bestehenden Arbeitsvertrag vom {prior_contract_date_text}"),
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(1.5)

    _para(
        pdf,
        "Die nachfolgenden Regelungen treten ergänzend und abändernd zum bestehenden Arbeitsvertrag vom "
        f"{prior_contract_date_text} in Kraft. Alle nicht ausdrücklich geänderten Bestimmungen des ursprünglichen "
        "Arbeitsvertrages behalten ihre Gültigkeit.",
    )

    pdf.set_font("Helvetica", "B", 10.5)
    pdf.multi_cell(0, 5.8, "A R B E I T G E B E R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10.5)
    _para(
        pdf,
        f"{employer_name}\n"
        f"vertreten durch {employer_represented}\n"
        f"{employer_street}\n"
        f"{employer_city}\n"
        "– nachfolgend „Arbeitgeber\" –",
    )

    pdf.set_font("Helvetica", "B", 10.5)
    pdf.multi_cell(0, 5.8, "A R B E I T N E H M E R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10.5)
    _para(
        pdf,
        f"{employee_name}\n"
        f"geb. {_fmt_date(employee_birth)}\n"
        f"{employee_street}\n"
        f"{employee_city}\n"
        "– nachfolgend „Arbeitnehmer\" –",
    )

    _title(pdf, "§ 1 Inkrafttreten der Änderungen")
    _para(
        pdf,
        "Die nachfolgenden Änderungen treten mit Wirkung zum "
        f"{_fmt_date(amendment_effective)} in Kraft und ersetzen die bisherigen Regelungen "
        f"der entsprechenden Paragrafen des Arbeitsvertrages vom {prior_contract_date_text}.",
    )

    _title(pdf, "§ 2 Probezeit")
    _para(
        pdf,
        "Die ersten sechs Monate des Arbeitsverhältnisses "
        f"({_fmt_date(probe_start)} bis {_fmt_date(probe_end)}) gelten als Probezeit gemäß § 622 Abs. 3 BGB. "
        "Während der Probezeit kann das Arbeitsverhältnis von beiden Parteien mit einer Frist von zwei Wochen "
        "zu jedem beliebigen Tag gekündigt werden.",
    )

    _title(pdf, "§ 3 Arbeitszeit")
    _para(pdf, f"(1) Die monatliche Sollarbeitszeit beträgt {monthly_hours:.0f} Stunden. Die Verteilung erfolgt auf 4–5 Arbeitstage pro Woche.")
    _para(
        pdf,
        "(2) Montag und Dienstag sind betriebliche Ruhetage; eine Einplanung an diesen Tagen erfolgt grundsätzlich nicht. "
        "Da es sich um einen gastronomischen Betrieb handelt, kann die Arbeitsleistung an allen übrigen Wochentagen einschließlich "
        "Sonn- und Feiertagen erbracht werden, sofern die gesetzlichen Vorgaben des Arbeitszeitgesetzes (ArbZG) eingehalten werden.",
    )
    _para(
        pdf,
        "(3) Die Lage der Arbeitszeit wird vom Arbeitgeber entsprechend dem Arbeitsanfall festgelegt. Der Arbeitgeber teilt dem "
        "Arbeitnehmer die Lage seiner Arbeitszeit jeweils mindestens 4 Tage im Voraus mit. In Krankheitsfällen oder anderen "
        "betrieblichen Notfällen kann eine kurzfristige Änderung des Dienstes auch mit kürzerer Vorankündigungsfrist erfolgen.",
    )
    _para(
        pdf,
        "(4) Gesetzliche Ruhepausen werden gewährt: bei einer Arbeitszeit von mehr als 6 Stunden mindestens 30 Minuten, bei mehr "
        "als 9 Stunden mindestens 45 Minuten (§ 4 ArbZG). Nach Beendigung der täglichen Arbeitszeit wird eine ununterbrochene "
        "Ruhezeit von mindestens 11 Stunden gewährleistet (§ 5 ArbZG).",
    )
    _para(
        pdf,
        "(5) Die monatliche Sollarbeitszeit kann bei betrieblicher Notwendigkeit überschritten werden. Mehrarbeitsstunden werden "
        "dem Arbeitszeitkonto des Arbeitnehmers gutgeschrieben und nach den Bestimmungen des § 7 dieses Vertrages abgerechnet "
        "oder ausgeglichen.",
    )

    _title(pdf, "§ 4 Tätigkeit")
    _para(
        pdf,
        "Der Arbeitnehmer wird mit folgenden Aufgaben betraut:\n"
        "• Beikoch und Koch\n"
        "• Küchenhilfe\n"
        "• Reinigung der Betriebsräume und des Inventars\n"
        "• Logistik",
    )

    _title(pdf, "§ 5 Vergütung")
    _para(
        pdf,
        "(1) Die Vergütung beträgt als monatliche Brutto-Vergütung "
        f"{monthly_gross:.2f} € brutto. Der monatliche Bruttolohn orientiert sich an der vereinbarten "
        f"Sollarbeitszeit von {monthly_hours:.0f} Stunden.",
    )
    _para(
        pdf,
        "(2) Zusätzlich zum Grundlohn können freiwillige Zuschläge gewährt werden (z. B. Feiertags- und Sonntagszuschlag).",
    )
    _para(
        pdf,
        "(3) Die Zuschläge nach Abs. 2 sind freiwillige Leistungen des Arbeitgebers, auf die kein dauerhafter Rechtsanspruch "
        "für die Zukunft besteht. Der Arbeitgeber behält sich den Widerruf dieser Leistungen aus sachlichen Gründen vor.",
    )
    _para(pdf, "(4) Die Auszahlung der Vergütung erfolgt jeweils zum 15. des Monats, spätestens jedoch bis zum nächsten Werktag.")
    _para(
        pdf,
        "(5) Die Anordnung von Überstunden ist bei betrieblicher Notwendigkeit zulässig. Angeordnete Überstunden werden dem "
        "Arbeitszeitkonto gutgeschrieben oder nach Wahl des Arbeitgebers vergütet.",
    )

    _title(pdf, "§ 6 Urlaub")
    _para(
        pdf,
        f"Der Arbeitnehmer hat Anspruch auf einen jährlichen Erholungsurlaub von {annual_vacation:.0f} Arbeitstagen. "
        "Im Übrigen gelten die Bestimmungen des Bundesurlaubsgesetzes (BUrlG).",
    )

    _title(pdf, "§ 7 Arbeitszeitkonto")
    _para(
        pdf,
        "(1) Für den Arbeitnehmer wird ein Arbeitszeitkonto geführt, auf dem die Differenz zwischen der geleisteten Arbeitszeit "
        f"und der monatlichen Sollarbeitszeit von {monthly_hours:.0f} Stunden als Plus- oder Minusstunden erfasst wird.",
    )
    _para(
        pdf,
        "(2) Plusstunden entstehen, wenn die geleistete Arbeitszeit die monatliche Sollarbeitszeit übersteigt. "
        "Die gesetzlichen Grenzen sind einzuhalten.",
    )
    _para(
        pdf,
        "(3) Minusstunden können entstehen, wenn die geleistete Arbeitszeit die monatliche Sollarbeitszeit unterschreitet "
        "und dies auf betriebliche Gründe oder auf Wunsch des Arbeitnehmers zurückzuführen ist.",
    )
    _para(
        pdf,
        "(4) Der Ausgleichszeitraum beträgt 12 Monate (Kalenderjahr). Aufgelaufene Plus- und Minusstunden sind bis "
        "zum 31. März des Folgejahres auszugleichen.",
    )
    _para(
        pdf,
        "(5) Bei Beendigung des Arbeitsverhältnisses werden vorhandene Plusstunden ausgezahlt. Verbleibende Minusstunden "
        "können mit der letzten Vergütung verrechnet werden, sofern dies gesetzlich zulässig ist.",
    )
    _para(pdf, "(6) Der Arbeitnehmer hat das Recht, jederzeit Einsicht in seinen aktuellen Kontostand zu nehmen.")

    _title(pdf, "§ 8 Sonstige Vereinbarungen")
    _para(pdf, additional)

    _title(pdf, "§ 9 Schlussbestimmungen")
    _para(
        pdf,
        "(1) Alle nicht durch diesen Änderungsvertrag ausdrücklich geänderten Bestimmungen des Arbeitsvertrages "
        f"vom {prior_contract_date_text} bleiben unverändert in Kraft.",
    )
    _para(
        pdf,
        "(2) Mündliche Nebenabreden bestehen nicht. Änderungen und Ergänzungen dieses Vertrages bedürfen zu ihrer "
        "Wirksamkeit der Textform.",
    )
    _para(
        pdf,
        "(3) Sollten einzelne Bestimmungen dieses Änderungsvertrages unwirksam sein oder werden, so wird hierdurch die "
        "Wirksamkeit der übrigen Bestimmungen nicht berührt.",
    )
    _para(
        pdf,
        "(4) Hinweis zum Kündigungsschutz: Möchte der Arbeitnehmer die Unwirksamkeit einer Kündigung geltend machen, "
        "muss er innerhalb von drei Wochen nach Zugang der schriftlichen Kündigung Klage beim zuständigen Arbeitsgericht erheben.",
    )

    # Unterschriftenblock - zwei Spalten wie gefordert
    pdf.ln(4)
    col_gap = 8
    total_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = (total_w - col_gap) / 2
    left_x = pdf.l_margin
    right_x = left_x + col_w + col_gap
    y = pdf.get_y()

    pdf.set_xy(left_x, y)
    pdf.multi_cell(col_w, 5.8, _pdf_safe(f"{signing_city}, den {_fmt_date(signing_date)}"), new_x="LEFT", new_y="NEXT")
    left_after = pdf.get_y()
    pdf.set_xy(right_x, y)
    pdf.multi_cell(col_w, 5.8, " ", new_x="LEFT", new_y="NEXT")
    right_after = pdf.get_y()
    pdf.set_y(max(left_after, right_after) + 10)

    y = pdf.get_y()
    pdf.set_xy(left_x, y)
    pdf.cell(col_w, 6, "______________________________", align="C")
    pdf.set_xy(right_x, y)
    pdf.cell(col_w, 6, "______________________________", align="C")
    pdf.ln(7)

    pdf.set_xy(left_x, pdf.get_y())
    pdf.cell(col_w, 6, _pdf_safe(f"{employer_signatory} (Arbeitgeber)"), align="C")
    pdf.set_xy(right_x, pdf.get_y())
    pdf.cell(col_w, 6, _pdf_safe(f"{employee_name} (Arbeitnehmer)"), align="C")

    return bytes(pdf.output())
