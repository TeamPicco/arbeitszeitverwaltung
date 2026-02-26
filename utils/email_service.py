"""
E-Mail-Benachrichtigungssystem für CrewBase
Sendet E-Mails für Urlaubsanträge, Dienstpläne, Stammdatenänderungen etc.

Konfiguration über Umgebungsvariablen:
    SMTP_SERVER: SMTP-Server (Standard: smtp.gmail.com)
    SMTP_PORT: SMTP-Port (Standard: 587)
    SMTP_USERNAME: SMTP-Benutzername / E-Mail-Adresse
    SMTP_PASSWORD: SMTP-Passwort oder App-Passwort
    SMTP_FROM_EMAIL: Absender-E-Mail (Standard: SMTP_USERNAME)
    ADMIN_EMAIL: E-Mail-Adresse des Administrators
"""

import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# Standard-Admin-E-Mail (kann in DB oder .env überschrieben werden)
DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "piccolo_leipzig@yahoo.de")


def ist_email_konfiguriert() -> bool:
    """Prüft ob SMTP-Konfiguration vorhanden ist."""
    return bool(os.getenv("SMTP_USERNAME") and os.getenv("SMTP_PASSWORD"))


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None,
    cc: str = None
) -> bool:
    """
    Sendet eine E-Mail über SMTP.
    
    Args:
        to_email: Empfänger-E-Mail-Adresse
        subject: Betreff
        body: Plaintext-Inhalt
        html_body: HTML-Inhalt (optional, bevorzugt wenn vorhanden)
        cc: CC-Empfänger (optional)
    
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    if not ist_email_konfiguriert():
        logger.warning("E-Mail-Konfiguration fehlt. Bitte SMTP_USERNAME und SMTP_PASSWORD in .env setzen.")
        return False
    
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username)
        from_name = os.getenv("SMTP_FROM_NAME", "CrewBase")
        
        # E-Mail erstellen
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = cc
        
        # Text-Teil (Fallback)
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # HTML-Teil (bevorzugt)
        if html_body:
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
        
        # E-Mail senden
        recipients = [to_email]
        if cc:
            recipients.append(cc)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, recipients, msg.as_string())
        
        logger.info(f"E-Mail erfolgreich gesendet an {to_email}: {subject}")
        return True
    
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP-Authentifizierung fehlgeschlagen. Bitte SMTP-Zugangsdaten prüfen.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP-Fehler beim Senden der E-Mail: {e}")
        return False
    except Exception as e:
        logger.error(f"Unbekannter Fehler beim Senden der E-Mail: {e}")
        return False


def _erstelle_html_template(titel: str, inhalt: str, farbe: str = "#1e3a5f") -> str:
    """Erstellt ein einheitliches HTML-E-Mail-Template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, Helvetica, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <!-- Header -->
        <div style="background-color: {farbe}; padding: 20px 30px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 1.5rem;">🍽️ CrewBase</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 0.9rem;">Arbeitszeitverwaltung</p>
        </div>
        <!-- Inhalt -->
        <div style="padding: 30px;">
            <h2 style="color: {farbe}; margin-top: 0;">{titel}</h2>
            {inhalt}
        </div>
        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 15px 30px; border-top: 1px solid #dee2e6;">
            <p style="color: #6c757d; font-size: 0.8rem; margin: 0;">
                Diese E-Mail wurde automatisch von CrewBase generiert. Bitte nicht direkt antworten.
            </p>
        </div>
    </div>
</body>
</html>
    """


# ============================================================
# URLAUBSANTRAG-BENACHRICHTIGUNGEN
# ============================================================

def send_urlaubsantrag_email(
    mitarbeiter_name: str,
    von_datum: str,
    bis_datum: str,
    tage: int,
    grund: str = None,
    admin_email: str = None
) -> bool:
    """
    Sendet E-Mail an Admin bei neuem Urlaubsantrag.
    
    Args:
        mitarbeiter_name: Name des Mitarbeiters
        von_datum: Startdatum (formatiert)
        bis_datum: Enddatum (formatiert)
        tage: Anzahl Urlaubstage
        grund: Bemerkung des Mitarbeiters (optional)
        admin_email: Admin-E-Mail (Standard aus .env)
    """
    empfaenger = admin_email or DEFAULT_ADMIN_EMAIL
    
    subject = f"📅 Neuer Urlaubsantrag von {mitarbeiter_name}"
    
    body = (
        f"Guten Tag,\n\n"
        f"{mitarbeiter_name} hat einen neuen Urlaubsantrag gestellt:\n\n"
        f"Zeitraum: {von_datum} bis {bis_datum}\n"
        f"Anzahl Tage: {tage}\n"
        f"{f'Bemerkung: {grund}' if grund else ''}\n\n"
        f"Bitte prüfen und genehmigen Sie den Antrag in CrewBase.\n\n"
        f"Mit freundlichen Grüßen\nCrewBase"
    )
    
    inhalt = f"""
        <p><strong>{mitarbeiter_name}</strong> hat einen neuen Urlaubsantrag gestellt:</p>
        <table style="border-collapse: collapse; width: 100%; margin: 15px 0;">
            <tr style="background-color: #f8f9fa;">
                <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Zeitraum</td>
                <td style="padding: 10px; border: 1px solid #dee2e6;">{von_datum} bis {bis_datum}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Anzahl Tage</td>
                <td style="padding: 10px; border: 1px solid #dee2e6;">{tage} Tage</td>
            </tr>
            {f'<tr style="background-color: #f8f9fa;"><td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Bemerkung</td><td style="padding: 10px; border: 1px solid #dee2e6;">{grund}</td></tr>' if grund else ''}
        </table>
        <p>Bitte melden Sie sich in <strong>CrewBase</strong> an, um den Antrag zu genehmigen oder abzulehnen.</p>
    """
    
    html_body = _erstelle_html_template(f"Neuer Urlaubsantrag: {mitarbeiter_name}", inhalt)
    
    return send_email(empfaenger, subject, body, html_body)


def send_urlaubsgenehmigung_email(
    mitarbeiter_email: str,
    mitarbeiter_name: str,
    status: str,
    von_datum: str,
    bis_datum: str,
    tage: int = None,
    bemerkung_admin: str = None
) -> bool:
    """
    Sendet E-Mail an Mitarbeiter über Urlaubsgenehmigung/-ablehnung.
    
    Args:
        mitarbeiter_email: E-Mail des Mitarbeiters
        mitarbeiter_name: Name des Mitarbeiters
        status: 'genehmigt' oder 'abgelehnt'
        von_datum: Startdatum (formatiert)
        bis_datum: Enddatum (formatiert)
        tage: Anzahl Tage (optional)
        bemerkung_admin: Bemerkung des Admins (optional)
    """
    if not mitarbeiter_email:
        logger.warning(f"Keine E-Mail-Adresse für {mitarbeiter_name} hinterlegt.")
        return False
    
    if status == 'genehmigt':
        subject = f"✅ Urlaubsantrag genehmigt ({von_datum} – {bis_datum})"
        status_text = "genehmigt"
        farbe = "#28a745"
        emoji = "✅"
    else:
        subject = f"❌ Urlaubsantrag abgelehnt ({von_datum} – {bis_datum})"
        status_text = "leider abgelehnt"
        farbe = "#dc3545"
        emoji = "❌"
    
    body = (
        f"Hallo {mitarbeiter_name},\n\n"
        f"Ihr Urlaubsantrag für den Zeitraum {von_datum} bis {bis_datum} wurde {status_text}.\n"
        f"{f'Bemerkung: {bemerkung_admin}' if bemerkung_admin else ''}\n\n"
        f"Mit freundlichen Grüßen\nIhr Team"
    )
    
    tage_zeile = f'<tr style="background-color: #f8f9fa;"><td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Anzahl Tage</td><td style="padding: 10px; border: 1px solid #dee2e6;">{tage} Tage</td></tr>' if tage else ''
    bemerkung_zeile = f'<tr><td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Bemerkung</td><td style="padding: 10px; border: 1px solid #dee2e6;">{bemerkung_admin}</td></tr>' if bemerkung_admin else ''
    
    inhalt = f"""
        <p>Hallo <strong>{mitarbeiter_name}</strong>,</p>
        <p>Ihr Urlaubsantrag wurde bearbeitet:</p>
        <div style="background-color: {farbe}15; border-left: 4px solid {farbe}; padding: 15px; margin: 15px 0; border-radius: 4px;">
            <p style="margin: 0; font-size: 1.1rem; color: {farbe}; font-weight: bold;">{emoji} Antrag {status_text}</p>
        </div>
        <table style="border-collapse: collapse; width: 100%; margin: 15px 0;">
            <tr>
                <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Zeitraum</td>
                <td style="padding: 10px; border: 1px solid #dee2e6;">{von_datum} bis {bis_datum}</td>
            </tr>
            {tage_zeile}
            {bemerkung_zeile}
        </table>
    """
    
    html_body = _erstelle_html_template(f"Urlaubsantrag {status_text}", inhalt, farbe=farbe)
    
    return send_email(mitarbeiter_email, subject, body, html_body)


# ============================================================
# DIENSTPLAN-BENACHRICHTIGUNGEN
# ============================================================

def send_dienstplan_email(
    mitarbeiter_email: str,
    mitarbeiter_name: str,
    monat: str,
    jahr: int,
    app_url: str = None
) -> bool:
    """
    Sendet E-Mail an Mitarbeiter wenn Dienstplan veröffentlicht wurde.
    
    Args:
        mitarbeiter_email: E-Mail des Mitarbeiters
        mitarbeiter_name: Name des Mitarbeiters
        monat: Monatsname (z.B. "März")
        jahr: Jahr
        app_url: URL der App (optional)
    """
    if not mitarbeiter_email:
        logger.warning(f"Keine E-Mail-Adresse für {mitarbeiter_name} hinterlegt.")
        return False
    
    app_link = app_url or os.getenv("APP_URL", "https://arbeitszeitverwaltung.onrender.com")
    
    subject = f"📅 Ihr Dienstplan für {monat} {jahr} ist verfügbar"
    
    body = (
        f"Hallo {mitarbeiter_name},\n\n"
        f"Ihr Dienstplan für {monat} {jahr} wurde veröffentlicht und ist jetzt verfügbar.\n\n"
        f"Bitte melden Sie sich in CrewBase an, um Ihren Dienstplan einzusehen:\n"
        f"{app_link}\n\n"
        f"Mit freundlichen Grüßen\nIhr Team"
    )
    
    inhalt = f"""
        <p>Hallo <strong>{mitarbeiter_name}</strong>,</p>
        <p>Ihr Dienstplan für <strong>{monat} {jahr}</strong> wurde veröffentlicht und ist jetzt verfügbar.</p>
        <div style="text-align: center; margin: 25px 0;">
            <a href="{app_link}" 
               style="background-color: #1e3a5f; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                📅 Dienstplan ansehen
            </a>
        </div>
        <p style="color: #6c757d; font-size: 0.9rem;">
            Falls der Button nicht funktioniert, öffnen Sie bitte: <a href="{app_link}">{app_link}</a>
        </p>
    """
    
    html_body = _erstelle_html_template(f"Dienstplan {monat} {jahr} verfügbar", inhalt)
    
    return send_email(mitarbeiter_email, subject, body, html_body)


def send_dienstplan_alle_mitarbeiter(
    mitarbeiter_liste: list,
    monat: str,
    jahr: int,
    app_url: str = None
) -> dict:
    """
    Sendet Dienstplan-Benachrichtigung an alle Mitarbeiter mit E-Mail-Adresse.
    
    Args:
        mitarbeiter_liste: Liste von Mitarbeiter-Dicts (mit 'email', 'vorname', 'nachname')
        monat: Monatsname
        jahr: Jahr
        app_url: App-URL
        
    Returns:
        dict: {'gesendet': int, 'fehlgeschlagen': int, 'keine_email': int}
    """
    ergebnis = {'gesendet': 0, 'fehlgeschlagen': 0, 'keine_email': 0}
    
    for ma in mitarbeiter_liste:
        email = ma.get('email')
        name = f"{ma.get('vorname', '')} {ma.get('nachname', '')}".strip()
        
        if not email:
            ergebnis['keine_email'] += 1
            continue
        
        success = send_dienstplan_email(email, name, monat, jahr, app_url)
        
        if success:
            ergebnis['gesendet'] += 1
        else:
            ergebnis['fehlgeschlagen'] += 1
    
    return ergebnis


# ============================================================
# STAMMDATEN-BENACHRICHTIGUNGEN
# ============================================================

def send_stammdaten_aenderung_email(
    admin_email: str,
    mitarbeiter_name: str,
    feld: str,
    alter_wert: str,
    neuer_wert: str,
    benoetigt_genehmigung: bool = False
) -> bool:
    """
    Sendet E-Mail an Admin bei Stammdatenänderung eines Mitarbeiters.
    
    Args:
        admin_email: E-Mail des Admins
        mitarbeiter_name: Name des Mitarbeiters
        feld: Geändertes Feld (z.B. 'E-Mail', 'Telefon')
        alter_wert: Alter Wert
        neuer_wert: Neuer Wert
        benoetigt_genehmigung: True wenn Genehmigung erforderlich (z.B. Nachname)
    """
    empfaenger = admin_email or DEFAULT_ADMIN_EMAIL
    
    if benoetigt_genehmigung:
        subject = f"✋ Änderungsanfrage von {mitarbeiter_name}: {feld}"
        titel = f"Änderungsanfrage: {feld}"
        hinweis = "<p><strong>Diese Änderung benötigt Ihre Genehmigung.</strong> Bitte melden Sie sich in CrewBase an.</p>"
    else:
        subject = f"ℹ️ Stammdaten geändert: {mitarbeiter_name}"
        titel = f"Stammdatenänderung: {mitarbeiter_name}"
        hinweis = "<p>Diese Änderung wurde automatisch übernommen.</p>"
    
    body = (
        f"Guten Tag,\n\n"
        f"{mitarbeiter_name} hat folgende Stammdaten geändert:\n\n"
        f"Feld: {feld}\n"
        f"Alt: {alter_wert}\n"
        f"Neu: {neuer_wert}\n\n"
        f"{'Diese Änderung benötigt Ihre Genehmigung.' if benoetigt_genehmigung else 'Diese Änderung wurde automatisch übernommen.'}\n\n"
        f"Mit freundlichen Grüßen\nCrewBase"
    )
    
    inhalt = f"""
        <p><strong>{mitarbeiter_name}</strong> hat folgende Stammdaten geändert:</p>
        <table style="border-collapse: collapse; width: 100%; margin: 15px 0;">
            <tr style="background-color: #f8f9fa;">
                <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Feld</td>
                <td style="padding: 10px; border: 1px solid #dee2e6;">{feld}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Alter Wert</td>
                <td style="padding: 10px; border: 1px solid #dee2e6; color: #dc3545;">{alter_wert or '(leer)'}</td>
            </tr>
            <tr style="background-color: #f8f9fa;">
                <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Neuer Wert</td>
                <td style="padding: 10px; border: 1px solid #dee2e6; color: #28a745;">{neuer_wert}</td>
            </tr>
        </table>
        {hinweis}
    """
    
    html_body = _erstelle_html_template(titel, inhalt)
    
    return send_email(empfaenger, subject, body, html_body)


# ============================================================
# LOHNABRECHNUNG-BENACHRICHTIGUNGEN
# ============================================================

def send_lohnabrechnung_email(
    mitarbeiter_email: str,
    mitarbeiter_name: str,
    monat: str,
    jahr: int,
    gesamtbetrag: float,
    app_url: str = None
) -> bool:
    """
    Sendet E-Mail an Mitarbeiter wenn Lohnabrechnung erstellt wurde.
    
    Args:
        mitarbeiter_email: E-Mail des Mitarbeiters
        mitarbeiter_name: Name des Mitarbeiters
        monat: Monatsname
        jahr: Jahr
        gesamtbetrag: Brutto-Gesamtbetrag
        app_url: App-URL
    """
    if not mitarbeiter_email:
        return False
    
    app_link = app_url or os.getenv("APP_URL", "https://arbeitszeitverwaltung.onrender.com")
    
    subject = f"💰 Ihre Lohnabrechnung für {monat} {jahr} ist verfügbar"
    
    body = (
        f"Hallo {mitarbeiter_name},\n\n"
        f"Ihre Lohnabrechnung für {monat} {jahr} wurde erstellt.\n"
        f"Gesamtbetrag (Brutto): {gesamtbetrag:.2f} €\n\n"
        f"Die vollständige Abrechnung finden Sie in CrewBase unter 'Meine Dokumente'.\n\n"
        f"Mit freundlichen Grüßen\nIhr Team"
    )
    
    inhalt = f"""
        <p>Hallo <strong>{mitarbeiter_name}</strong>,</p>
        <p>Ihre Lohnabrechnung für <strong>{monat} {jahr}</strong> wurde erstellt und steht zum Download bereit.</p>
        <div style="background-color: #e8f5e9; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; border-radius: 4px;">
            <p style="margin: 0; font-size: 1.1rem; font-weight: bold; color: #1e7e34;">
                💰 Gesamtbetrag (Brutto): {gesamtbetrag:,.2f} €
            </p>
        </div>
        <p>Die vollständige Abrechnung finden Sie in CrewBase unter <strong>Meine Dokumente → Lohnabrechnungen</strong>.</p>
        <div style="text-align: center; margin: 25px 0;">
            <a href="{app_link}" 
               style="background-color: #1e3a5f; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                📄 Abrechnung ansehen
            </a>
        </div>
    """
    
    html_body = _erstelle_html_template(f"Lohnabrechnung {monat} {jahr}", inhalt)
    
    return send_email(mitarbeiter_email, subject, body, html_body)
