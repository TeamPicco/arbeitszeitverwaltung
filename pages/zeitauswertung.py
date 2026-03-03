"""
Zeitauswertung / Lohn – Modul für Mitarbeiter und Admin
=========================================================
Archiv-Ansicht, Monatsauswertung, Soll-Ist-Vergleich,
Zuschlagsaufschlüsselung (Sachsen), Korrektur-Markierungen,
Audit-Log, Feiertag-Warnungen, PDF-Export
"""

import streamlit as st
from datetime import datetime, date, time, timedelta
from calendar import monthrange
import io

from utils.database import get_supabase_client
from utils.lohnberechnung import (
    berechne_monat,
    berechne_eintrag,
    pruefe_feiertag_warnungen,
    get_feiertage_sachsen,
    ist_feiertag_sachsen,
    ist_sonntag,
    format_stunden,
    format_euro,
    get_feiertage_monat,
)
from utils.calculations import (
    berechne_arbeitsstunden,
    parse_zeit,
    get_wochentag,
    get_monatsnamen,
)

MONATE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


# ─────────────────────────────────────────────────────────────────────────────
# DATEN LADEN
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# PDF-EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def _erstelle_pdf(mitarbeiter: dict, monat: int, jahr: int, monat_ergebnis: dict,
                  soll_stunden: float) -> bytes:
    """Erstellt eine PDF-Monatsauswertung mit vollständiger Zuschlagsaufschlüsselung."""
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
        f"<b>Personal-Nr.:</b> {mitarbeiter.get('personalnummer', '–')} &nbsp;&nbsp; "
        f"<b>Stundenlohn:</b> {mitarbeiter.get('stundenlohn_brutto', 0):.2f} €",
        info_style))
    story.append(Spacer(1, 0.5*cm))

    # Detailtabelle
    header = ['Datum', 'Tag', 'Von', 'Bis', 'Pause', 'Netto-h', 'Typ', 'Grundlohn', 'Zuschlag', 'Gesamt']
    data = [header]

    zeilen = monat_ergebnis.get("zeilen", [])
    for z in zeilen:
        if z.get("fehler") and z["fehler"] == "Eintrag offen (kein Ende)":
            continue

        datum = z["datum"]
        datum_str = datum.strftime('%d.%m.%Y') if isinstance(datum, date) else str(datum)
        wochentag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][datum.weekday()] if isinstance(datum, date) else "–"

        typ = "Arbeit"
        if z.get("ist_feiertag"):
            typ = f"Feiertag"
        elif z.get("ist_sonntag"):
            typ = "Sonntag"

        zuschlag_gesamt = z.get("sonntagszuschlag", 0) + z.get("feiertagszuschlag", 0)

        data.append([
            datum_str,
            wochentag,
            str(z.get("datum", ""))[:5] if False else "–",  # Platzhalter
            "–",
            f"{z.get('pause_minuten', 0)} Min",
            f"{z.get('netto_stunden', 0):.2f}",
            typ,
            f"{z.get('grundlohn', 0):.2f} €",
            f"+{zuschlag_gesamt:.2f} €" if zuschlag_gesamt > 0 else "–",
            f"{z.get('gesamtlohn', 0):.2f} €",
        ])

    # Wir bauen die Tabelle aus den Zeiterfassungs-Rohdaten neu auf (mit Zeiten)
    # Dazu nutzen wir die zeilen-Daten direkt
    data = [header]
    for z in zeilen:
        if z.get("fehler") and z["fehler"] == "Eintrag offen (kein Ende)":
            continue
        datum = z["datum"]
        datum_str = datum.strftime('%d.%m.%Y') if isinstance(datum, date) else str(datum)
        wochentag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][datum.weekday()] if isinstance(datum, date) else "–"
        typ = "Arbeit"
        if z.get("ist_feiertag"):
            typ = f"Feiertag"
        elif z.get("ist_sonntag"):
            typ = "Sonntag"
        zuschlag_gesamt = z.get("sonntagszuschlag", 0) + z.get("feiertagszuschlag", 0)
        data.append([
            datum_str, wochentag, "–", "–",
            f"{z.get('pause_minuten', 0)} Min",
            f"{z.get('netto_stunden', 0):.2f}",
            typ,
            f"{z.get('grundlohn', 0):.2f} €",
            f"+{zuschlag_gesamt:.2f} €" if zuschlag_gesamt > 0 else "–",
            f"{z.get('gesamtlohn', 0):.2f} €",
        ])

    ist_stunden = monat_ergebnis.get("gesamt_stunden", 0)
    gesamtbrutto = monat_ergebnis.get("gesamtbrutto", 0)
    data.append(['', '', '', '', 'Gesamt:', f"{ist_stunden:.2f}", '', '', '',
                 f"{gesamtbrutto:.2f} €"])

    col_widths = [1.9*cm, 0.9*cm, 1.2*cm, 1.2*cm, 1.5*cm, 1.4*cm, 1.8*cm, 2.0*cm, 1.8*cm, 2.0*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ])
    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 0.8*cm))

    # Zusammenfassung mit Zuschlagsaufschlüsselung
    diff = ist_stunden - soll_stunden
    diff_str = f"+{diff:.2f} h" if diff >= 0 else f"{diff:.2f} h"
    stundenlohn = mitarbeiter.get("stundenlohn_brutto", 0) or 0

    zusammen = [
        ['Soll-Stunden:', f"{soll_stunden:.2f} h"],
        ['Ist-Stunden (Netto):', f"{ist_stunden:.2f} h"],
        ['Differenz:', diff_str],
        ['', ''],
        ['Grundlohn:', f"{monat_ergebnis.get('grundlohn', 0):.2f} €"],
    ]
    if monat_ergebnis.get("sonntags_stunden", 0) > 0:
        zusammen.append([
            f"Sonntagszuschlag ({monat_ergebnis['sonntags_stunden']:.2f} h × 50%):",
            f"+{monat_ergebnis.get('sonntagszuschlag', 0):.2f} €"
        ])
    if monat_ergebnis.get("feiertags_stunden", 0) > 0:
        zusammen.append([
            f"Feiertagszuschlag ({monat_ergebnis['feiertags_stunden']:.2f} h × 100%):",
            f"+{monat_ergebnis.get('feiertagszuschlag', 0):.2f} €"
        ])
    zusammen.append(['Gesamt-Bruttolohn:', f"{gesamtbrutto:.2f} €"])

    t2 = Table(zusammen, colWidths=[7*cm, 4*cm])
    t2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)
    story.append(Spacer(1, 1*cm))

    story.append(Paragraph(
        f"Erstellt am: {date.today().strftime('%d.%m.%Y')} | "
        f"Bundesland: Sachsen (SN) | CrewBase Arbeitszeitverwaltung",
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=7,
                       alignment=TA_CENTER, textColor=colors.grey)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ─────────────────────────────────────────────────────────────────────────────
# HAUPTFUNKTION
# ─────────────────────────────────────────────────────────────────────────────

def show_zeitauswertung(mitarbeiter: dict, admin_modus: bool = False,
                        filter_mitarbeiter_id: int = None):
    """
    Hauptfunktion: Zeitauswertung / Lohn
    - admin_modus=True: Admin sieht alle Mitarbeiter + Audit-Log + Warnungen
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
            'sonntagszuschlag_aktiv,feiertagszuschlag_aktiv,personalnummer,beschaeftigungsart'
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

    # ── Lohnberechnung mit neuem Modul ───────────────────────────────────────
    monat_ergebnis = berechne_monat(zeiterfassungen, aktiver_ma, auto_pause=True)

    # ── Soll-Stunden ─────────────────────────────────────────────────────────
    soll_aus_dienstplan = _berechne_soll_stunden(dienstplaene)
    soll_stunden = soll_aus_dienstplan if soll_aus_dienstplan > 0 else (
        aktiver_ma.get('monatliche_soll_stunden', 0) or 0
    )

    ist_stunden = monat_ergebnis["gesamt_stunden"]
    differenz = ist_stunden - soll_stunden
    gesamtbrutto = monat_ergebnis["gesamtbrutto"]
    zeilen = monat_ergebnis["zeilen"]
    warnungen = monat_ergebnis["warnungen"]

    # Korrekturen zählen (Zeilen mit updated_at != created_at)
    korrektur_count = sum(
        1 for z_raw in zeiterfassungen
        if z_raw.get('updated_at') and z_raw.get('created_at')
        and z_raw['updated_at'] != z_raw['created_at']
    )

    # ── Feiertag-Warnungen (Admin) ────────────────────────────────────────────
    if admin_modus and warnungen:
        for warnung in warnungen:
            st.warning(warnung)

    if korrektur_count > 0:
        st.warning(
            f"⚠️ **{korrektur_count} Eintrag/Einträge** in diesem Monat wurden vom Administrator "
            f"korrigiert und sind in der Tabelle **gelb markiert**."
        )

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
        st.metric("💶 Bruttolohn (ges.)", f"{gesamtbrutto:.2f} €")

    st.markdown("---")

    # ── Detailtabelle ─────────────────────────────────────────────────────────
    st.markdown(f"### 📅 Zeiterfassungen – {MONATE[monat-1]} {jahr}")

    # Feiertage des Monats für Tooltip
    feiertage_monat = get_feiertage_monat(monat, jahr)

    if not zeilen:
        st.info(f"Keine Zeiterfassungen für {MONATE[monat-1]} {jahr} vorhanden.")
    else:
        # Rohdaten für Zeiten (start_zeit, ende_zeit)
        raw_map = {z.get("id"): z for z in zeiterfassungen}

        df_rows = []
        for idx, z in enumerate(zeilen):
            # Korrektur-Flag aus Rohdaten
            raw = raw_map.get(z.get("id"), {})
            korrigiert = bool(
                raw.get('updated_at') and raw.get('created_at')
                and raw['updated_at'] != raw['created_at']
            )

            datum = z["datum"]
            datum_str = datum.strftime('%d.%m.%Y') if isinstance(datum, date) else str(datum)
            wochentag = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][datum.weekday()] if isinstance(datum, date) else "–"

            start_str = str(raw.get("start_zeit", "–"))[:5] if raw.get("start_zeit") else "–"
            ende_str = str(raw.get("ende_zeit", ""))[:5] if raw.get("ende_zeit") else "Offen"

            # Typ
            if z.get("ist_feiertag"):
                ft_name = z.get("feiertag_name", "Feiertag")
                typ_str = f"🔴 {ft_name[:15]}"
            elif z.get("ist_sonntag"):
                typ_str = "🟡 Sonntag"
            else:
                typ_str = "🔵 Arbeit"

            if korrigiert:
                typ_str += " ✏️"

            # Zuschlag-Info
            so_z = z.get("sonntagszuschlag", 0)
            ft_z = z.get("feiertagszuschlag", 0)
            zuschlag_str = ""
            if so_z > 0:
                zuschlag_str += f"+{so_z:.2f}€ So"
            if ft_z > 0:
                zuschlag_str += f" +{ft_z:.2f}€ Ft"

            # Warnung
            if z.get("hat_zuschlag_aber_kein_haekchen"):
                typ_str += " ⚠️"

            # Offener Eintrag
            if z.get("fehler"):
                netto_str = "Offen"
                gesamt_str = "–"
            else:
                netto_str = f"{z.get('netto_stunden', 0):.2f} h"
                gesamt_str = f"{z.get('gesamtlohn', 0):.2f} €"

            grundlohn_str = f"{z.get('grundlohn', 0):.2f} €"
            if zuschlag_str:
                grundlohn_str += f" ({zuschlag_str.strip()})"

            df_rows.append({
                "Datum": datum_str,
                "Tag": wochentag[:2],
                "Von": start_str,
                "Bis": ende_str,
                "Pause": f"{z.get('pause_minuten', 0)} Min",
                "Netto-h": netto_str,
                "Typ": typ_str,
                "Grundlohn": grundlohn_str,
                "Gesamt": gesamt_str,
            })

        # Summenzeile
        df_rows.append({
            "Datum": "── Monatssumme ──",
            "Tag": "",
            "Von": "",
            "Bis": "",
            "Pause": "",
            "Netto-h": f"{ist_stunden:.2f} h",
            "Typ": "",
            "Grundlohn": "",
            "Gesamt": f"{gesamtbrutto:.2f} €",
        })

        st.dataframe(df_rows, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Lohnaufschlüsselung ───────────────────────────────────────────────────
    st.markdown("### 💶 Lohnaufschlüsselung – Zuschlagsübersicht")

    stundenlohn = aktiver_ma.get('stundenlohn_brutto', 0) or 0
    so_stunden = monat_ergebnis["sonntags_stunden"]
    ft_stunden = monat_ergebnis["feiertags_stunden"]
    normal_stunden = max(0, ist_stunden - so_stunden - ft_stunden)
    grundlohn = monat_ergebnis["grundlohn"]
    so_zuschlag = monat_ergebnis["sonntagszuschlag"]
    ft_zuschlag = monat_ergebnis["feiertagszuschlag"]

    lohn_cols = st.columns(3)
    with lohn_cols[0]:
        st.markdown(f"""
        <div style="background:white;padding:1rem;border-radius:10px;border:1px solid #dee2e6;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="font-size:0.8rem;color:#6c757d;margin-bottom:4px;">Normalstunden</div>
            <div style="font-size:1.4rem;font-weight:700;color:#1a1a2e;">{normal_stunden:.2f} h</div>
            <div style="font-size:0.95rem;color:#0d6efd;font-weight:600;">{grundlohn:.2f} €</div>
            <div style="font-size:0.75rem;color:#adb5bd;margin-top:4px;">× {stundenlohn:.2f} €/h</div>
        </div>
        """, unsafe_allow_html=True)

    with lohn_cols[1]:
        so_aktiv = aktiver_ma.get("sonntagszuschlag_aktiv", False)
        so_badge = '<span style="background:#fd7e14;color:white;padding:1px 6px;border-radius:3px;font-size:0.7rem;">+50%</span>' if so_aktiv else '<span style="background:#dee2e6;color:#6c757d;padding:1px 6px;border-radius:3px;font-size:0.7rem;">inaktiv</span>'
        st.markdown(f"""
        <div style="background:white;padding:1rem;border-radius:10px;border:1px solid #dee2e6;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="font-size:0.8rem;color:#6c757d;margin-bottom:4px;">Sonntagsstunden {so_badge}</div>
            <div style="font-size:1.4rem;font-weight:700;color:#1a1a2e;">Davon {so_stunden:.2f} h</div>
            <div style="font-size:0.95rem;color:#fd7e14;font-weight:600;">+{so_zuschlag:.2f} € Zuschlag</div>
            <div style="font-size:0.75rem;color:#adb5bd;margin-top:4px;">So 00:00–24:00 Uhr</div>
        </div>
        """, unsafe_allow_html=True)

    with lohn_cols[2]:
        ft_aktiv = aktiver_ma.get("feiertagszuschlag_aktiv", False)
        ft_badge = '<span style="background:#dc3545;color:white;padding:1px 6px;border-radius:3px;font-size:0.7rem;">+100%</span>' if ft_aktiv else '<span style="background:#dee2e6;color:#6c757d;padding:1px 6px;border-radius:3px;font-size:0.7rem;">inaktiv</span>'
        st.markdown(f"""
        <div style="background:white;padding:1rem;border-radius:10px;border:1px solid #dee2e6;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="font-size:0.8rem;color:#6c757d;margin-bottom:4px;">Feiertagsstunden {ft_badge}</div>
            <div style="font-size:1.4rem;font-weight:700;color:#1a1a2e;">Davon {ft_stunden:.2f} h</div>
            <div style="font-size:0.95rem;color:#dc3545;font-weight:600;">+{ft_zuschlag:.2f} € Zuschlag</div>
            <div style="font-size:0.75rem;color:#adb5bd;margin-top:4px;">Sachsen (SN) inkl. Buß- &amp; Bettag</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Gesamtlohn-Box
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:1.2rem 1.5rem;border-radius:12px;color:white;display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div style="font-size:0.85rem;opacity:0.7;letter-spacing:1px;text-transform:uppercase;">Gesamt-Bruttolohn {MONATE[monat-1]} {jahr}</div>
            <div style="font-size:0.8rem;opacity:0.6;margin-top:2px;">
                {grundlohn:.2f} € Grundlohn
                {f" + {so_zuschlag:.2f} € So-Zuschlag" if so_zuschlag > 0 else ""}
                {f" + {ft_zuschlag:.2f} € Ft-Zuschlag" if ft_zuschlag > 0 else ""}
            </div>
        </div>
        <div style="font-size:2rem;font-weight:800;letter-spacing:1px;">{gesamtbrutto:.2f} €</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Soll-Ist-Vergleich ────────────────────────────────────────────────────
    st.markdown("### 📊 Soll-Ist-Vergleich")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div style="background:#f8f9fa;padding:1rem;border-radius:8px;border-left:4px solid #0d6efd;">
            <div style="font-size:0.85rem;color:#6c757d;">Soll-Stunden (Dienstplan/Profil)</div>
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

    st.markdown("---")

    # ── Feiertage des Monats (Info) ───────────────────────────────────────────
    if feiertage_monat:
        st.markdown(f"### 🗓️ Feiertage in Sachsen – {MONATE[monat-1]} {jahr}")
        ft_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:1rem;">'
        for ft_datum, ft_name in sorted(feiertage_monat.items()):
            wt = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][ft_datum.weekday()]
            ruhetag = ft_datum.weekday() in (0, 1)
            bg = "#dee2e6" if ruhetag else "#dc3545"
            opacity = "0.5" if ruhetag else "1"
            hinweis = " (Ruhetag)" if ruhetag else ""
            ft_html += f'<span style="background:{bg};color:white;padding:4px 10px;border-radius:6px;font-size:0.82rem;opacity:{opacity};">{ft_datum.strftime("%d.%m.")} {wt} – {ft_name}{hinweis}</span>'
        ft_html += '</div>'
        st.markdown(ft_html, unsafe_allow_html=True)
        st.markdown("---")

    # ── Audit-Log (nur Admin) ─────────────────────────────────────────────────
    if admin_modus:
        with st.expander("🔍 Audit-Log (Berechnungsprotokoll)", expanded=False):
            st.markdown("""
            <div style="background:#f8f9fa;padding:0.5rem;border-radius:6px;margin-bottom:0.5rem;">
                <small style="color:#6c757d;">Das Audit-Log protokolliert jeden Rechenschritt für Revisionszwecke.
                Es zeigt welcher Zuschlag an welchem Tag durch welche Regel ausgelöst wurde.</small>
            </div>
            """, unsafe_allow_html=True)
            audit_text = "\n".join(monat_ergebnis.get("audit_log_gesamt", []))
            st.code(audit_text, language=None)

            # Download-Button für Audit-Log
            if audit_text:
                st.download_button(
                    label="⬇️ Audit-Log als TXT herunterladen",
                    data=audit_text.encode("utf-8"),
                    file_name=f"AuditLog_{aktiver_ma.get('nachname','MA')}_{jahr}_{monat:02d}.txt",
                    mime="text/plain"
                )

    # ── PDF-Export ────────────────────────────────────────────────────────────
    st.markdown("### 📥 Monatsauswertung exportieren")

    col_pdf, col_info = st.columns([1, 2])
    with col_pdf:
        if st.button("📄 PDF-Monatsauswertung erstellen", type="primary", use_container_width=True):
            try:
                pdf_bytes = _erstelle_pdf(aktiver_ma, monat, jahr, monat_ergebnis, soll_stunden)
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
            "Zuschlagsberechnungen nach Sachsen-Feiertagskalender und dient als Grundlage "
            "für die Lohnabrechnung."
        )

    if korrektur_count > 0:
        st.markdown(f"""
        <div style="background:#fff3cd;padding:0.8rem;border-radius:6px;border-left:4px solid #ffc107;margin-top:0.5rem;">
            <strong>ℹ️ Hinweis zu Korrekturen:</strong> {korrektur_count} Zeiterfassung(en)
            wurden in diesem Monat durch den Administrator angepasst.
            Diese sind in der Tabelle gelb markiert.
        </div>
        """, unsafe_allow_html=True)

    # Offene Einträge
    if monat_ergebnis.get("offene_eintraege", 0) > 0:
        st.warning(
            f"⚠️ **{monat_ergebnis['offene_eintraege']} offene Einträge** (kein Ende gestempelt) "
            f"wurden nicht in die Lohnberechnung einbezogen."
        )
