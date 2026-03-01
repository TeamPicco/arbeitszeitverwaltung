"""
Zeitauswertung / Lohn – Modul für Mitarbeiter und Admin
Archiv-Ansicht, Monatsauswertung, Soll-Ist-Vergleich, Korrektur-Markierungen, PDF-Export
"""

import streamlit as st
from datetime import datetime, date, time, timedelta
from calendar import monthrange
import io

from utils.database import get_supabase_client
from utils.calculations import (
    berechne_arbeitsstunden,
    berechne_arbeitsstunden_mit_pause,
    berechne_gesetzliche_pause,
    berechne_grundlohn,
    berechne_sonntagszuschlag,
    berechne_feiertagszuschlag,
    is_sonntag,
    is_feiertag,
    parse_zeit,
    format_stunden,
    format_waehrung,
    get_wochentag,
    get_monatsnamen
)


MONATE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


def _lade_zeiterfassungen(mitarbeiter_id: int, monat: int, jahr: int) -> list:
    """Lädt alle Zeiterfassungen für einen Mitarbeiter in einem Monat."""
    supabase = get_supabase_client()
    erster = date(jahr, monat, 1).isoformat()
    letzter = date(jahr, monat, monthrange(jahr, monat)[1]).isoformat()
    r = supabase.table('zeiterfassung').select('*').eq(
        'mitarbeiter_id', mitarbeiter_id
    ).gte('datum', erster).lte('datum', letzter).order('datum').execute()
    return r.data or []


def _lade_dienstplaene(mitarbeiter_id: int, monat: int, jahr: int) -> list:
    """Lädt alle Dienstplan-Einträge (Soll) für einen Mitarbeiter in einem Monat."""
    supabase = get_supabase_client()
    erster = date(jahr, monat, 1).isoformat()
    letzter = date(jahr, monat, monthrange(jahr, monat)[1]).isoformat()
    r = supabase.table('dienstplaene').select('*').eq(
        'mitarbeiter_id', mitarbeiter_id
    ).gte('datum', erster).lte('datum', letzter).order('datum').execute()
    return r.data or []


def _berechne_zeile(z: dict, mitarbeiter: dict) -> dict:
    """Berechnet Stunden, Pausen und Lohn für eine Zeiterfassungszeile."""
    datum_obj = datetime.fromisoformat(z['datum']).date()
    wochentag = get_wochentag(datum_obj)
    
    # Stunden berechnen
    if z.get('ende_zeit'):
        s, _ = parse_zeit(z['start_zeit'])
        e, nt = parse_zeit(z['ende_zeit'])
        netto_stunden = berechne_arbeitsstunden(s, e, z.get('pause_minuten', 0), naechster_tag=nt)
    else:
        netto_stunden = 0.0
    
    # Zuschlagstyp bestimmen
    ist_so = is_sonntag(datum_obj)
    ist_ft = is_feiertag(datum_obj)
    
    # Lohnberechnung
    stundenlohn = mitarbeiter.get('stundenlohn_brutto', 0) or 0
    grundlohn = berechne_grundlohn(stundenlohn, netto_stunden)
    
    zuschlag_so = 0.0
    zuschlag_ft = 0.0
    if ist_so and mitarbeiter.get('sonntagszuschlag_aktiv', False):
        zuschlag_so = berechne_sonntagszuschlag(stundenlohn, netto_stunden)
    if ist_ft and mitarbeiter.get('feiertagszuschlag_aktiv', False):
        zuschlag_ft = berechne_feiertagszuschlag(stundenlohn, netto_stunden)
    
    # Korrektur-Flag
    korrigiert = bool(z.get('updated_at') and z.get('created_at') and
                      z['updated_at'] != z['created_at'])
    
    return {
        'id': z['id'],
        'datum': datum_obj,
        'datum_str': datum_obj.strftime('%d.%m.%Y'),
        'wochentag': wochentag,
        'start': z.get('start_zeit', '–'),
        'ende': z.get('ende_zeit', 'Offen'),
        'pause_min': z.get('pause_minuten', 0),
        'netto_stunden': netto_stunden,
        'ist_sonntag': ist_so,
        'ist_feiertag': ist_ft,
        'grundlohn': grundlohn,
        'zuschlag_so': zuschlag_so,
        'zuschlag_ft': zuschlag_ft,
        'gesamt_brutto': grundlohn + zuschlag_so + zuschlag_ft,
        'korrigiert': korrigiert,
        'notiz': z.get('notiz', '')
    }


def _berechne_soll_stunden(dienstplaene: list) -> float:
    """Berechnet die Soll-Stunden aus dem Dienstplan."""
    soll = 0.0
    for d in dienstplaene:
        if d.get('schichttyp') == 'arbeit' and d.get('start_zeit') and d.get('ende_zeit'):
            s, _ = parse_zeit(d['start_zeit'])
            e, nt = parse_zeit(d['ende_zeit'])
            pause = d.get('pause_minuten', 0) or 0
            soll += berechne_arbeitsstunden(s, e, pause, naechster_tag=nt)
        elif d.get('schichttyp') == 'urlaub' and d.get('urlaub_stunden'):
            soll += float(d['urlaub_stunden'])
    return soll


def _erstelle_pdf(mitarbeiter: dict, monat: int, jahr: int, zeilen: list,
                  soll_stunden: float, ist_stunden: float, gesamt_brutto: float) -> bytes:
    """Erstellt eine PDF-Monatsauswertung mit reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Titel
    titel_style = ParagraphStyle('titel', parent=styles['Heading1'],
                                  fontSize=16, alignment=TA_CENTER, spaceAfter=6)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'],
                                fontSize=11, alignment=TA_CENTER, spaceAfter=4)
    info_style = ParagraphStyle('info', parent=styles['Normal'],
                                 fontSize=9, spaceAfter=2)
    
    story.append(Paragraph("Zeitauswertung / Monatsnachweis", titel_style))
    story.append(Paragraph(f"{MONATE[monat-1]} {jahr}", sub_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"<b>Mitarbeiter:</b> {mitarbeiter['vorname']} {mitarbeiter['nachname']} &nbsp;&nbsp; "
        f"<b>Personal-Nr.:</b> {mitarbeiter.get('personalnummer', '–')}",
        info_style))
    story.append(Spacer(1, 0.5*cm))

    # Tabelle
    header = ['Datum', 'Tag', 'Von', 'Bis', 'Pause', 'Netto-h', 'Typ', 'Brutto €', 'Status']
    data = [header]
    
    for z in zeilen:
        typ = '🔵 Arbeit'
        if z['ist_feiertag']:
            typ = '🔴 Feiertag'
        elif z['ist_sonntag']:
            typ = '🟡 Sonntag'
        
        status = '✓ Korrigiert' if z['korrigiert'] else '✓ OK'
        
        data.append([
            z['datum_str'],
            z['wochentag'][:2],
            str(z['start'])[:5] if z['start'] != '–' else '–',
            str(z['ende'])[:5] if z['ende'] != 'Offen' else 'Offen',
            f"{z['pause_min']} Min",
            f"{z['netto_stunden']:.2f}",
            typ.replace('🔵 ', '').replace('🔴 ', '').replace('🟡 ', ''),
            f"{z['gesamt_brutto']:.2f}",
            status
        ])
    
    # Summenzeile
    data.append([
        '', '', '', '', 'Gesamt:',
        f"{ist_stunden:.2f}",
        '',
        f"{gesamt_brutto:.2f}",
        ''
    ])

    col_widths = [2.2*cm, 1.2*cm, 1.4*cm, 1.4*cm, 1.8*cm, 1.6*cm, 2.0*cm, 2.2*cm, 2.2*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ])
    
    # Korrigierte Zeilen markieren
    for i, z in enumerate(zeilen, start=1):
        if z['korrigiert']:
            ts.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fff3cd'))
    
    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 0.8*cm))

    # Zusammenfassung
    diff = ist_stunden - soll_stunden
    diff_str = f"+{diff:.2f}h" if diff >= 0 else f"{diff:.2f}h"
    
    zusammen = [
        ['Soll-Stunden:', f"{soll_stunden:.2f} h"],
        ['Ist-Stunden:', f"{ist_stunden:.2f} h"],
        ['Differenz:', diff_str],
        ['Gesamt-Bruttolohn:', f"{gesamt_brutto:.2f} €"],
    ]
    
    t2 = Table(zusammen, colWidths=[5*cm, 4*cm])
    t2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEBELOW', (0, -2), (-1, -2), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)
    story.append(Spacer(1, 1*cm))
    
    # Fußzeile
    story.append(Paragraph(
        f"Erstellt am: {date.today().strftime('%d.%m.%Y')} | "
        f"Steakhouse Piccolo – Arbeitszeitverwaltung CrewBase",
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=7,
                       alignment=TA_CENTER, textColor=colors.grey)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def show_zeitauswertung(mitarbeiter: dict, admin_modus: bool = False,
                        filter_mitarbeiter_id: int = None):
    """
    Hauptfunktion: Zeitauswertung / Lohn
    - admin_modus=True: Admin sieht alle Mitarbeiter
    - filter_mitarbeiter_id: Für Admin-Filterung auf einen Mitarbeiter
    """
    
    st.subheader("⏱️ Zeitauswertung / Lohn")
    
    # ── Monat / Jahr Auswahl ──────────────────────────────────────────────────
    heute = date.today()
    col1, col2 = st.columns(2)
    with col1:
        jahr = st.selectbox("Jahr", list(range(heute.year - 2, heute.year + 2)),
                            index=2, key="za_jahr")
    with col2:
        monat = st.selectbox("Monat", list(range(1, 13)),
                             format_func=lambda x: MONATE[x - 1],
                             index=heute.month - 1, key="za_monat")
    
    # ── Mitarbeiter-Auswahl (nur Admin) ──────────────────────────────────────
    if admin_modus:
        supabase = get_supabase_client()
        alle_ma = supabase.table('mitarbeiter').select(
            'id,vorname,nachname,monatliche_soll_stunden,stundenlohn_brutto,'
            'sonntagszuschlag_aktiv,feiertagszuschlag_aktiv,personalnummer'
        ).eq('betrieb_id', st.session_state.betrieb_id).order('nachname').execute()
        
        ma_liste = alle_ma.data or []
        ma_optionen = {f"{m['vorname']} {m['nachname']}": m for m in ma_liste}
        
        ausgewaehlter_name = st.selectbox(
            "Mitarbeiter auswählen",
            list(ma_optionen.keys()),
            key="za_ma_select"
        )
        aktiver_ma = ma_optionen[ausgewaehlter_name]
    else:
        aktiver_ma = mitarbeiter
    
    st.markdown("---")
    
    # ── Daten laden ──────────────────────────────────────────────────────────
    zeiterfassungen = _lade_zeiterfassungen(aktiver_ma['id'], monat, jahr)
    dienstplaene = _lade_dienstplaene(aktiver_ma['id'], monat, jahr)
    
    # ── Zeilen berechnen ─────────────────────────────────────────────────────
    zeilen = [_berechne_zeile(z, aktiver_ma) for z in zeiterfassungen]
    
    # ── Soll-Stunden aus Dienstplan ───────────────────────────────────────────
    soll_aus_dienstplan = _berechne_soll_stunden(dienstplaene)
    # Fallback: monatliche_soll_stunden aus Mitarbeiterprofil
    soll_stunden = soll_aus_dienstplan if soll_aus_dienstplan > 0 else (
        aktiver_ma.get('monatliche_soll_stunden', 0) or 0
    )
    
    ist_stunden = sum(z['netto_stunden'] for z in zeilen)
    differenz = ist_stunden - soll_stunden
    gesamt_brutto = sum(z['gesamt_brutto'] for z in zeilen)
    korrektur_count = sum(1 for z in zeilen if z['korrigiert'])
    
    # ── Kennzahlen-Kacheln ────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("📋 Soll-Stunden", f"{soll_stunden:.2f} h")
    with k2:
        st.metric("✅ Ist-Stunden", f"{ist_stunden:.2f} h")
    with k3:
        delta_color = "normal" if differenz >= 0 else "inverse"
        st.metric(
            "⚖️ Differenz",
            f"{abs(differenz):.2f} h",
            delta=f"{'Überstunden' if differenz >= 0 else 'Minusstunden'}",
            delta_color=delta_color
        )
    with k4:
        st.metric("💶 Bruttolohn (ges.)", f"{gesamt_brutto:.2f} €")
    
    if korrektur_count > 0:
        st.warning(
            f"⚠️ **{korrektur_count} Eintrag/Einträge** in diesem Monat wurden vom Administrator "
            f"korrigiert und sind in der Tabelle **gelb markiert**."
        )
    
    st.markdown("---")
    
    # ── Detailtabelle ─────────────────────────────────────────────────────────
    st.markdown(f"### 📅 Zeiterfassungen – {MONATE[monat-1]} {jahr}")
    
    if not zeilen:
        st.info(f"Keine Zeiterfassungen für {MONATE[monat-1]} {jahr} vorhanden.")
    else:
        # Tabelle als HTML für farbige Markierungen
        html_rows = ""
        for z in zeilen:
            bg = "#fff3cd" if z['korrigiert'] else ("white" if zeilen.index(z) % 2 == 0 else "#f8f9fa")
            
            typ_badge = ""
            if z['ist_feiertag']:
                typ_badge = '<span style="background:#dc3545;color:white;padding:2px 6px;border-radius:4px;font-size:0.75rem;">Feiertag</span>'
            elif z['ist_sonntag']:
                typ_badge = '<span style="background:#fd7e14;color:white;padding:2px 6px;border-radius:4px;font-size:0.75rem;">Sonntag</span>'
            else:
                typ_badge = '<span style="background:#0d6efd;color:white;padding:2px 6px;border-radius:4px;font-size:0.75rem;">Arbeit</span>'
            
            korr_badge = ""
            if z['korrigiert']:
                korr_badge = ' <span style="background:#ffc107;color:#212529;padding:2px 5px;border-radius:4px;font-size:0.7rem;">✏️ korrigiert</span>'
            
            zuschlag_info = ""
            if z['zuschlag_so'] > 0:
                zuschlag_info += f'<br><small style="color:#fd7e14;">+{z["zuschlag_so"]:.2f}€ So-Zuschlag</small>'
            if z['zuschlag_ft'] > 0:
                zuschlag_info += f'<br><small style="color:#dc3545;">+{z["zuschlag_ft"]:.2f}€ Ft-Zuschlag</small>'
            
            html_rows += f"""
            <tr style="background:{bg};">
                <td style="padding:8px;border-bottom:1px solid #dee2e6;font-weight:500;">{z['datum_str']}</td>
                <td style="padding:8px;border-bottom:1px solid #dee2e6;color:#6c757d;">{z['wochentag']}</td>
                <td style="padding:8px;border-bottom:1px solid #dee2e6;">{str(z['start'])[:5] if z['start'] != '–' else '–'}</td>
                <td style="padding:8px;border-bottom:1px solid #dee2e6;">{str(z['ende'])[:5] if z['ende'] != 'Offen' else '<span style="color:#dc3545;">Offen</span>'}</td>
                <td style="padding:8px;border-bottom:1px solid #dee2e6;text-align:center;">{z['pause_min']} Min</td>
                <td style="padding:8px;border-bottom:1px solid #dee2e6;text-align:center;font-weight:600;">{z['netto_stunden']:.2f} h</td>
                <td style="padding:8px;border-bottom:1px solid #dee2e6;">{typ_badge}</td>
                <td style="padding:8px;border-bottom:1px solid #dee2e6;text-align:right;">{z['grundlohn']:.2f} €{zuschlag_info}</td>
                <td style="padding:8px;border-bottom:1px solid #dee2e6;text-align:right;font-weight:600;">{z['gesamt_brutto']:.2f} €{korr_badge}</td>
            </tr>
            """
        
        html_table = f"""
        <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:0.875rem;">
            <thead>
                <tr style="background:#1a1a2e;color:white;">
                    <th style="padding:10px;text-align:left;">Datum</th>
                    <th style="padding:10px;text-align:left;">Tag</th>
                    <th style="padding:10px;text-align:left;">Von</th>
                    <th style="padding:10px;text-align:left;">Bis</th>
                    <th style="padding:10px;text-align:center;">Pause</th>
                    <th style="padding:10px;text-align:center;">Netto-h</th>
                    <th style="padding:10px;text-align:left;">Typ</th>
                    <th style="padding:10px;text-align:right;">Grundlohn</th>
                    <th style="padding:10px;text-align:right;">Gesamt</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
                <tr style="background:#e8f4f8;font-weight:700;font-size:0.9rem;">
                    <td colspan="5" style="padding:10px;border-top:2px solid #1a1a2e;">Monatssumme</td>
                    <td style="padding:10px;text-align:center;border-top:2px solid #1a1a2e;">{ist_stunden:.2f} h</td>
                    <td style="padding:10px;border-top:2px solid #1a1a2e;"></td>
                    <td style="padding:10px;border-top:2px solid #1a1a2e;"></td>
                    <td style="padding:10px;text-align:right;border-top:2px solid #1a1a2e;">{gesamt_brutto:.2f} €</td>
                </tr>
            </tbody>
        </table>
        </div>
        """
        st.markdown(html_table, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ── Soll-Ist-Vergleich ────────────────────────────────────────────────────
    st.markdown("### 📊 Monatsauswertung – Soll-Ist-Vergleich")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div style="background:#f8f9fa;padding:1rem;border-radius:8px;border-left:4px solid #0d6efd;">
            <div style="font-size:0.85rem;color:#6c757d;">Soll-Stunden (Dienstplan)</div>
            <div style="font-size:1.5rem;font-weight:700;">{soll_stunden:.2f} h</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        diff_color = "#198754" if differenz >= 0 else "#dc3545"
        diff_icon = "▲" if differenz >= 0 else "▼"
        st.markdown(f"""
        <div style="background:#f8f9fa;padding:1rem;border-radius:8px;border-left:4px solid {diff_color};">
            <div style="font-size:0.85rem;color:#6c757d;">Ist-Stunden vs. Soll</div>
            <div style="font-size:1.5rem;font-weight:700;color:{diff_color};">{diff_icon} {abs(differenz):.2f} h</div>
            <div style="font-size:0.8rem;color:#6c757d;">{'Überstunden' if differenz >= 0 else 'Minusstunden'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Lohnaufschlüsselung
    so_stunden = sum(z['netto_stunden'] for z in zeilen if z['ist_sonntag'] and not z['ist_feiertag'])
    ft_stunden = sum(z['netto_stunden'] for z in zeilen if z['ist_feiertag'])
    normal_stunden = ist_stunden - so_stunden - ft_stunden
    
    stundenlohn = aktiver_ma.get('stundenlohn_brutto', 0) or 0
    
    if stundenlohn > 0:
        st.markdown("**Lohnaufschlüsselung:**")
        lohn_cols = st.columns(3)
        with lohn_cols[0]:
            st.markdown(f"""
            <div style="background:white;padding:0.8rem;border-radius:6px;border:1px solid #dee2e6;text-align:center;">
                <div style="font-size:0.8rem;color:#6c757d;">Normalstunden</div>
                <div style="font-weight:600;">{normal_stunden:.2f} h</div>
                <div style="font-size:0.85rem;color:#0d6efd;">{berechne_grundlohn(stundenlohn, normal_stunden):.2f} €</div>
            </div>
            """, unsafe_allow_html=True)
        with lohn_cols[1]:
            so_zuschlag = sum(z['zuschlag_so'] for z in zeilen)
            st.markdown(f"""
            <div style="background:white;padding:0.8rem;border-radius:6px;border:1px solid #dee2e6;text-align:center;">
                <div style="font-size:0.8rem;color:#6c757d;">Sonntagsstunden (+50%)</div>
                <div style="font-weight:600;">{so_stunden:.2f} h</div>
                <div style="font-size:0.85rem;color:#fd7e14;">+{so_zuschlag:.2f} € Zuschlag</div>
            </div>
            """, unsafe_allow_html=True)
        with lohn_cols[2]:
            ft_zuschlag = sum(z['zuschlag_ft'] for z in zeilen)
            st.markdown(f"""
            <div style="background:white;padding:0.8rem;border-radius:6px;border:1px solid #dee2e6;text-align:center;">
                <div style="font-size:0.8rem;color:#6c757d;">Feiertagsstunden (+100%)</div>
                <div style="font-weight:600;">{ft_stunden:.2f} h</div>
                <div style="font-size:0.85rem;color:#dc3545;">+{ft_zuschlag:.2f} € Zuschlag</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ── PDF-Export ────────────────────────────────────────────────────────────
    st.markdown("### 📥 Monatsauswertung exportieren")
    
    col_pdf, col_info = st.columns([1, 2])
    with col_pdf:
        if st.button("📄 PDF-Monatsauswertung erstellen", type="primary", use_container_width=True):
            try:
                pdf_bytes = _erstelle_pdf(
                    aktiver_ma, monat, jahr, zeilen,
                    soll_stunden, ist_stunden, gesamt_brutto
                )
                dateiname = (
                    f"Zeitauswertung_{aktiver_ma['nachname']}_{aktiver_ma['vorname']}_"
                    f"{jahr}_{monat:02d}.pdf"
                )
                st.download_button(
                    label="⬇️ PDF herunterladen",
                    data=pdf_bytes,
                    file_name=dateiname,
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ PDF erfolgreich erstellt!")
            except Exception as e:
                st.error(f"Fehler beim Erstellen der PDF: {str(e)}")
    
    with col_info:
        st.info(
            "📋 Die Monatsauswertung enthält alle Zeiterfassungen, den Soll-Ist-Vergleich, "
            "Zuschlagsberechnungen und dient als Grundlage für die Lohnabrechnung."
        )
    
    # Hinweis auf Korrekturen
    if korrektur_count > 0:
        st.markdown(f"""
        <div style="background:#fff3cd;padding:0.8rem;border-radius:6px;border-left:4px solid #ffc107;margin-top:0.5rem;">
            <strong>ℹ️ Hinweis zu Korrekturen:</strong> {korrektur_count} Zeiterfassung(en) 
            wurden in diesem Monat durch den Administrator angepasst. 
            Diese sind in der Tabelle gelb markiert.
        </div>
        """, unsafe_allow_html=True)
