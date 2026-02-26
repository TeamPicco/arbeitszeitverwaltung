"""
Mastergeräte-Verwaltung
Geräte-Identifikation, Aktivierung und Zugriffskontrolle
"""

import streamlit as st
import hashlib
import json
from utils.database import get_supabase_client


def get_device_id():
    """
    Generiert eine eindeutige Geräte-ID basierend auf Browser-Informationen
    Verwendet Streamlit's Session State für Persistenz
    
    Returns:
        str: Eindeutige Geräte-ID
    """
    # Prüfe ob bereits eine Device-ID im Session State existiert
    if 'device_id' in st.session_state:
        return st.session_state.device_id
    
    # Generiere neue Device-ID basierend auf Browser-Fingerprint
    # In Streamlit verwenden wir eine Kombination aus Session-ID und Browser-Info
    try:
        # Verwende Session-ID als Basis (eindeutig pro Browser-Tab/Session)
        session_id = st.runtime.scriptrunner.get_script_run_ctx().session_id
        
        # Erstelle Hash
        device_hash = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        
        # Speichere in Session State
        st.session_state.device_id = device_hash
        
        return device_hash
    except:
        # Fallback: Generiere zufällige ID
        import uuid
        device_id = str(uuid.uuid4())[:16]
        st.session_state.device_id = device_id
        return device_id


def is_device_activated(betrieb_id: int):
    """
    Prüft, ob das aktuelle Gerät als Mastergerät aktiviert ist
    
    Args:
        betrieb_id: ID des Betriebs
        
    Returns:
        tuple: (bool: aktiviert, str: Gerätename oder None)
    """
    device_id = get_device_id()
    
    try:
        supabase = get_supabase_client()
        
        # Prüfe ob Gerät in aktivierten Geräten gespeichert ist
        result = supabase.table('mastergeraete').select('*').eq(
            'geraete_id', device_id
        ).eq('betrieb_id', betrieb_id).eq('aktiv', True).execute()
        
        if result.data and len(result.data) > 0:
            return True, result.data[0]['name']
        
        return False, None
        
    except Exception as e:
        import logging
        logging.error(f"Fehler bei Geräte-Prüfung: {e}")
        return False, None


def activate_device_with_code(code: str, betrieb_id: int):
    """
    Aktiviert das aktuelle Gerät mit einem Registrierungscode
    
    Args:
        code: Registrierungscode
        betrieb_id: ID des Betriebs
        
    Returns:
        tuple: (bool: erfolgreich, str: Fehlermeldung oder Gerätename)
    """
    device_id = get_device_id()
    
    try:
        supabase = get_supabase_client()
        
        # Suche Mastergerät mit diesem Code
        result = supabase.table('mastergeraete').select('*').eq(
            'registrierungscode', code
        ).eq('betrieb_id', betrieb_id).eq('aktiv', True).execute()
        
        if not result.data or len(result.data) == 0:
            return False, "Ungültiger Code oder Gerät nicht aktiv"
        
        mastergeraet = result.data[0]
        
        # Aktualisiere Gerät mit Device-ID
        supabase.table('mastergeraete').update({
            'geraete_id': device_id,
            'letzter_kontakt': 'now()'
        }).eq('id', mastergeraet['id']).execute()
        
        return True, mastergeraet['name']
        
    except Exception as e:
        import logging
        logging.error(f"Fehler bei Geräte-Aktivierung: {e}")
        return False, f"Fehler: {str(e)}"


def check_device_or_mobile_permission(mitarbeiter: dict, betrieb_id: int):
    """
    Prüft, ob Zeiterfassung erlaubt ist (Mastergerät ODER mobile Berechtigung)
    
    Args:
        mitarbeiter: Mitarbeiter-Dict
        betrieb_id: ID des Betriebs
        
    Returns:
        tuple: (bool: erlaubt, str: Grund)
    """
    # Prüfe mobile Berechtigung
    if mitarbeiter.get('mobile_zeiterfassung', False):
        return True, "Mobile Zeiterfassung aktiviert"
    
    # Prüfe Mastergerät
    is_activated, device_name = is_device_activated(betrieb_id)
    
    if is_activated:
        return True, f"Mastergerät: {device_name}"
    
    return False, "Keine Berechtigung"


def show_device_activation_dialog(betrieb_id: int):
    """
    Zeigt Dialog zur Geräte-Aktivierung an.
    Unterstützt automatische Aktivierung per QR-Code-URL-Parameter
    sowie manuelle Code-Eingabe.
    
    Args:
        betrieb_id: ID des Betriebs
        
    Returns:
        bool: True wenn aktiviert
    """
    import streamlit as st
    
    # Prüfe ob QR-Code-Aktivierung per URL-Parameter (?activate=CODE)
    query_params = st.query_params
    auto_code = query_params.get('activate', None)
    
    if auto_code:
        # Automatische Aktivierung per QR-Code
        st.info(f"📱 QR-Code erkannt. Aktiviere Gerät...")
        success, message = activate_device_with_code(auto_code, betrieb_id)
        
        if success:
            st.success(f"✅ Gerät erfolgreich als Mastergerät aktiviert: **{message}**")
            st.balloons()
            # URL-Parameter entfernen
            st.query_params.clear()
            st.rerun()
            return True
        else:
            st.error(f"❌ Aktivierung fehlgeschlagen: {message}")
            st.query_params.clear()
    
    st.warning("⚠️ Dieses Gerät ist nicht als Mastergerät registriert.")
    
    st.info("""
    **Mastergeräte-Aktivierung erforderlich**
    
    Um die Zeiterfassung auf diesem Gerät zu nutzen, benötigen Sie einen Registrierungscode.
    
    **Option 1: QR-Code scannen (empfohlen)**
    1. Administrator öffnet Mastergeräte-Verwaltung
    2. Klickt auf "📱 QR-Code anzeigen" beim gewünschten Gerät
    3. QR-Code mit diesem Gerät scannen – Aktivierung erfolgt automatisch
    
    **Option 2: Code manuell eingeben**
    1. Administrator öffnet Mastergeräte-Verwaltung
    2. Notiert den Registrierungscode des Geräts
    3. Code unten eingeben
    """)
    
    with st.form("device_activation_form"):
        code = st.text_input("Registrierungscode", placeholder="z.B. 6F336234")
        submit = st.form_submit_button("🔓 Gerät aktivieren", use_container_width=True)
        
        if submit and code:
            success, message = activate_device_with_code(code.strip().upper(), betrieb_id)
            
            if success:
                st.success(f"✅ Gerät erfolgreich aktiviert: {message}")
                st.balloons()
                st.rerun()
                return True
            else:
                st.error(f"❌ {message}")
                return False
    
    return False
