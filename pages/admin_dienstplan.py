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
from utils.database import get_supabase_client, get_all_mitarbeiter
from utils.calculations import (
    parse_zeit,
    berechne_arbeitsstunden_mit_pause
)

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
    'arbeit': {'label': '🔵 Arbeit',      'farbe': '#0d6efd', 'kuerzel': 'A'},
    'urlaub': {'label': '🟡 Urlaub',      'farbe': '#ffeb3b', 'kuerzel': 'U'},
    'frei':   {'label': '⚪ Frei',         'farbe': '#e9ecef', 'kuerzel': 'F'},
}

try:
    locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'de_DE')
    except:
        pass


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
            hd = [[logo, Paragraph("<b>Steakhouse Piccolo</b><br/>Dienstplan",
                   ParagraphStyle('h', fontSize=14, alignment=TA_LEFT))]]
        except:
            hd = [[Paragraph("<b>Steakhouse Piccolo</b>",
                   ParagraphStyle('h', fontSize=14, alignment=TA_LEFT))]]
    else:
        hd = [[Paragraph("<b>Steakhouse Piccolo</b>",
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

    col_widths = [2.5*cm, 3*cm, 3*cm, 3.5*cm, 2*cm, 3*cm]
    table_data = [["Datum", "Wochentag", "Typ", "Zeiten", "Pause", "Stunden"]]
    total_stunden = 0

    for dienst in dienstplaene:
        datum_obj = datetime.fromisoformat(dienst['datum']).date()
        wt = WOCHENTAGE_DE_PDF[datum_obj.weekday()]
        schichttyp = dienst.get('schichttyp', 'arbeit')

        if schichttyp == 'urlaub':
            std = float(dienst.get('urlaub_stunden') or 0)
            total_stunden += std
            table_data.append([datum_obj.strftime('%d.%m.%Y'), wt, "Urlaub",
                                f"{std:.1f}h Urlaub", "-", f"{std:.2f} h"])
        elif schichttyp == 'frei':
            table_data.append([datum_obj.strftime('%d.%m.%Y'), wt, "Frei",
                                "Freier Tag", "-", "-"])
        else:
            try:
                start = datetime.strptime(dienst['start_zeit'], '%H:%M:%S').time()
                ende = datetime.strptime(dienst['ende_zeit'], '%H:%M:%S').time()
                start_dt = datetime.combine(date.today(), start)
                ende_dt = datetime.combine(date.today(), ende)
                if ende_dt <= start_dt:
                    ende_dt += timedelta(days=1)
                std = (ende_dt - start_dt).total_seconds() / 3600
                pause_min = dienst.get('pause_minuten', 0) or 0
                std -= pause_min / 60
                total_stunden += std
                table_data.append([datum_obj.strftime('%d.%m.%Y'), wt, "Arbeit",
                                    f"{dienst['start_zeit'][:5]} - {dienst['ende_zeit'][:5]}",
                                    f"{pause_min} Min" if pause_min > 0 else "-",
                                    f"{std:.2f} h"])
            except:
                table_data.append([datum_obj.strftime('%d.%m.%Y'), wt, "Arbeit", "n.v.", "-", "-"])

    if not dienstplaene:
        table_data.append(["", "", "Keine Eintr\u00e4ge", "", "", ""])
    table_data.append(["", "", "", "Gesamt:", "", f"{total_stunden:.2f} h"])

    dark_blue = colors.HexColor('#1e1e3c')
    light_blue = colors.HexColor('#ebf0ff')
    urlaub_yellow = colors.HexColor('#fff3cd')
    frei_grey = colors.HexColor('#f0f0f0')

    t = Table(table_data, colWidths=col_widths)
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), dark_blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, light_blue]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('BACKGROUND', (0, -1), (-1, -1), dark_blue),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]
    for i, dienst in enumerate(dienstplaene, start=1):
        if dienst.get('schichttyp') == 'urlaub':
            ts.append(('BACKGROUND', (0, i), (-1, i), urlaub_yellow))
        elif dienst.get('schichttyp') == 'frei':
            ts.append(('BACKGROUND', (0, i), (-1, i), frei_grey))
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
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "piccolo_logo.jpeg")
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
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "piccolo_logo.jpeg")

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


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def lade_genehmigte_urlaube(supabase, betrieb_id: int, erster_tag: date, letzter_tag: date) -> dict:
    """
    Lädt alle genehmigten Urlaubsanträge für den Monat.
    Gibt ein Dict zurück: {(mitarbeiter_id, datum_str): urlaubsantrag_dict}
    """
    urlaube_resp = supabase.table('urlaubsantraege').select(
        'id, mitarbeiter_id, von_datum, bis_datum, anzahl_tage'
    ).eq('status', 'genehmigt').lte('von_datum', letzter_tag.isoformat()).gte(
        'bis_datum', erster_tag.isoformat()
    ).execute()

    urlaub_map = {}
    if urlaube_resp.data:
        for u in urlaube_resp.data:
            von = date.fromisoformat(u['von_datum'])
            bis = date.fromisoformat(u['bis_datum'])
            aktuell = von
            while aktuell <= bis:
                if erster_tag <= aktuell <= letzter_tag:
                    # Ruhetage (Mo/Di) nicht als Urlaubstag eintragen
                    if aktuell.weekday() not in [0, 1]:
                        urlaub_map[(u['mitarbeiter_id'], aktuell.isoformat())] = u
                aktuell += timedelta(days=1)
    return urlaub_map


def setze_urlaub_automatisch(supabase, betrieb_id: int, mitarbeiter_id: int,
                              urlaub_map: dict, erster_tag: date, letzter_tag: date,
                              mitarbeiter_soll_stunden: float) -> int:
    """
    Trägt genehmigte Urlaubstage automatisch in den Dienstplan ein.
    Überschreibt keine bestehenden Einträge.
    Gibt Anzahl neu eingetragener Tage zurück.
    """
    eingetragen = 0
    tage_pro_woche = 5  # Mi-So = 5 Arbeitstage
    stunden_pro_tag = mitarbeiter_soll_stunden / (tage_pro_woche * 4.33) if mitarbeiter_soll_stunden > 0 else 8.0

    for (ma_id, datum_str), urlaub in urlaub_map.items():
        if ma_id != mitarbeiter_id:
            continue

        # Prüfe ob bereits ein Eintrag existiert
        existing = supabase.table('dienstplaene').select('id').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('datum', datum_str).execute()

        if existing.data:
            continue  # Nicht überschreiben

        try:
            supabase.table('dienstplaene').insert({
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
            eingetragen += 1
        except Exception:
            pass

    return eingetragen


# ============================================================
# HAUPTFUNKTION
# ============================================================

def show_dienstplanung():
    """Zeigt die Dienstplanung für Administratoren an"""

    st.markdown('<div class="section-header">📅 Dienstplanung</div>', unsafe_allow_html=True)

    supabase = get_supabase_client()

    tabs = st.tabs(["📆 Monatsplan", "📊 Monatsübersicht (Tabelle)", "⚙️ Schichtvorlagen"])

    with tabs[0]:
        show_monatsplan(supabase)

    with tabs[1]:
        show_monatsuebersicht_tabelle(supabase)

    with tabs[2]:
        show_schichtvorlagen(supabase)


# ============================================================
# MONATSPLAN
# ============================================================

def show_monatsplan(supabase):
    """Zeigt den monatlichen Dienstplan mit Frei/Urlaub-Optionen"""

    st.subheader("📆 Monatlicher Dienstplan")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024)
    with col2:
        monat = st.selectbox("Monat", range(1, 13), index=date.today().month - 1,
                             format_func=lambda x: MONATE_DE[x])
    with col3:
        if st.button("🔄 Aktualisieren", use_container_width=True):
            st.rerun()

    mitarbeiter_liste = get_all_mitarbeiter()
    if not mitarbeiter_liste:
        st.warning("Keine Mitarbeiter gefunden.")
        return

    schichtvorlagen_resp = supabase.table('schichtvorlagen').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).execute()
    vorlagen_dict = {v['id']: v for v in schichtvorlagen_resp.data} if schichtvorlagen_resp.data else {}

    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])

    # Lade Dienstpläne
    dienstplaene_resp = supabase.table('dienstplaene').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).gte('datum', erster_tag.isoformat()).lte('datum', letzter_tag.isoformat()).execute()

    dienste_map = {}
    if dienstplaene_resp.data:
        for d in dienstplaene_resp.data:
            key = (d['mitarbeiter_id'], d['datum'])
            if key not in dienste_map:
                dienste_map[key] = []
            dienste_map[key].append(d)

    # Lade genehmigte Urlaube
    urlaub_map = lade_genehmigte_urlaube(supabase, st.session_state.betrieb_id, erster_tag, letzter_tag)

    st.markdown("---")

    # ── AUTOMATISCHE URLAUBSEINTRÄGE ──────────────────────────
    with st.expander("🔄 Genehmigte Urlaube automatisch in Dienstplan eintragen"):
        st.info(
            "Alle genehmigten Urlaubsanträge für diesen Monat werden automatisch als **Urlaub**-Einträge "
            "in den Dienstplan eingetragen. Bereits vorhandene Einträge werden **nicht** überschrieben."
        )

        col_a, col_b = st.columns(2)
        with col_a:
            auto_alle = st.button("📥 Alle Mitarbeiter – Urlaube eintragen", use_container_width=True, type="primary")
        with col_b:
            ma_auto = st.selectbox(
                "Oder nur für Mitarbeiter:",
                options=[None] + [m['id'] for m in mitarbeiter_liste],
                format_func=lambda x: "Alle" if x is None else next(
                    (f"{m['vorname']} {m['nachname']}" for m in mitarbeiter_liste if m['id'] == x), "")
            )
            auto_einzeln = st.button("📥 Urlaube eintragen", use_container_width=True)

        if auto_alle or auto_einzeln:
            gesamt = 0
            ziel_ids = [m['id'] for m in mitarbeiter_liste] if (auto_alle or ma_auto is None) else [ma_auto]
            for ma in mitarbeiter_liste:
                if ma['id'] not in ziel_ids:
                    continue
                soll = float(ma.get('monatliche_soll_stunden') or 160.0)
                n = setze_urlaub_automatisch(
                    supabase, st.session_state.betrieb_id, ma['id'],
                    urlaub_map, erster_tag, letzter_tag, soll
                )
                gesamt += n
            if gesamt > 0:
                st.success(f"✅ {gesamt} Urlaubstag(e) automatisch eingetragen!")
                st.rerun()
            else:
                st.info("Keine neuen Urlaubstage einzutragen (bereits vorhanden oder keine genehmigten Urlaube).")

    st.markdown("---")

    # ── SCHNELLPLANUNG ────────────────────────────────────────
    with st.expander("➕ Dienst / Urlaub / Frei hinzufügen"):
        st.info("📅 **Betriebszeiten:** Mittwoch – Sonntag | **Ruhetage:** Montag & Dienstag")

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
                st.warning(f"⚠️ {wt} ist ein Ruhetag!")

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
                    _, vorgeschlagene_pause = berechne_arbeitsstunden_mit_pause(start_z, ende_z)
                    pause_m = st.number_input("Pause (Min)", min_value=0, max_value=240,
                                              value=vorgeschlagene_pause, step=15)
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
        else:  # frei
            st.info("💡 Freie Tage werden ohne Lohn eingetragen.")
            start_z = datetime.strptime("00:00", "%H:%M").time()
            ende_z = datetime.strptime("00:00", "%H:%M").time()
            pause_m = 0
            vorlage_id = None
            urlaub_stunden = 0.0

        if st.button("✅ Eintragen", use_container_width=True, type="primary"):
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

                supabase.table('dienstplaene').insert(eintrag).execute()
                st.success(f"✅ {SCHICHTTYPEN[schichttyp]['label']} eingetragen!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {str(e)}")

    st.markdown("---")
    st.markdown(f"### {MONATE_DE[monat]} {jahr}")

    # ── MITARBEITER-ÜBERSICHT ─────────────────────────────────
    for mitarbeiter in mitarbeiter_liste:
        # Zähle Typen (alle Einträge aus der Listen-Map zusammenführen)
        ma_dienste_flat = []
        for key, eintraege in dienste_map.items():
            if key[0] == mitarbeiter['id']:
                ma_dienste_flat.extend(eintraege)
        ma_dienste = ma_dienste_flat
        arbeit_tage = sum(1 for d in ma_dienste if d.get('schichttyp', 'arbeit') == 'arbeit')
        urlaub_tage = sum(1 for d in ma_dienste if d.get('schichttyp') == 'urlaub')
        frei_tage   = sum(1 for d in ma_dienste if d.get('schichttyp') == 'frei')

        # Ausstehende Urlaube für diesen MA im Monat
        ausstehend = sum(1 for (ma_id, _) in urlaub_map if ma_id == mitarbeiter['id'])
        bereits_im_plan = len(set(d['datum'] for d in ma_dienste if d.get('schichttyp') == 'urlaub'))
        nicht_eingetragen = ausstehend - bereits_im_plan

        badge = ""
        if nicht_eingetragen > 0:
            badge = f" 🟡 {nicht_eingetragen} Urlaub(e) fehlen im Plan"

        with st.expander(
            f"👤 {mitarbeiter['vorname']} {mitarbeiter['nachname']} "
            f"| 🔵 {arbeit_tage} Arbeit  🟡 {urlaub_tage} Urlaub  ⚪ {frei_tage} Frei"
            + badge
        ):
            if nicht_eingetragen > 0:
                st.warning(
                    f"⚠️ {nicht_eingetragen} genehmigte(r) Urlaubstag(e) noch nicht im Dienstplan. "
                    f"Nutze 'Genehmigte Urlaube automatisch eintragen' oben."
                )

            # PDF-Download für einzelnen Mitarbeiter
            ma_dienste_sorted = sorted(ma_dienste, key=lambda x: (x['datum'], x.get('start_zeit', '00:00')))
            try:
                pdf_bytes = erstelle_einzelner_dienstplan_pdf(mitarbeiter, ma_dienste_sorted, jahr, monat)
                dateiname = f"Dienstplan_{mitarbeiter['nachname']}_{MONATE_DE[monat]}_{jahr}.pdf"
                st.download_button(
                    label=f"📥 Dienstplan als PDF herunterladen",
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

                    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])

                    with col1:
                        st.write(f"**{datum_obj.strftime('%d.%m.%Y')}**")
                        st.caption(wt)

                    with col2:
                        st.markdown(
                            f"<span style='background:{typ_info['farbe']}; "
                            f"padding:2px 8px; border-radius:4px; font-size:0.85rem;'>"
                            f"{typ_info['label']}</span>",
                            unsafe_allow_html=True
                        )

                    with col3:
                        if typ == 'arbeit':
                            if dienst.get('schichtvorlage_id') and dienst['schichtvorlage_id'] in vorlagen_dict:
                                vn = vorlagen_dict[dienst['schichtvorlage_id']]['name']
                                st.write(f"🏷️ {vn}")
                            st.write(f"⏰ {dienst['start_zeit'][:5]} – {dienst['ende_zeit'][:5]}")
                            if dienst.get('pause_minuten', 0) > 0:
                                st.caption(f"Pause: {dienst['pause_minuten']} Min")
                        elif typ == 'urlaub':
                            stunden = dienst.get('urlaub_stunden') or 0
                            st.write(f"🏖️ {stunden:.2f}h Urlaubsvergütung")
                        else:
                            st.write("Kein Lohn")

                    with col4:
                        if st.button("🗑️", key=f"del_{dienst['id']}", help="Löschen"):
                            try:
                                supabase.table('dienstplaene').delete().eq('id', dienst['id']).execute()
                                st.success("✅ Gelöscht!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {str(e)}")
            else:
                st.info("Keine Einträge für diesen Monat.")


# ============================================================
# MONATSÜBERSICHT (TABELLE)
# ============================================================

def show_monatsuebersicht_tabelle(supabase):
    """Zeigt Monatsübersicht aller Mitarbeiter in Tabellenform"""

    st.subheader("📊 Monatsübersicht (Tabelle)")
    st.info("💡 Übersicht aller Mitarbeiter – Arbeit (blau), Urlaub (gelb), Frei (grau), Ruhetag (–)")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024, key="tabelle_jahr")
    with col2:
        monat = st.selectbox("Monat", range(1, 13), index=date.today().month - 1,
                             format_func=lambda x: MONATE_DE[x], key="tabelle_monat")
    with col3:
        if st.button("🔄 Aktualisieren", use_container_width=True, key="tabelle_refresh"):
            st.rerun()

    mitarbeiter_liste = get_all_mitarbeiter()
    if not mitarbeiter_liste:
        st.warning("Keine Mitarbeiter gefunden.")
        return

    schichtvorlagen_resp = supabase.table('schichtvorlagen').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).execute()
    vorlagen_dict = {v['id']: v for v in schichtvorlagen_resp.data} if schichtvorlagen_resp.data else {}

    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])

    dienstplaene_resp = supabase.table('dienstplaene').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).gte('datum', erster_tag.isoformat()).lte('datum', letzter_tag.isoformat()).execute()

    dienste_map = {}
    if dienstplaene_resp.data:
        for d in dienstplaene_resp.data:
            key = (d['mitarbeiter_id'], d['datum'])
            if key not in dienste_map:
                dienste_map[key] = []
            dienste_map[key].append(d)

    # Genehmigte Urlaube als Fallback (falls nicht im Dienstplan)
    urlaub_map = lade_genehmigte_urlaube(supabase, st.session_state.betrieb_id, erster_tag, letzter_tag)

    st.markdown("---")

    anzahl_tage = calendar.monthrange(jahr, monat)[1]

    html = '<div style="overflow-x: auto;"><table style="width:100%; border-collapse: collapse; font-size: 0.82rem;">'
    html += '<thead><tr>'
    html += ('<th style="border:1px solid #ddd; padding:8px; background:#1e3a5f; color:white; '
             'position:sticky; left:0; z-index:10;">Mitarbeiter</th>')

    for tag in range(1, anzahl_tage + 1):
        tag_datum = date(jahr, monat, tag)
        wt_kurz = WOCHENTAGE_KURZ[tag_datum.weekday()]
        bg = '#888' if tag_datum.weekday() in [0, 1] else '#1e3a5f'
        html += (f'<th style="border:1px solid #ddd; padding:5px; background:{bg}; color:white; '
                 f'text-align:center; min-width:52px;">{tag}<br><small>{wt_kurz}</small></th>')

    html += '</tr></thead><tbody>'

    for mitarbeiter in mitarbeiter_liste:
        html += '<tr>'
        html += (f'<td style="border:1px solid #ddd; padding:8px; background:#f8f9fa; font-weight:bold; '
                 f'position:sticky; left:0; z-index:5;">'
                 f'{mitarbeiter["vorname"]} {mitarbeiter["nachname"]}</td>')

        for tag in range(1, anzahl_tage + 1):
            tag_datum = date(jahr, monat, tag)
            key = (mitarbeiter['id'], tag_datum.isoformat())

            if key in dienste_map:
                eintraege = sorted(dienste_map[key], key=lambda x: x.get('start_zeit', '00:00'))
                # Prüfe ob Urlaub oder Frei dabei ist (nur ein Eintrag erwartet)
                typen = [d.get('schichttyp', 'arbeit') for d in eintraege]

                if 'urlaub' in typen:
                    dienst = next(d for d in eintraege if d.get('schichttyp') == 'urlaub')
                    stunden = dienst.get('urlaub_stunden') or 0
                    html += (f'<td style="border:1px solid #ddd; padding:5px; text-align:center; '
                             f'background:#fff9c4;" title="Urlaub ({stunden}h)">'
                             f'<strong style="color:#856404;">U</strong>'
                             f'<br><small>{stunden:.1f}h</small></td>')

                elif 'frei' in typen:
                    html += (f'<td style="border:1px solid #ddd; padding:5px; text-align:center; '
                             f'background:#e9ecef;" title="Frei">'
                             f'<span style="color:#6c757d;">F</span></td>')

                else:  # arbeit (ggf. mehrere Schichten)
                    arbeit_eintraege = [d for d in eintraege if d.get('schichttyp', 'arbeit') == 'arbeit']
                    if len(arbeit_eintraege) == 1:
                        dienst = arbeit_eintraege[0]
                        if dienst.get('schichtvorlage_id') and dienst['schichtvorlage_id'] in vorlagen_dict:
                            vorlage = vorlagen_dict[dienst['schichtvorlage_id']]
                            kuerzel = vorlage['name'][:1].upper()
                            farbe = vorlage.get('farbe', '#0d6efd')
                            zeiten = f"{dienst['start_zeit'][:5]}–{dienst['ende_zeit'][:5]}"
                            title = f"{vorlage['name']}: {zeiten}"
                        else:
                            kuerzel = 'A'
                            farbe = '#0d6efd'
                            zeiten = f"{dienst['start_zeit'][:5]}–{dienst['ende_zeit'][:5]}"
                            title = f"Arbeit: {zeiten}"
                        html += (f'<td style="border:1px solid #ddd; padding:5px; text-align:center; '
                                 f'background:{farbe}22;" title="{title}">'
                                 f'<strong style="color:{farbe};">{kuerzel}</strong>'
                                 f'<br><small style="font-size:0.7rem;">{zeiten}</small></td>')
                    else:
                        # Mehrere Schichten an einem Tag
                        zeiten_list = [f"{d['start_zeit'][:5]}–{d['ende_zeit'][:5]}" for d in arbeit_eintraege]
                        title = ' | '.join(zeiten_list)
                        html += (f'<td style="border:1px solid #ddd; padding:3px; text-align:center; '
                                 f'background:#cfe2ff;" title="{title}">'
                                 f'<strong style="color:#0d6efd;">A²</strong>'
                                 f'<br>' + '<br>'.join(f'<small style="font-size:0.65rem;">{z}</small>' for z in zeiten_list) + '</td>')

            elif key in urlaub_map:
                # Urlaub genehmigt aber noch nicht im Dienstplan
                html += (f'<td style="border:1px solid #ddd; padding:5px; text-align:center; '
                         f'background:#fff3cd;" title="Urlaub (nicht im Plan)">'
                         f'<strong style="color:#856404;">U*</strong></td>')

            elif tag_datum.weekday() in [0, 1]:
                html += ('<td style="border:1px solid #ddd; padding:5px; text-align:center; '
                         'background:#f0f0f0; color:#aaa;">–</td>')
            else:
                html += '<td style="border:1px solid #ddd; padding:5px; text-align:center;"></td>'

        html += '</tr>'

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # Legende
    st.markdown("---")
    st.markdown("**Legende:**")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown("🔵 **A** = Arbeit")
    with col2:
        st.markdown("🟡 **U** = Urlaub (im Plan)")
    with col3:
        st.markdown("🟠 **U*** = Urlaub genehmigt, fehlt im Plan")
    with col4:
        st.markdown("⚪ **F** = Frei")
    with col5:
        st.markdown("**–** = Ruhetag (Mo/Di)")

    # CSV-Export
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Als CSV exportieren", use_container_width=True):
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
                label="💾 CSV herunterladen",
                data=csv_data.encode('utf-8-sig'),
                file_name=f"dienstplan_{MONATE_DE[monat]}_{jahr}.csv",
                mime="text/csv",
                use_container_width=True
            )
    with col2:
        if st.button("📄 Alle Dienstpläne als PDF", use_container_width=True, key="admin_pdf_alle"):
            try:
                pdf_bytes = erstelle_admin_dienstplan_pdf(mitarbeiter_liste, dienste_map, jahr, monat)
                st.download_button(
                    label="💾 PDF herunterladen",
                    data=pdf_bytes,
                    file_name=f"Dienstplan_Alle_{MONATE_DE[monat]}_{jahr}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="admin_pdf_alle_dl"
                )
            except Exception as e:
                st.error(f"PDF-Fehler: {str(e)}")


# ============================================================
# SCHICHTVORLAGEN
# ============================================================

def show_schichtvorlagen(supabase):
    """Zeigt die Schichtvorlagen-Verwaltung an"""

    st.subheader("⚙️ Schichtvorlagen")
    st.info("💡 Erstellen Sie wiederverwendbare Schichtvorlagen (z.B. Frühschicht, Spätschicht) für schnellere Dienstplanung.")

    vorlagen = supabase.table('schichtvorlagen').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).order('name').execute()

    with st.expander("➕ Neue Schichtvorlage erstellen", expanded=False):
        with st.form("neue_vorlage_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Name", placeholder="z.B. Frühschicht")
                beschreibung = st.text_area("Beschreibung (optional)")
                ist_urlaub = st.checkbox("🏖️ Urlaub-Schicht (keine festen Zeiten)",
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
                        brutto_stunden, vorgeschlagene_pause = berechne_arbeitsstunden_mit_pause(start_zeit, ende_zeit)
                        st.info(f"⚙️ Gesetzliche Pause: {vorgeschlagene_pause} Min (bei {brutto_stunden:.1f}h)")
                        pause_minuten = st.number_input("Pause (Minuten)", min_value=0, max_value=240,
                                                        value=vorgeschlagene_pause, step=15)
                    else:
                        pause_minuten = 0
                else:
                    st.info("💡 Bei Urlaub werden Zeiten automatisch aus Mitarbeiterprofil berechnet")
                    start_zeit = datetime.strptime("00:00", "%H:%M").time()
                    ende_zeit = datetime.strptime("00:00", "%H:%M").time()
                    pause_minuten = 0

            farbe = st.color_picker("Farbe für Kalender",
                                    value="#ffeb3b" if ist_urlaub else "#0d6efd")

            if st.form_submit_button("💾 Vorlage speichern", use_container_width=True) and name:
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
                    st.success("✅ Schichtvorlage erstellt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {str(e)}")

    st.markdown("---")

    if vorlagen.data:
        st.markdown(f"**{len(vorlagen.data)} Schichtvorlagen**")
        for vorlage in vorlagen.data:
            with st.expander(f"🏷️ {vorlage['name']}", expanded=False):
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
                            submit = st.form_submit_button("💾 Speichern", use_container_width=True, type="primary")
                        with col_c:
                            cancel = st.form_submit_button("❌ Abbrechen", use_container_width=True)

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
                                st.session_state[f"edit_vorlage_{vorlage['id']}"] = False
                                st.success("✅ Vorlage aktualisiert!")
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
                            st.write("🏖️ Urlaub-Schicht")
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
                        if st.button("✏️", key=f"edit_btn_{vorlage['id']}", help="Bearbeiten"):
                            st.session_state[f"edit_vorlage_{vorlage['id']}"] = True
                            st.rerun()
                        if st.button("🗑️", key=f"del_vorlage_{vorlage['id']}", help="Löschen"):
                            try:
                                supabase.table('schichtvorlagen').delete().eq('id', vorlage['id']).execute()
                                st.success("✅ Vorlage gelöscht!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {str(e)}")
    else:
        st.info("Noch keine Schichtvorlagen vorhanden. Erstellen Sie Ihre erste Vorlage!")
