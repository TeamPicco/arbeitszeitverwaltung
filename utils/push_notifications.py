"""
Push-Benachrichtigungen
Sendet Browser-Push-Benachrichtigungen an Benutzer
"""

import streamlit as st
from datetime import datetime
from typing import Optional, List, Dict, Any

from utils.database import get_supabase_client
from utils.session import get_current_betrieb_id


def save_notification(
    user_id: str,
    titel: str,
    nachricht: str,
    typ: str = 'info',
    link: Optional[str] = None
) -> bool:
    """
    Speichert eine Benachrichtigung in der Datenbank
    
    Args:
        user_id: Empfänger User-ID
        titel: Titel der Benachrichtigung
        nachricht: Nachrichtentext
        typ: Typ ('info', 'success', 'warning', 'error')
        link: Optionaler Link
        
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        betrieb_id = get_current_betrieb_id()
        if not betrieb_id:
            return False
        
        supabase = get_supabase_client()
        
        notification_data = {
            'betrieb_id': betrieb_id,
            'user_id': user_id,
            'titel': titel,
            'nachricht': nachricht,
            'typ': typ,
            'link': link,
            'gelesen': False,
            'erstellt_am': datetime.now().isoformat()
        }
        
        supabase.table('benachrichtigungen').insert(notification_data).execute()
        
        # Hier würde die eigentliche Push-Benachrichtigung gesendet werden
        # Das erfordert Service Worker und Web Push API
        # Für jetzt speichern wir nur in der Datenbank
        
        return True
        
    except Exception as e:
        st.error(f"Fehler beim Speichern der Benachrichtigung: {str(e)}")
        return False


def get_unread_notifications(user_id: str) -> List[Dict[str, Any]]:
    """
    Holt alle ungelesenen Benachrichtigungen eines Benutzers
    
    Args:
        user_id: User-ID
        
    Returns:
        List[Dict]: Liste der ungelesenen Benachrichtigungen
    """
    try:
        betrieb_id = get_current_betrieb_id()
        if not betrieb_id:
            return []
        
        supabase = get_supabase_client()
        
        response = supabase.table('benachrichtigungen')\
            .select('*')\
            .eq('betrieb_id', betrieb_id)\
            .eq('user_id', user_id)\
            .eq('gelesen', False)\
            .order('erstellt_am', desc=True)\
            .execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Benachrichtigungen: {str(e)}")
        return []


def mark_notification_as_read(notification_id: str) -> bool:
    """
    Markiert eine Benachrichtigung als gelesen
    
    Args:
        notification_id: Benachrichtigungs-ID
        
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        supabase = get_supabase_client()
        
        supabase.table('benachrichtigungen')\
            .update({'gelesen': True, 'gelesen_am': datetime.now().isoformat()})\
            .eq('id', notification_id)\
            .execute()
        
        return True
        
    except Exception as e:
        st.error(f"Fehler beim Markieren der Benachrichtigung: {str(e)}")
        return False


def mark_all_notifications_as_read(user_id: str) -> bool:
    """
    Markiert alle Benachrichtigungen eines Benutzers als gelesen
    
    Args:
        user_id: User-ID
        
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        betrieb_id = get_current_betrieb_id()
        if not betrieb_id:
            return False
        
        supabase = get_supabase_client()
        
        supabase.table('benachrichtigungen')\
            .update({'gelesen': True, 'gelesen_am': datetime.now().isoformat()})\
            .eq('betrieb_id', betrieb_id)\
            .eq('user_id', user_id)\
            .eq('gelesen', False)\
            .execute()
        
        return True
        
    except Exception as e:
        st.error(f"Fehler beim Markieren aller Benachrichtigungen: {str(e)}")
        return False


def send_urlaubsantrag_notification(admin_user_id: str, mitarbeiter_name: str, von: str, bis: str) -> bool:
    """
    Sendet Benachrichtigung über neuen Urlaubsantrag an Admin
    
    Args:
        admin_user_id: Admin User-ID
        mitarbeiter_name: Name des Mitarbeiters
        von: Start-Datum
        bis: End-Datum
        
    Returns:
        bool: True wenn erfolgreich
    """
    return save_notification(
        user_id=admin_user_id,
        titel="Neuer Urlaubsantrag",
        nachricht=f"{mitarbeiter_name} hat einen Urlaubsantrag gestellt: {von} bis {bis}",
        typ='info',
        link='/admin_dashboard?tab=urlaubsgenehmigung'
    )


def send_urlaubsgenehmigung_notification(mitarbeiter_user_id: str, status: str, von: str, bis: str) -> bool:
    """
    Sendet Benachrichtigung über Urlaubsgenehmigung/-ablehnung an Mitarbeiter
    
    Args:
        mitarbeiter_user_id: Mitarbeiter User-ID
        status: 'genehmigt' oder 'abgelehnt'
        von: Start-Datum
        bis: End-Datum
        
    Returns:
        bool: True wenn erfolgreich
    """
    if status == 'genehmigt':
        titel = "Urlaub genehmigt ✅"
        nachricht = f"Ihr Urlaubsantrag vom {von} bis {bis} wurde genehmigt!"
        typ = 'success'
    else:
        titel = "Urlaub abgelehnt ❌"
        nachricht = f"Ihr Urlaubsantrag vom {von} bis {bis} wurde leider abgelehnt."
        typ = 'warning'
    
    return save_notification(
        user_id=mitarbeiter_user_id,
        titel=titel,
        nachricht=nachricht,
        typ=typ
    )


def send_dienstplan_notification(mitarbeiter_user_id: str, monat: str) -> bool:
    """
    Sendet Benachrichtigung über neuen/aktualisierten Dienstplan
    
    Args:
        mitarbeiter_user_id: Mitarbeiter User-ID
        monat: Monat des Dienstplans
        
    Returns:
        bool: True wenn erfolgreich
    """
    return save_notification(
        user_id=mitarbeiter_user_id,
        titel="Neuer Dienstplan verfügbar 📅",
        nachricht=f"Der Dienstplan für {monat} ist jetzt verfügbar!",
        typ='info',
        link='/mitarbeiter_dashboard?tab=dienstplan'
    )


def send_stammdaten_aenderung_notification(admin_user_id: str, mitarbeiter_name: str, aenderung: str) -> bool:
    """
    Sendet Benachrichtigung über Stammdaten-Änderung an Admin
    
    Args:
        admin_user_id: Admin User-ID
        mitarbeiter_name: Name des Mitarbeiters
        aenderung: Beschreibung der Änderung
        
    Returns:
        bool: True wenn erfolgreich
    """
    return save_notification(
        user_id=admin_user_id,
        titel="Stammdaten-Änderung",
        nachricht=f"{mitarbeiter_name} hat Stammdaten geändert: {aenderung}",
        typ='info',
        link='/admin_dashboard?tab=mitarbeiterverwaltung'
    )


def send_chat_notification(user_id: str, absender_name: str, nachricht_preview: str) -> bool:
    """
    Sendet Benachrichtigung über neue Chat-Nachricht
    
    Args:
        user_id: Empfänger User-ID
        absender_name: Name des Absenders
        nachricht_preview: Vorschau der Nachricht (erste 50 Zeichen)
        
    Returns:
        bool: True wenn erfolgreich
    """
    preview = nachricht_preview[:50] + "..." if len(nachricht_preview) > 50 else nachricht_preview
    
    return save_notification(
        user_id=user_id,
        titel=f"Neue Nachricht von {absender_name} 💬",
        nachricht=preview,
        typ='info',
        link='/dashboard?tab=plauderecke'
    )


def show_notifications_widget(user_id: str):
    """
    Zeigt Benachrichtigungs-Widget in der Sidebar
    
    Args:
        user_id: User-ID
    """
    notifications = get_unread_notifications(user_id)
    
    if notifications:
        st.sidebar.markdown(f"### 🔔 Benachrichtigungen ({len(notifications)})")
        
        for notif in notifications[:5]:  # Zeige max. 5
            typ_emoji = {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌'
            }.get(notif['typ'], 'ℹ️')
            
            with st.sidebar.expander(f"{typ_emoji} {notif['titel']}", expanded=False):
                st.write(notif['nachricht'])
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✓ Gelesen", key=f"read_{notif['id']}", use_container_width=True):
                        mark_notification_as_read(notif['id'])
                        st.rerun()
                
                if notif.get('link'):
                    with col2:
                        st.link_button("→ Öffnen", notif['link'], use_container_width=True)
        
        if len(notifications) > 5:
            st.sidebar.info(f"+ {len(notifications) - 5} weitere Benachrichtigungen")
        
        if st.sidebar.button("Alle als gelesen markieren", use_container_width=True):
            mark_all_notifications_as_read(user_id)
            st.rerun()
