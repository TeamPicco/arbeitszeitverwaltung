"""
Benachrichtigungssystem für Admin und Mitarbeiter
"""

from utils.database import get_supabase_client
from datetime import datetime


def create_benachrichtigung(mitarbeiter_id: int, typ: str, nachricht: str):
    """Erstellt eine neue Benachrichtigung für den Admin"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('benachrichtigungen').insert({
            'mitarbeiter_id': mitarbeiter_id,
            'typ': typ,
            'nachricht': nachricht,
            'gelesen': False
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Fehler beim Erstellen der Benachrichtigung: {e}")
        return None


def get_ungelesene_benachrichtigungen():
    """Holt alle ungelesenen Benachrichtigungen für den Admin"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('benachrichtigungen').select(
            '*, mitarbeiter(vorname, nachname, personalnummer)'
        ).eq('gelesen', False).order('erstellt_am', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Fehler beim Laden der Benachrichtigungen: {e}")
        return []


def markiere_benachrichtigung_gelesen(benachrichtigung_id: int):
    """Markiert eine Benachrichtigung als gelesen"""
    try:
        supabase = get_supabase_client()
        supabase.table('benachrichtigungen').update({
            'gelesen': True
        }).eq('id', benachrichtigung_id).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Markieren der Benachrichtigung: {e}")
        return False


def create_aenderungsanfrage(mitarbeiter_id: int, feld: str, alter_wert: str, neuer_wert: str, grund: str = None):
    """Erstellt eine Änderungsanfrage (z.B. für Nachname)"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('aenderungsanfragen').insert({
            'mitarbeiter_id': mitarbeiter_id,
            'feld': feld,
            'alter_wert': alter_wert,
            'neuer_wert': neuer_wert,
            'grund': grund,
            'status': 'pending'
        }).execute()
        
        # Erstelle Benachrichtigung für Admin
        if result.data:
            create_benachrichtigung(
                mitarbeiter_id,
                'aenderungsanfrage',
                f"Änderungsanfrage für {feld}: {alter_wert} → {neuer_wert}"
            )
        
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Fehler beim Erstellen der Änderungsanfrage: {e}")
        return None


def get_pending_aenderungsanfragen():
    """Holt alle offenen Änderungsanfragen"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('aenderungsanfragen').select(
            '*, mitarbeiter(vorname, nachname, personalnummer)'
        ).eq('status', 'pending').order('erstellt_am', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Fehler beim Laden der Änderungsanfragen: {e}")
        return []


def approve_aenderungsanfrage(anfrage_id: int, admin_user_id: int):
    """Genehmigt eine Änderungsanfrage"""
    try:
        supabase = get_supabase_client()
        
        # Hole Anfrage-Details
        anfrage = supabase.table('aenderungsanfragen').select('*').eq('id', anfrage_id).single().execute()
        
        if not anfrage.data:
            return False
        
        # Aktualisiere Mitarbeiter-Daten
        from utils.database import update_mitarbeiter
        update_data = {anfrage.data['feld']: anfrage.data['neuer_wert']}
        update_mitarbeiter(anfrage.data['mitarbeiter_id'], update_data)
        
        # Markiere Anfrage als genehmigt
        supabase.table('aenderungsanfragen').update({
            'status': 'approved',
            'bearbeitet_am': datetime.now().isoformat(),
            'bearbeitet_von': admin_user_id
        }).eq('id', anfrage_id).execute()
        
        return True
    except Exception as e:
        print(f"Fehler beim Genehmigen der Änderungsanfrage: {e}")
        return False


def reject_aenderungsanfrage(anfrage_id: int, admin_user_id: int):
    """Lehnt eine Änderungsanfrage ab"""
    try:
        supabase = get_supabase_client()
        supabase.table('aenderungsanfragen').update({
            'status': 'rejected',
            'bearbeitet_am': datetime.now().isoformat(),
            'bearbeitet_von': admin_user_id
        }).eq('id', anfrage_id).execute()
        return True
    except Exception as e:
        print(f"Fehler beim Ablehnen der Änderungsanfrage: {e}")
        return False


def update_mitarbeiter_stammdaten(mitarbeiter_id: int, feld: str, neuer_wert: str, alter_wert: str = None):
    """
    Aktualisiert Mitarbeiter-Stammdaten und erstellt Benachrichtigung
    Für sensible Felder wie 'nachname' wird eine Änderungsanfrage erstellt
    """
    from utils.database import update_mitarbeiter
    
    # Felder die eine Genehmigung benötigen
    genehmigungspflichtige_felder = ['nachname']
    
    if feld in genehmigungspflichtige_felder:
        # Erstelle Änderungsanfrage
        return create_aenderungsanfrage(mitarbeiter_id, feld, alter_wert, neuer_wert)
    else:
        # Direkte Aktualisierung
        update_data = {feld: neuer_wert}
        success = update_mitarbeiter(mitarbeiter_id, update_data)
        
        if success:
            # Erstelle Benachrichtigung für Admin
            create_benachrichtigung(
                mitarbeiter_id,
                'stammdaten_aenderung',
                f"Stammdaten geändert: {feld} → {neuer_wert}"
            )
        
        return success
