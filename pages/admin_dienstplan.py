"""
Admin-Dienstplanung
Monatliche Dienstplan-Erstellung und Schichtverwaltung
Schichttypen: arbeit | frei | urlaub
"""

import streamlit as st
from datetime import datetime, date, timedelta
import calendar
import locale
import io
import os
import html
from utils.database import get_supabase_client
from utils.planning_tables import resolve_planning_table
from utils.cache_manager import clear_app_caches
from utils.audit_log import log_aktion
from utils.calculations import (
    parse_zeit,
)
from utils.lohnberechnung import summarize_employee_month
from utils.branding import BRAND_COMPANY_NAME, BRAND_LOGO_IMAGE

# Deutsche Monatsnamen
MONATE_DE = [
    "",  # Index 0
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

WOCHENTAGE_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Schichttypen
SCHICHTTYPEN = {
    'arbeit': {'label': 'Geplant',     'farbe': '#0d6efd', 'text_farbe': '#ffffff', 'kuerzel': 'A'},
    'urlaub': {'label': 'Urlaub',      'farbe': '#ffeb3b', 'text_farbe': '#000000', 'kuerzel': 'U'},
    'krank':  {'label': 'Krank',       'farbe': '#ff9800', 'text_farbe': '#000000', 'kuerzel': 'K'},
    'frei':   {'label': 'Frei',        'farbe': '#e9ecef', 'text_farbe': '#000000', 'kuerzel': 'F'},
}

try:
    locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'de_DE')
    except:
        pass


@st.cache_data(ttl=60, show_spinner=False)
def _cached_mitarbeiter(betrieb_id: int) -> list:
    supabase = get_supabase_client()
    resp = (
        supabase.table("mitarbeiter")
        .select("id, betrieb_id, vorname, nachname, email, monatliche_soll_stunden")
        .eq("betrieb_id", betrieb_id)
        .order("nachname")
        .execute()
    )
    return resp.data or []


@st.cache_data(ttl=60, show_spinner=False)
def _cached_schichtvorlagen(betrieb_id: int) -> list:
    supabase = get_supabase_client()
    resp = (
        supabase.table("schichtvorlagen")
        .select("id, betrieb_id, name, start_zeit, ende_zeit, pause_minuten, farbe, ist_urlaub")
        .eq("betrieb_id", betrieb_id)
        .execute()
    )
    return resp.data or []


@st.cache_data(ttl=60, show_spinner=False)
def _cached_monatsdienste(planning_table: str, betrieb_id: int, start_iso: str, end_iso: str) -> list:
    supabase = get_supabase_client()
    resp = (
        supabase.table(planning_table)
        .select(
            "id, betrieb_id, mitarbeiter_id, datum, schichttyp, start_zeit, ende_zeit, "
            "pause_minuten, urlaub_stunden, schichtvorlage_id, urlaubsantrag_id"
        )
        .eq("betrieb_id", betrieb_id)
        .gte("datum", start_iso)
        .lte("datum", end_iso)
        .execute()
    )
    return resp.data or []


@st.cache_data(ttl=60, show_spinner=False)
def _cached_genehmigte_urlaube(betrieb_id: int, start_iso: str, end_iso: str) -> list:
    supabase = get_supabase_client()
    resp = (
        supabase.table("urlaubsantraege")
        .select("id, mitarbeiter_id, von_datum, bis_datum, anzahl_tage")
        .eq("status", "genehmigt")
        .lte("von_datum", end_iso)
        .gte("bis_datum", start_iso)
        .execute()
    )
    return resp.data or []


def _clear_dienstplan_cache():
    _cached_mitarbeiter.clear()
    _cached_schichtvorlagen.clear()
    _cached_monatsdienste.clear()
    _cached_genehmigte_urlaube.clear()


def _refresh_after_write() -> None:
    _clear_dienstplan_cache()
    clear_app_caches()


def _audit_dienstplan_change(
    *,
    action: str,
    dienst_id: int,
    mitarbeiter_id: int,
    alter_wert: dict | None,
    neuer_wert: dict | None,
    begruendung: str | None = None,
) -> None:
    try:
        log_aktion(
            admin_user_id=int(st.session_state.get("user_id") or 0),
            admin_name=str(st.session_state.get("username") or st.session_state.get("user_name") or "Admin"),
            aktion=action,
            tabelle="dienstplan",
            datensatz_id=int(dienst_id),
            mitarbeiter_id=int(mitarbeiter_id),
            mitarbeiter_name=None,
            alter_wert=alter_wert,
            neuer_wert=neuer_wert,
            begruendung=(begruendung or "Dienstplan-Anpassung"),
            betrieb_id=int(st.session_state.get("betrieb_id") or 0),
        )
    except Exception:
        pass


def _build_urlaub_map_from_rows(urlaub_rows: list, erster_tag: date, letzter_tag: date) -> dict:
    """Baut aus Urlaubszeilen eine Datum-Map pro Mitarbeiter."""
    urlaub_map = {}
    for u in urlaub_rows:
        von = date.fromisoformat(u["von_datum"])
        bis = date.fromisoformat(u["bis_datum"])
        aktuell = von
        while aktuell <= bis:
            if erster_tag <= aktuell <= letzter_tag and aktuell.weekday() not in [0, 1]:
                urlaub_map[(u["mitarbeiter_id"], aktuell.isoformat())] = u
            aktuell += timedelta(days=1)
    return urlaub_map


def _apply_schichtvorlage_one_click(
    supabase,
    planning_table: str,
    betrieb_id: int,
    mitarbeiter: dict,
    datum_iso: str,
    vorlage: dict,
):
    """
    Wendet eine Schichtvorlage per 1-Klick an.
    Vorhandene Tageseinträge werden ersetzt.
    """
    supabase.table(planning_table).delete().eq("betrieb_id", betrieb_id).eq(
        "mitarbeiter_id", mitarbeiter["id"]
    ).eq("datum", datum_iso).execute()

    soll = float(mitarbeiter.get("monatliche_soll_stunden") or 160.0)
    urlaub_tagessatz = round(soll / (5 * 4.33), 2)
    ist_urlaub = bool(vorlage.get("ist_urlaub"))

    payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter["id"],
        "datum": datum_iso,
        "schichttyp": "urlaub" if ist_urlaub else "arbeit",
        "start_zeit": "00:00:00" if ist_urlaub else (vorlage.get("start_zeit") or "08:00:00"),
        "ende_zeit": "00:00:00" if ist_urlaub else (vorlage.get("ende_zeit") or "16:00:00"),
        "pause_minuten": 0 if ist_urlaub else int(vorlage.get("pause_minuten") or 0),
        "urlaub_stunden": urlaub_tagessatz if ist_urlaub else 0.0,
        "schichtvorlage_id": None if ist_urlaub else vorlage.get("id"),
    }
    supabase.table(planning_table).insert(payload).execute()


# ============================================================
# PDF-FUNKTIONEN
# ============================================================

WOCHENTAGE_DE_PDF = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def _pdf_header(elements, logo_path, monat, jahr, mitarbeiter_name):
    """Erstellt den PDF-Header mit Logo, Titel und Mitarbeitername"""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=3*cm, height=2.5*cm)
            hd = [[logo, Paragraph(f"<b>{BRAND_COMPANY_NAME}</b><br/>Dienstplan",
                   ParagraphStyle('h', fontSize=14, alignment=TA_LEFT))]]
        except:
            hd = [[Paragraph(f"<b>{BRAND_COMPANY_NAME}</b>",
                   ParagraphStyle('h', fontSize=14, alignment=TA_LEFT))]]
    else:
        hd = [[Paragraph(f"<b>{BRAND_COMPANY_NAME}</b>",
               ParagraphStyle('h', fontSize=14, alignment=TA_LEFT))]]

    ht = Table(hd, colWidths=[4*cm, 13*cm])
    ht.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elements.append(ht)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Dienstplan {MONATE_DE[monat]} {jahr}",
                               ParagraphStyle('title', fontSize=18, alignment=TA_CENTER,
                                              spaceAfter=0.3*cm, fontName='Helvetica-Bold')))
    elements.append(Paragraph(mitarbeiter_name,
                               ParagraphStyle('sub', fontSize=12, alignment=TA_CENTER,
                                              spaceAfter=0.5*cm, textColor=colors.grey)))
    elements.append(Spacer(1, 0.3*cm))


def _pdf_dienste_tabelle(elements, dienstplaene):
    """Erstellt die Dienstplan-Tabelle als PDF-Element"""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Table, TableStyle, Spacer

    # Nur Planungsebene: Datum | Wochentag | Einsatzzeit – keine Stunden, keine Lohnwerte
    col_widths = [3*cm, 4*cm, 10*cm]
    table_data = [["Datum", "Wochentag", "Einsatzzeit"]]

    for dienst in dienstplaene:
        datum_obj = datetime.fromisoformat(dienst['datum']).date()
        wt = WOCHENTAGE_DE_PDF[datum_obj.weekday()]
        schichttyp = dienst.get('schichttyp', 'arbeit')

        if schichttyp == 'urlaub':
            zeit = "Urlaub"
        elif schichttyp == 'krank':
            zeit = "Krank (LFZ)"
        elif schichttyp == 'frei':
            zeit = "Frei"
        else:
            start = dienst.get('start_zeit', '')
            ende = dienst.get('ende_zeit', '')
            zeit = f"{start[:5]} – {ende[:5]}" if start and ende else "n.v."

        table_data.append([datum_obj.strftime('%d.%m.%Y'), wt, zeit])

    if not dienstplaene:
        table_data.append(["", "", "Keine Eintr\u00e4ge"])

    dark = colors.HexColor('#111827')
    light_row = colors.HexColor('#f9fafb')
    green_bg = colors.HexColor('#d1fae5')
    orange_bg = colors.HexColor('#ffe0b2')
    yellow_bg = colors.HexColor('#fef3c7')
    grey_bg = colors.HexColor('#f3f4f6')

    t = Table(table_data, colWidths=col_widths)
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
    for i, dienst in enumerate(dienstplaene, start=1):
        typ = dienst.get('schichttyp', 'arbeit')
        if typ == 'urlaub':
            ts.append(('BACKGROUND', (0, i), (-1, i), yellow_bg))
        elif typ == 'krank':
            ts.append(('BACKGROUND', (0, i), (-1, i), orange_bg))
        elif typ == 'frei':
            ts.append(('BACKGROUND', (0, i), (-1, i), grey_bg))
        else:
            ts.append(('BACKGROUND', (0, i), (-1, i), green_bg))
    t.setStyle(TableStyle(ts))
    elements.append(t)
    elements.append(Spacer(1, 1*cm))


def _pdf_unterschriften(elements):
    """F\u00fcgt Unterschriftenzeilen hinzu"""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle

    sig_style = ParagraphStyle('sig', fontSize=9, textColor=colors.grey)
    sig_data = [
        [Paragraph("____________________________", sig_style),
         Paragraph("____________________________", sig_style)],
        [Paragraph("Datum / Unterschrift Mitarbeiter", sig_style),
         Paragraph("Datum / Unterschrift Arbeitgeber", sig_style)]
    ]
    st = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
    st.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(st)


def erstelle_einzelner_dienstplan_pdf(mitarbeiter: dict, dienstplaene: list, jahr: int, monat: int) -> bytes:
    """Erstellt ein professionelles PDF des Dienstplans f\u00fcr einen Mitarbeiter"""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.pagesizes import A4

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    logo_path = BRAND_LOGO_IMAGE
    name = f"{mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}"

    _pdf_header(elements, logo_path, monat, jahr, name)
    _pdf_dienste_tabelle(elements, dienstplaene)
    _pdf_unterschriften(elements)

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(A4[0] / 2, 1.5*cm,
            f"Seite {doc.page} | Erstellt am {date.today().strftime('%d.%m.%Y')} | Vertraulich")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    return buffer.getvalue()


def erstelle_admin_dienstplan_pdf(mitarbeiter_liste: list, dienste_map: dict, jahr: int, monat: int) -> bytes:
    """Erstellt ein PDF mit allen Mitarbeitern auf separaten Seiten"""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, PageBreak
    from reportlab.lib.pagesizes import A4

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    logo_path = BRAND_LOGO_IMAGE

    for idx, mitarbeiter in enumerate(mitarbeiter_liste):
        if idx > 0:
            elements.append(PageBreak())
        name = f"{mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}"
        _pdf_header(elements, logo_path, monat, jahr, name)

        ma_dienste = []
        for key, eintraege in dienste_map.items():
            if key[0] == mitarbeiter['id']:
                ma_dienste.extend(eintraege)
        ma_dienste_sorted = sorted(ma_dienste, key=lambda x: (x['datum'], x.get('start_zeit', '00:00')))

        _pdf_dienste_tabelle(elements, ma_dienste_sorted)
        _pdf_unterschriften(elements)

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(A4[0] / 2, 1.5*cm,
            f"Seite {doc.page} | Erstellt am {date.today().strftime('%d.%m.%Y')} | Vertraulich")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    return buffer.getvalue()


def _collect_employee_dienste(dienste_map: dict, mitarbeiter_id: int) -> list:
    """Sammelt und sortiert alle Dienste für einen Mitarbeiter aus der Monats-Map."""
    ma_dienste = []
    for key, eintraege in dienste_map.items():
        if key[0] == mitarbeiter_id:
            ma_dienste.extend(eintraege)
    return sorted(ma_dienste, key=lambda x: (x['datum'], x.get('start_zeit', '00:00')))


def _render_download_center(mitarbeiter_liste: list, dienste_map: dict, jahr: int, monat: int, key_prefix: str = "dl"):
    """
    Zeigt direkte Download-Buttons für:
    1) Einzel-Dienstplan je Mitarbeiter
    2) Gesamtansicht (alle Mitarbeiter)
    """
    st.markdown("### Download-Center")
    d1, d2 = st.columns(2)

    with d1:
        st.markdown("**Einzelansicht je Mitarbeiter**")
        ma_download_id = st.selectbox(
            "Mitarbeiter für PDF",
            options=[m['id'] for m in mitarbeiter_liste],
            format_func=lambda x: next((f"{m['vorname']} {m['nachname']}" for m in mitarbeiter_liste if m['id'] == x), ""),
            key=f"{key_prefix}_ma_pdf_select",
        )
        ma_download = next((m for m in mitarbeiter_liste if m['id'] == ma_download_id), None)
        generated_pdfs = st.session_state.setdefault("generated_pdfs", {})
        ma_pdf_key = f"{key_prefix}_ma_pdf_bytes"
        ma_pdf_filename_key = f"{key_prefix}_ma_pdf_filename"
        ma_pdf_sig_key = f"{key_prefix}_ma_pdf_sig"
        current_ma_sig = f"{jahr}-{monat}-{ma_download_id}-{len(dienste_map)}"
        if st.button("PDF für Mitarbeiter generieren", use_container_width=True, key=f"{key_prefix}_ma_pdf_generate"):
            try:
                ma_dienste_sorted = _collect_employee_dienste(dienste_map, ma_download['id']) if ma_download else []
                generated_pdfs[ma_pdf_key] = erstelle_einzelner_dienstplan_pdf(
                    ma_download,
                    ma_dienste_sorted,
                    jahr,
                    monat,
                )
                st.session_state[ma_pdf_filename_key] = (
                    f"Dienstplan_{ma_download.get('nachname', 'Mitarbeiter')}_{MONATE_DE[monat]}_{jahr}.pdf"
                )
                st.session_state[ma_pdf_sig_key] = current_ma_sig
                st.success("Einzel-PDF wurde generiert.")
            except Exception as e:
                st.warning(f"Einzel-PDF konnte nicht erstellt werden: {str(e)}")
        if ma_download:
            if (
                generated_pdfs.get(ma_pdf_key)
                and st.session_state.get(ma_pdf_filename_key)
                and st.session_state.get(ma_pdf_sig_key) == current_ma_sig
            ):
                st.download_button(
                    label="Einzel-Dienstplan herunterladen",
                    data=generated_pdfs.get(ma_pdf_key),
                    file_name=st.session_state.get(ma_pdf_filename_key),
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"{key_prefix}_ma_pdf_download",
                )
            else:
                st.info("Bitte zuerst „PDF für Mitarbeiter generieren“ ausführen.")

    with d2:
        st.markdown("**Komplettansicht (alle Mitarbeiter)**")
        generated_pdfs = st.session_state.setdefault("generated_pdfs", {})
        all_pdf_key = f"{key_prefix}_all_pdf_bytes"
        all_pdf_sig_key = f"{key_prefix}_all_pdf_sig"
        all_pdf_sig = f"{jahr}-{monat}-{len(mitarbeiter_liste)}-{len(dienste_map)}"
        if st.button("Komplett-PDF generieren", use_container_width=True, key=f"{key_prefix}_all_pdf_generate"):
            try:
                generated_pdfs[all_pdf_key] = erstelle_admin_dienstplan_pdf(
                    mitarbeiter_liste,
                    dienste_map,
                    jahr,
                    monat,
                )
                st.session_state[all_pdf_sig_key] = all_pdf_sig
                st.success("Komplett-PDF wurde generiert.")
            except Exception as e:
                st.warning(f"Gesamt-PDF konnte nicht erstellt werden: {str(e)}")
        if generated_pdfs.get(all_pdf_key) and st.session_state.get(all_pdf_sig_key) == all_pdf_sig:
            st.download_button(
                label="Komplettansicht als PDF herunterladen",
                data=generated_pdfs.get(all_pdf_key),
                file_name=f"Dienstplan_Alle_{MONATE_DE[monat]}_{jahr}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"{key_prefix}_alle_pdf_download",
            )
        else:
            st.info("Bitte zuerst „Komplett-PDF generieren“ ausführen.")


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def lade_genehmigte_urlaube(betrieb_id: int, erster_tag: date, letzter_tag: date) -> dict:
    """
    Lädt alle genehmigten Urlaubsanträge für den Monat.
    Gibt ein Dict zurück: {(mitarbeiter_id, datum_str): urlaubsantrag_dict}
    """
    rows = _cached_genehmigte_urlaube(
        betrieb_id,
        erster_tag.isoformat(),
        letzter_tag.isoformat(),
    )
    return _build_urlaub_map_from_rows(rows, erster_tag, letzter_tag)


def setze_urlaub_automatisch(
    supabase,
    planning_table: str,
    betrieb_id: int,
    mitarbeiter_id: int,
    urlaub_map: dict,
    erster_tag: date,
    letzter_tag: date,
    mitarbeiter_soll_stunden: float,
) -> int:
    """
    Trägt genehmigte Urlaubstage automatisch in den Dienstplan ein.
    Überschreibt keine bestehenden Einträge.
    Gibt Anzahl neu eingetragener Tage zurück.
    """
    eingetragen = 0
    tage_pro_woche = 5  # Mi-So = 5 Arbeitstage
    stunden_pro_tag = mitarbeiter_soll_stunden / (tage_pro_woche * 4.33) if mitarbeiter_soll_stunden > 0 else 8.0

    # N+1-Fix: Vorhandene Tage im Zielmonat einmalig laden und lokal prüfen.
    existing_res = (
        supabase.table(planning_table)
        .select("datum")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .gte("datum", erster_tag.isoformat())
        .lte("datum", letzter_tag.isoformat())
        .execute()
    )
    existing_dates = {str(r.get("datum")) for r in (existing_res.data or []) if r.get("datum")}

    for (ma_id, datum_str), urlaub in urlaub_map.items():
        if ma_id != mitarbeiter_id:
            continue

        if datum_str in existing_dates:
            continue  # Nicht überschreiben

        try:
            supabase.table(planning_table).insert({
                'betrieb_id': betrieb_id,
                'mitarbeiter_id': mitarbeiter_id,
                'datum': datum_str,
                'schichttyp': 'urlaub',
                'urlaubsantrag_id': urlaub['id'],
                'urlaub_stunden': round(stunden_pro_tag, 2),
                'start_zeit': '00:00:00',
                'ende_zeit': '00:00:00',
                'pause_minuten': 0,
            }).execute()
            existing_dates.add(datum_str)
            eingetragen += 1
        except Exception:
            pass

    return eingetragen


# ============================================================
# HAUPTFUNKTION
# ============================================================

def show_dienstplanung():
    """Zeigt die Dienstplanung für Administratoren an"""

    st.markdown('<div class="section-header">Dienstplanung</div>', unsafe_allow_html=True)

    supabase = get_supabase_client()

    section = st.radio(
        "Dienstplanung Bereich",
        options=["Monatsplan", "Monatsübersicht (Tabelle)", "Schichtvorlagen"],
        horizontal=True,
        label_visibility="collapsed",
        key="dienstplanung_section",
    )
    if section == "Monatsplan":
        show_monatsplan(supabase)
    elif section == "Monatsübersicht (Tabelle)":
        show_monatsuebersicht_tabelle(supabase)
    else:
        show_schichtvorlagen(supabase)


# ============================================================
# MONATSPLAN
# ============================================================

def show_monatsplan(supabase):
    """Zeigt den monatlichen Dienstplan mit Frei/Urlaub-Optionen"""
    planning_table = resolve_planning_table(supabase)

    st.subheader("Monatlicher Dienstplan")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024)
    with col2:
        monat = st.selectbox("Monat", range(1, 13), index=date.today().month - 1,
                             format_func=lambda x: MONATE_DE[x])
    with col3:
        if st.button("Aktualisieren", use_container_width=True):
            st.rerun()

    mitarbeiter_liste = _cached_mitarbeiter(st.session_state.betrieb_id)
    if not mitarbeiter_liste:
        st.warning("Keine Mitarbeiter gefunden.")
        return

    schichtvorlagen_rows = _cached_schichtvorlagen(st.session_state.betrieb_id)
    vorlagen_dict = {v['id']: v for v in schichtvorlagen_rows} if schichtvorlagen_rows else {}

    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])

    # Lade Dienstpläne
    dienstplaene_rows = _cached_monatsdienste(
        planning_table,
        st.session_state.betrieb_id,
        erster_tag.isoformat(),
        letzter_tag.isoformat(),
    )

    dienste_map = {}
    if dienstplaene_rows:
        for d in dienstplaene_rows:
            key = (d['mitarbeiter_id'], d['datum'])
            if key not in dienste_map:
                dienste_map[key] = []
            dienste_map[key].append(d)

    # Lade genehmigte Urlaube
    urlaub_rows = _cached_genehmigte_urlaube(
        st.session_state.betrieb_id,
        erster_tag.isoformat(),
        letzter_tag.isoformat(),
    )
    urlaub_map = _build_urlaub_map_from_rows(urlaub_rows, erster_tag, letzter_tag)

    _render_download_center(mitarbeiter_liste, dienste_map, jahr, monat, key_prefix="monatsplan")
    st.markdown("---")

    # ── AUTOMATISCHE URLAUBSEINTRÄGE ──────────────────────────
    with st.expander("Genehmigte Urlaube automatisch in Dienstplan eintragen"):
        st.info(
            "Alle genehmigten Urlaubsanträge für diesen Monat werden automatisch als **Urlaub**-Einträge "
            "in den Dienstplan eingetragen. Bereits vorhandene Einträge werden **nicht** überschrieben."
        )

        col_a, col_b = st.columns(2)
        with col_a:
            auto_alle = st.button("Alle Mitarbeiter – Urlaube eintragen", use_container_width=True, type="primary")
        with col_b:
            ma_auto = st.selectbox(
                "Oder nur für Mitarbeiter:",
                options=[None] + [m['id'] for m in mitarbeiter_liste],
                format_func=lambda x: "Alle" if x is None else next(
                    (f"{m['vorname']} {m['nachname']}" for m in mitarbeiter_liste if m['id'] == x), "")
            )
            auto_einzeln = st.button("Urlaube eintragen", use_container_width=True)

        if auto_alle or auto_einzeln:
            gesamt = 0
            ziel_ids = [m['id'] for m in mitarbeiter_liste] if (auto_alle or ma_auto is None) else [ma_auto]
            for ma in mitarbeiter_liste:
                if ma['id'] not in ziel_ids:
                    continue
                soll = float(ma.get('monatliche_soll_stunden') or 160.0)
                n = setze_urlaub_automatisch(
                    supabase,
                    planning_table,
                    st.session_state.betrieb_id,
                    ma['id'],
                    urlaub_map,
                    erster_tag,
                    letzter_tag,
                    soll,
                )
                gesamt += n
            if gesamt > 0:
                st.success(f"{gesamt} Urlaubstag(e) automatisch eingetragen!")
                _refresh_after_write()
                st.rerun()
            else:
                st.info("Keine neuen Urlaubstage einzutragen (bereits vorhanden oder keine genehmigten Urlaube).")

    st.markdown("---")

    # ── SCHNELLPLANUNG ────────────────────────────────────────
    with st.expander("Dienst / Urlaub / Frei hinzufügen"):
        st.info("Betriebszeiten: Mittwoch – Sonntag | Ruhetage: Montag & Dienstag")

        col1, col2, col3 = st.columns(3)

        with col1:
            mitarbeiter_id = st.selectbox(
                "Mitarbeiter",
                options=[m['id'] for m in mitarbeiter_liste],
                format_func=lambda x: next(
                    (f"{m['vorname']} {m['nachname']}" for m in mitarbeiter_liste if m['id'] == x), "")
            )

        with col2:
            dienst_datum = st.date_input(
                "Datum", value=erster_tag,
                min_value=erster_tag, max_value=letzter_tag,
                format="DD.MM.YYYY"
            )
            if dienst_datum.weekday() in [0, 1]:
                wt = WOCHENTAGE_DE[dienst_datum.weekday()]
                st.warning(f"{wt} ist ein Ruhetag.")

        with col3:
            schichttyp = st.selectbox(
                "Typ",
                options=list(SCHICHTTYPEN.keys()),
                format_func=lambda x: SCHICHTTYPEN[x]['label']
            )

        # Zeiten nur bei Arbeit anzeigen
        if schichttyp == 'arbeit':
            col4, col5 = st.columns(2)
            with col4:
                if vorlagen_dict:
                    vorlage_id = st.selectbox(
                        "Schichtvorlage",
                        options=[None] + list(vorlagen_dict.keys()),
                        format_func=lambda x: "Benutzerdefiniert" if x is None else vorlagen_dict[x]['name']
                    )
                else:
                    vorlage_id = None
                    st.info("Keine Schichtvorlagen vorhanden")

            with col5:
                if vorlage_id:
                    v = vorlagen_dict[vorlage_id]
                    start_z, _ = parse_zeit(v['start_zeit'])
                    ende_z, _ = parse_zeit(v['ende_zeit'])
                    pause_m = v.get('pause_minuten', 0)
                    st.write(f"⏰ {v['start_zeit'][:5]} – {v['ende_zeit'][:5]}")
                    st.caption(f"Pause: {pause_m} Min")
                else:
                    start_z = st.time_input("Startzeit", value=datetime.strptime("08:00", "%H:%M").time())
                    ende_z = st.time_input("Endzeit", value=datetime.strptime("16:00", "%H:%M").time())
                    pause_m = st.number_input("Pause (Min)", min_value=0, max_value=240,
                                              value=0, step=5,
                                              help="Pause wird manuell eingetragen")
                    vorlage_id = None
        elif schichttyp == 'urlaub':
            # Urlaubsstunden aus Mitarbeiterprofil berechnen
            ma_data = next((m for m in mitarbeiter_liste if m['id'] == mitarbeiter_id), {})
            soll = float(ma_data.get('monatliche_soll_stunden') or 160.0)
            stunden_pro_tag = round(soll / (5 * 4.33), 2)
            urlaub_stunden = st.number_input(
                "Urlaubsstunden (Tagessatz)",
                min_value=0.0, max_value=24.0,
                value=stunden_pro_tag, step=0.5, format="%.2f",
                help=f"Berechnet aus Soll-Stunden ({soll}h / Monat ÷ 21,65 Arbeitstage)"
            )
            start_z = datetime.strptime("00:00", "%H:%M").time()
            ende_z = datetime.strptime("00:00", "%H:%M").time()
            pause_m = 0
            vorlage_id = None
        elif schichttyp == 'krank':
            # Krankheitsstunden = LFZ-Tagessatz (Soll-Stunden / Arbeitstage)
            ma_data = next((m for m in mitarbeiter_liste if m['id'] == mitarbeiter_id), {})
            soll = float(ma_data.get('monatliche_soll_stunden') or 160.0)
            stunden_pro_tag = round(soll / 21.65, 2)
            krank_stunden = st.number_input(
                "LFZ-Stunden (Tagessatz)",
                min_value=0.0, max_value=24.0,
                value=stunden_pro_tag, step=0.5, format="%.2f",
                help=f"Lohnfortzahlungsstunden: Soll ({soll}h) ÷ 21,65 Arbeitstage"
            )
            st.info("Krankheitstage werden mit Lohnfortzahlung (EFZG) eingetragen.")
            start_z = datetime.strptime("00:00", "%H:%M").time()
            ende_z = datetime.strptime("00:00", "%H:%M").time()
            pause_m = 0
            vorlage_id = None
            urlaub_stunden = 0.0
        else:  # frei
            st.info("Freie Tage werden ohne Lohn eingetragen.")
            start_z = datetime.strptime("00:00", "%H:%M").time()
            ende_z = datetime.strptime("00:00", "%H:%M").time()
            pause_m = 0
            vorlage_id = None
            urlaub_stunden = 0.0
            krank_stunden = 0.0

        if st.button(
            "Eintrag speichern",
            type="primary",
            use_container_width=True,
            key=f"quick_add_confirm_{monat}_{jahr}",
        ):
            try:
                eintrag = {
                    'betrieb_id': st.session_state.betrieb_id,
                    'mitarbeiter_id': mitarbeiter_id,
                    'datum': dienst_datum.isoformat(),
                    'schichttyp': schichttyp,
                    'start_zeit': start_z.strftime('%H:%M:%S'),
                    'ende_zeit': ende_z.strftime('%H:%M:%S'),
                    'pause_minuten': pause_m,
                }
                if vorlage_id:
                    eintrag['schichtvorlage_id'] = vorlage_id
                if schichttyp == 'urlaub':
                    eintrag['urlaub_stunden'] = urlaub_stunden
                    # Verknüpfe mit Urlaubsantrag wenn vorhanden
                    urlaub_key = (mitarbeiter_id, dienst_datum.isoformat())
                    if urlaub_key in urlaub_map:
                        eintrag['urlaubsantrag_id'] = urlaub_map[urlaub_key]['id']
                elif schichttyp == 'krank':
                    eintrag['urlaub_stunden'] = krank_stunden  # LFZ-Stunden im urlaub_stunden-Feld speichern

                resp = supabase.table(planning_table).insert(eintrag).execute()
                inserted = (resp.data or [{}])[0]
                _audit_dienstplan_change(
                    action="dienstplan_anlage",
                    dienst_id=int(inserted.get("id") or 0),
                    mitarbeiter_id=int(mitarbeiter_id),
                    alter_wert=None,
                    neuer_wert=eintrag,
                    begruendung="Dienstplan-Anlage",
                )
                _refresh_after_write()
                st.success(f"{SCHICHTTYPEN[schichttyp]['label']} eingetragen.")
                # E-Mail-Benachrichtigung an Mitarbeiter
                try:
                    from utils.email_service import send_dienstplan_email
                    ma_data = next((m for m in mitarbeiter_liste if m['id'] == mitarbeiter_id), {})
                    ma_email = ma_data.get('email', '')
                    ma_name = f"{ma_data.get('vorname', '')} {ma_data.get('nachname', '')}".strip()
                    if ma_email:
                        send_dienstplan_email(
                            empfaenger_email=ma_email,
                            empfaenger_name=ma_name,
                            monat=MONATE_DE[monat],
                            jahr=str(jahr),
                            schichten=[{
                                'datum': dienst_datum.strftime('%d.%m.%Y'),
                                'typ': SCHICHTTYPEN[schichttyp]['label'],
                                'start': start_z.strftime('%H:%M') if schichttyp == 'arbeit' else '',
                                'ende': ende_z.strftime('%H:%M') if schichttyp == 'arbeit' else '',
                            }]
                        )
                except Exception:
                    pass  # E-Mail-Fehler sollen den Hauptworkflow nicht blockieren
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {str(e)}")

    st.markdown("---")
    st.markdown(f"### {MONATE_DE[monat]} {jahr}")

    # ── MITARBEITER-ÜBERSICHT ─────────────────────────────────
    for mitarbeiter in mitarbeiter_liste:
        # Zähle Typen (einheitliche Monatslogik, inkl. Ruhetage als Frei ohne Eintrag)
        ma_dienste_flat = []
        for key, eintraege in dienste_map.items():
            if key[0] == mitarbeiter['id']:
                ma_dienste_flat.extend(eintraege)
        ma_dienste = ma_dienste_flat
        genehmigt_urlaub_dates = {
            datum_iso
            for (ma_id, datum_iso), _ in urlaub_map.items()
            if ma_id == mitarbeiter['id']
        }
        counts = summarize_employee_month(
            year=jahr,
            month=monat,
            entries=ma_dienste,
            extra_urlaub_dates=genehmigt_urlaub_dates,
        )

        # Ausstehende Urlaube für diesen MA im Monat
        ausstehend = len(genehmigt_urlaub_dates)
        bereits_im_plan = len(set(d['datum'] for d in ma_dienste if d.get('schichttyp') == 'urlaub'))
        nicht_eingetragen = max(0, ausstehend - bereits_im_plan)

        summary_line = (
            f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}: "
            f"{counts.geplant} Geplant | "
            f"{counts.urlaub} Urlaub | "
            f"{counts.frei} Frei | "
            f"{counts.krank} Krank"
        )
        if nicht_eingetragen > 0:
            summary_line += f" | {nicht_eingetragen} Urlaub Offen"
        with st.expander(
            summary_line
        ):
            if nicht_eingetragen > 0:
                st.warning(
                    f"{nicht_eingetragen} genehmigte(r) Urlaubstag(e) noch nicht im Dienstplan. "
                    f"Nutze 'Genehmigte Urlaube automatisch eintragen' oben."
                )

            # PDF-Download für einzelnen Mitarbeiter
            ma_dienste_sorted = _collect_employee_dienste(dienste_map, mitarbeiter['id'])
            try:
                pdf_bytes = erstelle_einzelner_dienstplan_pdf(mitarbeiter, ma_dienste_sorted, jahr, monat)
                dateiname = f"Dienstplan_{mitarbeiter['nachname']}_{MONATE_DE[monat]}_{jahr}.pdf"
                st.download_button(
                    label="Dienstplan als PDF herunterladen",
                    data=pdf_bytes,
                    file_name=dateiname,
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"pdf_dl_{mitarbeiter['id']}"
                )
            except Exception as e:
                st.warning(f"PDF nicht verfügbar: {str(e)}")

            if ma_dienste:
                for dienst in sorted(ma_dienste, key=lambda x: (x['datum'], x.get('start_zeit', '00:00'))):
                    datum_obj = date.fromisoformat(dienst['datum'])
                    wt = WOCHENTAGE_DE[datum_obj.weekday()]
                    typ = dienst.get('schichttyp', 'arbeit')
                    typ_info = SCHICHTTYPEN.get(typ, SCHICHTTYPEN['arbeit'])
                    edit_key = f"edit_dienst_{dienst['id']}"

                    col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 1, 1], gap="small")

                    with col1:
                        st.write(f"**{datum_obj.strftime('%d.%m.%Y')}**")
                        st.caption(wt)

                    with col2:
                        st.markdown(
                            f"<span style='background:{typ_info['farbe']}; "
                            f"color:{typ_info.get('text_farbe', '#ffffff')}; "
                            f"padding:2px 8px; border-radius:4px; font-size:0.85rem;'>"
                            f"{typ_info['label']}</span>",
                            unsafe_allow_html=True
                        )

                    with col3:
                        if typ == 'arbeit':
                            if dienst.get('schichtvorlage_id') and dienst['schichtvorlage_id'] in vorlagen_dict:
                                vn = vorlagen_dict[dienst['schichtvorlage_id']]['name']
                                st.caption(vn)
                            st.write(f"{dienst['start_zeit'][:5]} - {dienst['ende_zeit'][:5]}")
                        elif typ == 'urlaub':
                            st.write("Urlaub")
                        elif typ == 'krank':
                            lfz_h = dienst.get('urlaub_stunden') or 0
                            st.write(f"Krank (LFZ: {lfz_h:.1f}h)")
                        else:
                            st.write("Frei")

                    with col4:
                        if st.button("Bearbeiten", key=f"edit_btn_{dienst['id']}", help="Direkt bearbeiten"):
                            st.session_state[edit_key] = not st.session_state.get(edit_key, False)

                    with col5:
                        with st.popover("Löschen", use_container_width=True):
                            do_delete_direct = st.button(
                                "Eintrag löschen",
                                key=f"del_confirm_direct_{dienst['id']}",
                                use_container_width=True,
                            )
                            if do_delete_direct:
                                try:
                                    old_data = {
                                        "datum": dienst.get("datum"),
                                        "schichttyp": dienst.get("schichttyp"),
                                        "start_zeit": dienst.get("start_zeit"),
                                        "ende_zeit": dienst.get("ende_zeit"),
                                        "pause_minuten": dienst.get("pause_minuten"),
                                        "urlaub_stunden": dienst.get("urlaub_stunden"),
                                    }
                                    supabase.table(planning_table).delete().eq('id', dienst['id']).execute()
                                    _audit_dienstplan_change(
                                        action="dienstplan_loeschung",
                                        dienst_id=int(dienst["id"]),
                                        mitarbeiter_id=int(mitarbeiter["id"]),
                                        alter_wert=old_data,
                                        neuer_wert=None,
                                        begruendung="Dienstplan-Löschung",
                                    )
                                    _refresh_after_write()
                                    st.success("Eintrag gelöscht.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler: {str(e)}")

                    # Inline-Bearbeitungsformular
                    if st.session_state.get(edit_key, False):
                        with st.container():
                            st.markdown(
                                "<div style='background:#f0f4ff;padding:12px;border-radius:8px;"
                                "border-left:4px solid #1f2937;margin:4px 0 8px 0;color:#1f2937;'>",
                                unsafe_allow_html=True,
                            )
                            with st.form(key=f"form_edit_{dienst['id']}"):
                                st.markdown(f"**Dienst bearbeiten: {datum_obj.strftime('%d.%m.%Y')} ({wt})**")
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    neuer_typ = st.selectbox(
                                        "Schichttyp",
                                        options=list(SCHICHTTYPEN.keys()),
                                        index=list(SCHICHTTYPEN.keys()).index(typ) if typ in SCHICHTTYPEN else 0,
                                        format_func=lambda x: SCHICHTTYPEN[x]['label'],
                                        key=f"typ_edit_{dienst['id']}"
                                    )
                                with ec2:
                                    neues_datum = st.date_input(
                                        "Datum",
                                        value=datum_obj,
                                        key=f"datum_edit_{dienst['id']}"
                                    )
                                ec3, ec4 = st.columns(2)
                                with ec3:
                                    start_val = dienst.get('start_zeit', '08:00')[:5] if dienst.get('start_zeit') else '08:00'
                                    neue_start = st.text_input("Startzeit (HH:MM)", value=start_val, key=f"start_edit_{dienst['id']}")
                                with ec4:
                                    ende_val = dienst.get('ende_zeit', '16:00')[:5] if dienst.get('ende_zeit') else '16:00'
                                    neue_ende = st.text_input("Endzeit (HH:MM)", value=ende_val, key=f"ende_edit_{dienst['id']}")
                                sb1, sb2 = st.columns(2)
                                with sb1:
                                    speichern = st.form_submit_button("Speichern", use_container_width=True)
                                with sb2:
                                    abbrechen = st.form_submit_button("Abbrechen", use_container_width=True)
                                if speichern:
                                    try:
                                        update_data = {
                                            'datum': neues_datum.isoformat(),
                                            'schichttyp': neuer_typ,
                                            'start_zeit': neue_start + ':00' if len(neue_start) == 5 else neue_start,
                                            'ende_zeit': neue_ende + ':00' if len(neue_ende) == 5 else neue_ende,
                                        }
                                        old_data = {
                                            "datum": dienst.get("datum"),
                                            "schichttyp": dienst.get("schichttyp"),
                                            "start_zeit": dienst.get("start_zeit"),
                                            "ende_zeit": dienst.get("ende_zeit"),
                                            "pause_minuten": dienst.get("pause_minuten"),
                                            "urlaub_stunden": dienst.get("urlaub_stunden"),
                                        }
                                        supabase.table(planning_table).update(update_data).eq('id', dienst['id']).execute()
                                        _audit_dienstplan_change(
                                            action="dienstplan_korrektur",
                                            dienst_id=int(dienst["id"]),
                                            mitarbeiter_id=int(mitarbeiter["id"]),
                                            alter_wert=old_data,
                                            neuer_wert=update_data,
                                            begruendung="Dienstplan-Korrektur",
                                        )
                                        _refresh_after_write()
                                        st.session_state[edit_key] = False
                                        st.success("Dienst aktualisiert.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Fehler beim Speichern: {str(e)}")
                                if abbrechen:
                                    st.session_state[edit_key] = False
                                    st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Keine Einträge für diesen Monat.")


# ============================================================
# MONATSÜBERSICHT (TABELLE)
# ============================================================

def show_monatsuebersicht_tabelle(supabase):
    """Zeigt Monatsübersicht aller Mitarbeiter in Tabellenform"""
    planning_table = resolve_planning_table(supabase)

    st.subheader("Monatsübersicht (Tabelle)")
    st.info("Übersicht aller Mitarbeiter – Geplant, Urlaub, Frei, Krank (Ruhetage ohne Eintrag zählen als Frei).")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024, key="tabelle_jahr")
    with col2:
        monat = st.selectbox("Monat", range(1, 13), index=date.today().month - 1,
                             format_func=lambda x: MONATE_DE[x], key="tabelle_monat")
    with col3:
        if st.button("Aktualisieren", use_container_width=True, key="tabelle_refresh"):
            st.rerun()

    mitarbeiter_liste = _cached_mitarbeiter(st.session_state.betrieb_id)
    if not mitarbeiter_liste:
        st.warning("Keine Mitarbeiter gefunden.")
        return

    schichtvorlagen_rows = _cached_schichtvorlagen(st.session_state.betrieb_id)
    vorlagen_dict = {v['id']: v for v in schichtvorlagen_rows} if schichtvorlagen_rows else {}

    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])

    dienstplaene_rows = _cached_monatsdienste(
        planning_table,
        st.session_state.betrieb_id,
        erster_tag.isoformat(),
        letzter_tag.isoformat(),
    )

    dienste_map = {}
    if dienstplaene_rows:
        for d in dienstplaene_rows:
            key = (d['mitarbeiter_id'], d['datum'])
            if key not in dienste_map:
                dienste_map[key] = []
            dienste_map[key].append(d)

    # Genehmigte Urlaube als Fallback (falls nicht im Dienstplan)
    urlaub_rows = _cached_genehmigte_urlaube(
        st.session_state.betrieb_id,
        erster_tag.isoformat(),
        letzter_tag.isoformat(),
    )
    urlaub_map = _build_urlaub_map_from_rows(urlaub_rows, erster_tag, letzter_tag)

    vorlagen_arbeit = [v for v in vorlagen_dict.values() if not v.get("ist_urlaub")]
    if vorlagen_arbeit:
        vorlage_quickpick = st.selectbox(
            "1-Klick-Vorlage für Monatsübersicht",
            options=[None] + [v["id"] for v in vorlagen_arbeit],
            format_func=lambda x: "Keine" if x is None else next((v["name"] for v in vorlagen_arbeit if v["id"] == x), ""),
            help="Wenn gewählt, setzt ein Klick auf eine Tageszelle direkt diese Schichtvorlage.",
            key="tabelle_quickpick_vorlage",
        )
    else:
        vorlage_quickpick = None
        st.caption("Keine Arbeits-Schichtvorlagen vorhanden.")

    _render_download_center(mitarbeiter_liste, dienste_map, jahr, monat, key_prefix="tabelle")
    st.markdown("---")

    anzahl_tage = calendar.monthrange(jahr, monat)[1]

    st.markdown(
        """
        <style>
        .dp-month-table-wrap {
            overflow-x: auto;
            overflow-y: hidden;
            border: 1px solid #2a2a2a;
            border-radius: 10px;
            background: #0b0b0b;
            padding: 0;
            margin: 0.35rem 0 0.6rem 0;
        }
        .dp-month-table {
            border-collapse: separate;
            border-spacing: 0;
            width: max-content;
            min-width: 100%;
            table-layout: fixed;
        }
        .dp-month-table th, .dp-month-table td {
            min-width: 112px;
            max-width: 112px;
            width: 112px;
            padding: 6px 8px;
            text-align: center;
            vertical-align: middle;
            border-bottom: 1px solid #1f2937;
            border-right: 1px solid #1f2937;
            font-size: 0.78rem;
            line-height: 1.15rem;
            white-space: nowrap;
        }
        .dp-month-table th {
            position: sticky;
            top: 0;
            z-index: 3;
            background: #111827;
            color: #ffffff;
            font-weight: 700;
        }
        .dp-month-table th:first-child,
        .dp-month-table td:first-child {
            position: sticky;
            left: 0;
            z-index: 4;
            min-width: 230px;
            max-width: 230px;
            width: 230px;
            text-align: left;
            font-weight: 700;
            background: #0f172a;
            color: #ffffff;
        }
        .dp-cell-geplant { background: #1e3a8a; color: #ffffff; font-weight: 600; }
        .dp-cell-urlaub  { background: #fde68a; color: #000000; font-weight: 600; }
        .dp-cell-frei    { background: #e5e7eb; color: #000000; font-weight: 600; }
        .dp-cell-krank   { background: #fdba74; color: #000000; font-weight: 600; }
        .dp-cell-ruhetag { background: #1f2937; color: #ffffff; }
        .dp-cell-leer    { background: #111827; color: #ffffff; }
        .dp-month-table tr:last-child td { border-bottom: none; }
        .dp-month-table th:last-child, .dp-month-table td:last-child { border-right: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Monatsübersicht ist horizontal scrollbar. Die Mitarbeiter-Spalte bleibt beim Scrollen fixiert.")

    def _cell_state_label(ma: dict, tag_datum: date) -> tuple[str, str]:
        key = (ma["id"], tag_datum.isoformat())
        eintraege = sorted(dienste_map.get(key, []), key=lambda x: x.get("start_zeit", "00:00"))
        if eintraege:
            typen = [d.get("schichttyp", "arbeit") for d in eintraege]
            if "urlaub" in typen:
                stunden = float(next((d.get("urlaub_stunden") or 0.0) for d in eintraege if d.get("schichttyp") == "urlaub"))
                return ("dp-cell-urlaub", f"Urlaub {stunden:.1f}h")
            if "krank" in typen:
                lfz_h = float(next((d.get("urlaub_stunden") or 0.0) for d in eintraege if d.get("schichttyp") == "krank"))
                return ("dp-cell-krank", f"Krank {lfz_h:.1f}h")
            if "frei" in typen:
                return ("dp-cell-frei", "Frei")
            arbeit = [d for d in eintraege if d.get("schichttyp", "arbeit") == "arbeit"]
            if len(arbeit) > 1:
                zeit = " | ".join(f"{d.get('start_zeit', '')[:5]}-{d.get('ende_zeit', '')[:5]}" for d in arbeit)
                return ("dp-cell-geplant", f"Geplant {zeit}")
            if arbeit:
                return ("dp-cell-geplant", f"Geplant {arbeit[0].get('start_zeit', '')[:5]}-{arbeit[0].get('ende_zeit', '')[:5]}")
            return ("dp-cell-leer", "+")
        if key in urlaub_map:
            return ("dp-cell-urlaub", "Urlaub offen")
        if tag_datum.weekday() in [0, 1]:
            return ("dp-cell-ruhetag", "Ruhetag")
        return ("dp-cell-leer", "—")

    table_parts: list[str] = ["<div class='dp-month-table-wrap'><table class='dp-month-table'><thead><tr>"]
    table_parts.append("<th>Mitarbeiter</th>")
    for tag in range(1, anzahl_tage + 1):
        tag_datum = date(jahr, monat, tag)
        wt_kurz = WOCHENTAGE_KURZ[tag_datum.weekday()]
        table_parts.append(f"<th>{tag:02d}<br><span style='font-size:0.68rem;'>{wt_kurz}</span></th>")
    table_parts.append("</tr></thead><tbody>")

    for ma in mitarbeiter_liste:
        ma_name = html.escape(f"{ma['vorname']} {ma['nachname']}")
        table_parts.append(f"<tr><td>{ma_name}</td>")
        for tag in range(1, anzahl_tage + 1):
            tag_datum = date(jahr, monat, tag)
            css_cls, label = _cell_state_label(ma, tag_datum)
            table_parts.append(f"<td class='{css_cls}'>{html.escape(label)}</td>")
        table_parts.append("</tr>")

    table_parts.append("</tbody></table></div>")
    st.markdown("".join(table_parts), unsafe_allow_html=True)

    st.markdown("### Dienst im Feld bearbeiten")
    b1, b2, b3 = st.columns([2, 2, 1.4], gap="small")
    with b1:
        selected_ma_id = st.selectbox(
            "Mitarbeiter",
            options=[m["id"] for m in mitarbeiter_liste],
            format_func=lambda x: next((f"{m['vorname']} {m['nachname']}" for m in mitarbeiter_liste if m["id"] == x), ""),
            key=f"table_edit_ma_{jahr}_{monat}",
        )
    with b2:
        selected_day = st.date_input(
            "Datum",
            value=erster_tag,
            min_value=erster_tag,
            max_value=letzter_tag,
            format="DD.MM.YYYY",
            key=f"table_edit_day_{jahr}_{monat}",
        )
    with b3:
        open_editor = st.button("Bearbeiten öffnen", use_container_width=True, key=f"table_edit_open_{jahr}_{monat}")

    if open_editor:
        if vorlage_quickpick is not None:
            quick_vorlage = vorlagen_dict.get(vorlage_quickpick)
            ma_sel = next((m for m in mitarbeiter_liste if m["id"] == selected_ma_id), None)
            if quick_vorlage and ma_sel:
                try:
                    _apply_schichtvorlage_one_click(
                        supabase=supabase,
                        planning_table=planning_table,
                        betrieb_id=st.session_state.betrieb_id,
                        mitarbeiter=ma_sel,
                        datum_iso=selected_day.isoformat(),
                        vorlage=quick_vorlage,
                    )
                    _refresh_after_write()
                    st.success(
                        f"{quick_vorlage['name']} gesetzt: {ma_sel['vorname']} {ma_sel['nachname']} · {selected_day.strftime('%d.%m.%Y')}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Vorlage konnte nicht gesetzt werden: {str(e)}")
                    st.stop()

        st.session_state["tabelle_cell_editor"] = {
            "ma_id": int(selected_ma_id),
            "datum": selected_day.isoformat(),
            "jahr": jahr,
            "monat": monat,
        }
        st.rerun()

    active_editor = st.session_state.get("tabelle_cell_editor")
    if active_editor and (
        int(active_editor.get("jahr") or 0) != int(jahr) or int(active_editor.get("monat") or 0) != int(monat)
    ):
        st.session_state["tabelle_cell_editor"] = None
        active_editor = None

    if active_editor:
        @st.dialog("Dienst im Feld bearbeiten")
        def _cell_editor_dialog():
            ma_id = int(active_editor.get("ma_id"))
            datum_iso = str(active_editor.get("datum"))
            datum_obj = date.fromisoformat(datum_iso)
            ma = next((m for m in mitarbeiter_liste if m["id"] == ma_id), None)
            if not ma:
                st.error("Mitarbeiter nicht gefunden.")
                if st.button("Schließen", key="cell_editor_close_missing"):
                    st.session_state["tabelle_cell_editor"] = None
                    st.rerun()
                return

            st.markdown(f"**{ma['vorname']} {ma['nachname']}** – {datum_obj.strftime('%d.%m.%Y')} ({WOCHENTAGE_DE[datum_obj.weekday()]})")

            fresh_resp = (
                supabase.table(planning_table)
                .select("id, schichttyp, start_zeit, ende_zeit, pause_minuten, urlaub_stunden")
                .eq("betrieb_id", st.session_state.betrieb_id)
                .eq("mitarbeiter_id", ma_id)
                .eq("datum", datum_iso)
                .order("start_zeit")
                .execute()
            )
            bestehende = fresh_resp.data or []

            if bestehende:
                st.success(f"{len(bestehende)} bestehende(r) Dienst(e) gefunden.")
                for dienst in bestehende:
                    typ_b = dienst.get("schichttyp", "arbeit")
                    with st.form(key=f"cell_edit_form_{dienst['id']}"):
                        st.markdown(f"**Dienst #{dienst['id']}**")
                        fc1, fc2, fc3 = st.columns(3)
                        with fc1:
                            neuer_typ = st.selectbox(
                                "Typ",
                                options=list(SCHICHTTYPEN.keys()),
                                index=list(SCHICHTTYPEN.keys()).index(typ_b) if typ_b in SCHICHTTYPEN else 0,
                                format_func=lambda x: SCHICHTTYPEN[x]["label"],
                                key=f"cell_typ_{dienst['id']}",
                            )
                        with fc2:
                            start_v = (dienst.get("start_zeit") or "08:00")[:5]
                            neue_start = st.text_input("Start (HH:MM)", value=start_v, key=f"cell_start_{dienst['id']}")
                        with fc3:
                            ende_v = (dienst.get("ende_zeit") or "16:00")[:5]
                            neue_ende = st.text_input("Ende (HH:MM)", value=ende_v, key=f"cell_ende_{dienst['id']}")

                        ec1, ec2 = st.columns(2)
                        with ec1:
                            pause_minuten = st.number_input(
                                "Pause (Min)",
                                min_value=0,
                                max_value=240,
                                value=int(dienst.get("pause_minuten") or 0),
                                step=5,
                                key=f"cell_pause_{dienst['id']}",
                            )
                        with ec2:
                            stunden_sonder = st.number_input(
                                "Stunden (Urlaub/Krank)",
                                min_value=0.0,
                                max_value=24.0,
                                value=float(dienst.get("urlaub_stunden") or 0.0),
                                step=0.5,
                                format="%.2f",
                                key=f"cell_stunden_{dienst['id']}",
                            )

                        s1, s2 = st.columns(2)
                        with s1:
                            speichern = st.form_submit_button("Speichern", use_container_width=True)
                        with s2:
                            loeschen = st.form_submit_button("Löschen", use_container_width=True)

                        if speichern:
                            try:
                                if neuer_typ == "arbeit":
                                    update_data = {
                                        "schichttyp": neuer_typ,
                                        "start_zeit": neue_start + ":00" if len(neue_start) == 5 else neue_start,
                                        "ende_zeit": neue_ende + ":00" if len(neue_ende) == 5 else neue_ende,
                                        "pause_minuten": int(pause_minuten),
                                        "urlaub_stunden": 0.0,
                                    }
                                elif neuer_typ in ("urlaub", "krank"):
                                    update_data = {
                                        "schichttyp": neuer_typ,
                                        "start_zeit": "00:00:00",
                                        "ende_zeit": "00:00:00",
                                        "pause_minuten": 0,
                                        "urlaub_stunden": float(stunden_sonder),
                                    }
                                else:
                                    update_data = {
                                        "schichttyp": neuer_typ,
                                        "start_zeit": "00:00:00",
                                        "ende_zeit": "00:00:00",
                                        "pause_minuten": 0,
                                        "urlaub_stunden": 0.0,
                                    }
                                old_data = {
                                    "datum": dienst.get("datum"),
                                    "schichttyp": dienst.get("schichttyp"),
                                    "start_zeit": dienst.get("start_zeit"),
                                    "ende_zeit": dienst.get("ende_zeit"),
                                    "pause_minuten": dienst.get("pause_minuten"),
                                    "urlaub_stunden": dienst.get("urlaub_stunden"),
                                }
                                supabase.table(planning_table).update(update_data).eq("id", dienst["id"]).execute()
                                _audit_dienstplan_change(
                                    action="dienstplan_korrektur",
                                    dienst_id=int(dienst["id"]),
                                    mitarbeiter_id=int(ma_id),
                                    alter_wert=old_data,
                                    neuer_wert=update_data,
                                    begruendung="Dienstplan-Korrektur",
                                )
                                _refresh_after_write()
                                st.session_state["tabelle_cell_editor"] = None
                                st.success("Dienst gespeichert.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Speichern: {str(e)}")

                        if loeschen:
                            try:
                                old_data = {
                                    "datum": dienst.get("datum"),
                                    "schichttyp": dienst.get("schichttyp"),
                                    "start_zeit": dienst.get("start_zeit"),
                                    "ende_zeit": dienst.get("ende_zeit"),
                                    "pause_minuten": dienst.get("pause_minuten"),
                                    "urlaub_stunden": dienst.get("urlaub_stunden"),
                                }
                                supabase.table(planning_table).delete().eq("id", dienst["id"]).execute()
                                _audit_dienstplan_change(
                                    action="dienstplan_loeschung",
                                    dienst_id=int(dienst["id"]),
                                    mitarbeiter_id=int(ma_id),
                                    alter_wert=old_data,
                                    neuer_wert=None,
                                    begruendung="Dienstplan-Löschung",
                                )
                                _refresh_after_write()
                                st.session_state["tabelle_cell_editor"] = None
                                st.success("Dienst gelöscht.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Löschen: {str(e)}")

                st.markdown("---")
                st.markdown("**Zusätzlichen Dienst anlegen**")

            with st.form(key=f"cell_new_form_{ma_id}_{datum_iso}"):
                n1, n2, n3 = st.columns(3)
                with n1:
                    neuer_typ = st.selectbox(
                        "Neuer Typ",
                        options=list(SCHICHTTYPEN.keys()),
                        format_func=lambda x: SCHICHTTYPEN[x]["label"],
                        key=f"cell_new_typ_{ma_id}_{datum_iso}",
                    )
                with n2:
                    neue_start = st.text_input("Start (HH:MM)", value="08:00", key=f"cell_new_start_{ma_id}_{datum_iso}")
                with n3:
                    neue_ende = st.text_input("Ende (HH:MM)", value="16:00", key=f"cell_new_ende_{ma_id}_{datum_iso}")

                p1, p2 = st.columns(2)
                with p1:
                    neue_pause = st.number_input(
                        "Pause (Min)",
                        min_value=0,
                        max_value=240,
                        value=0,
                        step=5,
                        key=f"cell_new_pause_{ma_id}_{datum_iso}",
                    )
                with p2:
                    neue_stunden = st.number_input(
                        "Stunden (Urlaub/Krank)",
                        min_value=0.0,
                        max_value=24.0,
                        value=0.0,
                        step=0.5,
                        format="%.2f",
                        key=f"cell_new_stunden_{ma_id}_{datum_iso}",
                    )

                anlegen = st.form_submit_button("Anlegen", use_container_width=True, type="primary")
                if anlegen:
                    try:
                        if neuer_typ == "arbeit":
                            payload = {
                                "betrieb_id": st.session_state.betrieb_id,
                                "mitarbeiter_id": ma_id,
                                "datum": datum_iso,
                                "schichttyp": neuer_typ,
                                "start_zeit": neue_start + ":00" if len(neue_start) == 5 else neue_start,
                                "ende_zeit": neue_ende + ":00" if len(neue_ende) == 5 else neue_ende,
                                "pause_minuten": int(neue_pause),
                                "urlaub_stunden": 0.0,
                            }
                        elif neuer_typ in ("urlaub", "krank"):
                            payload = {
                                "betrieb_id": st.session_state.betrieb_id,
                                "mitarbeiter_id": ma_id,
                                "datum": datum_iso,
                                "schichttyp": neuer_typ,
                                "start_zeit": "00:00:00",
                                "ende_zeit": "00:00:00",
                                "pause_minuten": 0,
                                "urlaub_stunden": float(neue_stunden),
                            }
                        else:
                            payload = {
                                "betrieb_id": st.session_state.betrieb_id,
                                "mitarbeiter_id": ma_id,
                                "datum": datum_iso,
                                "schichttyp": neuer_typ,
                                "start_zeit": "00:00:00",
                                "ende_zeit": "00:00:00",
                                "pause_minuten": 0,
                                "urlaub_stunden": 0.0,
                            }
                        insert_res = supabase.table(planning_table).insert(payload).execute()
                        new_id = (insert_res.data or [{}])[0].get("id") if hasattr(insert_res, "data") else None
                        if new_id is not None:
                            _audit_dienstplan_change(
                                action="dienstplan_anlage",
                                dienst_id=int(new_id),
                                mitarbeiter_id=int(ma_id),
                                alter_wert=None,
                                neuer_wert=payload,
                                begruendung="Dienstplan-Anlage",
                            )
                        _refresh_after_write()
                        st.session_state["tabelle_cell_editor"] = None
                        st.success("Dienst angelegt.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Anlegen: {str(e)}")

            if st.button("Schließen", key=f"cell_editor_close_{ma_id}_{datum_iso}", use_container_width=True):
                st.session_state["tabelle_cell_editor"] = None
                st.rerun()

        _cell_editor_dialog()

    # Legende
    st.markdown("---")
    st.markdown("**Legende:**")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown("**A** = Arbeit")
    with col2:
        st.markdown("**U** = Urlaub (im Plan)")
    with col3:
        st.markdown("**U*** = Urlaub genehmigt, fehlt im Plan")
    with col4:
        st.markdown("**F** = Frei")
    with col5:
        st.markdown("**–** = Ruhetag (Mo/Di)")

    # CSV-Export
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Als CSV exportieren", use_container_width=True):
            csv_data = "Mitarbeiter," + ",".join([str(t) for t in range(1, anzahl_tage + 1)]) + "\n"
            for mitarbeiter in mitarbeiter_liste:
                row = f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}"
                for tag in range(1, anzahl_tage + 1):
                    tag_datum = date(jahr, monat, tag)
                    key = (mitarbeiter['id'], tag_datum.isoformat())
                    if key in dienste_map:
                        eintraege = sorted(dienste_map[key], key=lambda x: x.get('start_zeit', '00:00'))
                        typen = [d.get('schichttyp', 'arbeit') for d in eintraege]
                        if 'urlaub' in typen:
                            d = next(d for d in eintraege if d.get('schichttyp') == 'urlaub')
                            stunden = d.get('urlaub_stunden') or 0
                            row += f",U({stunden:.1f}h)"
                        elif 'frei' in typen:
                            row += ",F"
                        else:
                            arbeit_eintraege = [d for d in eintraege if d.get('schichttyp', 'arbeit') == 'arbeit']
                            zeiten = '|'.join(f"{d['start_zeit'][:5]}-{d['ende_zeit'][:5]}" for d in arbeit_eintraege)
                            row += f",A {zeiten}"
                    elif key in urlaub_map:
                        row += ",U*"
                    elif tag_datum.weekday() in [0, 1]:
                        row += ",-"
                    else:
                        row += ","
                csv_data += row + "\n"

            st.download_button(
                label="CSV herunterladen",
                data=csv_data.encode('utf-8-sig'),
                file_name=f"dienstplan_{MONATE_DE[monat]}_{jahr}.csv",
                mime="text/csv",
                use_container_width=True
            )
    with col2:
        st.info("PDF-Downloads finden Sie oben im Download-Center.")
    
    # ============================================================
    # DIENSTPLAN-VERÖFFENTLICHUNG: E-Mail an alle Mitarbeiter
    # ============================================================
    st.markdown("---")
    st.markdown("### Dienstplan veröffentlichen und Mitarbeiter benachrichtigen")
    st.info("Dieser Button sendet eine E-Mail an ALLE Mitarbeiter mit E-Mail-Adresse. "
            "Die Nachricht enthält einen Vorbehalt-Hinweis und den Link zur App.")
    
    col_mail1, col_mail2 = st.columns([2, 1])
    with col_mail1:
        vorbehalt_aktiv = st.checkbox(
            "Vorbehalt-Hinweis einfügen (Endzeiten richten sich nach wirtschaftlichem Betriebsende)",
            value=True,
            key="dienstplan_vorbehalt"
        )
    with col_mail2:
        if st.button("Dienstplan veröffentlichen und E-Mails senden",
                     use_container_width=True, type="primary", key="dienstplan_publish_email"):
            try:
                from utils.email_service import send_dienstplan_veroeffentlichung_alle
                ergebnis = send_dienstplan_veroeffentlichung_alle(
                    mitarbeiter_liste=mitarbeiter_liste,
                    monat=MONATE_DE[monat],
                    jahr=jahr,
                    hinweis_vorbehalt=vorbehalt_aktiv
                )
                gesendet = ergebnis.get('gesendet', 0)
                fehlgeschlagen = ergebnis.get('fehlgeschlagen', 0)
                keine_email = ergebnis.get('keine_email', 0)
                if gesendet > 0:
                    st.success(f"{gesendet} E-Mail(s) erfolgreich gesendet!"
                               f"{f' | {fehlgeschlagen} fehlgeschlagen' if fehlgeschlagen else ''}"
                               f"{f' | {keine_email} ohne E-Mail' if keine_email else ''}")
                else:
                    st.warning(f"Keine E-Mails gesendet. "
                               f"Fehlgeschlagen: {fehlgeschlagen}, Ohne E-Mail: {keine_email}")
            except Exception as e:
                st.error(f"E-Mail-Fehler: {str(e)}")


# ============================================================
# SCHICHTVORLAGEN
# ============================================================

def show_schichtvorlagen(supabase):
    """Zeigt die Schichtvorlagen-Verwaltung an"""

    st.subheader("Schichtvorlagen")
    st.info("Erstellen Sie wiederverwendbare Schichtvorlagen (z.B. Frühschicht, Spätschicht) für schnellere Dienstplanung.")

    vorlagen = supabase.table('schichtvorlagen').select(
        'id,name,beschreibung,start_zeit,ende_zeit,pause_minuten,farbe,ist_urlaub'
    ).eq(
        'betrieb_id', st.session_state.betrieb_id
    ).order('name').execute()

    with st.expander("Neue Schichtvorlage erstellen", expanded=False):
        with st.form("neue_vorlage_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Name", placeholder="z.B. Frühschicht")
                beschreibung = st.text_area("Beschreibung (optional)")
                ist_urlaub = st.checkbox("Urlaub-Schicht (keine festen Zeiten)",
                                         help="Für Urlaubstage – Stunden werden aus Mitarbeiterprofil berechnet")

            with col2:
                if not ist_urlaub:
                    start_zeit = st.time_input("Startzeit",
                                               value=datetime.strptime("08:00", "%H:%M").time(),
                                               key="neue_vorlage_start")
                    ende_zeit = st.time_input("Endzeit",
                                              value=datetime.strptime("16:00", "%H:%M").time(),
                                              key="neue_vorlage_ende")
                    if start_zeit and ende_zeit:
                        pause_minuten = st.number_input("Pause (Minuten)", min_value=0, max_value=240,
                                                        value=0, step=5,
                                                        help="Pause wird manuell eingetragen")
                    else:
                        pause_minuten = 0
                else:
                    st.info("Bei Urlaub werden Zeiten automatisch aus Mitarbeiterprofil berechnet")
                    start_zeit = datetime.strptime("00:00", "%H:%M").time()
                    ende_zeit = datetime.strptime("00:00", "%H:%M").time()
                    pause_minuten = 0

            farbe = st.color_picker("Farbe für Kalender",
                                    value="#ffeb3b" if ist_urlaub else "#0d6efd")

            if st.form_submit_button("Vorlage speichern", use_container_width=True) and name:
                try:
                    supabase.table('schichtvorlagen').insert({
                        'betrieb_id': st.session_state.betrieb_id,
                        'name': name,
                        'beschreibung': beschreibung if beschreibung else None,
                        'start_zeit': start_zeit.strftime('%H:%M:%S'),
                        'ende_zeit': ende_zeit.strftime('%H:%M:%S'),
                        'pause_minuten': pause_minuten,
                        'farbe': farbe,
                        'ist_urlaub': ist_urlaub
                    }).execute()
                    _refresh_after_write()
                    st.success("Schichtvorlage erstellt.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {str(e)}")

    st.markdown("---")

    if vorlagen.data:
        st.markdown(f"**{len(vorlagen.data)} Schichtvorlagen**")
        for vorlage in vorlagen.data:
            with st.expander(f"{vorlage['name']}", expanded=False):
                edit_mode = st.session_state.get(f"edit_vorlage_{vorlage['id']}", False)

                if edit_mode:
                    with st.form(f"edit_vorlage_form_{vorlage['id']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            name = st.text_input("Name", value=vorlage['name'])
                            beschreibung = st.text_area("Beschreibung", value=vorlage.get('beschreibung', ''))
                        with col2:
                            _sv, _ = parse_zeit(vorlage['start_zeit'])
                            start_zeit = st.time_input("Startzeit", value=_sv)
                            _ev, _ = parse_zeit(vorlage['ende_zeit'])
                            ende_zeit = st.time_input("Endzeit", value=_ev)
                            pause_minuten = st.number_input("Pause (Min)", min_value=0, max_value=240,
                                                            value=vorlage.get('pause_minuten', 0), step=15)
                        farbe = st.color_picker("Farbe", value=vorlage.get('farbe', '#0d6efd'))

                        col_s, col_c = st.columns(2)
                        with col_s:
                            submit = st.form_submit_button("Speichern", use_container_width=True, type="primary")
                        with col_c:
                            cancel = st.form_submit_button("Abbrechen", use_container_width=True)

                        if submit and name:
                            try:
                                supabase.table('schichtvorlagen').update({
                                    'name': name,
                                    'beschreibung': beschreibung if beschreibung else None,
                                    'start_zeit': start_zeit.strftime('%H:%M:%S'),
                                    'ende_zeit': ende_zeit.strftime('%H:%M:%S'),
                                    'pause_minuten': pause_minuten,
                                    'farbe': farbe,
                                }).eq('id', vorlage['id']).execute()
                                _refresh_after_write()
                                st.session_state[f"edit_vorlage_{vorlage['id']}"] = False
                                st.success("Vorlage aktualisiert.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {str(e)}")
                        if cancel:
                            st.session_state[f"edit_vorlage_{vorlage['id']}"] = False
                            st.rerun()
                else:
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"**Zeiten:** {vorlage['start_zeit'][:5]} – {vorlage['ende_zeit'][:5]}")
                        if vorlage.get('pause_minuten', 0) > 0:
                            st.write(f"**Pause:** {vorlage['pause_minuten']} Min")
                        if vorlage.get('ist_urlaub'):
                            st.write("Urlaub-Schicht")
                    with col2:
                        if vorlage.get('beschreibung'):
                            st.write(f"**Beschreibung:** {vorlage['beschreibung']}")
                        st.markdown(
                            f"**Farbe:** <span style='background:{vorlage['farbe']}; "
                            f"padding:2px 10px; border-radius:3px; color:white;'>"
                            f"{vorlage['farbe']}</span>",
                            unsafe_allow_html=True
                        )
                    with col3:
                        if st.button("Bearbeiten", key=f"sv_edit_btn_{vorlage['id']}", help="Bearbeiten"):
                            st.session_state[f"edit_vorlage_{vorlage['id']}"] = True
                            st.rerun()
                        if st.button("Löschen", key=f"del_vorlage_{vorlage['id']}", help="Löschen"):
                            try:
                                supabase.table('schichtvorlagen').delete().eq('id', vorlage['id']).execute()
                                _refresh_after_write()
                                st.success("Vorlage gelöscht.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {str(e)}")
    else:
        st.info("Noch keine Schichtvorlagen vorhanden. Erstellen Sie Ihre erste Vorlage!")
