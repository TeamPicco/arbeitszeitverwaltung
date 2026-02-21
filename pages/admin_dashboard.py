"""
Administrator-Dashboard
Zentrale Verwaltung aller Mitarbeiter, Zeiterfassung und Lohnabrechnung
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Optional

from utils.database import (
    get_supabase_client,
    get_all_mitarbeiter,
    create_user,
    create_mitarbeiter,
    update_mitarbeiter,
    upload_file_to_storage,
    download_file_from_storage,
    change_password
)
from utils.calculations import (
    berechne_urlaubstage,
    format_waehrung,
    get_monatsnamen,
    berechne_arbeitsstunden
)
from utils.push_notifications import show_notifications_widget
from utils.chat_notifications import get_unread_chat_count
from utils.styles import apply_custom_css, get_icon, COLORS


def show():
    """Zeigt das Administrator-Dashboard an"""
    
    # Wende Custom CSS an
    apply_custom_css()
    
    # Zeige Benachrichtigungen in Sidebar
    if hasattr(st.session_state, 'user_id'):
        show_notifications_widget(st.session_state.user_id)
    
    # Zeige Betriebslogo für Piccolo (Betriebsnummer 20262204)
    import os
    import base64
    
    # Prüfe ob Piccolo-Betrieb
    if hasattr(st.session_state, 'betrieb_id'):
        supabase = get_supabase_client()
        betrieb_response = supabase.table('betriebe').select('betriebsnummer').eq('id', st.session_state.betrieb_id).execute()
        
        if betrieb_response.data and betrieb_response.data[0].get('betriebsnummer') == '20262204':
            # Zeige Piccolo-Logo
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "piccolo_logo.jpeg")
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as f:
                    logo_data = base64.b64encode(f.read()).decode()
                st.markdown(
                    f'<div style="text-align: center; margin-bottom: 1rem;"><img src="data:image/jpeg;base64,{logo_data}" style="max-width: 300px; height: auto;"></div>',
                    unsafe_allow_html=True
                )
    
    st.title(f"{get_icon('dashboard')} Administrator-Dashboard")
    
    # Zähle ungelesene Chat-Nachrichten
    last_read = st.session_state.get('chat_last_read', None)
    unread_count = get_unread_chat_count(st.session_state.user_id, st.session_state.betrieb_id, last_read)
    chat_badge = f" ({unread_count})" if unread_count > 0 else ""
    
    # Tab-Navigation mit einheitlichen Icons
    tabs = st.tabs([
        f"{get_icon('dashboard')} Übersicht",
        f"{get_icon('mitarbeiter')} Mitarbeiterverwaltung",
        f"{get_icon('dienstplan')} Dienstplanung",
        f"{get_icon('urlaub')} Urlaubsgenehmigung",
        f"{get_icon('dienstplan')} Urlaubskalender",
        f"{get_icon('chat')} Plauderecke{chat_badge}",
        f"{get_icon('zeit')} Zeiterfassung",
        f"{get_icon('lohn')} Lohnabrechnung",
        f"{get_icon('mastergeraete')} Mastergeräte",
        f"{get_icon('einstellungen')} Einstellungen"
    ])
    
    with tabs[0]:
        show_uebersicht()
    
    with tabs[1]:
        show_mitarbeiterverwaltung()
    
    with tabs[2]:
        from pages.admin_dienstplan import show_dienstplanung
        show_dienstplanung()
    
    with tabs[3]:
        show_urlaubsgenehmigung()
    
    with tabs[4]:
        show_urlaubskalender_admin()
    
    with tabs[5]:
        show_plauderecke_admin()
    
    with tabs[6]:
        show_zeiterfassung_admin()
    
    with tabs[7]:
        show_lohnabrechnung()
    
    with tabs[8]:
        from pages.admin_mastergeraete import show_mastergeraete
        show_mastergeraete()
    
    with tabs[9]:
        show_einstellungen()


def show_uebersicht():
    """Zeigt die Übersicht mit wichtigen Kennzahlen"""
    
    st.subheader("📊 Übersicht")
    
    # Benachrichtigungen anzeigen
    show_benachrichtigungen_widget()
    
    supabase = get_supabase_client()
    
    # Lade Statistiken
    try:
        # Anzahl Mitarbeiter
        mitarbeiter_response = supabase.table('mitarbeiter').select('id', count='exact').execute()
        anzahl_mitarbeiter = len(mitarbeiter_response.data) if mitarbeiter_response.data else 0
        
        # Offene Urlaubsanträge
        urlaub_response = supabase.table('urlaubsantraege').select('id', count='exact').eq('status', 'beantragt').execute()
        offene_antraege = len(urlaub_response.data) if urlaub_response.data else 0
        
        # Zeiterfassungen heute
        heute = date.today().isoformat()
        zeit_response = supabase.table('zeiterfassung').select('id', count='exact').eq('datum', heute).execute()
        zeiterfassungen_heute = len(zeit_response.data) if zeit_response.data else 0
        
        # Zeige Kennzahlen
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Mitarbeiter", anzahl_mitarbeiter)
        
        with col2:
            st.metric("Offene Urlaubsanträge", offene_antraege)
        
        with col3:
            st.metric("Zeiterfassungen heute", zeiterfassungen_heute)
        
        with col4:
            st.metric("Aktueller Monat", get_monatsnamen(date.today().month))
        
        st.markdown("---")
        
        # Zeige offene Urlaubsanträge
        if offene_antraege > 0:
            st.subheader("🔔 Offene Urlaubsanträge")
            
            urlaub_data = supabase.table('urlaubsantraege').select(
                '*, mitarbeiter(vorname, nachname)'
            ).eq('status', 'beantragt').order('beantragt_am').execute()
            
            if urlaub_data.data:
                for antrag in urlaub_data.data:
                    mitarbeiter = antrag['mitarbeiter']
                    
                    with st.expander(f"📅 {mitarbeiter['vorname']} {mitarbeiter['nachname']} - {antrag['von_datum']} bis {antrag['bis_datum']} ({antrag['anzahl_tage']} Tage)"):
                        st.write(f"**Beantragt am:** {antrag['beantragt_am']}")
                        if antrag.get('bemerkung_mitarbeiter'):
                            st.write(f"**Bemerkung:** {antrag['bemerkung_mitarbeiter']}")
                        
                        st.markdown("---")
                        
                        # Genehmigung/Ablehnung
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✅ Genehmigen", key=f"approve_{antrag['id']}", use_container_width=True, type="primary"):
                                import logging
                                logger = logging.getLogger(__name__)
                                try:
                                    logger.info(f"DEBUG: Genehmige Urlaubsantrag ID {antrag['id']}")
                                    
                                    response = supabase.table('urlaubsantraege').update({
                                        'status': 'Genehmigt',
                                        'bearbeitet_am': datetime.now().isoformat()
                                    }).eq('id', antrag['id']).execute()
                                    
                                    logger.info(f"DEBUG: Update Response: {response}")
                                    
                                    # Benachrichtigung für Mitarbeiter
                                    mitarbeiter_user = supabase.table('mitarbeiter').select('user_id').eq('id', antrag['mitarbeiter_id']).execute()
                                    if mitarbeiter_user.data:
                                        logger.info(f"DEBUG: Erstelle Benachrichtigung für User {mitarbeiter_user.data[0]['user_id']}")
                                        supabase.table('benachrichtigungen').insert({
                                            'user_id': mitarbeiter_user.data[0]['user_id'],
                                            'typ': 'urlaubsantrag',
                                            'titel': 'Urlaubsantrag genehmigt',
                                            'nachricht': f"Ihr Urlaubsantrag vom {antrag['von_datum']} bis {antrag['bis_datum']} wurde genehmigt.",
                                            'gelesen': False,
                                            'betrieb_id': st.session_state.betrieb_id
                                        }).execute()
                                    
                                    st.success("✅ Urlaubsantrag genehmigt!")
                                    logger.info("DEBUG: Urlaubsantrag erfolgreich genehmigt, rerun...")
                                    st.rerun()
                                except Exception as e:
                                    logger.error(f"DEBUG ERROR bei Urlaubsgenehmigung: {e}", exc_info=True)
                                    st.error(f"Fehler: {str(e)}")
                        
                        with col2:
                            if st.button("❌ Ablehnen", key=f"reject_{antrag['id']}", use_container_width=True):
                                try:
                                    supabase.table('urlaubsantraege').update({
                                        'status': 'abgelehnt',
                                        'bearbeitet_am': datetime.now().isoformat()
                                    }).eq('id', antrag['id']).execute()
                                    
                                    # Benachrichtigung für Mitarbeiter
                                    mitarbeiter_user = supabase.table('mitarbeiter').select('user_id').eq('id', antrag['mitarbeiter_id']).execute()
                                    if mitarbeiter_user.data:
                                        supabase.table('benachrichtigungen').insert({
                                            'user_id': mitarbeiter_user.data[0]['user_id'],
                                            'typ': 'urlaubsantrag',
                                            'titel': 'Urlaubsantrag abgelehnt',
                                            'nachricht': f"Ihr Urlaubsantrag vom {antrag['von_datum']} bis {antrag['bis_datum']} wurde abgelehnt.",
                                            'gelesen': False,
                                            'betrieb_id': st.session_state.betrieb_id
                                        }).execute()
                                    
                                    st.success("❌ Urlaubsantrag abgelehnt.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler: {str(e)}")
        else:
            st.info("✅ Keine offenen Urlaubsanträge")
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Übersicht: {str(e)}")


def show_mitarbeiterverwaltung():
    """Zeigt die Mitarbeiterverwaltung an"""
    
    st.subheader("👥 Mitarbeiterverwaltung")
    
    # Aktionen
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("➕ Neuer Mitarbeiter", use_container_width=True):
            st.session_state.show_mitarbeiter_form = True
    
    # Zeige Formular für neuen/bearbeiteten Mitarbeiter
    if st.session_state.get('show_mitarbeiter_form', False):
        # Prüfe ob Bearbeitung oder Neuanlage
        edit_id = st.session_state.get('edit_mitarbeiter_id', None)
        if edit_id:
            # Lade Mitarbeiterdaten für Bearbeitung
            mitarbeiter_to_edit = next((m for m in get_all_mitarbeiter() if m['id'] == edit_id), None)
            if mitarbeiter_to_edit:
                show_mitarbeiter_form(mitarbeiter_to_edit)
            else:
                st.error("Mitarbeiter nicht gefunden.")
                st.session_state.show_mitarbeiter_form = False
                st.session_state.edit_mitarbeiter_id = None
        else:
            show_mitarbeiter_form()
        st.markdown("---")
    
    # Lade alle Mitarbeiter
    mitarbeiter_list = get_all_mitarbeiter()
    
    if not mitarbeiter_list:
        st.info("Noch keine Mitarbeiter angelegt.")
        return
    
    # Zeige Mitarbeiter-Tabelle
    st.subheader("Mitarbeiter-Übersicht")
    
    # Erstelle Tabellen-Daten
    table_data = []
    for m in mitarbeiter_list:
        table_data.append({
            'Personalnr.': m['personalnummer'],
            'Vorname': m['vorname'],
            'Nachname': m['nachname'],
            'E-Mail': m['email'],
            'Soll-Std.': m['monatliche_soll_stunden'],
            'Stundenlohn': f"{m['stundenlohn_brutto']:.2f} €",
            'Urlaubstage': m['jahres_urlaubstage']
        })
    
    st.dataframe(table_data, use_container_width=True, hide_index=True)
    
    # Details anzeigen
    st.subheader("Mitarbeiter-Details")
    
    selected_mitarbeiter = st.selectbox(
        "Mitarbeiter auswählen",
        options=mitarbeiter_list,
        format_func=lambda x: f"{x['vorname']} {x['nachname']} ({x['personalnummer']})"
    )
    
    if selected_mitarbeiter:
        show_mitarbeiter_details(selected_mitarbeiter)


def show_mitarbeiter_form(mitarbeiter_data: Optional[dict] = None):
    """Zeigt das Formular zum Anlegen/Bearbeiten eines Mitarbeiters"""
    
    is_edit = mitarbeiter_data is not None
    
    st.subheader("✏️ Mitarbeiter bearbeiten" if is_edit else "➕ Neuer Mitarbeiter")
    
    with st.form("mitarbeiter_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Persönliche Daten**")
            vorname = st.text_input("Vorname*", value=mitarbeiter_data.get('vorname', '') if is_edit else '')
            nachname = st.text_input("Nachname*", value=mitarbeiter_data.get('nachname', '') if is_edit else '')
            geburtsdatum = st.date_input(
                "Geburtsdatum*",
                value=datetime.fromisoformat(mitarbeiter_data['geburtsdatum']) if is_edit else date(1990, 1, 1),
                min_value=date(1950, 1, 1),
                max_value=date.today(),
                format="DD.MM.YYYY"
            )
            
            st.markdown("**Kontaktdaten**")
            email = st.text_input("E-Mail", value=mitarbeiter_data.get('email', '') if is_edit else '')
            telefon = st.text_input("Telefon", value=mitarbeiter_data.get('telefon', '') if is_edit else '')
        
        with col2:
            st.markdown("**Adresse**")
            strasse = st.text_input("Straße & Hausnummer", value=mitarbeiter_data.get('strasse', '') if is_edit else '')
            plz = st.text_input("PLZ", value=mitarbeiter_data.get('plz', '') if is_edit else '')
            ort = st.text_input("Ort", value=mitarbeiter_data.get('ort', '') if is_edit else '')
            
            st.markdown("**Beschäftigung**")
            personalnummer = st.text_input(
                "Personalnummer",
                value=mitarbeiter_data.get('personalnummer', '') if is_edit else '',
                disabled=is_edit
            )
            eintrittsdatum = st.date_input(
                "Eintrittsdatum",
                value=datetime.fromisoformat(mitarbeiter_data['eintrittsdatum']) if is_edit else date.today(),
                min_value=date(1995, 1, 1),
                max_value=date.today(),
                format="DD.MM.YYYY"
            )
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Lohnparameter**")
            monatliche_soll_stunden = st.number_input(
                "Monatliche Soll-Stunden*",
                min_value=0.0,
                max_value=250.0,
                value=float(mitarbeiter_data.get('monatliche_soll_stunden', 160.0)) if is_edit else 160.0,
                step=0.5
            )
            stundenlohn_brutto = st.number_input(
                "Stundenlohn (brutto)*",
                min_value=0.0,
                max_value=100.0,
                value=float(mitarbeiter_data.get('stundenlohn_brutto', 15.0)) if is_edit else 15.0,
                step=0.5
            )
        
        with col2:
            st.markdown("**Urlaub**")
            jahres_urlaubstage = st.number_input(
                "Jährliche Urlaubstage*",
                min_value=20,
                max_value=50,
                value=int(mitarbeiter_data.get('jahres_urlaubstage', 28)) if is_edit else 28
            )
            resturlaub_vorjahr = st.number_input(
                "Resturlaub Vorjahr",
                min_value=0.0,
                max_value=50.0,
                value=float(mitarbeiter_data.get('resturlaub_vorjahr', 0.0)) if is_edit else 0.0,
                step=0.5
            )
        
        with col3:
            st.markdown("**Zuschäge**")
            sonntagszuschlag_aktiv = st.checkbox(
                "50% Sonntagszuschlag",
                value=mitarbeiter_data.get('sonntagszuschlag_aktiv', False) if is_edit else False
            )
            feiertagszuschlag_aktiv = st.checkbox(
                "100% Feiertagszuschlag",
                value=mitarbeiter_data.get('feiertagszuschlag_aktiv', False) if is_edit else False
            )
            
            st.markdown("**Zeiterfassung**")
            mobile_zeiterfassung = st.checkbox(
                "📱 Mobile Zeiterfassung erlaubt",
                value=mitarbeiter_data.get('mobile_zeiterfassung', False) if is_edit else False,
                help="Erlaubt Zeiterfassung per App (für Außendienst)"
            )
        
        st.markdown("---")
        
        # Benutzerkonto (nur bei Neuanlage)
        if not is_edit:
            st.markdown("**Benutzerkonto**")
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Benutzername*")
            with col2:
                password = st.text_input("Passwort*", type="password")
        
        col1, col2 = st.columns([1, 5])
        
        with col1:
            submit = st.form_submit_button("Speichern", use_container_width=True)
        
        with col2:
            if st.form_submit_button("Abbrechen", use_container_width=True):
                st.session_state.show_mitarbeiter_form = False
                st.session_state.edit_mitarbeiter_id = None
                st.rerun()
        
        if submit:
            # Validierung - nur Name und Vorname sind Pflichtfelder
            if not vorname or not nachname:
                st.error("Bitte füllen Sie mindestens Vorname und Nachname aus.")
                return
            
            if not is_edit and (not username or not password):
                st.error("Bitte geben Sie Benutzername und Passwort ein.")
                return
            
            # Personalnummer-Validierung
            if not personalnummer or personalnummer.strip() == '':
                st.error("Bitte geben Sie eine Personalnummer ein.")
                return
            
            # Erstelle/Aktualisiere Mitarbeiter
            mitarbeiter_daten = {
                'vorname': vorname,
                'nachname': nachname,
                'geburtsdatum': geburtsdatum.isoformat(),
                'strasse': strasse,
                'plz': plz,
                'ort': ort,
                'email': email,
                'telefon': telefon,
                'personalnummer': personalnummer,
                'eintrittsdatum': eintrittsdatum.isoformat(),
                'monatliche_soll_stunden': monatliche_soll_stunden,
                'stundenlohn_brutto': stundenlohn_brutto,
                'jahres_urlaubstage': jahres_urlaubstage,
                'resturlaub_vorjahr': resturlaub_vorjahr,
                'sonntagszuschlag_aktiv': sonntagszuschlag_aktiv,
                'feiertagszuschlag_aktiv': feiertagszuschlag_aktiv,
                'mobile_zeiterfassung': mobile_zeiterfassung
            }
            
            if is_edit:
                # Aktualisiere bestehenden Mitarbeiter
                if update_mitarbeiter(mitarbeiter_data['id'], mitarbeiter_daten):
                    st.success("Mitarbeiter erfolgreich aktualisiert!")
                    st.session_state.show_mitarbeiter_form = False
                    st.session_state.edit_mitarbeiter_id = None
                    st.rerun()
            else:
                # Erstelle neuen Benutzer
                try:
                    user_id = create_user(username, password, 'mitarbeiter')
                    
                    if user_id:
                        # Erstelle Mitarbeiter
                        mitarbeiter_id = create_mitarbeiter(user_id, mitarbeiter_daten)
                        
                        if mitarbeiter_id:
                            st.success(f"Mitarbeiter {vorname} {nachname} erfolgreich angelegt!")
                            st.session_state.show_mitarbeiter_form = False
                            st.rerun()
                        else:
                            st.error("Fehler beim Erstellen des Mitarbeiters. Bitte prüfen Sie die Logs.")
                    else:
                        st.error("Fehler beim Erstellen des Benutzerkontos. Möglicherweise existiert der Benutzername bereits.")
                except Exception as e:
                    st.error(f"Fehler beim Anlegen des Mitarbeiters: {str(e)}")
                    import logging
                    logging.error(f"Fehler beim Anlegen des Mitarbeiters: {e}", exc_info=True)


def show_mitarbeiter_details(mitarbeiter: dict):
    """Zeigt die Details eines Mitarbeiters an"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Persönliche Daten**")
        st.write(f"**Name:** {mitarbeiter['vorname']} {mitarbeiter['nachname']}")
        geburtsdatum_formatted = datetime.fromisoformat(mitarbeiter['geburtsdatum']).strftime('%d.%m.%Y')
        st.write(f"**Geburtsdatum:** {geburtsdatum_formatted}")
        st.write(f"**E-Mail:** {mitarbeiter.get('email', 'Nicht angegeben')}")
        st.write(f"**Telefon:** {mitarbeiter.get('telefon', 'Nicht angegeben')}")
        
        st.markdown("**Adresse**")
        st.write(f"{mitarbeiter['strasse']}")
        st.write(f"{mitarbeiter['plz']} {mitarbeiter['ort']}")
    
    with col2:
        st.markdown("**Vertragsdaten**")
        st.write(f"**Personalnummer:** {mitarbeiter.get('personalnummer', 'Nicht angegeben')}")
        eintrittsdatum_formatted = datetime.fromisoformat(mitarbeiter['eintrittsdatum']).strftime('%d.%m.%Y') if mitarbeiter.get('eintrittsdatum') else 'Nicht angegeben'
        st.write(f"**Eintrittsdatum:** {eintrittsdatum_formatted}")
        st.write(f"**Soll-Stunden/Monat:** {mitarbeiter['monatliche_soll_stunden']}")
        st.write(f"**Stundenlohn:** {format_waehrung(mitarbeiter['stundenlohn_brutto'])}")
        st.write(f"**Urlaubstage/Jahr:** {mitarbeiter['jahres_urlaubstage']}")
        
        st.markdown("**Zuschläge**")
        st.write(f"Sonntagszuschlag: {'✅ Aktiv' if mitarbeiter['sonntagszuschlag_aktiv'] else '❌ Inaktiv'}")
        st.write(f"Feiertagszuschlag: {'✅ Aktiv' if mitarbeiter['feiertagszuschlag_aktiv'] else '❌ Inaktiv'}")
    
    st.markdown("---")
    
    # Bearbeiten und Löschen-Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✏️ Mitarbeiter bearbeiten", key=f"edit_{mitarbeiter['id']}", use_container_width=True):
            st.session_state.edit_mitarbeiter_id = mitarbeiter['id']
            st.session_state.show_mitarbeiter_form = True
            st.rerun()
    
    with col2:
        if st.button("🗑️ Mitarbeiter löschen", key=f"delete_{mitarbeiter['id']}", use_container_width=True, type="secondary"):
            # Bestätigung erforderlich
            if not st.session_state.get(f"confirm_delete_mitarbeiter_{mitarbeiter['id']}", False):
                st.session_state[f"confirm_delete_mitarbeiter_{mitarbeiter['id']}"] = True
                st.warning("⚠️ Bitte klicken Sie erneut zum Bestätigen!")
                st.rerun()
            else:
                # Lösche Mitarbeiter
                import logging
                logger = logging.getLogger(__name__)
                try:
                    from utils.database import delete_mitarbeiter
                    logger.info(f"DEBUG: Lösche Mitarbeiter ID {mitarbeiter['id']}")
                    
                    if delete_mitarbeiter(mitarbeiter['id']):
                        st.success(f"✅ Mitarbeiter {mitarbeiter['vorname']} {mitarbeiter['nachname']} gelöscht!")
                        st.session_state.pop(f"confirm_delete_mitarbeiter_{mitarbeiter['id']}", None)
                        st.rerun()
                    else:
                        st.error("Fehler beim Löschen des Mitarbeiters.")
                except Exception as e:
                    logger.error(f"DEBUG ERROR beim Löschen: {e}", exc_info=True)
                    st.error(f"Fehler: {str(e)}")
    



def show_urlaubsgenehmigung():
    """Zeigt die Urlaubsgenehmigung an"""
    
    st.subheader("🏖️ Urlaubsgenehmigung")
    
    supabase = get_supabase_client()
    
    # Lade alle Urlaubsanträge
    try:
        urlaub_data = supabase.table('urlaubsantraege').select(
            '*, mitarbeiter(vorname, nachname, personalnummer)'
        ).order('beantragt_am', desc=True).execute()
        
        if not urlaub_data.data:
            st.info("Keine Urlaubsanträge vorhanden.")
            return
        
        # Filtere nach Status
        status_filter = st.selectbox(
            "Status filtern",
            options=['Alle', 'Beantragt', 'Genehmigt', 'Abgelehnt'],
            index=1
        )
        
        filtered_data = urlaub_data.data
        if status_filter != 'Alle':
            filtered_data = [a for a in urlaub_data.data if a['status'] == status_filter.lower()]
        
        if not filtered_data:
            st.info(f"Keine Urlaubsanträge mit Status '{status_filter}'.")
            return
        
        # Zeige Anträge
        for antrag in filtered_data:
            mitarbeiter = antrag['mitarbeiter']
            
            with st.expander(
                f"{mitarbeiter['vorname']} {mitarbeiter['nachname']} - "
                f"{antrag['von_datum']} bis {antrag['bis_datum']} "
                f"({antrag['anzahl_tage']} Tage) - Status: {antrag['status'].upper()}"
            ):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Mitarbeiter:** {mitarbeiter['vorname']} {mitarbeiter['nachname']}")
                    st.write(f"**Personalnummer:** {mitarbeiter['personalnummer']}")
                    st.write(f"**Zeitraum:** {antrag['von_datum']} bis {antrag['bis_datum']}")
                    st.write(f"**Anzahl Tage:** {antrag['anzahl_tage']}")
                
                with col2:
                    st.write(f"**Beantragt am:** {antrag['beantragt_am']}")
                    st.write(f"**Status:** {antrag['status'].upper()}")
                    if antrag.get('bemerkung_mitarbeiter'):
                        st.write(f"**Bemerkung:** {antrag['bemerkung_mitarbeiter']}")
                
                # Genehmigung/Ablehnung (nur für offene Anträge)
                if antrag['status'] == 'beantragt':
                    st.markdown("---")
                    
                    bemerkung_admin = st.text_area(
                        "Bemerkung (optional)",
                        key=f"bemerkung_{antrag['id']}"
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("✅ Genehmigen", key=f"approve_{antrag['id']}", use_container_width=True):
                            # Aktualisiere Antrag
                            supabase.table('urlaubsantraege').update({
                                'status': 'genehmigt',
                                'bemerkung_admin': bemerkung_admin,
                                'bearbeitet_am': datetime.now().isoformat(),
                                'bearbeitet_von': st.session_state.user_id
                            }).eq('id', antrag['id']).execute()
                            
                            st.success("Urlaubsantrag genehmigt!")
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ Ablehnen", key=f"reject_{antrag['id']}", use_container_width=True):
                            # Aktualisiere Antrag
                            supabase.table('urlaubsantraege').update({
                                'status': 'abgelehnt',
                                'bemerkung_admin': bemerkung_admin,
                                'bearbeitet_am': datetime.now().isoformat(),
                                'bearbeitet_von': st.session_state.user_id
                            }).eq('id', antrag['id']).execute()
                            
                            st.warning("Urlaubsantrag abgelehnt!")
                            st.rerun()
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Urlaubsanträge: {str(e)}")


def show_zeiterfassung_admin():
    """Zeigt die Zeiterfassung für alle Mitarbeiter an"""
    
    st.subheader("⏰ Zeiterfassung (Übersicht & Korrektur)")
    
    # Filter
    col1, col2, col3 = st.columns(3)
    
    with col1:
        mitarbeiter_list = get_all_mitarbeiter()
        if not mitarbeiter_list:
            st.warning("Keine Mitarbeiter vorhanden.")
            return
        
        mitarbeiter_options = [{'id': None, 'name': 'Alle Mitarbeiter'}] + \
                             [{'id': m['id'], 'name': f"{m['vorname']} {m['nachname']}"} for m in mitarbeiter_list]
        
        selected_mitarbeiter_idx = st.selectbox(
            "Mitarbeiter",
            range(len(mitarbeiter_options)),
            format_func=lambda x: mitarbeiter_options[x]['name']
        )
        selected_mitarbeiter_id = mitarbeiter_options[selected_mitarbeiter_idx]['id']
    
    with col2:
        filter_datum_von = st.date_input(
            "Von",
            value=date.today() - timedelta(days=30),
            format="DD.MM.YYYY"
        )
    
    with col3:
        filter_datum_bis = st.date_input(
            "Bis",
            value=date.today(),
            format="DD.MM.YYYY"
        )
    
    # Lade Zeiterfassungen
    supabase = get_supabase_client()
    
    try:
        query = supabase.table('zeiterfassung').select('*, mitarbeiter(vorname, nachname)')
        
        if selected_mitarbeiter_id:
            query = query.eq('mitarbeiter_id', selected_mitarbeiter_id)
        
        query = query.gte('datum', filter_datum_von.isoformat())
        query = query.lte('datum', filter_datum_bis.isoformat())
        query = query.order('datum', desc=True).order('start_zeit', desc=True)
        
        response = query.execute()
        zeiterfassungen = response.data if response.data else []
        
        if not zeiterfassungen:
            st.info("ℹ️ Keine Zeiterfassungen im gewählten Zeitraum gefunden.")
            return
        
        st.write(f"**{len(zeiterfassungen)} Zeiterfassungen gefunden**")
        
        # Zeige Zeiterfassungen mit Bearbeitungs-Option
        for ze in zeiterfassungen:
            with st.expander(
                f"👤 {ze['mitarbeiter']['vorname']} {ze['mitarbeiter']['nachname']} - "
                f"{datetime.fromisoformat(ze['datum']).strftime('%d.%m.%Y')} - "
                f"{ze['start_zeit'][:5]} bis {ze['ende_zeit'][:5] if ze['ende_zeit'] else 'Offen'}"
            ):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Datum:** {datetime.fromisoformat(ze['datum']).strftime('%d.%m.%Y')}")
                    st.write(f"**Check-In:** {ze['start_zeit']}")
                    st.write(f"**Check-Out:** {ze['ende_zeit'] if ze['ende_zeit'] else '❌ Noch nicht ausgestempelt'}")
                    
                    if ze.get('arbeitsstunden'):
                        st.write(f"**Arbeitsstunden:** {ze['arbeitsstunden']:.2f} h")
                
                with col2:
                    st.write(f"**Pause (Min):** {ze.get('pause_minuten', 0)}")
                    st.write(f"**Sonntag:** {'✅' if ze.get('ist_sonntag') else '❌'}")
                    st.write(f"**Feiertag:** {'✅' if ze.get('ist_feiertag') else '❌'}")
                
                # Korrektur-Formular
                st.markdown("---")
                st.markdown("**✏️ Zeiterfassung korrigieren**")
                
                with st.form(f"korrektur_form_{ze['id']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        new_check_in = st.time_input(
                            "Check-In",
                            value=datetime.strptime(ze['start_zeit'], '%H:%M:%S').time()
                        )
                    
                    with col2:
                        if ze['ende_zeit']:
                            default_checkout = datetime.strptime(ze['ende_zeit'], '%H:%M:%S').time()
                        else:
                            default_checkout = datetime.now().time()
                        
                        new_check_out = st.time_input(
                            "Check-Out",
                            value=default_checkout
                        )
                    
                    with col3:
                        new_pause = st.number_input(
                            "Pause (Min)",
                            min_value=0,
                            max_value=240,
                            value=ze.get('pause_minuten', 0)
                        )
                    
                    korrektur_grund = st.text_area(
                        "Grund der Korrektur",
                        placeholder="z.B. Vergessener Logout, Systemfehler, etc."
                    )
                    
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        if st.form_submit_button("💾 Speichern", use_container_width=True):
                            if not korrektur_grund:
                                st.error("⚠️ Bitte geben Sie einen Grund für die Korrektur an.")
                            else:
                                # Berechne neue Arbeitsstunden
                                from utils.calculations import berechne_arbeitsstunden
                                
                                check_in_dt = datetime.combine(date.today(), new_check_in)
                                check_out_dt = datetime.combine(date.today(), new_check_out)
                                
                                arbeitsstunden = berechne_arbeitsstunden(
                                    check_in_dt,
                                    check_out_dt,
                                    new_pause
                                )
                                
                                # Aktualisiere Zeiterfassung
                                update_data = {
                                    'start_zeit': new_check_in.strftime('%H:%M:%S'),
                                    'ende_zeit': new_check_out.strftime('%H:%M:%S'),
                                    'pause_minuten': new_pause,
                                    'arbeitsstunden': arbeitsstunden,
                                    'korrigiert_von_admin': True,
                                    'korrektur_grund': korrektur_grund,
                                    'korrektur_datum': datetime.now().isoformat()
                                }
                                
                                supabase.table('zeiterfassung').update(update_data).eq('id', ze['id']).execute()
                                
                                st.success("✅ Zeiterfassung erfolgreich korrigiert!")
                                st.rerun()
                    
                    with col2:
                        if st.form_submit_button("🗑️ Löschen", use_container_width=True):
                            if st.session_state.get(f'confirm_delete_{ze["id"]}', False):
                                supabase.table('zeiterfassung').delete().eq('id', ze['id']).execute()
                                st.success("✅ Zeiterfassung gelöscht!")
                                st.rerun()
                            else:
                                st.session_state[f'confirm_delete_{ze["id"]}'] = True
                                st.warning("⚠️ Nochmal klicken zum Bestätigen!")
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Zeiterfassungen: {str(e)}")


def show_lohnabrechnung():
    """Zeigt die Lohnabrechnung an"""
    
    st.subheader("💰 Lohnabrechnung")
    
    from utils.lohnabrechnung import (
        erstelle_lohnabrechnung,
        generiere_lohnabrechnung_pdf,
        speichere_lohnabrechnung_pdf
    )
    
    # Auswahl Mitarbeiter und Zeitraum
    col1, col2, col3 = st.columns(3)
    
    with col1:
        mitarbeiter_list = get_all_mitarbeiter()
        if not mitarbeiter_list:
            st.warning("Keine Mitarbeiter vorhanden.")
            return
        
        selected_mitarbeiter = st.selectbox(
            "Mitarbeiter",
            options=mitarbeiter_list,
            format_func=lambda x: f"{x['vorname']} {x['nachname']} ({x['personalnummer']})"
        )
    
    with col2:
        jahr = st.number_input(
            "Jahr",
            min_value=2020,
            max_value=2030,
            value=date.today().year
        )
    
    with col3:
        monat = st.number_input(
            "Monat",
            min_value=1,
            max_value=12,
            value=date.today().month
        )
    
    if st.button("💰 Lohnabrechnung erstellen", use_container_width=True):
        with st.spinner("Erstelle Lohnabrechnung..."):
            lohnabrechnung_id = erstelle_lohnabrechnung(
                selected_mitarbeiter['id'],
                monat,
                jahr
            )
            
            if lohnabrechnung_id:
                # Generiere und speichere PDF
                pdf_path = speichere_lohnabrechnung_pdf(lohnabrechnung_id)
                
                if pdf_path:
                    st.success("✅ Lohnabrechnung erfolgreich erstellt!")
                    st.rerun()
                else:
                    st.warning("Lohnabrechnung erstellt, aber PDF-Speicherung fehlgeschlagen.")
            else:
                st.error("Fehler beim Erstellen der Lohnabrechnung.")
    
    st.markdown("---")
    
    # Zeige vorhandene Lohnabrechnungen
    st.subheader("Vorhandene Lohnabrechnungen")
    
    supabase = get_supabase_client()
    
    try:
        lohnabrechnungen = supabase.table('lohnabrechnungen').select(
            '*, mitarbeiter(vorname, nachname, personalnummer)'
        ).order('jahr', desc=True).order('monat', desc=True).execute()
        
        if lohnabrechnungen.data:
            for abrechnung in lohnabrechnungen.data:
                mitarbeiter = abrechnung['mitarbeiter']
                
                with st.expander(
                    f"{mitarbeiter['vorname']} {mitarbeiter['nachname']} - "
                    f"{get_monatsnamen(abrechnung['monat'])} {abrechnung['jahr']} - "
                    f"{format_waehrung(abrechnung['gesamtbetrag'])}"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Grundlohn:** {format_waehrung(abrechnung['grundlohn'])}")
                        if abrechnung['sonntagszuschlag'] > 0:
                            st.write(f"**Sonntagszuschlag:** {format_waehrung(abrechnung['sonntagszuschlag'])}")
                        if abrechnung['feiertagszuschlag'] > 0:
                            st.write(f"**Feiertagszuschlag:** {format_waehrung(abrechnung['feiertagszuschlag'])}")
                    
                    with col2:
                        st.write(f"**Gesamtbetrag:** {format_waehrung(abrechnung['gesamtbetrag'])}")
                        st.write(f"**Erstellt am:** {abrechnung['erstellt_am']}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📥 PDF herunterladen", key=f"download_lohn_{abrechnung['id']}"):
                            pdf_bytes = generiere_lohnabrechnung_pdf(abrechnung['id'])
                            if pdf_bytes:
                                st.download_button(
                                    label="Download starten",
                                    data=pdf_bytes,
                                    file_name=f"Lohnabrechnung_{mitarbeiter['personalnummer']}_{abrechnung['jahr']}_{abrechnung['monat']:02d}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{abrechnung['id']}"
                                )
                    
                    with col2:
                        if st.button("🔄 Neu berechnen", key=f"recalc_{abrechnung['id']}"):
                            lohnabrechnung_id = erstelle_lohnabrechnung(
                                abrechnung['mitarbeiter_id'],
                                abrechnung['monat'],
                                abrechnung['jahr']
                            )
                            if lohnabrechnung_id:
                                speichere_lohnabrechnung_pdf(lohnabrechnung_id)
                                st.success("✅ Lohnabrechnung neu berechnet!")
                                st.rerun()
        else:
            st.info("Noch keine Lohnabrechnungen erstellt.")
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Lohnabrechnungen: {str(e)}")


def show_einstellungen():
    """Zeigt die Einstellungen an"""
    
    st.subheader("⚙️ Einstellungen")
    
    # Passwort ändern
    st.markdown("**Passwort ändern**")
    
    with st.form("change_password_form"):
        new_password = st.text_input("Neues Passwort", type="password")
        confirm_password = st.text_input("Passwort bestätigen", type="password")
        
        submit = st.form_submit_button("Passwort ändern")
        
        if submit:
            if not new_password or not confirm_password:
                st.error("Bitte füllen Sie alle Felder aus.")
            elif new_password != confirm_password:
                st.error("Passwörter stimmen nicht überein.")
            elif len(new_password) < 8:
                st.error("Passwort muss mindestens 8 Zeichen lang sein.")
            else:
                if change_password(st.session_state.user_id, new_password):
                    st.success("Passwort erfolgreich geändert!")
                else:
                    st.error("Fehler beim Ändern des Passworts.")


def show_benachrichtigungen_widget():
    """Zeigt Widget mit ungelesenen Benachrichtigungen und Änderungsanfragen"""
    from utils.notifications import (
        get_ungelesene_benachrichtigungen,
        markiere_benachrichtigung_gelesen,
        get_pending_aenderungsanfragen,
        approve_aenderungsanfrage,
        reject_aenderungsanfrage
    )
    
    # Lade Benachrichtigungen und Änderungsanfragen
    benachrichtigungen = get_ungelesene_benachrichtigungen()
    aenderungsanfragen = get_pending_aenderungsanfragen()
    
    total_notifications = len(benachrichtigungen) + len(aenderungsanfragen)
    
    if total_notifications > 0:
        st.markdown(f"""
        <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 1rem; margin-bottom: 1.5rem; border-radius: 5px;">
            <strong>🔔 {total_notifications} neue Benachrichtigung(en)</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Expander für Benachrichtigungen
        if benachrichtigungen:
            with st.expander(f"📬 {len(benachrichtigungen)} Benachrichtigungen", expanded=True):
                for notif in benachrichtigungen:
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        mitarbeiter_info = notif.get('mitarbeiter', {})
                        st.markdown(f"""
                        **{mitarbeiter_info.get('vorname', '')} {mitarbeiter_info.get('nachname', '')} (#{mitarbeiter_info.get('personalnummer', '')})**  
                        {notif['nachricht']}  
                        <small>{notif['erstellt_am'][:16]}</small>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("✓", key=f"mark_read_{notif['id']}", help="Als gelesen markieren"):
                            markiere_benachrichtigung_gelesen(notif['id'])
                            st.rerun()
                    
                    st.markdown("---")
        
        # Expander für Änderungsanfragen
        if aenderungsanfragen:
            with st.expander(f"✋ {len(aenderungsanfragen)} Änderungsanfragen", expanded=True):
                for anfrage in aenderungsanfragen:
                    mitarbeiter_info = anfrage.get('mitarbeiter', {})
                    
                    st.markdown(f"""
                    **{mitarbeiter_info.get('vorname', '')} {mitarbeiter_info.get('nachname', '')} (#{mitarbeiter_info.get('personalnummer', '')})**  
                    Feld: **{anfrage['feld']}**  
                    Alt: `{anfrage['alter_wert']}` → Neu: `{anfrage['neuer_wert']}`  
                    Grund: {anfrage.get('grund', 'Nicht angegeben')}  
                    <small>{anfrage['erstellt_am'][:16]}</small>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("✅ Genehmigen", key=f"approve_{anfrage['id']}", use_container_width=True):
                            if approve_aenderungsanfrage(anfrage['id'], st.session_state.user_id):
                                st.success("Änderung genehmigt!")
                                st.rerun()
                            else:
                                st.error("Fehler beim Genehmigen")
                    
                    with col2:
                        if st.button("❌ Ablehnen", key=f"reject_{anfrage['id']}", use_container_width=True):
                            if reject_aenderungsanfrage(anfrage['id'], st.session_state.user_id):
                                st.info("Änderung abgelehnt")
                                st.rerun()
                            else:
                                st.error("Fehler beim Ablehnen")
                    
                    st.markdown("---")
    else:
        st.success("✅ Keine neuen Benachrichtigungen")


def show_plauderecke_admin():
    """Zeigt die Plauderecke für Administrator an"""
    from utils.chat import get_chat_nachrichten, send_chat_nachricht, delete_chat_nachricht
    from utils.chat_notifications import mark_chat_as_read
    
    # Markiere Chat als gelesen
    mark_chat_as_read(st.session_state.user_id)
    
    st.subheader("💬 Plauderecke")
    st.caption("Interner Chat für alle Mitarbeiter und Administrator")
    
    # Lade Chat-Nachrichten
    nachrichten = get_chat_nachrichten(limit=100, betrieb_id=st.session_state.betrieb_id)
    
    # Chat-Container
    chat_container = st.container()
    
    with chat_container:
        if nachrichten:
            for msg in nachrichten:
                # Hole Mitarbeiter-Info
                mitarbeiter_info = msg.get('mitarbeiter', {})
                if mitarbeiter_info:
                    vorname = mitarbeiter_info.get('vorname', 'Administrator')
                    nachname = mitarbeiter_info.get('nachname', '')
                else:
                    vorname = "Administrator"
                    nachname = ""
                
                # Eigene Nachricht?
                is_own = msg['user_id'] == st.session_state.user_id
                
                # Zeitstempel formatieren
                timestamp = msg['erstellt_am'][:16].replace('T', ' ')
                
                if is_own:
                    # Eigene Nachricht rechts
                    col1, col2 = st.columns([1, 3])
                    with col2:
                        st.markdown(f"""
                        <div style="background-color: #198754; padding: 0.75rem; border-radius: 10px; margin-bottom: 0.5rem; text-align: right;">
                            <strong style="color: #ffffff;">Sie (Admin)</strong><br>
                            <span style="color: #ffffff;">{msg['nachricht']}</span><br>
                            <small style="color: #e0e0e0;">{timestamp}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("🗑️", key=f"delete_admin_{msg['id']}", help="Nachricht löschen"):
                            if delete_chat_nachricht(msg['id'], st.session_state.user_id):
                                st.rerun()
                else:
                    # Andere Nachricht links
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                        <div style="background-color: #e9ecef; padding: 0.75rem; border-radius: 10px; margin-bottom: 0.5rem; border: 1px solid #dee2e6;">
                            <strong style="color: #212529;">{vorname} {nachname}</strong><br>
                            <span style="color: #212529;">{msg['nachricht']}</span><br>
                            <small style="color: #6c757d;">{timestamp}</small>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("Noch keine Nachrichten in der Plauderecke.")
    
    st.markdown("---")
    
    # Nachricht senden
    with st.form("send_message_form_admin", clear_on_submit=True):
        nachricht = st.text_area("Nachricht schreiben", placeholder="Ihre Nachricht an das Team...", height=100)
        submit = st.form_submit_button("📤 Senden", use_container_width=True)
        
        if submit and nachricht.strip():
            if send_chat_nachricht(st.session_state.user_id, nachricht.strip(), st.session_state.betrieb_id):
                st.success("✅ Nachricht gesendet!")
                st.rerun()
            else:
                st.error("Fehler beim Senden der Nachricht.")


def show_urlaubskalender_admin():
    """Zeigt Urlaubskalender aller Mitarbeiter an (Admin-Ansicht) - JAHRESÜBERSICHT"""
    st.markdown('<div class="section-header">📅 Urlaubskalender - Jahresübersicht</div>', unsafe_allow_html=True)
    
    st.info("ℹ️ Jahresübersicht aller genehmigten Urlaube. Hilft bei der Personalplanung und Dienstplan-Erstellung.")
    
    # Nur Jahr-Auswahl (keine Monatsauswahl mehr)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        heute = date.today()
        jahr = st.selectbox("Jahr", range(heute.year - 1, heute.year + 3), index=1, key="admin_jahr")
    
    with col2:
        st.markdown(f"### 📆 Urlaubsübersicht für das Jahr {jahr}")
    
    # Lade Urlaube für das gesamte Jahr
    supabase = get_supabase_client()
    
    # Berechne Start- und Enddatum des Jahres
    erster_tag = date(jahr, 1, 1)
    letzter_tag = date(jahr, 12, 31)
    
    try:
        # Lade ALLE genehmigten Urlaubsanträge für das gesamte Jahr
        urlaube_response = supabase.table('urlaubsantraege').select(
            'id, mitarbeiter_id, von_datum, bis_datum, status, grund, mitarbeiter(vorname, nachname)'
        ).gte('bis_datum', str(erster_tag)).lte('von_datum', str(letzter_tag)).eq('status', 'Genehmigt').execute()
        
        if not urlaube_response.data:
            st.info(f"📬 Keine genehmigten Urlaube im Jahr {jahr}")
            return
        
        # Erstelle Kalender-Ansicht
        st.markdown("---")
        
        # Gruppiere Urlaube nach Mitarbeiter
        urlaube_nach_mitarbeiter = {}
        for urlaub in urlaube_response.data:
            mitarbeiter_name = f"{urlaub['mitarbeiter']['vorname']} {urlaub['mitarbeiter']['nachname']}"
            if mitarbeiter_name not in urlaube_nach_mitarbeiter:
                urlaube_nach_mitarbeiter[mitarbeiter_name] = []
            urlaube_nach_mitarbeiter[mitarbeiter_name].append(urlaub)
        
        # Zeige Urlaube nach Mitarbeiter
        for mitarbeiter_name in sorted(urlaube_nach_mitarbeiter.keys()):
            with st.expander(f"👤 {mitarbeiter_name}", expanded=True):
                for urlaub in urlaube_nach_mitarbeiter[mitarbeiter_name]:
                    von = datetime.strptime(urlaub['von_datum'], '%Y-%m-%d').date()
                    bis = datetime.strptime(urlaub['bis_datum'], '%Y-%m-%d').date()
                    
                    # Berechne Anzahl Tage
                    tage = (bis - von).days + 1
                    
                    # Formatiere Datum
                    von_str = von.strftime('%d.%m.%Y')
                    bis_str = bis.strftime('%d.%m.%Y')
                    
                    # Status-Badge
                    if urlaub['status'] == 'Genehmigt':
                        status_badge = "✅ Genehmigt"
                        status_color = "green"
                    elif urlaub['status'] == 'Abgelehnt':
                        status_badge = "❌ Abgelehnt"
                        status_color = "red"
                    else:
                        status_badge = "⏳ Ausstehend"
                        status_color = "orange"
                    
                    # Zeige Urlaub
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                    with col1:
                        st.write(f"📅 **Von:** {von_str}")
                    with col2:
                        st.write(f"📅 **Bis:** {bis_str}")
                    with col3:
                        st.write(f"🗓️ **{tage} Tag{'e' if tage != 1 else ''}**")
                    with col4:
                        st.markdown(f"<span style='color: {status_color};'>{status_badge}</span>", unsafe_allow_html=True)
                    
                    if urlaub.get('grund'):
                        st.caption(f"💬 Grund: {urlaub['grund']}")
                    
                    st.markdown("---")
        
        # Statistik
        st.markdown("### 📊 Statistik")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Mitarbeiter im Urlaub", len(urlaube_nach_mitarbeiter))
        
        with col2:
            gesamt_tage = sum([
                (datetime.strptime(u['bis_datum'], '%Y-%m-%d').date() - 
                 datetime.strptime(u['von_datum'], '%Y-%m-%d').date()).days + 1
                for urlaube in urlaube_nach_mitarbeiter.values()
                for u in urlaube
            ])
            st.metric("Gesamt Urlaubstage", gesamt_tage)
        
        with col3:
            genehmigt_count = len([u for urlaube in urlaube_nach_mitarbeiter.values() for u in urlaube if u['status'] == 'Genehmigt'])
            st.metric("Genehmigte Anträge", genehmigt_count)
        
        # Jahres-Kalender-Ansicht (12 Monate)
        st.markdown("---")
        st.markdown("### 📆 Jahreskalender-Ansicht")
        
        import calendar
        
        monate = [
            "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember"
        ]
        
        # Zeige 12 Monate in 3 Spalten
        for quartal in range(4):  # 4 Quartale
            cols = st.columns(3)
            for i in range(3):
                monat_nr = quartal * 3 + i + 1
                if monat_nr <= 12:
                    with cols[i]:
                        st.markdown(f"**{monate[monat_nr-1]} {jahr}**")
                        
                        # Erstelle Monatskalender
                        cal = calendar.monthcalendar(jahr, monat_nr)
                        wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
                        
                        html = '<table style="width:100%; border-collapse: collapse; font-size: 0.8rem;">'
                        html += '<tr>' + ''.join([f'<th style="border: 1px solid #ddd; padding: 4px; text-align: center; background-color: #1e3a5f; color: white;">{tag}</th>' for tag in wochentage]) + '</tr>'
                        
                        for woche in cal:
                            html += '<tr>'
                            for tag in woche:
                                if tag == 0:
                                    html += '<td style="border: 1px solid #ddd; padding: 4px;"></td>'
                                else:
                                    aktuelles_datum = date(jahr, monat_nr, tag)
                                    
                                    # Prüfe ob an diesem Tag jemand im Urlaub ist
                                    urlaub_heute = []
                                    for urlaub in urlaube_response.data:
                                        von = datetime.strptime(urlaub['von_datum'], '%Y-%m-%d').date()
                                        bis = datetime.strptime(urlaub['bis_datum'], '%Y-%m-%d').date()
                                        if von <= aktuelles_datum <= bis:
                                            urlaub_heute.append(f"{urlaub['mitarbeiter']['vorname']} {urlaub['mitarbeiter']['nachname']}")
                                    
                                    # Färbe Zelle wenn Urlaub
                                    if urlaub_heute:
                                        if len(urlaub_heute) >= 3:
                                            bg_color = '#ff9800'  # Orange
                                        else:
                                            bg_color = '#ffeb3b'  # Gelb
                                        title = f"{len(urlaub_heute)} im Urlaub: {', '.join(urlaub_heute)}"
                                        html += f'<td style="border: 1px solid #ddd; padding: 4px; background-color: {bg_color}; text-align: center;" title="{title}"><strong>{tag}</strong></td>'
                                    else:
                                        html += f'<td style="border: 1px solid #ddd; padding: 4px; text-align: center;">{tag}</td>'
                            html += '</tr>'
                        
                        html += '</table>'
                        st.markdown(html, unsafe_allow_html=True)
        
        st.caption("💡 Tipp: Gelb = 1-2 Mitarbeiter im Urlaub | Orange = 3+ Mitarbeiter im Urlaub. Fahre mit der Maus über die Zelle für Details.")
        st.markdown("---")
        
        # Export-Funktion
        st.markdown("---")
        if st.button("📥 Urlaubsplan als CSV exportieren"):
            import io
            
            # Erstelle CSV
            csv_data = "Mitarbeiter,Von,Bis,Tage,Status,Grund\n"
            for mitarbeiter_name in sorted(urlaube_nach_mitarbeiter.keys()):
                for urlaub in urlaube_nach_mitarbeiter[mitarbeiter_name]:
                    von = datetime.strptime(urlaub['von_datum'], '%Y-%m-%d').date().strftime('%d.%m.%Y')
                    bis = datetime.strptime(urlaub['bis_datum'], '%Y-%m-%d').date().strftime('%d.%m.%Y')
                    tage = (datetime.strptime(urlaub['bis_datum'], '%Y-%m-%d').date() - 
                           datetime.strptime(urlaub['von_datum'], '%Y-%m-%d').date()).days + 1
                    grund = urlaub.get('grund', '').replace(',', ';')  # Kommas ersetzen
                    csv_data += f"{mitarbeiter_name},{von},{bis},{tage},{urlaub['status']},{grund}\n"
            
            st.download_button(
                label="💾 CSV herunterladen",
                data=csv_data,
                file_name=f"urlaubsplan_{jahr}.csv",
                mime="text/csv"
            )
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Urlaube: {str(e)}")
