"""
QR-Code-Generierung für Mastergeräte-Aktivierung
"""

import qrcode
import io
import base64
from typing import Optional


def generiere_aktivierungs_qr(registrierungscode: str, geraet_name: str, app_url: str = None) -> Optional[bytes]:
    """
    Generiert einen QR-Code für die Mastergeräte-Aktivierung.
    
    Der QR-Code enthält die URL zur App mit dem Registrierungscode als Parameter,
    sodass das Gerät durch einfaches Scannen aktiviert werden kann.
    
    Args:
        registrierungscode: Der eindeutige Registrierungscode des Mastergeräts
        geraet_name: Name des Geräts (für den QR-Code-Inhalt)
        app_url: Basis-URL der App (z.B. https://arbeitszeitverwaltung.onrender.com)
        
    Returns:
        Optional[bytes]: PNG-Bytes des QR-Codes oder None bei Fehler
    """
    try:
        # Erstelle Aktivierungs-URL
        if app_url:
            # URL mit Code-Parameter für automatische Aktivierung
            qr_inhalt = f"{app_url.rstrip('/')}/?activate={registrierungscode}"
        else:
            # Fallback: Nur der Code
            qr_inhalt = f"CREWBASE-ACTIVATE:{registrierungscode}"
        
        # QR-Code konfigurieren
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Hohe Fehlerkorrektur
            box_size=10,
            border=4,
        )
        
        qr.add_data(qr_inhalt)
        qr.make(fit=True)
        
        # Erstelle Bild
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Konvertiere zu Bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer.getvalue()
    
    except Exception as e:
        print(f"Fehler beim Generieren des QR-Codes: {e}")
        return None


def qr_zu_base64(qr_bytes: bytes) -> Optional[str]:
    """
    Konvertiert QR-Code-Bytes zu Base64-String für HTML-Einbettung.
    
    Args:
        qr_bytes: PNG-Bytes des QR-Codes
        
    Returns:
        Optional[str]: Base64-kodierter String
    """
    if not qr_bytes:
        return None
    return base64.b64encode(qr_bytes).decode('utf-8')


def zeige_qr_code_html(registrierungscode: str, geraet_name: str, app_url: str = None) -> str:
    """
    Erstellt HTML-Darstellung des QR-Codes mit Anleitung.
    
    Args:
        registrierungscode: Registrierungscode
        geraet_name: Gerätename
        app_url: App-URL
        
    Returns:
        str: HTML-String mit QR-Code und Anleitung
    """
    qr_bytes = generiere_aktivierungs_qr(registrierungscode, geraet_name, app_url)
    
    if not qr_bytes:
        return "<p>QR-Code konnte nicht generiert werden.</p>"
    
    qr_b64 = qr_zu_base64(qr_bytes)
    
    html = f"""
    <div style="text-align: center; padding: 20px; border: 2px solid #1e3a5f; border-radius: 10px; background-color: #f8f9fa;">
        <h3 style="color: #1e3a5f;">📱 QR-Code für Gerät: {geraet_name}</h3>
        <img src="data:image/png;base64,{qr_b64}" 
             style="max-width: 200px; border: 1px solid #dee2e6; border-radius: 5px;" 
             alt="QR-Code für {geraet_name}"/>
        <p style="margin-top: 10px; color: #6c757d; font-size: 0.9rem;">
            <strong>Registrierungscode:</strong> <code style="background: #e9ecef; padding: 2px 6px; border-radius: 3px;">{registrierungscode}</code>
        </p>
        <p style="color: #6c757d; font-size: 0.85rem;">
            📱 QR-Code mit dem Gerät scannen oder Code manuell eingeben
        </p>
    </div>
    """
    
    return html
