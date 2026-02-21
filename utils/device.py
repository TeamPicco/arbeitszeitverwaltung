"""
Geräte-Erkennung und mobile Einschränkungen
"""

import streamlit as st
from typing import Dict, Any


def is_mobile_device() -> bool:
    """
    Prüft ob das Gerät ein mobiles Gerät ist
    
    Returns:
        bool: True wenn mobiles Gerät, False sonst
    """
    try:
        # Prüfe User Agent über JavaScript
        user_agent = st.query_params.get('mobile', [''])[0] if hasattr(st, 'query_params') else ''
        
        # Fallback: Prüfe Session State
        if 'is_mobile' in st.session_state:
            return st.session_state.is_mobile
        
        # Standard: False (Desktop)
        return False
    except:
        return False


def detect_device_type() -> str:
    """
    Erkennt den Gerätetyp
    
    Returns:
        str: 'mobile', 'tablet' oder 'desktop'
    """
    if is_mobile_device():
        return 'mobile'
    return 'desktop'


def inject_device_detection():
    """
    Fügt JavaScript zur Geräte-Erkennung ein
    """
    st.markdown("""
    <script>
        // Geräte-Erkennung
        function detectDevice() {
            const userAgent = navigator.userAgent.toLowerCase();
            const isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
            const isTablet = /ipad|android(?!.*mobile)/i.test(userAgent);
            
            // Speichere in Session Storage
            if (isMobile || isTablet) {
                sessionStorage.setItem('deviceType', isMobile ? 'mobile' : 'tablet');
                sessionStorage.setItem('isMobile', 'true');
            } else {
                sessionStorage.setItem('deviceType', 'desktop');
                sessionStorage.setItem('isMobile', 'false');
            }
            
            // Sende an Streamlit
            const event = new CustomEvent('deviceDetected', {
                detail: {
                    type: sessionStorage.getItem('deviceType'),
                    isMobile: sessionStorage.getItem('isMobile') === 'true'
                }
            });
            window.dispatchEvent(event);
        }
        
        // Führe bei Seitenload aus
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', detectDevice);
        } else {
            detectDevice();
        }
    </script>
    """, unsafe_allow_html=True)


def get_device_restrictions(is_mobile: bool, mitarbeiter: Dict[str, Any] = None) -> Dict[str, bool]:
    """
    Gibt Funktions-Einschränkungen basierend auf Gerät zurück
    
    Args:
        is_mobile: Ob es ein mobiles Gerät ist
        mitarbeiter: Mitarbeiter-Daten (optional)
    
    Returns:
        Dict mit Berechtigungen
    """
    if not is_mobile:
        # Desktop: Alle Funktionen erlaubt
        return {
            'zeiterfassung': True,
            'stammdaten_bearbeiten': True,
            'dienstplan_einsehen': True,
            'urlaub_beantragen': True,
            'plauderecke': True,
            'dokumente': True
        }
    
    # Mobile: Eingeschränkte Funktionen
    mobile_zeiterfassung = False
    if mitarbeiter:
        mobile_zeiterfassung = mitarbeiter.get('mobile_zeiterfassung', False)
    
    return {
        'zeiterfassung': mobile_zeiterfassung,  # Nur wenn erlaubt
        'stammdaten_bearbeiten': False,  # Nur am Desktop
        'dienstplan_einsehen': True,
        'urlaub_beantragen': True,
        'plauderecke': True,
        'dokumente': True
    }


def show_mobile_restriction_message(feature: str):
    """
    Zeigt Hinweis bei eingeschränkter Funktion
    
    Args:
        feature: Name der eingeschränkten Funktion
    """
    messages = {
        'zeiterfassung': """
        ⚠️ **Zeiterfassung nur am Terminal**
        
        Die Zeiterfassung ist nur am registrierten Terminal im Restaurant möglich.
        Bitte stempeln Sie dort ein und aus.
        """,
        'stammdaten_bearbeiten': """
        ⚠️ **Stammdaten-Bearbeitung nur am Desktop**
        
        Aus Sicherheitsgründen können Stammdaten nur am Desktop-Computer bearbeitet werden.
        Bitte melden Sie sich am Computer an.
        """
    }
    
    message = messages.get(feature, f"⚠️ Diese Funktion ist auf mobilen Geräten nicht verfügbar.")
    st.warning(message)


def is_mastergeraet() -> bool:
    """
    Prüft ob das aktuelle Gerät ein registriertes Mastergerät ist
    
    Returns:
        bool: True wenn Mastergerät, False sonst
    """
    # Prüfe Session State
    if 'is_mastergeraet' in st.session_state:
        return st.session_state.is_mastergeraet
    
    # Prüfe Cookie/LocalStorage über JavaScript
    # TODO: Implementierung mit Geräte-Code-Prüfung
    
    return False


def register_mastergeraet(geraete_code: str) -> bool:
    """
    Registriert das aktuelle Gerät als Mastergerät
    
    Args:
        geraete_code: Eindeutiger Geräte-Code
    
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    from utils.database import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        
        # Prüfe ob Code existiert und aktiv ist
        result = supabase.table('mastergeraete').select('*').eq('geraete_code', geraete_code).eq('aktiv', True).execute()
        
        if result.data and len(result.data) > 0:
            # Speichere in Session State
            st.session_state.is_mastergeraet = True
            st.session_state.mastergeraet_id = result.data[0]['id']
            st.session_state.mastergeraet_name = result.data[0]['name']
            
            # Aktualisiere letzten Zugriff
            supabase.table('mastergeraete').update({
                'letzter_zugriff': 'now()'
            }).eq('id', result.data[0]['id']).execute()
            
            return True
        else:
            return False
    except Exception as e:
        print(f"Fehler beim Registrieren des Mastergeräts: {e}")
        return False
