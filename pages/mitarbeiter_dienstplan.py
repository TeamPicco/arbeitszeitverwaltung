"""
Mitarbeiter-Dienstplan-Ansicht
Zeigt nur die eigenen Dienste des eingeloggten Mitarbeiters.
Anzeige: Wochentag | Datum | Arbeitszeiten (von–bis)
Keine Stundenberechnungen, keine Lohnwerte – diese gehören in die Monatsauswertung.
"""

import streamlit as st
from datetime import datetime, date, timedelta
import calendar
import os
import io
from utils.database import get_supabase_client
from utils.planning_tables import resolve_planning_table
from utils.branding import BRAND_COMPANY_NAME, BRAND_LOGO_IMAGE
from utils.lohnberechnung import summarize_dienstplan_month

# Deutsche Monatsnamen
MONATE_DE = [
    "",
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

WOCHENTAGE_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


# ─────────────────────────────────────────────────────────────
# CSS: Minimalistisches, mobil-optimiertes Design
# ─────────────────────────────────────────────────────────────
DIENSTPLAN_CSS = """
<style>
/* Dienstplan-Karte */
.dp-card {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    margin-bottom: 6px;
    border-radius: 10px;
    background: #0b0b0b;
    border-left: 5px solid #2563eb;
    border: 1px solid #2a2a2a;
    box-shadow: 0 1px 4px rgba(0,0,0,0.35);
    gap: 12px;
}
.dp-card.urlaub  { border-left-color: #f59e0b; background: #1a1405; }
.dp-card.frei    { border-left-color: #9ca3af; background: #111111; }
.dp-card.arbeit  { border-left-color: #10b981; background: #06150f; }

/* Datum-Block – Wochentag neben dem Datum */
.dp-date {
    min-width: 90px;
    display: flex;
    align-items: center;
    gap: 6px;
    line-height: 1.2;
}
.dp-date .day   { font-size: 1.4rem; font-weight: 700; color: #ffffff; }
.dp-date .month { font-size: 0.7rem; color: #e5e7eb; text-transform: uppercase; letter-spacing: 0.05em; }
.dp-date .weekday-inline { font-size: 0.82rem; color: #e5e7eb; font-weight: 600; min-width: 26px; }

/* Wochentag (versteckt, da jetzt inline im Datum-Block) */
.dp-weekday {
    display: none;
}

/* Zeiten */
.dp-time {
    flex: 1;
    font-size: 1rem;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: 0.02em;
}

/* Typ-Badge */
.dp-badge {
    font-size: 0.75rem;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
    white-space: nowrap;
}
.dp-badge.arbeit  { background: #0d2e1f; color: #ffffff; border: 1px solid #1f6f4e; }
.dp-badge.urlaub  { background: #3b2a07; color: #ffffff; border: 1px solid #996a08; }
.dp-badge.frei    { background: #1f2937; color: #ffffff; border: 1px solid #4b5563; }

/* Kalender */
.dp-cal-header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
    margin-bottom: 3px;
}
.dp-cal-header div {
    text-align: center;
    font-size: 0.72rem;
    font-weight: 700;
    color: #e5e7eb;
    padding: 4px 0;
}
.dp-cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
}
.dp-cal-day {
    border-radius: 8px;
    padding: 5px 3px;
    text-align: center;
    font-size: 0.78rem;
    min-height: 48px;
}
.dp-cal-day .num   { font-weight: 700; font-size: 0.9rem; }
.dp-cal-day .zeit  { font-size: 0.65rem; margin-top: 2px; }
.dp-cal-day.leer   { background: transparent; }
.dp-cal-day.arbeit { background: #0d2e1f; color: #ffffff; border: 1px solid #1f6f4e; }
.dp-cal-day.urlaub { background: #3b2a07; color: #ffffff; border: 1px solid #996a08; }
.dp-cal-day.frei   { background: #1f2937; color: #ffffff; border: 1px solid #4b5563; }
.dp-cal-day.normal { background: #0f0f0f; color: #ffffff; border: 1px solid #2a2a2a; }

/* Monat-Header */
.dp-month-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #ffffff;
    margin: 16px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 2px solid #2a2a2a;
}

/* Responsive */
@media (max-width: 600px) {
    .dp-card { flex-wrap: wrap; gap: 6px; }
    .dp-weekday {
        order: -1;
        width: 100%;
        font-size: 0.8rem;
        font-weight: 700;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 2px;
    }
    .dp-date { min-width: 44px; }
    .dp-date .day { font-size: 1.2rem; }
    .dp-time { font-size: 0.95rem; }
}
</style>
"""


def _format_zeit(dienst: dict) -> str:
    """Gibt nur die Einsatzzeiten zurück – keine Stunden, keine Pausen."""
    typ = dienst.get('schichttyp', 'arbeit')
    if typ == 'urlaub':
        return "Urlaub"
    if typ == 'frei':
        return "Frei"
    start = dienst.get('start_zeit', '')
    ende = dienst.get('ende_zeit', '')
    if start and ende:
        return f"{start[:5]} – {ende[:5]}"
    return "–"


def erstelle_dienstplan_pdf(mitarbeiter: dict, dienstplaene: list, jahr: int, monat: int) -> bytes:
    """Erstellt ein professionelles, minimalistisches PDF des Dienstplans (nur Planungsebene)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []

    logo_path = BRAND_LOGO_IMAGE

    # Header
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=3*cm, height=2.5*cm)
            hd = [[logo, Paragraph(f"<b>{BRAND_COMPANY_NAME}</b><br/>Dienstplan",
                   ParagraphStyle('h', fontSize=14, alignment=TA_LEFT))]]
        except Exception:
            hd = [[Paragraph(f"<b>{BRAND_COMPANY_NAME}</b>",
                   ParagraphStyle('h', fontSize=14, alignment=TA_LEFT))]]
    else:
        hd = [[Paragraph(f"<b>{BRAND_COMPANY_NAME}</b>",
               ParagraphStyle('h', fontSize=14, alignment=TA_LEFT))]]

    ht = Table(hd, colWidths=[4*cm, 13*cm])
    ht.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elements.append(ht)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    elements.append(Spacer(1, 0.5*cm))

    elements.append(Paragraph(
        f"Dienstplan {MONATE_DE[monat]} {jahr}",
        ParagraphStyle('title', fontSize=18, alignment=TA_CENTER,
                       spaceAfter=0.2*cm, fontName='Helvetica-Bold')
    ))
    elements.append(Paragraph(
        f"{mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}",
        ParagraphStyle('sub', fontSize=12, alignment=TA_CENTER,
                       spaceAfter=0.6*cm, textColor=colors.HexColor('#6b7280'))
    ))

    # Tabelle: nur Datum | Wochentag | Einsatzzeit
    dark = colors.HexColor('#111827')
    light_row = colors.HexColor('#f9fafb')
    green_bg = colors.HexColor('#d1fae5')
    yellow_bg = colors.HexColor('#fef3c7')
    grey_bg = colors.HexColor('#f3f4f6')

    col_widths = [3*cm, 4*cm, 10*cm]
    table_data = [["Datum", "Wochentag", "Einsatzzeit"]]

    for dienst in dienstplaene:
        datum_obj = datetime.fromisoformat(dienst['datum']).date()
        wt = WOCHENTAGE_DE[datum_obj.weekday()]
        zeit = _format_zeit(dienst)
        table_data.append([datum_obj.strftime('%d.%m.%Y'), wt, zeit])

    table = Table(table_data, colWidths=col_widths)
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), dark),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_row]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#e5e7eb')),
    ]
    # Farbige Zeilen je nach Typ
    for i, dienst in enumerate(dienstplaene, start=1):
        typ = dienst.get('schichttyp', 'arbeit')
        if typ == 'urlaub':
            ts.append(('BACKGROUND', (0, i), (-1, i), yellow_bg))
        elif typ == 'frei':
            ts.append(('BACKGROUND', (0, i), (-1, i), grey_bg))
        elif typ == 'arbeit':
            ts.append(('BACKGROUND', (0, i), (-1, i), green_bg))

    table.setStyle(TableStyle(ts))
    elements.append(table)
    elements.append(Spacer(1, 1.2*cm))

    # Unterschriften
    sig_s = ParagraphStyle('sig', fontSize=9, textColor=colors.HexColor('#9ca3af'))
    sig_data = [
        [Paragraph("____________________________", sig_s),
         Paragraph("____________________________", sig_s)],
        [Paragraph("Datum / Unterschrift Mitarbeiter", sig_s),
         Paragraph("Datum / Unterschrift Arbeitgeber", sig_s)]
    ]
    sig_t = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
    sig_t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(sig_t)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#9ca3af'))
        canvas.drawCentredString(
            A4[0] / 2, 1.5*cm,
            f"Seite {doc.page} | Erstellt am {date.today().strftime('%d.%m.%Y')} | Vertraulich – nur Planungsebene"
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


@st.cache_data(ttl=300, show_spinner=False)
def _cached_mitarbeiter_dienste(planning_table: str, mitarbeiter_id: int, start_iso: str, end_iso: str) -> list:
    supabase = get_supabase_client()
    resp = supabase.table(planning_table).select(
        '*, schichtvorlagen(name, farbe)'
    ).eq('mitarbeiter_id', mitarbeiter_id).gte(
        'datum', start_iso
    ).lte('datum', end_iso).order('datum').execute()
    return resp.data or []


def show_mitarbeiter_dienstplan(mitarbeiter: dict):
    """Zeigt den Dienstplan für den eingeloggten Mitarbeiter – clean & minimalistisch."""

    if not st.session_state.get("betrieb_id"):
        st.error("Session nicht vollständig. Bitte neu anmelden.")
        return

    st.markdown(DIENSTPLAN_CSS, unsafe_allow_html=True)
    st.subheader("Mein Dienstplan")

    supabase = get_supabase_client()
    planning_table = resolve_planning_table(supabase)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031),
                            index=date.today().year - 2024,
                            key="mitarbeiter_dienstplan_jahr")
    with col2:
        monat = st.selectbox("Monat", range(1, 13),
                             index=date.today().month - 1,
                             format_func=lambda x: MONATE_DE[x],
                             key="mitarbeiter_dienstplan_monat")
    with col3:
        if st.button("Aktualisieren", use_container_width=True, key="mitarbeiter_dienstplan_refresh",
                     help="Aktualisieren"):
            _cached_mitarbeiter_dienste.clear()
            st.rerun()

    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])

    dienste = _cached_mitarbeiter_dienste(
        planning_table, mitarbeiter['id'],
        erster_tag.isoformat(), letzter_tag.isoformat()
    )

    st.markdown("---")

    counts = summarize_dienstplan_month(year=jahr, month=monat, entries=dienste)

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Geplant", counts.geplant)
    col_b.metric("Urlaub", counts.urlaub)
    col_c.metric("Frei", counts.frei)
    col_d.metric("Krank", counts.krank)

    if not dienste:
        st.info(f"Keine Dienste für {MONATE_DE[monat]} {jahr} geplant.")
        st.caption("Tage ohne Eintrag (inkl. Ruhetage) werden in der Statistik als Frei gezählt.")
        return

    # PDF-Download (nur bei Klick generieren, nicht bei jedem Render)
    _pdf_key = f"ma_dp_pdf_{mitarbeiter['id']}_{jahr}_{monat}"
    _pdf_sig = f"{len(dienste)}"
    _pdf_sig_key = _pdf_key + "_sig"
    col_pdf1, col_pdf2 = st.columns(2)
    with col_pdf1:
        if st.button("PDF generieren", key="ma_dp_pdf_gen", use_container_width=True):
            try:
                st.session_state[_pdf_key] = erstelle_dienstplan_pdf(mitarbeiter, dienste, jahr, monat)
                st.session_state[_pdf_sig_key] = _pdf_sig
            except Exception as e:
                st.warning(f"PDF-Erstellung nicht verfügbar: {str(e)}")
    with col_pdf2:
        if st.session_state.get(_pdf_key) and st.session_state.get(_pdf_sig_key) == _pdf_sig:
            st.download_button(
                label="PDF herunterladen",
                data=st.session_state[_pdf_key],
                file_name=f"Dienstplan_{mitarbeiter.get('nachname', 'Mitarbeiter')}_{MONATE_DE[monat]}_{jahr}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="ma_dp_pdf_dl",
            )

    st.markdown("---")

    # ── KALENDER-ANSICHT ──────────────────────────────────────
    _show_kalender(dienste, jahr, monat)

    st.markdown("---")

    # ── LISTEN-ANSICHT (clean) ────────────────────────────────
    st.markdown(f'<div class="dp-month-header">{MONATE_DE[monat]} {jahr}</div>',
                unsafe_allow_html=True)

    # Gruppiere nach Datum (mehrere Schichten pro Tag möglich)
    tage_map: dict = {}
    for d in sorted(dienste, key=lambda x: (x['datum'], x.get('start_zeit', '00:00'))):
        tage_map.setdefault(d['datum'], []).append(d)

    for datum_str, eintraege in tage_map.items():
        datum_obj = date.fromisoformat(datum_str)
        wt = WOCHENTAGE_DE[datum_obj.weekday()]
        tag_num = datum_obj.day
        monat_kurz = datum_obj.strftime('%b')

        for dienst in eintraege:
            typ = dienst.get('schichttyp', 'arbeit')
            zeit = _format_zeit(dienst)

            badge_label = {"arbeit": "Geplant", "urlaub": "Urlaub", "frei": "Frei", "krank": "Krank"}.get(typ, typ.capitalize())

            st.markdown(f"""
            <div class="dp-card {typ}">
                <div class="dp-date">
                    <span class="weekday-inline">{wt}</span>
                    <div>
                        <div class="day">{tag_num:02d}</div>
                        <div class="month">{monat_kurz}</div>
                    </div>
                </div>
                <div class="dp-time">{zeit}</div>
                <div class="dp-badge {typ}">{badge_label}</div>
            </div>
            """, unsafe_allow_html=True)


def _show_kalender(dienstplaene: list, jahr: int, monat: int):
    """Zeigt eine kompakte Kalender-Ansicht – nur Tage und Startzeiten, keine Stunden."""

    st.markdown("### Kalender")

    # Dienste-Dict aufbauen (mehrere Einträge pro Tag)
    dienste_dict: dict = {}
    for d in dienstplaene:
        tag = date.fromisoformat(d['datum'])
        dienste_dict.setdefault(tag, []).append(d)

    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
    wochentag_start = erster_tag.weekday()  # 0=Mo

    # Kalender-HTML aufbauen
    header_html = "".join(f'<div>{t}</div>' for t in WOCHENTAGE_KURZ)
    cells_html = ""

    # Leere Zellen vor dem 1.
    for _ in range(wochentag_start):
        cells_html += '<div class="dp-cal-day leer"></div>'

    aktueller_tag = erster_tag
    while aktueller_tag <= letzter_tag:
        if aktueller_tag in dienste_dict:
            eintraege = dienste_dict[aktueller_tag]
            typ = eintraege[0].get('schichttyp', 'arbeit')

            # Nur Startzeiten anzeigen, keine Stunden
            zeiten_html = ""
            for e in eintraege:
                if typ == 'arbeit' and e.get('start_zeit'):
                    zeiten_html += f'<div class="zeit">{e["start_zeit"][:5]}</div>'
                elif typ == 'urlaub':
                    zeiten_html = '<div class="zeit">Urlaub</div>'
                    break
                elif typ == 'frei':
                    zeiten_html = '<div class="zeit">Frei</div>'
                    break

            cells_html += f"""
            <div class="dp-cal-day {typ}">
                <div class="num">{aktueller_tag.day}</div>
                {zeiten_html}
            </div>"""
        else:
            cells_html += f'<div class="dp-cal-day normal"><div class="num">{aktueller_tag.day}</div></div>'

        aktueller_tag += timedelta(days=1)

    st.markdown(f"""
    <div class="dp-cal-header">{header_html}</div>
    <div class="dp-cal-grid">{cells_html}</div>
    """, unsafe_allow_html=True)
