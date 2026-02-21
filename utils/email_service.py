"""
E-Mail-Benachrichtigungssystem
Sendet E-Mails für Urlaubsanträge, Dienstpläne, etc.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def send_email(to_email: str, subject: str, body: str, html_body: str = None):
    """
    Sendet eine E-Mail
    
    Args:
        to_email: Empfänger-E-Mail-Adresse
        subject: Betreff
        body: Text-Inhalt
        html_body: HTML-Inhalt (optional)
    
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # SMTP-Konfiguration aus Umgebungsvariablen
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username)
        
        if not smtp_username or not smtp_password:
            print("E-Mail-Konfiguration fehlt. Bitte SMTP-Einstellungen in .env setzen.")
            return False
        
        # E-Mail erstellen
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Text-Teil
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # HTML-Teil (optional)
        if html_body:
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
        
        # E-Mail senden
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")
        return False


def send_urlaubsantrag_email(mitarbeiter_name: str, von_datum: str, bis_datum: str, tage: int, grund: str = None):
    """
    Sendet E-Mail an Admin bei neuem Urlaubsantrag
    
    Args:
        mitarbeiter_name: Name des Mitarbeiters
        von_datum: Startdatum
        bis_datum: Enddatum
        tage: Anzahl Tage
        grund: Grund (optional)
    """
    admin_email = "piccolo_leipzig@yahoo.de"
    
    subject = f"Neuer Urlaubsantrag von {mitarbeiter_name}"
    
    body = f"""
Guten Tag,

{mitarbeiter_name} hat einen neuen Urlaubsantrag gestellt:

Zeitraum: {von_datum} bis {bis_datum}
Anzahl Tage: {tage}
{f'Grund: {grund}' if grund else ''}

Bitte prüfen und genehmigen Sie den Antrag in CrewBase.

Mit freundlichen Grüßen
CrewBase Arbeitszeitverwaltung
    """
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2>Neuer Urlaubsantrag</h2>
    <p><strong>{mitarbeiter_name}</strong> hat einen neuen Urlaubsantrag gestellt:</p>
    <ul>
        <li><strong>Zeitraum:</strong> {von_datum} bis {bis_datum}</li>
        <li><strong>Anzahl Tage:</strong> {tage}</li>
        {f'<li><strong>Grund:</strong> {grund}</li>' if grund else ''}
    </ul>
    <p>Bitte prüfen und genehmigen Sie den Antrag in CrewBase.</p>
    <hr>
    <p style="color: #666; font-size: 0.9em;">CrewBase Arbeitszeitverwaltung</p>
</body>
</html>
    """
    
    return send_email(admin_email, subject, body, html_body)


def send_dienstplan_email(mitarbeiter_email: str, mitarbeiter_name: str, monat: str, jahr: int):
    """
    Sendet E-Mail an Mitarbeiter bei fertigem Dienstplan
    
    Args:
        mitarbeiter_email: E-Mail des Mitarbeiters
        mitarbeiter_name: Name des Mitarbeiters
        monat: Monatsname
        jahr: Jahr
    """
    subject = f"Dienstplan {monat} {jahr} ist fertig"
    
    body = f"""
Hallo {mitarbeiter_name},

Ihr Dienstplan für {monat} {jahr} ist jetzt verfügbar.

Bitte melden Sie sich in CrewBase an, um Ihren Dienstplan einzusehen.

Mit freundlichen Grüßen
Ihr Team
    """
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2>Dienstplan verfügbar</h2>
    <p>Hallo <strong>{mitarbeiter_name}</strong>,</p>
    <p>Ihr Dienstplan für <strong>{monat} {jahr}</strong> ist jetzt verfügbar.</p>
    <p>Bitte melden Sie sich in CrewBase an, um Ihren Dienstplan einzusehen.</p>
    <hr>
    <p style="color: #666; font-size: 0.9em;">CrewBase Arbeitszeitverwaltung</p>
</body>
</html>
    """
    
    return send_email(mitarbeiter_email, subject, body, html_body)


def send_urlaubsgenehmigung_email(mitarbeiter_email: str, mitarbeiter_name: str, status: str, von_datum: str, bis_datum: str):
    """
    Sendet E-Mail an Mitarbeiter über Urlaubsgenehmigung/-ablehnung
    
    Args:
        mitarbeiter_email: E-Mail des Mitarbeiters
        mitarbeiter_name: Name des Mitarbeiters
        status: 'genehmigt' oder 'abgelehnt'
        von_datum: Startdatum
        bis_datum: Enddatum
    """
    if status == 'genehmigt':
        subject = f"Urlaubsantrag genehmigt ({von_datum} - {bis_datum})"
        status_text = "genehmigt"
        status_color = "#28a745"
    else:
        subject = f"Urlaubsantrag abgelehnt ({von_datum} - {bis_datum})"
        status_text = "abgelehnt"
        status_color = "#dc3545"
    
    body = f"""
Hallo {mitarbeiter_name},

Ihr Urlaubsantrag für den Zeitraum {von_datum} bis {bis_datum} wurde {status_text}.

Mit freundlichen Grüßen
Ihr Team
    """
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2 style="color: {status_color};">Urlaubsantrag {status_text}</h2>
    <p>Hallo <strong>{mitarbeiter_name}</strong>,</p>
    <p>Ihr Urlaubsantrag für den Zeitraum <strong>{von_datum}</strong> bis <strong>{bis_datum}</strong> wurde <strong style="color: {status_color};">{status_text}</strong>.</p>
    <hr>
    <p style="color: #666; font-size: 0.9em;">CrewBase Arbeitszeitverwaltung</p>
</body>
</html>
    """
    
    return send_email(mitarbeiter_email, subject, body, html_body)
