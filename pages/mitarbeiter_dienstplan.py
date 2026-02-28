"""
Mitarbeiter-Dienstplan-Ansicht
Zeigt nur die eigenen Dienste des eingeloggten Mitarbeiters
inkl. PDF-Download-Funktion
"""

import streamlit as st
from datetime import datetime, date, timedelta
import calendar
import locale
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

# Setze Locale auf Deutsch für Monatsnamen
try:
    locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'de_DE')
    except:
        pass  # Fallback: Englisch bleibt


def erstelle_dienstplan_pdf(mitarbeiter: dict, dienstplaene: list, jahr: int, monat: int) -> bytes:
    """Erstellt ein professionelles PDF des Dienstplans"""
    from fpdf import FPDF

    class DienstplanPDF(FPDF):
        def header(self):
            # Logo links
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "piccolo_logo.jpeg")
            if os.path.exists(logo_path):
                self.image(logo_path, x=10, y=8, w=30)
            
            # Betriebsname rechts
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(30, 30, 30)
            self.set_xy(45, 10)
            self.cell(0, 7, "Steakhouse Piccolo", ln=True, align="L")
            
            # Trennlinie
            self.set_draw_color(200, 200, 200)
            self.line(10, 28, 200, 28)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Seite {self.page_no()} | Erstellt am {date.today().strftime('%d.%m.%Y')} | Vertraulich", align="C")

    pdf = DienstplanPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Titel
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 20, 20)
    pdf.set_xy(10, 32)
    pdf.cell(0, 10, f"Dienstplan {MONATE_DE[monat]} {jahr}", ln=True, align="C")

    # Mitarbeitername
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 7, f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}", ln=True, align="C")
    pdf.ln(6)

    # Tabellen-Header
    col_widths = [28, 30, 35, 35, 25, 37]
    headers = ["Datum", "Wochentag", "Typ", "Zeiten", "Pause", "Stunden"]
    
    pdf.set_fill_color(30, 30, 60)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    
    for i, (header, width) in enumerate(zip(headers, col_widths)):
        pdf.cell(width, 9, header, border=0, fill=True, align="C")
    pdf.ln()

    # Tabelleninhalt
    pdf.set_font("Helvetica", "", 9)
    total_stunden = 0
    fill = False

    for dienst in dienstplaene:
        datum_obj = datetime.fromisoformat(dienst['datum']).date()
        wochentag_de = WOCHENTAGE_DE[datum_obj.weekday()]
        schichttyp = dienst.get('schichttyp', 'arbeit')

        # Farbe je nach Typ
        if schichttyp == 'urlaub':
            pdf.set_fill_color(255, 243, 205)  # Gelb
            pdf.set_text_color(120, 80, 0)
            typ_text = "Urlaub"
            urlaub_std = float(dienst.get('urlaub_stunden') or 0)
            zeit_text = f"{urlaub_std:.1f}h Urlaubszeit"
            pause_text = "-"
            stunden_text = f"{urlaub_std:.2f} h"
            total_stunden += urlaub_std
        elif schichttyp == 'frei':
            pdf.set_fill_color(240, 240, 240)  # Grau
            pdf.set_text_color(100, 100, 100)
            typ_text = "Frei"
            zeit_text = "Freier Tag"
            pause_text = "-"
            stunden_text = "-"
        else:
            if fill:
                pdf.set_fill_color(235, 240, 255)  # Hellblau
            else:
                pdf.set_fill_color(255, 255, 255)  # Weiß
            pdf.set_text_color(20, 20, 20)
            typ_text = "Arbeit"
            if dienst.get('schichtvorlagen'):
                typ_text = dienst['schichtvorlagen']['name']
            
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
                zeit_text = "Zeiten n.v."
                pause_text = "-"
                stunden_text = "-"

        fill = not fill

        row_data = [
            datum_obj.strftime('%d.%m.%Y'),
            wochentag_de,
            typ_text,
            zeit_text,
            pause_text,
            stunden_text
        ]

        for i, (cell_text, width) in enumerate(zip(row_data, col_widths)):
            pdf.cell(width, 8, cell_text, border="B", fill=True, align="C")
        pdf.ln()

    # Gesamtstunden
    pdf.ln(4)
    pdf.set_fill_color(30, 30, 60)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(153, 9, "Gesamtstunden im Monat:", fill=True, align="R")
    pdf.cell(37, 9, f"{total_stunden:.2f} h", fill=True, align="C")
    pdf.ln()

    # Unterschriftenzeile
    pdf.ln(15)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(95, 5, "____________________________", align="C")
    pdf.cell(95, 5, "____________________________", align="C")
    pdf.ln(5)
    pdf.cell(95, 5, "Datum / Unterschrift Mitarbeiter", align="C")
    pdf.cell(95, 5, "Datum / Unterschrift Arbeitgeber", align="C")

    return bytes(pdf.output())


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
            dateiname = f"Dienstplan_{mitarbeiter['nachname']}_{MONATE_DE[monat]}_{jahr}.pdf"
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
        
        # Berechne Gesamtstunden
        total_stunden = 0
        
        for dienst in dienstplaene.data:
            datum_obj = datetime.fromisoformat(dienst['datum']).date()
            wochentag_de = WOCHENTAGE_DE[datum_obj.weekday()]
            schichttyp = dienst.get('schichttyp', 'arbeit')
            
            # Farbe und Name je nach Schichttyp
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
                # Arbeitstag: Zeiten parsen
                farbe = "#6c757d"
                schicht_name = "Benutzerdefiniert"
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
                    stunden -= dienst.get('pause_minuten', 0) / 60
                    total_stunden += stunden
                    zeit_anzeige = f"⏰ {dienst['start_zeit'][:5]} - {dienst['ende_zeit'][:5]}"
                    pause_anzeige = f"☕ Pause: {dienst['pause_minuten']} Min" if dienst.get('pause_minuten', 0) > 0 else ""
                except Exception:
                    stunden = 0
                    zeit_anzeige = "Zeiten nicht verfügbar"
                    pause_anzeige = ""
            
            # Zeige Dienst
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
        
        # Zeige Gesamtstunden
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
    
    # Kalender-Grid
    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
    
    # Wochentage als Header
    wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    cols = st.columns(7)
    for i, tag in enumerate(wochentage):
        with cols[i]:
            st.markdown(f"**{tag}**")
    
    # Kalender-Tage
    aktueller_tag = erster_tag
    
    # Fülle erste Woche mit leeren Zellen
    wochentag_start = erster_tag.weekday()  # 0 = Montag
    
    cols = st.columns(7)
    for i in range(wochentag_start):
        with cols[i]:
            st.write("")
    
    # Zeige alle Tage
    while aktueller_tag <= letzter_tag:
        wochentag = aktueller_tag.weekday()
        
        if wochentag == 0:  # Neue Woche
            cols = st.columns(7)
        
        with cols[wochentag]:
            if aktueller_tag in dienste_dict:
                eintraege = dienste_dict[aktueller_tag]
                
                # Mehrere Schichten: erste Schicht für Farbe verwenden
                farbe = "#198754"  # Standard-Grün
                if eintraege[0].get('schichtvorlagen'):
                    farbe = eintraege[0]['schichtvorlagen'].get('farbe', '#198754')
                schichttyp = eintraege[0].get('schichttyp', 'arbeit')
                if schichttyp == 'urlaub':
                    farbe = "#f59e0b"
                elif schichttyp == 'frei':
                    farbe = "#9ca3af"
                
                # Zeitanzeige: alle Schichten
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
