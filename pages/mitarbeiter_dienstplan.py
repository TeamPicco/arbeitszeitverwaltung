"""
Mitarbeiter-Dienstplan-Ansicht
Zeigt nur die eigenen Dienste des eingeloggten Mitarbeiters
inkl. PDF-Download-Funktion (via reportlab)
"""

import streamlit as st
from datetime import datetime, date, timedelta
import calendar
import os
import io
from utils.database import get_supabase_client

# Deutsche Monatsnamen
MONATE_DE = [
    "",  # Index 0 (leer, da Monate 1-12 sind)
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

WOCHENTAGE_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def erstelle_dienstplan_pdf(mitarbeiter: dict, dienstplaene: list, jahr: int, monat: int) -> bytes:
    """Erstellt ein professionelles PDF des Dienstplans mit reportlab"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    elements = []

    # Header mit Logo und Betriebsname
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "piccolo_logo.jpeg")
    
    header_data = []
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=3*cm, height=2.5*cm)
            header_data = [[logo, Paragraph("<b>Steakhouse Piccolo</b><br/>Dienstplan", 
                           ParagraphStyle('header', fontSize=14, alignment=TA_LEFT))]]
        except:
            header_data = [[Paragraph("<b>Steakhouse Piccolo</b>", 
                           ParagraphStyle('header', fontSize=14, alignment=TA_LEFT))]]
    else:
        header_data = [[Paragraph("<b>Steakhouse Piccolo</b>", 
                       ParagraphStyle('header', fontSize=14, alignment=TA_LEFT))]]
    
    if header_data:
        header_table = Table(header_data, colWidths=[4*cm, 13*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ]))
        elements.append(header_table)
    
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 0.5*cm))

    # Titel
    title_style = ParagraphStyle('title', fontSize=18, alignment=TA_CENTER, spaceAfter=0.3*cm, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('subtitle', fontSize=12, alignment=TA_CENTER, spaceAfter=0.5*cm, textColor=colors.grey)
    
    elements.append(Paragraph(f"Dienstplan {MONATE_DE[monat]} {jahr}", title_style))
    elements.append(Paragraph(f"{mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}", subtitle_style))
    elements.append(Spacer(1, 0.3*cm))

    # Tabellen-Header
    col_widths = [2.5*cm, 3*cm, 3*cm, 3.5*cm, 2*cm, 3*cm]
    header_row = ["Datum", "Wochentag", "Typ", "Zeiten", "Pause", "Stunden"]
    
    table_data = [header_row]
    total_stunden = 0

    for dienst in dienstplaene:
        datum_obj = datetime.fromisoformat(dienst['datum']).date()
        wochentag_de = WOCHENTAGE_DE[datum_obj.weekday()]
        schichttyp = dienst.get('schichttyp', 'arbeit')

        if schichttyp == 'urlaub':
            typ_text = "Urlaub"
            urlaub_std = float(dienst.get('urlaub_stunden') or 0)
            total_stunden += urlaub_std
            zeit_text = f"{urlaub_std:.1f}h Urlaub"
            pause_text = "-"
            stunden_text = f"{urlaub_std:.2f} h"
        elif schichttyp == 'frei':
            typ_text = "Frei"
            zeit_text = "Freier Tag"
            pause_text = "-"
            stunden_text = "-"
        else:
            schicht_name = "Arbeit"
            if dienst.get('schichtvorlagen'):
                schicht_name = dienst['schichtvorlagen']['name']
            typ_text = schicht_name
            
            try:
                start = datetime.strptime(dienst['start_zeit'], '%H:%M:%S').time()
                ende = datetime.strptime(dienst['ende_zeit'], '%H:%M:%S').time()
                start_dt = datetime.combine(date.today(), start)
                ende_dt = datetime.combine(date.today(), ende)
                if ende_dt <= start_dt:
                    ende_dt += timedelta(days=1)
                stunden = (ende_dt - start_dt).total_seconds() / 3600
                pause_min = dienst.get('pause_minuten', 0) or 0
                stunden -= pause_min / 60
                total_stunden += stunden
                zeit_text = f"{dienst['start_zeit'][:5]} - {dienst['ende_zeit'][:5]}"
                pause_text = f"{pause_min} Min" if pause_min > 0 else "-"
                stunden_text = f"{stunden:.2f} h"
            except Exception:
                zeit_text = "n.v."
                pause_text = "-"
                stunden_text = "-"

        table_data.append([
            datum_obj.strftime('%d.%m.%Y'),
            wochentag_de,
            typ_text,
            zeit_text,
            pause_text,
            stunden_text
        ])

    # Gesamtstunden-Zeile
    table_data.append(["", "", "", "Gesamt:", "", f"{total_stunden:.2f} h"])

    # Tabelle erstellen
    table = Table(table_data, colWidths=col_widths)
    
    # Tabellen-Style
    dark_blue = colors.HexColor('#1e1e3c')
    light_blue = colors.HexColor('#ebf0ff')
    urlaub_yellow = colors.HexColor('#fff3cd')
    frei_grey = colors.HexColor('#f0f0f0')
    
    table_style = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), dark_blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, light_blue]),
        # Borders
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        # Gesamt-Zeile
        ('BACKGROUND', (0, -1), (-1, -1), dark_blue),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]
    
    # Farbe für Urlaub/Frei-Zeilen
    for i, dienst in enumerate(dienstplaene, start=1):
        schichttyp = dienst.get('schichttyp', 'arbeit')
        if schichttyp == 'urlaub':
            table_style.append(('BACKGROUND', (0, i), (-1, i), urlaub_yellow))
        elif schichttyp == 'frei':
            table_style.append(('BACKGROUND', (0, i), (-1, i), frei_grey))
    
    table.setStyle(TableStyle(table_style))
    elements.append(table)
    elements.append(Spacer(1, 1*cm))

    # Unterschriften
    sig_style = ParagraphStyle('sig', fontSize=9, textColor=colors.grey)
    sig_data = [
        [Paragraph("____________________________", sig_style), 
         Paragraph("____________________________", sig_style)],
        [Paragraph("Datum / Unterschrift Mitarbeiter", sig_style), 
         Paragraph("Datum / Unterschrift Arbeitgeber", sig_style)]
    ]
    sig_table = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(sig_table)

    # Footer-Funktion
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            A4[0] / 2, 1.5*cm,
            f"Seite {doc.page} | Erstellt am {date.today().strftime('%d.%m.%Y')} | Vertraulich"
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    return buffer.getvalue()


def show_mitarbeiter_dienstplan(mitarbeiter: dict):
    """Zeigt den Dienstplan für den eingeloggten Mitarbeiter"""
    
    st.subheader("📅 Mein Dienstplan")
    
    supabase = get_supabase_client()
    
    # Monat auswählen
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024, key="mitarbeiter_dienstplan_jahr")
    
    with col2:
        monat = st.selectbox("Monat", range(1, 13), index=date.today().month - 1, 
                            format_func=lambda x: MONATE_DE[x], key="mitarbeiter_dienstplan_monat")
    
    with col3:
        if st.button("🔄 Aktualisieren", use_container_width=True, key="mitarbeiter_dienstplan_refresh"):
            st.rerun()
    
    # Lade Dienstpläne für den Monat (nur eigene!)
    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
    
    dienstplaene = supabase.table('dienstplaene').select(
        '*, schichtvorlagen(name, farbe)'
    ).eq('mitarbeiter_id', mitarbeiter['id']).gte(
        'datum', erster_tag.isoformat()
    ).lte('datum', letzter_tag.isoformat()).order('datum').execute()
    
    st.markdown("---")
    
    if dienstplaene.data and len(dienstplaene.data) > 0:
        st.success(f"✅ **{len(dienstplaene.data)} Dienste** im {MONATE_DE[monat]} {jahr}")
        
        # PDF-Download-Button
        try:
            pdf_bytes = erstelle_dienstplan_pdf(mitarbeiter, dienstplaene.data, jahr, monat)
            dateiname = f"Dienstplan_{mitarbeiter.get('nachname', 'Mitarbeiter')}_{MONATE_DE[monat]}_{jahr}.pdf"
            st.download_button(
                label="📥 Dienstplan als PDF herunterladen",
                data=pdf_bytes,
                file_name=dateiname,
                mime="application/pdf",
                use_container_width=True,
                key="pdf_download_btn"
            )
        except Exception as e:
            st.warning(f"PDF-Erstellung nicht verfügbar: {str(e)}")
        
        # Zeige Kalender-Ansicht
        show_kalender_ansicht(dienstplaene.data, jahr, monat)
        
        st.markdown("---")
        
        # Zeige Listen-Ansicht
        st.markdown("### 📋 Detaillierte Übersicht")
        
        total_stunden = 0
        
        for dienst in dienstplaene.data:
            datum_obj = datetime.fromisoformat(dienst['datum']).date()
            wochentag_de = WOCHENTAGE_DE[datum_obj.weekday()]
            schichttyp = dienst.get('schichttyp', 'arbeit')
            
            if schichttyp == 'urlaub':
                farbe = "#f59e0b"
                schicht_name = "🏖️ Urlaub"
                urlaub_std = float(dienst.get('urlaub_stunden') or 0)
                stunden = urlaub_std
                total_stunden += stunden
                zeit_anzeige = f"{urlaub_std:.1f}h Urlaubszeit"
                pause_anzeige = ""
            elif schichttyp == 'frei':
                farbe = "#9ca3af"
                schicht_name = "⚪ Frei"
                stunden = 0
                zeit_anzeige = "Freier Tag"
                pause_anzeige = ""
            else:
                farbe = "#6c757d"
                schicht_name = "Arbeit"
                if dienst.get('schichtvorlagen'):
                    schicht_name = dienst['schichtvorlagen']['name']
                    farbe = dienst['schichtvorlagen'].get('farbe', '#6c757d')
                
                try:
                    start = datetime.strptime(dienst['start_zeit'], '%H:%M:%S').time()
                    ende = datetime.strptime(dienst['ende_zeit'], '%H:%M:%S').time()
                    start_dt = datetime.combine(date.today(), start)
                    ende_dt = datetime.combine(date.today(), ende)
                    if ende_dt <= start_dt:
                        ende_dt += timedelta(days=1)
                    stunden = (ende_dt - start_dt).total_seconds() / 3600
                    pause_min = dienst.get('pause_minuten', 0) or 0
                    stunden -= pause_min / 60
                    total_stunden += stunden
                    zeit_anzeige = f"⏰ {dienst['start_zeit'][:5]} - {dienst['ende_zeit'][:5]}"
                    pause_anzeige = f"☕ Pause: {pause_min} Min" if pause_min > 0 else ""
                except Exception:
                    stunden = 0
                    zeit_anzeige = "Zeiten nicht verfügbar"
                    pause_anzeige = ""
            
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                
                with col1:
                    st.markdown(f"**{datum_obj.strftime('%d.%m.%Y')}**")
                    st.caption(wochentag_de)
                
                with col2:
                    st.markdown(f"<span style='background-color: {farbe}; padding: 2px 8px; border-radius: 3px; color: white;'>{schicht_name}</span>", unsafe_allow_html=True)
                
                with col3:
                    st.write(zeit_anzeige)
                    if pause_anzeige:
                        st.caption(pause_anzeige)
                
                with col4:
                    if stunden > 0:
                        st.write(f"📊 {stunden:.2f}h")
                    else:
                        st.write("–")
                
                if dienst.get('notiz'):
                    st.caption(f"📝 {dienst['notiz']}")
                
                st.markdown("---")
        
        st.info(f"📊 **Gesamtstunden im {MONATE_DE[monat]}:** {total_stunden:.2f} Stunden")
        
    else:
        st.info(f"ℹ️ Keine Dienste für {MONATE_DE[monat]} {jahr} geplant.")
        st.caption("Ihr Administrator hat noch keine Dienste für Sie eingetragen.")


def show_kalender_ansicht(dienstplaene: list, jahr: int, monat: int):
    """Zeigt eine Kalender-Ansicht der Dienste"""
    
    st.markdown("### 📆 Kalender-Ansicht")
    
    # Erstelle Kalender-Dict (mehrere Einträge pro Tag möglich)
    dienste_dict = {}
    for d in dienstplaene:
        tag = datetime.fromisoformat(d['datum']).date()
        if tag not in dienste_dict:
            dienste_dict[tag] = []
        dienste_dict[tag].append(d)
    
    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
    
    # Wochentage als Header
    wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    cols = st.columns(7)
    for i, tag in enumerate(wochentage):
        with cols[i]:
            st.markdown(f"**{tag}**")
    
    aktueller_tag = erster_tag
    wochentag_start = erster_tag.weekday()
    
    cols = st.columns(7)
    for i in range(wochentag_start):
        with cols[i]:
            st.write("")
    
    while aktueller_tag <= letzter_tag:
        wochentag = aktueller_tag.weekday()
        
        if wochentag == 0:
            cols = st.columns(7)
        
        with cols[wochentag]:
            if aktueller_tag in dienste_dict:
                eintraege = dienste_dict[aktueller_tag]
                
                farbe = "#198754"
                if eintraege[0].get('schichtvorlagen'):
                    farbe = eintraege[0]['schichtvorlagen'].get('farbe', '#198754')
                schichttyp = eintraege[0].get('schichttyp', 'arbeit')
                if schichttyp == 'urlaub':
                    farbe = "#f59e0b"
                elif schichttyp == 'frei':
                    farbe = "#9ca3af"
                
                zeiten_html = ""
                for e in eintraege:
                    if e.get('start_zeit'):
                        zeiten_html += f"<small>{e['start_zeit'][:5]}</small><br>"
                    else:
                        zeiten_html += f"<small>{schichttyp[:3].upper()}</small><br>"
                
                st.markdown(f"""
                <div style="background-color: {farbe}; padding: 5px; border-radius: 5px; text-align: center; color: white;">
                    <strong>{aktueller_tag.day}</strong><br>
                    {zeiten_html}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 5px; border-radius: 5px; text-align: center; color: #6c757d; border: 1px solid #dee2e6;">
                    {aktueller_tag.day}
                </div>
                """, unsafe_allow_html=True)
        
        aktueller_tag += timedelta(days=1)
