"""
Daten-Hygiene-Modul für CrewBase
DSGVO-konforme Verwaltung von Aufbewahrungsfristen und Anonymisierung.

Gesetzliche Grundlagen:
    - § 147 AO: Lohnunterlagen 10 Jahre aufbewahren
    - § 257 HGB: Buchungsbelege 10 Jahre
    - § 17 MiLoG: Arbeitszeitdokumentation 2 Jahre
    - DSGVO Art. 17: Recht auf Löschung

Workflow:
    1. Mitarbeiter tritt aus → ausgetreten_am wird gesetzt
    2. Trigger berechnet loeschfrist_datum = ausgetreten_am + 10 Jahre
    3. Cron-Job (monatlich) prüft fällige Datensätze
    4. Admin erhält E-Mail-Warnung
    5. Admin bestätigt Anonymisierung in der App
    6. Personenbezogene Daten werden anonymisiert (nicht gelöscht)

Anonymisierung bedeutet:
    - Name → "Ehemaliger Mitarbeiter [ID]"
    - E-Mail → NULL
    - Telefon → NULL
    - Adresse → NULL
    - Stundenlohn → 0.0 (für Statistiken)
    - Zeiterfassungs-Daten bleiben erhalten (für Betriebsstatistiken)
"""

import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def pruefe_faellige_loeschfristen(betrieb_id: int = None) -> List[Dict[str, Any]]:
    """
    Prüft welche Mitarbeiter-Datensätze die Aufbewahrungsfrist überschritten haben.
    
    Args:
        betrieb_id: Optional – nur für diesen Betrieb prüfen
        
    Returns:
        List[Dict]: Fällige Datensätze mit Name, Austrittsdatum, Löschfrist
    """
    try:
        from utils.database import get_supabase_client
        supabase = get_supabase_client()
        
        heute = date.today().isoformat()
        
        query = supabase.table('mitarbeiter').select(
            'id, vorname, nachname, ausgetreten_am, loeschfrist_datum'
        ).not_.is_('loeschfrist_datum', 'null').lte('loeschfrist_datum', heute).eq('anonymisiert', False)
        
        if betrieb_id:
            query = query.eq('betrieb_id', betrieb_id)
        
        result = query.execute()
        
        faellige = []
        for ma in (result.data or []):
            faellige.append({
                'id': ma['id'],
                'name': f"{ma['vorname']} {ma['nachname']}",
                'ausgetreten_am': ma.get('ausgetreten_am', 'Unbekannt'),
                'loeschfrist': ma.get('loeschfrist_datum', 'Unbekannt')
            })
        
        logger.info(f"Daten-Hygiene: {len(faellige)} fällige Datensätze gefunden")
        return faellige
        
    except Exception as e:
        logger.error(f"Fehler bei Löschfrist-Prüfung: {e}")
        return []


def anonymisiere_mitarbeiter(
    mitarbeiter_id: int,
    admin_user_id: int,
    admin_name: str,
    betrieb_id: int = None
) -> bool:
    """
    Anonymisiert einen Mitarbeiter-Datensatz nach Ablauf der Aufbewahrungsfrist.
    
    Personenbezogene Daten werden ersetzt, Zeiterfassungs-Daten bleiben für
    Betriebsstatistiken erhalten (aber ohne Personenbezug).
    
    Args:
        mitarbeiter_id: ID des zu anonymisierenden Mitarbeiters
        admin_user_id: ID des Admins der die Anonymisierung durchführt
        admin_name: Name des Admins
        betrieb_id: ID des Betriebs
        
    Returns:
        bool: True bei Erfolg
    """
    try:
        from utils.database import get_supabase_client
        from utils.audit_log import log_aktion
        supabase = get_supabase_client()
        
        # Hole aktuellen Datensatz für Audit-Log
        ma_result = supabase.table('mitarbeiter').select(
            'vorname, nachname, email, telefon, adresse'
        ).eq('id', mitarbeiter_id).execute()
        
        if not ma_result.data:
            logger.error(f"Mitarbeiter {mitarbeiter_id} nicht gefunden")
            return False
        
        ma = ma_result.data[0]
        alter_wert = {
            'vorname': ma.get('vorname'),
            'nachname': ma.get('nachname'),
            'email': ma.get('email'),
            'telefon': ma.get('telefon'),
            'adresse': ma.get('adresse')
        }
        
        # Anonymisierung durchführen
        anonymisiert_daten = {
            'vorname': 'Ehemaliger',
            'nachname': f'Mitarbeiter [{mitarbeiter_id}]',
            'email': None,
            'telefon': None,
            'adresse': None,
            'stundenlohn_brutto': 0.0,
            'iban': None,
            'steuer_id': None,
            'sozialversicherungsnummer': None,
            'anonymisiert': True,
            'anonymisiert_am': datetime.now().isoformat()
        }
        
        supabase.table('mitarbeiter').update(anonymisiert_daten).eq('id', mitarbeiter_id).execute()
        
        # Audit-Log schreiben
        log_aktion(
            admin_user_id=admin_user_id,
            admin_name=admin_name,
            aktion='anonymisierung',
            tabelle='mitarbeiter',
            datensatz_id=mitarbeiter_id,
            mitarbeiter_id=mitarbeiter_id,
            mitarbeiter_name=f"{ma.get('vorname', '')} {ma.get('nachname', '')}",
            alter_wert=alter_wert,
            neuer_wert={'anonymisiert': True},
            begruendung=f'Automatische Anonymisierung nach Ablauf der gesetzlichen Aufbewahrungsfrist (§ 147 AO)',
            betrieb_id=betrieb_id
        )
        
        logger.info(f"Mitarbeiter {mitarbeiter_id} erfolgreich anonymisiert")
        return True
        
    except Exception as e:
        logger.error(f"Fehler bei Anonymisierung von Mitarbeiter {mitarbeiter_id}: {e}")
        return False


def setze_austrittsdatum(
    mitarbeiter_id: int,
    austrittsdatum: date,
    admin_user_id: int,
    admin_name: str,
    betrieb_id: int = None
) -> bool:
    """
    Setzt das Austrittsdatum eines Mitarbeiters und berechnet automatisch die Löschfrist.
    
    Args:
        mitarbeiter_id: ID des Mitarbeiters
        austrittsdatum: Datum des Austritts
        admin_user_id: ID des Admins
        admin_name: Name des Admins
        betrieb_id: ID des Betriebs
        
    Returns:
        bool: True bei Erfolg
    """
    try:
        from utils.database import get_supabase_client
        from utils.audit_log import log_aktion
        supabase = get_supabase_client()
        
        # Löschfrist = Austrittsdatum + 10 Jahre (§ 147 AO)
        from dateutil.relativedelta import relativedelta
        loeschfrist = austrittsdatum + relativedelta(years=10)
        
        supabase.table('mitarbeiter').update({
            'ausgetreten_am': austrittsdatum.isoformat(),
            'loeschfrist_datum': loeschfrist.isoformat()
        }).eq('id', mitarbeiter_id).execute()
        
        # Audit-Log
        log_aktion(
            admin_user_id=admin_user_id,
            admin_name=admin_name,
            aktion='austritt_gesetzt',
            tabelle='mitarbeiter',
            datensatz_id=mitarbeiter_id,
            mitarbeiter_id=mitarbeiter_id,
            alter_wert={'ausgetreten_am': None},
            neuer_wert={
                'ausgetreten_am': austrittsdatum.isoformat(),
                'loeschfrist_datum': loeschfrist.isoformat()
            },
            begruendung=f'Austrittsdatum gesetzt. Löschfrist: {loeschfrist.strftime("%d.%m.%Y")}',
            betrieb_id=betrieb_id
        )
        
        logger.info(f"Austrittsdatum für Mitarbeiter {mitarbeiter_id} gesetzt: {austrittsdatum}")
        return True
        
    except ImportError:
        # dateutil nicht verfügbar, manuelle Berechnung
        from datetime import timedelta
        loeschfrist = date(
            austrittsdatum.year + 10,
            austrittsdatum.month,
            austrittsdatum.day
        )
        from utils.database import get_supabase_client
        supabase = get_supabase_client()
        supabase.table('mitarbeiter').update({
            'ausgetreten_am': austrittsdatum.isoformat(),
            'loeschfrist_datum': loeschfrist.isoformat()
        }).eq('id', mitarbeiter_id).execute()
        return True
        
    except Exception as e:
        logger.error(f"Fehler beim Setzen des Austrittsdatums: {e}")
        return False


def fuehre_monatliche_hygiene_pruefung_durch(betrieb_id: int, admin_email: str) -> Dict[str, Any]:
    """
    Führt die monatliche Daten-Hygiene-Prüfung durch und sendet ggf. E-Mail-Warnung.
    
    Wird als Cron-Job monatlich aufgerufen.
    
    Args:
        betrieb_id: ID des Betriebs
        admin_email: E-Mail des Admins für Warnungen
        
    Returns:
        Dict: {'faellige_datensaetze': int, 'email_gesendet': bool}
    """
    faellige = pruefe_faellige_loeschfristen(betrieb_id)
    
    ergebnis = {
        'faellige_datensaetze': len(faellige),
        'email_gesendet': False,
        'datum': date.today().isoformat()
    }
    
    if faellige:
        try:
            from utils.email_service import send_datenhygiene_warnung_email
            ergebnis['email_gesendet'] = send_datenhygiene_warnung_email(
                admin_email=admin_email,
                faellige_mitarbeiter=faellige
            )
        except Exception as e:
            logger.error(f"Fehler beim Senden der Hygiene-Warnung: {e}")
    
    logger.info(f"Monatliche Hygiene-Prüfung: {len(faellige)} fällige Datensätze, E-Mail: {ergebnis['email_gesendet']}")
    return ergebnis
