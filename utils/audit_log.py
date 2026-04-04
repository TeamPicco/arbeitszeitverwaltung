"""
Audit-Log für CrewBase
Revisionssichere Protokollierung aller Admin-Aktionen.

Die audit_log-Tabelle ist unveränderlich (nur INSERT-Rechte).
Jede manuelle Zeitkorrektur, Lohnänderung oder Datenlöschung
durch Admins wird hier mit Zeitstempel, Admin-ID und Begründung
gespeichert.

Verwendung:
    from utils.audit_log import log_zeitkorrektur, log_aktion, get_audit_log

    # Zeitkorrektur loggen:
    log_zeitkorrektur(
        admin_user_id=1,
        admin_name="Max Mustermann",
        mitarbeiter_id=5,
        mitarbeiter_name="Anna Schmidt",
        zeiterfassung_id=42,
        alter_wert={"start_zeit": "08:00", "ende_zeit": "16:00"},
        neuer_wert={"start_zeit": "09:00", "ende_zeit": "17:00"},
        begruendung="Vergessener Logout korrigiert",
        betrieb_id=1
    )
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def log_zeitkorrektur(
    admin_user_id: int,
    admin_name: str,
    mitarbeiter_id: int,
    mitarbeiter_name: str,
    zeiterfassung_id: int,
    alter_wert: Dict[str, Any],
    neuer_wert: Dict[str, Any],
    begruendung: str,
    betrieb_id: int = None
) -> bool:
    """
    Loggt eine manuelle Zeitkorrektur durch einen Admin.
    
    Args:
        admin_user_id: ID des Admins der die Korrektur durchführt
        admin_name: Name des Admins
        mitarbeiter_id: ID des betroffenen Mitarbeiters
        mitarbeiter_name: Name des betroffenen Mitarbeiters
        zeiterfassung_id: ID des korrigierten Zeiterfassungs-Datensatzes
        alter_wert: Zustand vor der Korrektur (dict)
        neuer_wert: Zustand nach der Korrektur (dict)
        begruendung: Pflichtbegründung für die Korrektur
        betrieb_id: ID des Betriebs
        
    Returns:
        bool: True bei Erfolg
    """
    return _log_eintrag(
        admin_user_id=admin_user_id,
        admin_name=admin_name,
        aktion="zeitkorrektur",
        tabelle="zeiterfassung",
        datensatz_id=zeiterfassung_id,
        mitarbeiter_id=mitarbeiter_id,
        mitarbeiter_name=mitarbeiter_name,
        alter_wert=alter_wert,
        neuer_wert=neuer_wert,
        begruendung=begruendung,
        betrieb_id=betrieb_id
    )


def log_zeitloeschung(
    admin_user_id: int,
    admin_name: str,
    mitarbeiter_id: int,
    mitarbeiter_name: str,
    zeiterfassung_id: int,
    alter_wert: Dict[str, Any],
    begruendung: str,
    betrieb_id: int = None
) -> bool:
    """Loggt die Löschung einer Zeiterfassung durch einen Admin."""
    return _log_eintrag(
        admin_user_id=admin_user_id,
        admin_name=admin_name,
        aktion="zeitloeschung",
        tabelle="zeiterfassung",
        datensatz_id=zeiterfassung_id,
        mitarbeiter_id=mitarbeiter_id,
        mitarbeiter_name=mitarbeiter_name,
        alter_wert=alter_wert,
        neuer_wert=None,
        begruendung=begruendung,
        betrieb_id=betrieb_id
    )


def log_stammdaten_aenderung(
    admin_user_id: int,
    admin_name: str,
    mitarbeiter_id: int,
    mitarbeiter_name: str,
    alter_wert: Dict[str, Any],
    neuer_wert: Dict[str, Any],
    begruendung: str,
    betrieb_id: int = None
) -> bool:
    """Loggt eine Stammdaten-Änderung (z.B. Lohnänderung) durch einen Admin."""
    return _log_eintrag(
        admin_user_id=admin_user_id,
        admin_name=admin_name,
        aktion="stammdaten_aenderung",
        tabelle="mitarbeiter",
        datensatz_id=mitarbeiter_id,
        mitarbeiter_id=mitarbeiter_id,
        mitarbeiter_name=mitarbeiter_name,
        alter_wert=alter_wert,
        neuer_wert=neuer_wert,
        begruendung=begruendung,
        betrieb_id=betrieb_id
    )


def log_aktion(
    admin_user_id: int,
    admin_name: str,
    aktion: str,
    tabelle: str,
    datensatz_id: int,
    begruendung: str,
    mitarbeiter_id: int = None,
    mitarbeiter_name: str = None,
    alter_wert: Dict[str, Any] = None,
    neuer_wert: Dict[str, Any] = None,
    betrieb_id: int = None
) -> bool:
    """
    Allgemeine Funktion zum Loggen beliebiger Admin-Aktionen.
    """
    return _log_eintrag(
        admin_user_id=admin_user_id,
        admin_name=admin_name,
        aktion=aktion,
        tabelle=tabelle,
        datensatz_id=datensatz_id,
        mitarbeiter_id=mitarbeiter_id,
        mitarbeiter_name=mitarbeiter_name,
        alter_wert=alter_wert,
        neuer_wert=neuer_wert,
        begruendung=begruendung,
        betrieb_id=betrieb_id
    )


def _log_eintrag(
    admin_user_id: int,
    admin_name: str,
    aktion: str,
    tabelle: str,
    datensatz_id: int,
    begruendung: str,
    mitarbeiter_id: int = None,
    mitarbeiter_name: str = None,
    alter_wert: Dict[str, Any] = None,
    neuer_wert: Dict[str, Any] = None,
    betrieb_id: int = None
) -> bool:
    """Interne Funktion: Schreibt einen Eintrag in audit_logs (Fallback audit_log)."""
    try:
        from utils.database import get_supabase_client
        supabase = get_supabase_client()
        
        eintrag = {
            'admin_user_id': admin_user_id,
            'admin_name': admin_name,
            'aktion': aktion,
            'tabelle': tabelle,
            'datensatz_id': datensatz_id,
            'begruendung': begruendung,
        }
        
        if mitarbeiter_id:
            eintrag['mitarbeiter_id'] = mitarbeiter_id
        if mitarbeiter_name:
            eintrag['mitarbeiter_name'] = mitarbeiter_name
        if alter_wert:
            eintrag['alter_wert'] = alter_wert
        if neuer_wert:
            eintrag['neuer_wert'] = neuer_wert
        if betrieb_id:
            eintrag['betrieb_id'] = betrieb_id
        
        try:
            supabase.table('audit_logs').insert(eintrag).execute()
        except Exception:
            # Legacy-Fallback für ältere Instanzen
            supabase.table('audit_log').insert(eintrag).execute()
        logger.info(f"Audit-Log: {aktion} von Admin {admin_name} für {mitarbeiter_name or 'unbekannt'}")
        return True
        
    except Exception as e:
        logger.error(f"Fehler beim Schreiben des Audit-Logs: {e}")
        # Audit-Log-Fehler darf die Hauptfunktion nicht blockieren
        return False


def get_audit_log(
    betrieb_id: int,
    mitarbeiter_id: int = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Liest den Audit-Log für einen Betrieb.
    
    Args:
        betrieb_id: ID des Betriebs
        mitarbeiter_id: Optional: Nur Einträge für diesen Mitarbeiter
        limit: Maximale Anzahl Einträge (Standard: 100)
        
    Returns:
        List[Dict]: Liste der Audit-Log-Einträge (neueste zuerst)
    """
    try:
        from utils.database import get_supabase_client
        supabase = get_supabase_client()
        
        try:
            query = supabase.table('audit_logs').select('*').eq('betrieb_id', betrieb_id)
        except Exception:
            query = supabase.table('audit_log').select('*').eq('betrieb_id', betrieb_id)
        
        if mitarbeiter_id:
            query = query.eq('mitarbeiter_id', mitarbeiter_id)
        
        result = query.order('erstellt_am', desc=True).limit(limit).execute()
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"Fehler beim Lesen des Audit-Logs: {e}")
        return []
