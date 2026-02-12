"""
Lohnabrechnung und PDF-Export
"""

from datetime import date, datetime, time
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

from utils.database import get_supabase_client
from utils.calculations import (
    berechne_arbeitsstunden,
    berechne_grundlohn,
    berechne_sonntagszuschlag,
    berechne_feiertagszuschlag,
    berechne_gesamtlohn,
    format_waehrung,
    format_stunden,
    get_monatsnamen
)


def berechne_arbeitszeitkonto(mitarbeiter_id: str, monat: int, jahr: int) -> Optional[Dict[str, Any]]:
    """
    Berechnet das Arbeitszeitkonto für einen Mitarbeiter und Monat
    
    Args:
        mitarbeiter_id: Mitarbeiter-ID
        monat: Monat (1-12)
        jahr: Jahr
        
    Returns:
        Optional[Dict]: Arbeitszeitkonto-Daten
    """
    try:
        supabase = get_supabase_client()
        
        # Lade Mitarbeiterdaten
        mitarbeiter_response = supabase.table('mitarbeiter').select('*').eq('id', mitarbeiter_id).execute()
        if not mitarbeiter_response.data:
            return None
        
        mitarbeiter = mitarbeiter_response.data[0]
        
        # Lade Zeiterfassungen für den Monat
        von_datum = date(jahr, monat, 1)
        
        # Letzter Tag des Monats
        if monat == 12:
            bis_datum = date(jahr + 1, 1, 1)
        else:
            bis_datum = date(jahr, monat + 1, 1)
        
        zeiterfassungen = supabase.table('zeiterfassung').select('*').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).gte('datum', von_datum.isoformat()).lt('datum', bis_datum.isoformat()).execute()
        
        # Berechne Stunden
        ist_stunden = 0
        sonntagsstunden = 0
        feiertagsstunden = 0
        
        for z in zeiterfassungen.data:
            if z['ende_zeit']:
                stunden = berechne_arbeitsstunden(
                    datetime.strptime(z['start_zeit'], '%H:%M:%S').time(),
                    datetime.strptime(z['ende_zeit'], '%H:%M:%S').time(),
                    z['pause_minuten']
                )
                
                ist_stunden += stunden
                
                # Zuschlagsstunden
                if z['ist_sonntag'] and mitarbeiter['sonntagszuschlag_aktiv']:
                    sonntagsstunden += stunden
                
                if z['ist_feiertag'] and mitarbeiter['feiertagszuschlag_aktiv']:
                    feiertagsstunden += stunden
        
        # Lade genommene Urlaubstage
        urlaub_response = supabase.table('urlaubsantraege').select('anzahl_tage').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('status', 'genehmigt').gte('von_datum', von_datum.isoformat()).lt('von_datum', bis_datum.isoformat()).execute()
        
        urlaubstage_genommen = sum([u['anzahl_tage'] for u in urlaub_response.data]) if urlaub_response.data else 0
        
        # Prüfe, ob bereits ein Arbeitszeitkonto existiert
        existing = supabase.table('arbeitszeitkonto').select('*').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('monat', monat).eq('jahr', jahr).execute()
        
        arbeitszeitkonto_data = {
            'mitarbeiter_id': mitarbeiter_id,
            'monat': monat,
            'jahr': jahr,
            'soll_stunden': float(mitarbeiter['monatliche_soll_stunden']),
            'ist_stunden': ist_stunden,
            'urlaubstage_genommen': urlaubstage_genommen,
            'sonntagsstunden': sonntagsstunden,
            'feiertagsstunden': feiertagsstunden
        }
        
        if existing.data:
            # Aktualisiere bestehendes Arbeitszeitkonto
            response = supabase.table('arbeitszeitkonto').update(arbeitszeitkonto_data).eq(
                'id', existing.data[0]['id']
            ).execute()
            return response.data[0] if response.data else None
        else:
            # Erstelle neues Arbeitszeitkonto
            response = supabase.table('arbeitszeitkonto').insert(arbeitszeitkonto_data).execute()
            return response.data[0] if response.data else None
    
    except Exception as e:
        print(f"Fehler beim Berechnen des Arbeitszeitkontos: {str(e)}")
        return None


def erstelle_lohnabrechnung(mitarbeiter_id: str, monat: int, jahr: int) -> Optional[str]:
    """
    Erstellt eine Lohnabrechnung für einen Mitarbeiter und Monat
    
    Args:
        mitarbeiter_id: Mitarbeiter-ID
        monat: Monat (1-12)
        jahr: Jahr
        
    Returns:
        Optional[str]: Lohnabrechnung-ID wenn erfolgreich
    """
    try:
        supabase = get_supabase_client()
        
        # Berechne/Aktualisiere Arbeitszeitkonto
        arbeitszeitkonto = berechne_arbeitszeitkonto(mitarbeiter_id, monat, jahr)
        if not arbeitszeitkonto:
            return None
        
        # Lade Mitarbeiterdaten
        mitarbeiter_response = supabase.table('mitarbeiter').select('*').eq('id', mitarbeiter_id).execute()
        if not mitarbeiter_response.data:
            return None
        
        mitarbeiter = mitarbeiter_response.data[0]
        
        # Berechne Lohnbestandteile
        grundlohn = berechne_grundlohn(
            float(mitarbeiter['stundenlohn_brutto']),
            arbeitszeitkonto['ist_stunden']
        )
        
        sonntagszuschlag = berechne_sonntagszuschlag(
            float(mitarbeiter['stundenlohn_brutto']),
            arbeitszeitkonto['sonntagsstunden']
        ) if mitarbeiter['sonntagszuschlag_aktiv'] else 0
        
        feiertagszuschlag = berechne_feiertagszuschlag(
            float(mitarbeiter['stundenlohn_brutto']),
            arbeitszeitkonto['feiertagsstunden']
        ) if mitarbeiter['feiertagszuschlag_aktiv'] else 0
        
        gesamtbetrag = berechne_gesamtlohn(grundlohn, sonntagszuschlag, feiertagszuschlag)
        
        # Prüfe, ob bereits eine Lohnabrechnung existiert
        existing = supabase.table('lohnabrechnungen').select('*').eq(
            'mitarbeiter_id', mitarbeiter_id
        ).eq('monat', monat).eq('jahr', jahr).execute()
        
        lohnabrechnung_data = {
            'mitarbeiter_id': mitarbeiter_id,
            'monat': monat,
            'jahr': jahr,
            'arbeitszeitkonto_id': arbeitszeitkonto['id'],
            'grundlohn': grundlohn,
            'sonntagszuschlag': sonntagszuschlag,
            'feiertagszuschlag': feiertagszuschlag,
            'gesamtbetrag': gesamtbetrag
        }
        
        if existing.data:
            # Aktualisiere bestehende Lohnabrechnung
            response = supabase.table('lohnabrechnungen').update(lohnabrechnung_data).eq(
                'id', existing.data[0]['id']
            ).execute()
            return response.data[0]['id'] if response.data else None
        else:
            # Erstelle neue Lohnabrechnung
            response = supabase.table('lohnabrechnungen').insert(lohnabrechnung_data).execute()
            return response.data[0]['id'] if response.data else None
    
    except Exception as e:
        print(f"Fehler beim Erstellen der Lohnabrechnung: {str(e)}")
        return None


def generiere_lohnabrechnung_pdf(lohnabrechnung_id: str) -> Optional[bytes]:
    """
    Generiert ein PDF für eine Lohnabrechnung
    
    Args:
        lohnabrechnung_id: Lohnabrechnung-ID
        
    Returns:
        Optional[bytes]: PDF-Bytes wenn erfolgreich
    """
    try:
        supabase = get_supabase_client()
        
        # Lade Lohnabrechnung mit allen Daten
        lohnabrechnung_response = supabase.table('lohnabrechnungen').select(
            '*, mitarbeiter(*), arbeitszeitkonto(*)'
        ).eq('id', lohnabrechnung_id).execute()
        
        if not lohnabrechnung_response.data:
            return None
        
        lohnabrechnung = lohnabrechnung_response.data[0]
        mitarbeiter = lohnabrechnung['mitarbeiter']
        arbeitszeitkonto = lohnabrechnung['arbeitszeitkonto']
        
        # Erstelle PDF in Memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        
        # Styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        normal_style = styles['Normal']
        
        # Story (Inhalt)
        story = []
        
        # Titel
        story.append(Paragraph("Entgeltaufstellung", title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Zeitraum
        monat_name = get_monatsnamen(lohnabrechnung['monat'])
        story.append(Paragraph(
            f"<b>Abrechnungszeitraum:</b> {monat_name} {lohnabrechnung['jahr']}",
            normal_style
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # Mitarbeiterdaten
        story.append(Paragraph("Mitarbeiterdaten", heading_style))
        
        mitarbeiter_data = [
            ['Personalnummer:', mitarbeiter['personalnummer']],
            ['Name:', f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}"],
            ['Geburtsdatum:', mitarbeiter['geburtsdatum']],
            ['Adresse:', f"{mitarbeiter['strasse']}, {mitarbeiter['plz']} {mitarbeiter['ort']}"]
        ]
        
        mitarbeiter_table = Table(mitarbeiter_data, colWidths=[5*cm, 10*cm])
        mitarbeiter_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(mitarbeiter_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Arbeitszeitkonto
        story.append(Paragraph("Arbeitszeitkonto", heading_style))
        
        arbeitszeitkonto_data = [
            ['Soll-Stunden:', format_stunden(arbeitszeitkonto['soll_stunden'])],
            ['Ist-Stunden:', format_stunden(arbeitszeitkonto['ist_stunden'])],
            ['Differenz:', format_stunden(abs(arbeitszeitkonto['differenz_stunden'])) + 
             (' (Plus)' if arbeitszeitkonto['differenz_stunden'] >= 0 else ' (Minus)')],
            ['Urlaubstage genommen:', f"{arbeitszeitkonto['urlaubstage_genommen']} Tage"]
        ]
        
        if arbeitszeitkonto['sonntagsstunden'] > 0:
            arbeitszeitkonto_data.append(['Sonntagsstunden:', format_stunden(arbeitszeitkonto['sonntagsstunden'])])
        
        if arbeitszeitkonto['feiertagsstunden'] > 0:
            arbeitszeitkonto_data.append(['Feiertagsstunden:', format_stunden(arbeitszeitkonto['feiertagsstunden'])])
        
        arbeitszeitkonto_table = Table(arbeitszeitkonto_data, colWidths=[5*cm, 10*cm])
        arbeitszeitkonto_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(arbeitszeitkonto_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Lohnberechnung
        story.append(Paragraph("Lohnberechnung (Brutto)", heading_style))
        
        lohn_data = [
            ['Beschreibung', 'Betrag'],
            ['Grundlohn', format_waehrung(lohnabrechnung['grundlohn'])],
        ]
        
        if lohnabrechnung['sonntagszuschlag'] > 0:
            lohn_data.append(['Sonntagszuschlag (50%)', format_waehrung(lohnabrechnung['sonntagszuschlag'])])
        
        if lohnabrechnung['feiertagszuschlag'] > 0:
            lohn_data.append(['Feiertagszuschlag (100%)', format_waehrung(lohnabrechnung['feiertagszuschlag'])])
        
        lohn_data.append(['', ''])  # Leerzeile
        lohn_data.append(['Gesamtbetrag (Brutto)', format_waehrung(lohnabrechnung['gesamtbetrag'])])
        
        lohn_table = Table(lohn_data, colWidths=[10*cm, 5*cm])
        lohn_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            
            # Body
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 10),
            ('ALIGN', (1, 1), (1, -2), 'RIGHT'),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 6),
            
            # Gesamtbetrag
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('ALIGN', (1, -1), (1, -1), 'RIGHT'),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1f77b4')),
            ('TOPPADDING', (0, -1), (-1, -1), 10),
            
            # Grid
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ]))
        
        story.append(lohn_table)
        story.append(Spacer(1, 1*cm))
        
        # Hinweise
        story.append(Paragraph("Hinweise", heading_style))
        story.append(Paragraph(
            "Diese Entgeltaufstellung dient als Nachweis der geleisteten Arbeitsstunden und "
            "der daraus resultierenden Vergütung gemäß Arbeitsvertrag. Die Zeiterfassung erfolgt "
            "nach den Vorgaben des EuGH-Urteils zur Arbeitszeiterfassung.",
            normal_style
        ))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            f"<i>Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>",
            normal_style
        ))
        
        # Generiere PDF
        doc.build(story)
        
        # Hole PDF-Bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    except Exception as e:
        print(f"Fehler beim Generieren des PDFs: {str(e)}")
        return None


def speichere_lohnabrechnung_pdf(lohnabrechnung_id: str) -> Optional[str]:
    """
    Generiert und speichert ein Lohnabrechnung-PDF in Supabase Storage
    
    Args:
        lohnabrechnung_id: Lohnabrechnung-ID
        
    Returns:
        Optional[str]: Pfad zum PDF wenn erfolgreich
    """
    try:
        from utils.database import upload_file_to_storage
        
        supabase = get_supabase_client()
        
        # Lade Lohnabrechnung
        lohnabrechnung_response = supabase.table('lohnabrechnungen').select(
            '*, mitarbeiter(id, personalnummer)'
        ).eq('id', lohnabrechnung_id).execute()
        
        if not lohnabrechnung_response.data:
            return None
        
        lohnabrechnung = lohnabrechnung_response.data[0]
        
        # Generiere PDF
        pdf_bytes = generiere_lohnabrechnung_pdf(lohnabrechnung_id)
        if not pdf_bytes:
            return None
        
        # Erstelle Pfad
        mitarbeiter_id = lohnabrechnung['mitarbeiter']['id']
        jahr = lohnabrechnung['jahr']
        monat = lohnabrechnung['monat']
        
        file_path = f"{mitarbeiter_id}/{jahr}/{monat:02d}_abrechnung.pdf"
        
        # Lade hoch
        result = upload_file_to_storage('lohnabrechnungen', file_path, pdf_bytes)
        
        if result:
            # Aktualisiere Lohnabrechnung mit PDF-Pfad
            supabase.table('lohnabrechnungen').update({
                'pdf_path': file_path
            }).eq('id', lohnabrechnung_id).execute()
            
            return file_path
        
        return None
    
    except Exception as e:
        print(f"Fehler beim Speichern des PDFs: {str(e)}")
        return None
