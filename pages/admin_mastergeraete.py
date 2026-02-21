"""
Mastergeräte-Verwaltung
Admin kann Geräte als Mastergeräte für Zeiterfassung registrieren
"""

import streamlit as st
from datetime import datetime
import uuid

from utils.database import get_supabase_client
from utils.session import get_current_betrieb_id


def show_mastergeraete():
    """Zeigt die Mastergeräte-Verwaltung an"""
    
    st.subheader("🖥️ Mastergeräte-Verwaltung")
    
    st.info("""
    **Mastergeräte** sind registrierte Terminals (z.B. am Eingang des Restaurants), 
    an denen Mitarbeiter ein- und ausstempeln können. Nur an Mastergeräten ist die 
    Zeiterfassung für Mitarbeiter ohne mobile Berechtigung möglich.
    """)
    
    # Lade Mastergeräte
    betrieb_id = get_current_betrieb_id()
    if not betrieb_id:
        st.error("Keine Betrieb-ID gefunden.")
        return
    
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('mastergeraete').select('*').eq('betrieb_id', betrieb_id).order('erstellt_am', desc=True).execute()
        mastergeraete = response.data if response.data else []
        
        # Statistik
        aktive_geraete = len([g for g in mastergeraete if g.get('aktiv', True)])
        st.metric("Aktive Mastergeräte", aktive_geraete)
        
        st.markdown("---")
        
        # Neues Mastergerät registrieren
        with st.expander("➕ Neues Mastergerät registrieren", expanded=False):
            with st.form("new_mastergeraet_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    geraet_name = st.text_input(
                        "Gerätename*",
                        placeholder="z.B. Terminal Eingang, Kasse 1, etc.",
                        help="Eindeutiger Name für das Gerät"
                    )
                
                with col2:
                    standort = st.text_input(
                        "Standort",
                        placeholder="z.B. Haupteingang, Küche, etc.",
                        help="Wo befindet sich das Gerät?"
                    )
                
                beschreibung = st.text_area(
                    "Beschreibung",
                    placeholder="Weitere Informationen zum Gerät..."
                )
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if st.form_submit_button("💾 Registrieren", use_container_width=True):
                        if not geraet_name:
                            st.error("⚠️ Bitte geben Sie einen Gerätenamen ein.")
                        else:
                            # Generiere eindeutige Geräte-ID und Registrierungscode
                            geraet_id = str(uuid.uuid4())
                            registrierungscode = str(uuid.uuid4())[:8].upper()
                            
                            # Speichere Mastergerät
                            new_geraet = {
                                'betrieb_id': betrieb_id,
                                'geraet_id': geraet_id,
                                'name': geraet_name,
                                'standort': standort,
                                'beschreibung': beschreibung,
                                'registrierungscode': registrierungscode,
                                'aktiv': True,
                                'erstellt_am': datetime.now().isoformat()
                            }
                            
                            supabase.table('mastergeraete').insert(new_geraet).execute()
                            
                            st.success(f"✅ Mastergerät '{geraet_name}' erfolgreich registriert!")
                            st.info(f"🔑 Registrierungscode: **{registrierungscode}**")
                            st.rerun()
        
        st.markdown("---")
        
        # Liste der Mastergeräte
        if not mastergeraete:
            st.info("ℹ️ Noch keine Mastergeräte registriert.")
            return
        
        st.subheader("Registrierte Mastergeräte")
        
        for geraet in mastergeraete:
            with st.expander(
                f"{'🟢' if geraet.get('aktiv', True) else '🔴'} {geraet['name']} - {geraet.get('standort', 'Kein Standort')}",
                expanded=False
            ):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Gerätename:** {geraet['name']}")
                    st.write(f"**Standort:** {geraet.get('standort', 'Nicht angegeben')}")
                    st.write(f"**Status:** {'✅ Aktiv' if geraet.get('aktiv', True) else '❌ Deaktiviert'}")
                    
                    if geraet.get('beschreibung'):
                        st.write(f"**Beschreibung:** {geraet['beschreibung']}")
                
                with col2:
                    st.write(f"**Geräte-ID:** `{geraet['geraet_id'][:8]}...`")
                    st.write(f"**Registrierungscode:** `{geraet['registrierungscode']}`")
                    
                    erstellt_am = datetime.fromisoformat(geraet['erstellt_am']).strftime('%d.%m.%Y %H:%M')
                    st.write(f"**Registriert am:** {erstellt_am}")
                    
                    if geraet.get('letzter_zugriff'):
                        letzter_zugriff = datetime.fromisoformat(geraet['letzter_zugriff']).strftime('%d.%m.%Y %H:%M')
                        st.write(f"**Letzter Zugriff:** {letzter_zugriff}")
                
                st.markdown("---")
                
                # Aktionen
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if geraet.get('aktiv', True):
                        if st.button(f"⏸️ Deaktivieren", key=f"deactivate_{geraet['id']}", use_container_width=True):
                            supabase.table('mastergeraete').update({'aktiv': False}).eq('id', geraet['id']).execute()
                            st.success("Gerät deaktiviert!")
                            st.rerun()
                    else:
                        if st.button(f"▶️ Aktivieren", key=f"activate_{geraet['id']}", use_container_width=True):
                            supabase.table('mastergeraete').update({'aktiv': True}).eq('id', geraet['id']).execute()
                            st.success("Gerät aktiviert!")
                            st.rerun()
                
                with col2:
                    if st.button(f"🔄 Code erneuern", key=f"renew_{geraet['id']}", use_container_width=True):
                        neuer_code = str(uuid.uuid4())[:8].upper()
                        supabase.table('mastergeraete').update({'registrierungscode': neuer_code}).eq('id', geraet['id']).execute()
                        st.success(f"Neuer Code: **{neuer_code}**")
                        st.rerun()
                
                with col3:
                    if st.button(f"🗑️ Löschen", key=f"delete_{geraet['id']}", use_container_width=True):
                        if st.session_state.get(f'confirm_delete_geraet_{geraet["id"]}', False):
                            supabase.table('mastergeraete').delete().eq('id', geraet['id']).execute()
                            st.success("Gerät gelöscht!")
                            st.rerun()
                        else:
                            st.session_state[f'confirm_delete_geraet_{geraet["id"]}'] = True
                            st.warning("⚠️ Nochmal klicken zum Bestätigen!")
        
        st.markdown("---")
        
        # Anleitung
        with st.expander("ℹ️ Wie funktioniert die Mastergeräte-Registrierung?"):
            st.markdown("""
            ### Mastergerät einrichten
            
            1. **Registrieren Sie ein neues Mastergerät** mit einem eindeutigen Namen
            2. **Notieren Sie den Registrierungscode** - dieser wird nur einmal angezeigt
            3. **Öffnen Sie CrewBase auf dem Terminal-Gerät** (z.B. Tablet am Eingang)
            4. **Geben Sie den Registrierungscode ein** wenn Sie dazu aufgefordert werden
            5. **Das Gerät ist jetzt als Mastergerät registriert**
            
            ### Zeiterfassung am Mastergerät
            
            - Mitarbeiter ohne mobile Berechtigung können **nur** an Mastergeräten stempeln
            - Mitarbeiter mit mobiler Berechtigung können **überall** stempeln
            - Das System erkennt automatisch, ob ein Gerät ein Mastergerät ist
            
            ### Sicherheit
            
            - Jedes Gerät hat eine eindeutige Geräte-ID
            - Der Registrierungscode kann jederzeit erneuert werden
            - Geräte können deaktiviert werden ohne sie zu löschen
            """)
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Mastergeräte: {str(e)}")
