"""
Mastergeräte-Verwaltung
Admin kann Geräte als Mastergeräte für Zeiterfassung registrieren
Aktivierung per QR-Code oder manuellem Registrierungscode
"""

import streamlit as st
from datetime import datetime
import uuid
import os

from utils.database import get_supabase_client
from utils.session import get_current_betrieb_id
from utils.qr_code import generiere_aktivierungs_qr, zeige_qr_code_html


def show_mastergeraete():
    """Zeigt die Mastergeräte-Verwaltung an"""
    
    st.subheader("Mastergeräte-Verwaltung")
    
    st.info("""
    **Mastergeräte** sind registrierte Terminals (z.B. am Eingang des Restaurants), 
    an denen Mitarbeiter ein- und ausstempeln können. Nur an Mastergeräten ist die 
    Zeiterfassung für Mitarbeiter ohne mobile Berechtigung möglich.
    
    **Aktivierung:** Einfach den QR-Code mit dem Gerät scannen oder den Registrierungscode manuell eingeben.
    """)
    
    # Lade Mastergeräte
    betrieb_id = get_current_betrieb_id()
    if not betrieb_id:
        st.error("Keine Betrieb-ID gefunden.")
        return
    
    # App-URL aus Umgebungsvariable oder Standard
    app_url = os.getenv('APP_URL', 'https://arbeitszeitverwaltung.onrender.com')
    
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('mastergeraete').select('*').eq(
            'betrieb_id', betrieb_id
        ).order('erstellt_am', desc=True).execute()
        mastergeraete = response.data if response.data else []
        
        # Statistik
        aktive_geraete = len([g for g in mastergeraete if g.get('aktiv', True)])
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Aktive Mastergeräte", aktive_geraete)
        with col2:
            st.metric("Gesamt registriert", len(mastergeraete))
        
        st.markdown("---")
        
        # Neues Mastergerät registrieren
        with st.expander("Neues Mastergerät registrieren", expanded=False):
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
                    if st.form_submit_button("Registrieren", use_container_width=True):
                        if not geraet_name:
                            st.error("Bitte geben Sie einen Gerätenamen ein.")
                        else:
                            # Generiere eindeutige Geräte-ID und Registrierungscode
                            geraet_id = str(uuid.uuid4())
                            registrierungscode = str(uuid.uuid4())[:8].upper()
                            
                            # Speichere Mastergerät
                            new_geraet = {
                                'betrieb_id': betrieb_id,
                                'geraet_id': geraet_id,
                                'name': geraet_name,
                                'standort': standort if standort else None,
                                'beschreibung': beschreibung if beschreibung else None,
                                'registrierungscode': registrierungscode,
                                'aktiv': True,
                                'erstellt_am': datetime.now().isoformat()
                            }
                            
                            result = supabase.table('mastergeraete').insert(new_geraet).execute()
                            
                            if result.data:
                                st.success(f"Mastergerät '{geraet_name}' erfolgreich registriert.")
                                st.info(f"Registrierungscode: **{registrierungscode}**")
                                st.session_state['show_qr_for_new'] = registrierungscode
                                st.session_state['show_qr_name'] = geraet_name
                                st.rerun()
                            else:
                                st.error("Fehler beim Registrieren des Geräts.")
        
        # QR-Code für neu registriertes Gerät anzeigen
        if st.session_state.get('show_qr_for_new'):
            code = st.session_state['show_qr_for_new']
            name = st.session_state.get('show_qr_name', 'Neues Gerät')
            
            st.success(f"Gerät '{name}' registriert. Scannen Sie den QR-Code:")
            
            qr_html = zeige_qr_code_html(code, name, app_url)
            st.markdown(qr_html, unsafe_allow_html=True)
            
            # QR-Code als Download
            qr_bytes = generiere_aktivierungs_qr(code, name, app_url)
            if qr_bytes:
                st.download_button(
                    label="QR-Code herunterladen",
                    data=qr_bytes,
                    file_name=f"mastergeraet_{name.replace(' ', '_')}_qr.png",
                    mime="image/png"
                )
            
            if st.button("Verstanden, QR-Code schließen"):
                del st.session_state['show_qr_for_new']
                if 'show_qr_name' in st.session_state:
                    del st.session_state['show_qr_name']
                st.rerun()
        
        st.markdown("---")
        
        # Liste der Mastergeräte
        if not mastergeraete:
            st.info("Noch keine Mastergeräte registriert.")
            return
        
        st.subheader("Registrierte Mastergeräte")
        
        for idx, geraet in enumerate(mastergeraete):
            # Bestimme Geräte-ID (geraet_id oder geraete_id je nach DB-Schema)
            geraet_uid = geraet.get('geraet_id') or geraet.get('geraete_id', str(geraet['id']))
            
            with st.expander(
                f"{'Aktiv' if geraet.get('aktiv', True) else 'Inaktiv'} · {geraet['name']} - {geraet.get('standort', 'Kein Standort')}",
                expanded=False
            ):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Gerätename:** {geraet['name']}")
                    st.write(f"**Standort:** {geraet.get('standort', 'Nicht angegeben')}")
                    st.write(f"**Status:** {'Aktiv' if geraet.get('aktiv', True) else 'Deaktiviert'}")
                    
                    if geraet.get('beschreibung'):
                        st.write(f"**Beschreibung:** {geraet['beschreibung']}")
                
                with col2:
                    st.write(f"**Geräte-ID:** `{str(geraet_uid)[:8]}...`")
                    st.write(f"**Registrierungscode:** `{geraet['registrierungscode']}`")
                    
                    if geraet.get('erstellt_am'):
                        try:
                            erstellt_am = datetime.fromisoformat(geraet['erstellt_am']).strftime('%d.%m.%Y %H:%M')
                            st.write(f"**Registriert am:** {erstellt_am}")
                        except:
                            st.write(f"**Registriert am:** {geraet['erstellt_am'][:10]}")
                    
                    if geraet.get('letzter_kontakt') or geraet.get('letzter_zugriff'):
                        letzter = geraet.get('letzter_kontakt') or geraet.get('letzter_zugriff')
                        try:
                            letzter_str = datetime.fromisoformat(letzter).strftime('%d.%m.%Y %H:%M')
                            st.write(f"**Letzter Kontakt:** {letzter_str}")
                        except:
                            pass
                
                st.markdown("---")
                
                # QR-Code anzeigen
                if st.session_state.get(f'show_qr_{geraet["id"]}', False):
                    qr_html = zeige_qr_code_html(
                        geraet['registrierungscode'],
                        geraet['name'],
                        app_url
                    )
                    st.markdown(qr_html, unsafe_allow_html=True)
                    
                    # QR-Code als Download
                    qr_bytes = generiere_aktivierungs_qr(
                        geraet['registrierungscode'],
                        geraet['name'],
                        app_url
                    )
                    if qr_bytes:
                        st.download_button(
                            label="QR-Code herunterladen",
                            data=qr_bytes,
                            file_name=f"mastergeraet_{geraet['name'].replace(' ', '_')}_qr.png",
                            mime="image/png",
                            key=f"dl_qr_{geraet['id']}"
                        )
                    
                    if st.button("QR-Code schließen", key=f"close_qr_{geraet['id']}"):
                        st.session_state[f'show_qr_{geraet["id"]}'] = False
                        st.rerun()
                
                # Kiosk-URL anzeigen
                kiosk_url = f"{app_url}?kiosk=1&geraet={geraet['registrierungscode']}"
                st.markdown(f"""
                <div style="background:#f0f4ff; border:1px solid #4a90d9; border-radius:8px; padding:10px; margin:8px 0;">
                    <b>Kiosk-URL (für Tablet/Terminal):</b><br>
                    <code style="font-size:0.85rem; word-break:break-all;">{kiosk_url}</code>
                </div>
                """, unsafe_allow_html=True)
                st.caption("Diese URL im Browser des Terminals öffnen – Mitarbeiter stempeln dann per PIN-Eingabe.")
                
                # Aktionen
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if geraet.get('aktiv', True):
                        if st.button("Deaktivieren", key=f"deactivate_{idx}_{geraet['id']}", use_container_width=True):
                            supabase.table('mastergeraete').update({'aktiv': False}).eq('id', geraet['id']).execute()
                            st.success("Gerät deaktiviert!")
                            st.rerun()
                    else:
                        if st.button("Aktivieren", key=f"activate_{idx}_{geraet['id']}", use_container_width=True):
                            supabase.table('mastergeraete').update({'aktiv': True}).eq('id', geraet['id']).execute()
                            st.success("Gerät aktiviert!")
                            st.rerun()
                
                with col2:
                    if st.button("QR-Code anzeigen", key=f"show_qr_btn_{idx}_{geraet['id']}", use_container_width=True):
                        st.session_state[f'show_qr_{geraet["id"]}'] = True
                        st.rerun()
                
                with col3:
                    if st.button("Code erneuern", key=f"renew_{idx}_{geraet['id']}", use_container_width=True):
                        neuer_code = str(uuid.uuid4())[:8].upper()
                        supabase.table('mastergeraete').update({
                            'registrierungscode': neuer_code,
                            # Setze geraete_id zurück, damit das Gerät neu aktiviert werden muss
                            'geraete_id': None
                        }).eq('id', geraet['id']).execute()
                        st.success(f"Neuer Code: **{neuer_code}**")
                        st.info("Das Gerät muss mit dem neuen Code neu aktiviert werden.")
                        st.rerun()
                
                with col4:
                    confirm_key = f'confirm_delete_geraet_{idx}_{geraet["id"]}'
                    if st.session_state.get(confirm_key, False):
                        if st.button("Bestätigen", key=f"confirm_del_{idx}_{geraet['id']}", use_container_width=True, type="primary"):
                            supabase.table('mastergeraete').delete().eq('id', geraet['id']).execute()
                            st.session_state[confirm_key] = False
                            st.success("Gerät gelöscht!")
                            st.rerun()
                    else:
                        if st.button("Löschen", key=f"delete_{idx}_{geraet['id']}", use_container_width=True):
                            st.session_state[confirm_key] = True
                            st.warning("Nochmal klicken zum Bestätigen.")
                            st.rerun()
        
        st.markdown("---")
        
        # Anleitung
        with st.expander("Wie funktioniert die Mastergeräte-Registrierung?"):
            st.markdown("""
            ### Mastergerät einrichten
            
            **Methode 1: QR-Code (empfohlen)**
            1. Registrieren Sie ein neues Mastergerät mit einem eindeutigen Namen
            2. Klicken Sie auf **"QR-Code anzeigen"**
            3. Öffnen Sie CrewBase auf dem Terminal-Gerät (z.B. Tablet am Eingang)
            4. Scannen Sie den QR-Code mit dem Gerät – die Aktivierung erfolgt automatisch
            
            **Methode 2: Manueller Code**
            1. Registrieren Sie ein neues Mastergerät
            2. Notieren Sie den angezeigten **Registrierungscode**
            3. Öffnen Sie CrewBase auf dem Terminal-Gerät
            4. Geben Sie den Code manuell ein wenn Sie dazu aufgefordert werden
            
            ### Zeiterfassung am Mastergerät
            
            - Mitarbeiter **ohne** mobile Berechtigung können **nur** an Mastergeräten stempeln
            - Mitarbeiter **mit** mobiler Berechtigung können überall stempeln
            - Das System erkennt automatisch, ob ein Gerät ein Mastergerät ist
            
            ### Sicherheit
            
            - Jedes Gerät hat eine eindeutige Geräte-ID
            - Der Registrierungscode kann jederzeit erneuert werden (altes Gerät muss dann neu aktiviert werden)
            - Geräte können deaktiviert werden ohne sie zu löschen
            """)
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Mastergeräte: {str(e)}")
        import traceback
        st.exception(e)
