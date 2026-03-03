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
    berechne_arbeitsstunden,
    parse_zeit
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
    
    # Tab-Navigation mit einheitlichen Icons (konsolidiert)
    tabs = st.tabs([
        f"{get_icon('dashboard')} Übersicht",
        f"{get_icon('mitarbeiter')} Mitarbeiterverwaltung",
        f"{get_icon('dienstplan')} Dienstplanung",
        f"{get_icon('urlaub')} Urlaubsgenehmigung",
        f"{get_icon('dienstplan')} Urlaubskalender",
        f"{get_icon('chat')} Plauderecke{chat_badge}",
        f"⏱️ Lohn & Zeiten",
        f"{get_icon('mastergeraete')} Mastergärate",
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
        show_lohn_und_zeiten_konsolidiert()
    
    with tabs[7]:
        from pages.admin_mastergeraete import show_mastergeraete
        show_mastergeraete()
    
    with tabs[8]:
        show_einstellungen()


def show_lohn_und_zeiten_konsolidiert():
    """Konsolidierter Tab: Zeiterfassung + Zeitauswertung + Lohnabrechnung in einem"""
    
    st.markdown('<div class="section-header">⏱️ Lohn & Zeiten</div>', unsafe_allow_html=True)
    
    # Sub-Navigation mit Selectbox
    sub_bereich = st.selectbox(
        "Bereich wählen:",
        [
            "📅 Zeiterfassung – Tagesbuchungen & Korrekturen",
            "📊 Zeitauswertung & Zuschlagsberechnung",
            "💰 Lohnabrechnung & Steuerberater-Export",
            "📜 Audit-Log – Änderungsprotokoll"
        ],
        key="lohn_zeiten_sub"
    )
    
    st.markdown("---")
    
    if sub_bereich.startswith("📅"):
        show_zeiterfassung_admin()
    
    elif sub_bereich.startswith("📊"):
        from pages.zeitauswertung import show_zeitauswertung
        admin_ma = st.session_state.get('mitarbeiter_data', {})
        show_zeitauswertung(admin_ma, admin_modus=True)
    
    elif sub_bereich.startswith("💰"):
        show_lohnabrechnung()
    
    elif sub_bereich.startswith("📜"):
        show_audit_log_admin()


def show_audit_log_admin():
    """Zeigt das Audit-Log für Admins an"""
    st.markdown("### 📜 Änderungsprotokoll (Audit-Log)")
    st.info("ℹ️ Dieses Protokoll ist unveränderlich und dokumentiert alle manuellen Korrekturen durch Admins (DSGVO-konform).")
    
    try:
        from utils.audit_log import get_audit_log
        from utils.database import get_supabase_client
        supabase = get_supabase_client()
        
        betrieb_id = st.session_state.get('betrieb_id')
        
        # Filter-Optionen
        col1, col2 = st.columns(2)
        with col1:
            # Mitarbeiter-Filter
            ma_response = supabase.table('mitarbeiter').select('id, vorname, nachname').execute()
            ma_liste = [('Alle', None)] + [(f"{m['vorname']} {m['nachname']}", m['id']) for m in (ma_response.data or [])]
            ma_auswahl = st.selectbox("Mitarbeiter filtern:", [m[0] for m in ma_liste], key="audit_ma_filter")
            ma_id_filter = next((m[1] for m in ma_liste if m[0] == ma_auswahl), None)
        with col2:
            limit = st.selectbox("Einträge anzeigen:", [25, 50, 100, 200], index=0, key="audit_limit")
        
        eintraege = get_audit_log(betrieb_id=betrieb_id, mitarbeiter_id=ma_id_filter, limit=limit)
        
        if not eintraege:
            st.info("📢 Noch keine Audit-Einträge vorhanden.")
            return
        
        st.markdown(f"**{len(eintraege)} Einträge gefunden**")
        
        for eintrag in eintraege:
            zeitstempel = eintrag.get('erstellt_am', '')[:19].replace('T', ' ')
            aktion = eintrag.get('aktion', '').replace('_', ' ').title()
            admin = eintrag.get('admin_name', 'Unbekannt')
            mitarbeiter = eintrag.get('mitarbeiter_name', 'Unbekannt')
            begruendung = eintrag.get('begruendung', '-')
            
            # Farbe je nach Aktion
            if 'loeschung' in eintrag.get('aktion', ''):
                farbe = '#9b2c2c'
                icon = '🗑️'
            elif 'korrektur' in eintrag.get('aktion', ''):
                farbe = '#b7791f'
                icon = '✏️'
            else:
                farbe = '#2c5282'
                icon = '📝'
            
            st.markdown(f"""
            <div style="border-left: 4px solid {farbe}; padding: 0.75rem 1rem; margin: 0.5rem 0;
                        background: #f8f9fa; border-radius: 0 8px 8px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; color: {farbe};">{icon} {aktion}</span>
                    <span style="font-size: 0.8rem; color: #6c757d;">{zeitstempel}</span>
                </div>
                <div style="margin-top: 0.3rem; font-size: 0.9rem;">
                    <strong>Admin:</strong> {admin} &nbsp;&nbsp;
                    <strong>Mitarbeiter:</strong> {mitarbeiter}
                </div>
                <div style="margin-top: 0.2rem; font-size: 0.85rem; color: #495057;">
                    <strong>Begründung:</strong> {begruendung}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Fehler beim Laden des Audit-Logs: {e}")


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
                                try:
                                    # 1) Status auf 'genehmigt' (lowercase!) setzen
                                    supabase.table('urlaubsantraege').update({
                                        'status': 'genehmigt',
                                        'bearbeitet_am': datetime.now().isoformat(),
                                        'bearbeitet_von': st.session_state.user_id
                                    }).eq('id', antrag['id']).execute()
                                    
                                    # 2) Resturlaub automatisch abziehen
                                    anzahl_tage = float(antrag.get('anzahl_tage') or 0)
                                    if anzahl_tage > 0:
                                        ma_id = antrag['mitarbeiter_id']
                                        ma_resp = supabase.table('mitarbeiter').select(
                                            'id, jahres_urlaubstage, resturlaub_vorjahr'
                                        ).eq('id', ma_id).execute()
                                        if ma_resp.data:
                                            ma_d = ma_resp.data[0]
                                            jahres = float(ma_d.get('jahres_urlaubstage') or 28)
                                            rest = float(ma_d.get('resturlaub_vorjahr') or 0)
                                            bereits_resp = supabase.table('urlaubsantraege').select(
                                                'anzahl_tage'
                                            ).eq('mitarbeiter_id', ma_id).eq('status', 'genehmigt').neq(
                                                'id', antrag['id']
                                            ).execute()
                                            bereits = sum(float(a.get('anzahl_tage') or 0) for a in (bereits_resp.data or []))
                                            neuer_rest = round(jahres + rest - bereits - anzahl_tage, 1)
                                            supabase.table('mitarbeiter').update({
                                                'resturlaub_vorjahr': max(0, neuer_rest)
                                            }).eq('id', ma_id).execute()
                                    
                                    # 3) Benachrichtigung für Mitarbeiter
                                    mitarbeiter_user = supabase.table('mitarbeiter').select('user_id').eq('id', antrag['mitarbeiter_id']).execute()
                                    if mitarbeiter_user.data:
                                        supabase.table('benachrichtigungen').insert({
                                            'user_id': mitarbeiter_user.data[0]['user_id'],
                                            'typ': 'urlaubsantrag',
                                            'titel': 'Urlaubsantrag genehmigt',
                                            'nachricht': f"Ihr Urlaubsantrag vom {antrag['von_datum']} bis {antrag['bis_datum']} wurde genehmigt.",
                                            'gelesen': False,
                                            'betrieb_id': st.session_state.betrieb_id
                                        }).execute()
                                    
                                    st.success(f"✅ Genehmigt! {anzahl_tage:.1f} Urlaubstage abgezogen.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler bei Genehmigung: {str(e)}")
                        
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
        format_func=lambda x: f"{x['vorname']} {x['nachname']} ({x['personalnummer']})",
        key="mitarbeiter_details_select"
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
            
            BESCHAEFTIGUNGSARTEN = {
                'vollzeit': 'Vollzeit',
                'teilzeit': 'Teilzeit',
                'minijob': '💼 Minijob (geringfügig)',
                'werkstudent': 'Werkstudent',
                'azubi': 'Auszubildende/r',
            }
            beschaeftigungsart_optionen = list(BESCHAEFTIGUNGSARTEN.keys())
            aktuell = (mitarbeiter_data.get('beschaeftigungsart') or 'vollzeit') if is_edit else 'vollzeit'
            if aktuell not in beschaeftigungsart_optionen:
                aktuell = 'vollzeit'
            beschaeftigungsart = st.selectbox(
                "Beschäftigungsart",
                options=beschaeftigungsart_optionen,
                format_func=lambda x: BESCHAEFTIGUNGSARTEN[x],
                index=beschaeftigungsart_optionen.index(aktuell)
            )
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Lohnparameter**")
            monatliche_soll_stunden = st.number_input(
                "Monatliche Soll-Stunden*",
                min_value=0.0,
                max_value=250.0,
                value=float(mitarbeiter_data.get('monatliche_soll_stunden') or 160.0) if is_edit else 160.0,
                step=0.5
            )
            stundenlohn_brutto = st.number_input(
                "Stundenlohn (brutto)*",
                min_value=0.0,
                max_value=100.0,
                value=float(mitarbeiter_data.get('stundenlohn_brutto') or 15.0) if is_edit else 15.0,
                step=0.10,
                format="%.2f"
            )
            
            # Minijob-Grenze (nur sichtbar wenn Minijob gewählt)
            # Wir lesen beschaeftigungsart aus dem aktuellen Formularwert
            # Da Streamlit-Widgets sequenziell sind, nutzen wir den gespeicherten Wert
            _ist_minijob = (mitarbeiter_data.get('beschaeftigungsart') == 'minijob') if is_edit else False
            minijob_monatsgrenze = st.number_input(
                "💼 Minijob-Monatsgrenze (€)",
                min_value=0.0,
                max_value=1000.0,
                value=float(mitarbeiter_data.get('minijob_monatsgrenze') or 556.0) if is_edit else 556.0,
                step=1.0,
                format="%.2f",
                help="Aktuelle Minijob-Grenze: 556,00 €/Monat (2025). \nBei Überschreitung wird eine Warnung in der Lohnabrechnung angezeigt."
            )
        
        with col2:
            st.markdown("**Urlaub**")
            jahres_urlaubstage = st.number_input(
                "Jährliche Urlaubstage*",
                min_value=20,
                max_value=50,
                value=int(mitarbeiter_data.get('jahres_urlaubstage') or 28) if is_edit else 28
            )
            resturlaub_vorjahr = st.number_input(
                "Resturlaub Vorjahr",
                min_value=0.0,
                max_value=50.0,
                value=float(mitarbeiter_data.get('resturlaub_vorjahr') or 0.0) if is_edit else 0.0,
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
                'mobile_zeiterfassung': mobile_zeiterfassung,
                'beschaeftigungsart': beschaeftigungsart,
                'minijob_monatsgrenze': minijob_monatsgrenze if beschaeftigungsart == 'minijob' else None,
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
        
        # Beschäftigungsart
        BESCHAEFTIGUNGSARTEN_LABEL = {
            'vollzeit': 'Vollzeit',
            'teilzeit': 'Teilzeit',
            'minijob': '💼 Minijob (geringfügig)',
            'werkstudent': 'Werkstudent',
            'azubi': 'Auszubildende/r',
        }
        art = mitarbeiter.get('beschaeftigungsart', 'vollzeit') or 'vollzeit'
        st.write(f"**Beschäftigungsart:** {BESCHAEFTIGUNGSARTEN_LABEL.get(art, art.capitalize())}")
        
        if art == 'minijob':
            grenze = mitarbeiter.get('minijob_monatsgrenze') or 556.0
            st.write(f"**Minijob-Monatsgrenze:** {grenze:.2f} €")
        
        st.markdown("**Zuschäge**")
        st.write(f"Sonntagszuschlag: {'✅ Aktiv' if mitarbeiter['sonntagszuschlag_aktiv'] else '❌ Inaktiv'}")
        st.write(f"Feiertagszuschlag: {'✅ Aktiv' if mitarbeiter['feiertagszuschlag_aktiv'] else '❌ Inaktiv'}")
    
    
    st.markdown("---")
    
    # Arbeitsvertrag Upload/Download
    st.markdown("**📄 Arbeitsvertrag**")
    
    # Zeige aktuellen Status
    if mitarbeiter.get('vertrag_pdf_path'):
        st.success("✅ Arbeitsvertrag ist hinterlegt.")
        
        # Download-Button für Admin
        col_download, col_delete = st.columns(2)
        
        with col_download:
            try:
                pdf_data = download_file_from_storage('arbeitsvertraege', mitarbeiter['vertrag_pdf_path'])
                if pdf_data:
                    st.download_button(
                        label="📥 Vertrag herunterladen",
                        data=pdf_data,
                        file_name=f"Arbeitsvertrag_{mitarbeiter['personalnummer']}.pdf",
                        mime="application/pdf",
                        key=f"download_vertrag_admin_{mitarbeiter['id']}",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Fehler beim Laden: {str(e)}")
        
        with col_delete:
            if st.button("🗑️ Vertrag löschen", key=f"delete_vertrag_{mitarbeiter['id']}", use_container_width=True):
                try:
                    # Lösche aus Storage
                    supabase = get_supabase_client()
                    supabase.storage.from_('arbeitsvertraege').remove([mitarbeiter['vertrag_pdf_path']])
                    
                    # Update Mitarbeiter
                    supabase.table('mitarbeiter').update({
                        'vertrag_pdf_path': None
                    }).eq('id', mitarbeiter['id']).execute()
                    
                    st.success("✅ Vertrag gelöscht!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {str(e)}")
    else:
        st.info("Noch kein Arbeitsvertrag hinterlegt.")
    
    # Upload-Formular
    vertrag_file = st.file_uploader(
        "Neuen Arbeitsvertrag hochladen (PDF)",
        type=['pdf'],
        key=f"vertrag_upload_{mitarbeiter['id']}"
    )
    
    if vertrag_file:
        if st.button("📤 Vertrag hochladen", key=f"upload_vertrag_btn_{mitarbeiter['id']}", use_container_width=True):
            try:
                # Erstelle eindeutigen Dateinamen
                file_path = f"{mitarbeiter['personalnummer']}/arbeitsvertrag.pdf"
                
                # Upload zu Storage
                success = upload_file_to_storage(
                    'arbeitsvertraege',
                    file_path,
                    vertrag_file.getvalue()
                )
                
                if success:
                    # Update Mitarbeiter-Datensatz
                    supabase = get_supabase_client()
                    try:
                        supabase.table('mitarbeiter').update({
                            'vertrag_pdf_path': file_path
                        }).eq('id', mitarbeiter['id']).execute()
                        st.success("✅ Arbeitsvertrag erfolgreich hochgeladen!")
                        st.rerun()
                    except Exception as db_err:
                        err_msg = str(db_err)
                        if 'vertrag_pdf_path' in err_msg or 'PGRST204' in err_msg:
                            st.warning("⚠️ Datei hochgeladen, aber Datenbankfeld fehlt noch. Bitte Migration ausführen (siehe unten).")
                            st.code("ALTER TABLE mitarbeiter ADD COLUMN IF NOT EXISTS vertrag_pdf_path TEXT DEFAULT NULL;", language='sql')
                        else:
                            st.error(f"Datenbankfehler: {err_msg}")
                else:
                    st.error("Fehler beim Hochladen des Vertrags.")
            except Exception as e:
                st.error(f"Fehler: {str(e)}")
    
    st.markdown("---")
    
    # ── Stempeluhr-PIN verwalten ──────────────────────────────────────────────
    st.markdown("**🔢 Stempeluhr-PIN**")
    
    supabase_pin = get_supabase_client()
    try:
        pin_result = supabase_pin.table('mitarbeiter').select('stempel_pin').eq('id', mitarbeiter['id']).execute()
        aktueller_pin = pin_result.data[0].get('stempel_pin') if pin_result.data else None
    except Exception:
        aktueller_pin = None
    
    if aktueller_pin:
        st.success(f"✅ PIN ist gesetzt (●●●●)")
    else:
        st.warning("⚠️ Noch kein Stempeluhr-PIN gesetzt")
    
    with st.form(f"pin_form_{mitarbeiter['id']}"):
        col_pin1, col_pin2 = st.columns(2)
        with col_pin1:
            neuer_pin = st.text_input(
                "Neuer PIN (4 Ziffern)",
                max_chars=4,
                type="password",
                placeholder="z.B. 1234",
                help="Genau 4 Ziffern, nur Zahlen"
            )
        with col_pin2:
            pin_bestaetigung = st.text_input(
                "PIN bestätigen",
                max_chars=4,
                type="password",
                placeholder="PIN wiederholen"
            )
        
        col_save_pin, col_del_pin = st.columns(2)
        with col_save_pin:
            pin_speichern = st.form_submit_button("💾 PIN speichern", use_container_width=True)
        with col_del_pin:
            pin_loeschen = st.form_submit_button("🗑️ PIN löschen", use_container_width=True)
        
        if pin_speichern:
            if not neuer_pin or not neuer_pin.isdigit() or len(neuer_pin) != 4:
                st.error("❌ PIN muss genau 4 Ziffern enthalten.")
            elif neuer_pin != pin_bestaetigung:
                st.error("❌ PINs stimmen nicht überein.")
            else:
                try:
                    supabase_pin.table('mitarbeiter').update({'stempel_pin': neuer_pin}).eq('id', mitarbeiter['id']).execute()
                    st.success("✅ PIN erfolgreich gesetzt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
        
        if pin_loeschen:
            try:
                supabase_pin.table('mitarbeiter').update({'stempel_pin': None}).eq('id', mitarbeiter['id']).execute()
                st.success("✅ PIN gelöscht.")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Löschen: {e}")
    
    st.markdown("---")
    
    # Bearbeiten und Löschen-Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✏️ Mitarbeiter bearbeiten", key=f"edit_{mitarbeiter['id']}", use_container_width=True):
            st.session_state.edit_mitarbeiter_id = mitarbeiter['id']
            st.session_state.show_mitarbeiter_form = True
            st.rerun()
    
    with col2:
        # Eindeutiger Key für Bestätigungsflag
        confirm_key = f"confirm_delete_ma_{mitarbeiter['id']}"
        
        # Zeige Bestätigungsbutton wenn Bestätigung aussteht
        if st.session_state.get(confirm_key, False):
            col_cancel, col_confirm = st.columns(2)
            with col_cancel:
                if st.button("❌ Abbrechen", key=f"cancel_delete_{mitarbeiter['id']}", use_container_width=True):
                    st.session_state[confirm_key] = False
                    st.rerun()
            with col_confirm:
                if st.button("✅ Bestätigen", key=f"confirm_delete_{mitarbeiter['id']}", use_container_width=True, type="primary"):
                    # Lösche Mitarbeiter
                    try:
                        from utils.database import delete_mitarbeiter
                        
                        if delete_mitarbeiter(mitarbeiter['id']):
                            st.success(f"✅ Mitarbeiter {mitarbeiter['vorname']} {mitarbeiter['nachname']} gelöscht!")
                            st.session_state[confirm_key] = False
                            st.rerun()
                        else:
                            st.error("Fehler beim Löschen des Mitarbeiters.")
                            st.session_state[confirm_key] = False
                    except Exception as e:
                        st.error(f"Fehler: {str(e)}")
                        st.session_state[confirm_key] = False
        else:
            # Zeige Löschen-Button
            if st.button("🗑️ Mitarbeiter löschen", key=f"delete_{mitarbeiter['id']}", use_container_width=True, type="secondary"):
                st.session_state[confirm_key] = True
                st.rerun()
    



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
            index=0,  # Standard: "Alle"
            key="urlaub_status_filter"
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
                            try:
                                # 1) Antrag auf 'genehmigt' setzen
                                supabase.table('urlaubsantraege').update({
                                    'status': 'genehmigt',
                                    'bemerkung_admin': bemerkung_admin,
                                    'bearbeitet_am': datetime.now().isoformat(),
                                    'bearbeitet_von': st.session_state.user_id
                                }).eq('id', antrag['id']).execute()
                                
                                # 2) Resturlaub des Mitarbeiters um anzahl_tage verringern
                                anzahl_tage = float(antrag.get('anzahl_tage') or 0)
                                if anzahl_tage > 0:
                                    ma_id = antrag['mitarbeiter_id']
                                    # Aktuellen Resturlaub laden
                                    ma_resp = supabase.table('mitarbeiter').select(
                                        'id, jahres_urlaubstage, resturlaub_vorjahr'
                                    ).eq('id', ma_id).execute()
                                    
                                    if ma_resp.data:
                                        ma_data = ma_resp.data[0]
                                        jahres = float(ma_data.get('jahres_urlaubstage') or 28)
                                        rest_vorjahr = float(ma_data.get('resturlaub_vorjahr') or 0)
                                        
                                        # Bereits genehmigte Tage in diesem Jahr summieren
                                        bereits_genehmigt_resp = supabase.table('urlaubsantraege').select(
                                            'anzahl_tage'
                                        ).eq('mitarbeiter_id', ma_id).eq('status', 'genehmigt').neq(
                                            'id', antrag['id']
                                        ).execute()
                                        
                                        bereits_tage = sum(
                                            float(a.get('anzahl_tage') or 0)
                                            for a in (bereits_genehmigt_resp.data or [])
                                        )
                                        
                                        # Resturlaub = Jahresanspruch + Vorjahresrest - bereits genehmigte Tage - neue Tage
                                        gesamt_anspruch = jahres + rest_vorjahr
                                        neuer_rest = round(gesamt_anspruch - bereits_tage - anzahl_tage, 1)
                                        
                                        if neuer_rest < 0:
                                            st.warning(
                                                f"⚠️ Achtung: Urlaubsanspruch ({gesamt_anspruch:.1f} Tage) wird "
                                                f"um {abs(neuer_rest):.1f} Tage überschritten!"
                                            )
                                        
                                        # Resturlaub aktualisieren
                                        supabase.table('mitarbeiter').update({
                                            'resturlaub_vorjahr': max(0, neuer_rest)
                                        }).eq('id', ma_id).execute()
                                
                                # 3) E-Mail an Mitarbeiter senden
                                try:
                                    from utils.email_service import send_urlaubsgenehmigung_email
                                    ma_email = mitarbeiter.get('email')
                                    ma_name = f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}"
                                    if ma_email:
                                        send_urlaubsgenehmigung_email(
                                            ma_email, ma_name, 'genehmigt',
                                            antrag['von_datum'], antrag['bis_datum'],
                                            antrag.get('anzahl_tage'),
                                            bemerkung_admin
                                        )
                                except Exception as mail_err:
                                    pass  # E-Mail-Fehler soll App nicht blockieren
                                
                                st.success(
                                    f"✅ Urlaubsantrag genehmigt! "
                                    f"{anzahl_tage:.1f} Urlaubstage wurden vom Resturlaub abgezogen."
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler bei der Urlaubsgenehmigung: {str(e)}")
                    
                    with col2:
                        if st.button("❌ Ablehnen", key=f"reject_{antrag['id']}", use_container_width=True):
                            # Aktualisiere Antrag
                            supabase.table('urlaubsantraege').update({
                                'status': 'abgelehnt',
                                'bemerkung_admin': bemerkung_admin,
                                'bearbeitet_am': datetime.now().isoformat(),
                                'bearbeitet_von': st.session_state.user_id
                            }).eq('id', antrag['id']).execute()
                            
                            # E-Mail an Mitarbeiter senden
                            try:
                                from utils.email_service import send_urlaubsgenehmigung_email
                                ma_email = mitarbeiter.get('email')
                                ma_name = f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}"
                                if ma_email:
                                    send_urlaubsgenehmigung_email(
                                        ma_email, ma_name, 'abgelehnt',
                                        antrag['von_datum'], antrag['bis_datum'],
                                        antrag.get('anzahl_tage'),
                                        bemerkung_admin
                                    )
                            except Exception as mail_err:
                                pass  # E-Mail-Fehler soll App nicht blockieren
                            
                            st.warning("❌ Urlaubsantrag abgelehnt! Mitarbeiter wurde per E-Mail informiert.")
                            st.rerun()
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Urlaubsanträge: {str(e)}")


def show_zeiterfassung_admin():
    """Zeigt die Zeiterfassung für alle Mitarbeiter an"""
    
    st.subheader("⏰ Zeiterfassung (Übersicht & Korrektur)")
    
    # ══════════════════════════════════════════════════════════════
    # MANUELLER ZEITEINTRAG (Admin-Override)
    # ══════════════════════════════════════════════════════════════
    with st.expander("✏️ ➕ Zeiteintrag manuell anlegen (Admin-Override)", expanded=False):
        st.info("ℹ️ Manuelle Einträge werden in der Zeitauswertung mit einem 🖊️-Symbol gekennzeichnet und im Audit-Log dokumentiert.")
        
        mitarbeiter_list_neu = get_all_mitarbeiter()
        if mitarbeiter_list_neu:
            with st.form("manueller_zeiteintrag_form", clear_on_submit=True):
                col_m1, col_m2 = st.columns(2)
                
                with col_m1:
                    ma_options_neu = {f"{m['vorname']} {m['nachname']}": m['id'] for m in mitarbeiter_list_neu}
                    selected_ma_name_neu = st.selectbox(
                        "Mitarbeiter *",
                        options=list(ma_options_neu.keys()),
                        key="manuell_ma_select"
                    )
                    selected_ma_id_neu = ma_options_neu[selected_ma_name_neu]
                    
                    manuell_datum = st.date_input(
                        "Datum *",
                        value=date.today(),
                        format="DD.MM.YYYY",
                        key="manuell_datum"
                    )
                
                with col_m2:
                    manuell_start = st.time_input(
                        "Startzeit *",
                        value=datetime.strptime("08:00", "%H:%M").time(),
                        key="manuell_start"
                    )
                    manuell_ende = st.time_input(
                        "Endzeit *",
                        value=datetime.strptime("16:00", "%H:%M").time(),
                        key="manuell_ende"
                    )
                
                col_m3, col_m4 = st.columns(2)
                with col_m3:
                    manuell_pause = st.number_input(
                        "Pause (Minuten)",
                        min_value=0,
                        max_value=120,
                        value=30,
                        step=5,
                        key="manuell_pause"
                    )
                with col_m4:
                    manuell_grund = st.text_input(
                        "Grund / Kommentar *",
                        placeholder="z.B. Terminal defekt, Vergessen zu stempeln",
                        key="manuell_grund"
                    )
                
                submitted_manuell = st.form_submit_button(
                    "💾 Zeiteintrag speichern",
                    use_container_width=True,
                    type="primary"
                )
                
                if submitted_manuell:
                    if not manuell_grund.strip():
                        st.error("❌ Bitte einen Grund/Kommentar angeben!")
                    elif manuell_ende <= manuell_start:
                        st.error("❌ Endzeit muss nach der Startzeit liegen!")
                    else:
                        try:
                            from utils.calculations import berechne_arbeitsstunden, is_sonntag, is_feiertag
                            
                            ist_so = is_sonntag(manuell_datum)
                            ist_ft = is_feiertag(manuell_datum)
                            arbeitsstunden_neu = berechne_arbeitsstunden(
                                manuell_start, manuell_ende, manuell_pause
                            )
                            
                            supabase_neu = get_supabase_client()
                            betrieb_id_neu = st.session_state.get('betrieb_id')
                            
                            neuer_eintrag = {
                                'mitarbeiter_id': selected_ma_id_neu,
                                'betrieb_id': betrieb_id_neu,
                                'datum': manuell_datum.isoformat(),
                                'start_zeit': manuell_start.strftime('%H:%M:%S'),
                                'ende_zeit': manuell_ende.strftime('%H:%M:%S'),
                                'pause_minuten': manuell_pause,
                                'arbeitsstunden': arbeitsstunden_neu,
                                'ist_sonntag': ist_so,
                                'ist_feiertag': ist_ft,
                                'quelle': 'manuell_admin',
                                'manuell_kommentar': manuell_grund.strip(),
                                'korrigiert_von_admin': True,
                                'korrektur_grund': f'Manuell angelegt: {manuell_grund.strip()}',
                                'korrektur_datum': datetime.now().isoformat()
                            }
                            
                            result_neu = supabase_neu.table('zeiterfassung').insert(neuer_eintrag).execute()
                            
                            # Audit-Log
                            try:
                                from utils.audit_log import log_zeitkorrektur
                                admin_result_neu = supabase_neu.table('users').select('username').eq('id', st.session_state.user_id).execute()
                                admin_name_neu = admin_result_neu.data[0]['username'] if admin_result_neu.data else 'Admin'
                                log_zeitkorrektur(
                                    admin_user_id=st.session_state.user_id,
                                    admin_name=admin_name_neu,
                                    mitarbeiter_id=selected_ma_id_neu,
                                    mitarbeiter_name=selected_ma_name_neu,
                                    zeiterfassung_id=result_neu.data[0]['id'] if result_neu.data else None,
                                    alter_wert={},
                                    neuer_wert=neuer_eintrag,
                                    begruendung=f'Manuell angelegt: {manuell_grund.strip()}',
                                    betrieb_id=betrieb_id_neu
                                )
                            except Exception:
                                pass
                            
                            st.success(f"✅ Zeiteintrag für {selected_ma_name_neu} am {manuell_datum.strftime('%d.%m.%Y')} erfolgreich angelegt! ({arbeitsstunden_neu:.2f} h, {'Sonntag' if ist_so else 'Feiertag' if ist_ft else 'Werktag'})")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Fehler beim Speichern: {str(e)}")
    
    st.divider()
    # ══════════════════════════════════════════════════════════════
    
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
            format_func=lambda x: mitarbeiter_options[x]['name'],
            key="zeiterfassung_mitarbeiter_select"
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
            # Kennzeichnung manueller Einträge
            ist_manuell = ze.get('quelle') == 'manuell_admin'
            manuell_badge = " 🖊️ [Manuell]" if ist_manuell else ""
            
            with st.expander(
                f"👤 {ze['mitarbeiter']['vorname']} {ze['mitarbeiter']['nachname']} - "
                f"{datetime.fromisoformat(ze['datum']).strftime('%d.%m.%Y')} - "
                f"{ze['start_zeit'][:5]} bis {ze['ende_zeit'][:5] if ze['ende_zeit'] else 'Offen'}{manuell_badge}"
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
                    so_icon = '\u2705' if ze.get('ist_sonntag') else '\u274c'
                    ft_icon = '\u2705' if ze.get('ist_feiertag') else '\u274c'
                    st.write(f"**Sonntag:** {so_icon}")
                    st.write(f"**Feiertag:** {ft_icon}")
                    # Quelle anzeigen
                    quelle = ze.get('quelle', 'terminal')
                    if quelle == 'manuell_admin':
                        st.markdown("**Quelle:** \ud83d\udd8a\ufe0f Manuell (Admin)")
                        if ze.get('manuell_kommentar'):
                            st.markdown(f"**Grund:** *{ze['manuell_kommentar']}*")
                    else:
                        st.write("**Quelle:** \ud83d\udcf1 Terminal")
                
                # Korrektur-Formular
                st.markdown("---")
                st.markdown("**✏️ Zeiterfassung korrigieren**")
                
                with st.form(f"korrektur_form_{ze['id']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        _s, _ = parse_zeit(ze['start_zeit'])
                        new_check_in = st.time_input(
                            "Check-In",
                            value=_s
                        )
                    
                    with col2:
                        if ze['ende_zeit']:
                            default_checkout, _ = parse_zeit(ze['ende_zeit'])
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
                                from utils.calculations import berechne_arbeitsstunden, is_sonntag, is_feiertag
                                
                                # Stelle sicher, dass new_check_in/out datetime.time Objekte sind
                                if isinstance(new_check_in, datetime):
                                    new_check_in = new_check_in.time()
                                if isinstance(new_check_out, datetime):
                                    new_check_out = new_check_out.time()
                                
                                check_in_dt = datetime.combine(date.today(), new_check_in)
                                check_out_dt = datetime.combine(date.today(), new_check_out)
                                
                                arbeitsstunden = berechne_arbeitsstunden(
                                    check_in_dt,
                                    check_out_dt,
                                    new_pause
                                )
                                
                                # Prüfe Sonntag/Feiertag für das Datum
                                zeiterfassung_datum = datetime.fromisoformat(ze['datum']).date()
                                ist_sonntag_tag = is_sonntag(zeiterfassung_datum)
                                ist_feiertag_tag = is_feiertag(zeiterfassung_datum)
                                
                                # Aktualisiere Zeiterfassung
                                update_data = {
                                    'start_zeit': new_check_in.strftime('%H:%M:%S'),
                                    'ende_zeit': new_check_out.strftime('%H:%M:%S'),
                                    'pause_minuten': new_pause,
                                    'arbeitsstunden': arbeitsstunden,
                                    'ist_sonntag': ist_sonntag_tag,
                                    'ist_feiertag': ist_feiertag_tag,
                                    'korrigiert_von_admin': True,
                                    'korrektur_grund': korrektur_grund,
                                    'korrektur_datum': datetime.now().isoformat()
                                }
                                
                                # Alten Wert für Audit-Log sichern
                                alter_wert = {
                                    'start_zeit': ze.get('start_zeit'),
                                    'ende_zeit': ze.get('ende_zeit'),
                                    'pause_minuten': ze.get('pause_minuten'),
                                    'arbeitsstunden': ze.get('arbeitsstunden')
                                }
                                
                                supabase.table('zeiterfassung').update(update_data).eq('id', ze['id']).execute()
                                
                                # Audit-Log schreiben (revisionssicher)
                                try:
                                    from utils.audit_log import log_zeitkorrektur
                                    # Hole Mitarbeiter-Name
                                    ma_result = supabase.table('mitarbeiter').select('vorname, nachname').eq('id', ze['mitarbeiter_id']).execute()
                                    ma_name = f"{ma_result.data[0]['vorname']} {ma_result.data[0]['nachname']}" if ma_result.data else 'Unbekannt'
                                    # Hole Admin-Name
                                    admin_result = supabase.table('users').select('username').eq('id', st.session_state.user_id).execute()
                                    admin_name = admin_result.data[0]['username'] if admin_result.data else 'Admin'
                                    log_zeitkorrektur(
                                        admin_user_id=st.session_state.user_id,
                                        admin_name=admin_name,
                                        mitarbeiter_id=ze['mitarbeiter_id'],
                                        mitarbeiter_name=ma_name,
                                        zeiterfassung_id=ze['id'],
                                        alter_wert=alter_wert,
                                        neuer_wert={
                                            'start_zeit': new_check_in.strftime('%H:%M:%S'),
                                            'ende_zeit': new_check_out.strftime('%H:%M:%S'),
                                            'pause_minuten': new_pause
                                        },
                                        begruendung=korrektur_grund,
                                        betrieb_id=st.session_state.get('betrieb_id')
                                    )
                                except Exception as audit_err:
                                    import logging
                                    logging.warning(f"Audit-Log konnte nicht geschrieben werden: {audit_err}")
                                
                                # E-Mail-Benachrichtigung an Mitarbeiter über Zeitkorrektur
                                try:
                                    from utils.email_service import send_zeitkorrektur_email
                                    ma_email_result = supabase.table('mitarbeiter').select('email, vorname, nachname').eq('id', ze['mitarbeiter_id']).execute()
                                    if ma_email_result.data and ma_email_result.data[0].get('email'):
                                        ma_info = ma_email_result.data[0]
                                        ma_email_addr = ma_info['email']
                                        ma_vollname = f"{ma_info.get('vorname','')} {ma_info.get('nachname','')}".strip()
                                        datum_str = ze.get('datum', '')
                                        alte_start_str = alter_wert.get('start_zeit', '?')[:5] if alter_wert.get('start_zeit') else '?'
                                        alte_ende_str = alter_wert.get('ende_zeit', '?')[:5] if alter_wert.get('ende_zeit') else '?'
                                        send_zeitkorrektur_email(
                                            mitarbeiter_email=ma_email_addr,
                                            mitarbeiter_name=ma_vollname,
                                            datum=datum_str,
                                            alte_start=alte_start_str,
                                            alte_ende=alte_ende_str,
                                            neue_start=new_check_in.strftime('%H:%M'),
                                            neue_ende=new_check_out.strftime('%H:%M'),
                                            pause_min=new_pause,
                                            korrektur_grund=korrektur_grund,
                                            admin_name=admin_name
                                        )
                                except Exception:
                                    pass  # E-Mail-Fehler blockieren nicht den Hauptworkflow
                                st.success("✅ Zeiterfassung erfolgreich korrigiert!")
                                st.rerun()
                    
                    with col2:
                        if st.form_submit_button("🗑️ Löschen", use_container_width=True):
                            if st.session_state.get(f'confirm_delete_{ze["id"]}', False):
                                # Audit-Log vor dem Löschen schreiben
                                try:
                                    from utils.audit_log import log_zeitloeschung
                                    ma_result = supabase.table('mitarbeiter').select('vorname, nachname').eq('id', ze['mitarbeiter_id']).execute()
                                    ma_name = f"{ma_result.data[0]['vorname']} {ma_result.data[0]['nachname']}" if ma_result.data else 'Unbekannt'
                                    admin_result = supabase.table('users').select('username').eq('id', st.session_state.user_id).execute()
                                    admin_name = admin_result.data[0]['username'] if admin_result.data else 'Admin'
                                    log_zeitloeschung(
                                        admin_user_id=st.session_state.user_id,
                                        admin_name=admin_name,
                                        mitarbeiter_id=ze['mitarbeiter_id'],
                                        mitarbeiter_name=ma_name,
                                        zeiterfassung_id=ze['id'],
                                        alter_wert={
                                            'datum': ze.get('datum'),
                                            'start_zeit': ze.get('start_zeit'),
                                            'ende_zeit': ze.get('ende_zeit'),
                                            'pause_minuten': ze.get('pause_minuten'),
                                            'arbeitsstunden': ze.get('arbeitsstunden')
                                        },
                                        begruendung='Manuell gelöscht durch Admin',
                                        betrieb_id=st.session_state.get('betrieb_id')
                                    )
                                except Exception as audit_err:
                                    import logging
                                    logging.warning(f"Audit-Log konnte nicht geschrieben werden: {audit_err}")
                                
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
    
    from utils.lohnkern import speichereMonatslohn
    from utils.lohnabrechnung import generiere_lohnabrechnung_pdf
    from utils.datev_export import erstelle_datev_lohnexport, erstelle_lohnuebersicht_csv
    
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
            format_func=lambda x: f"{x['vorname']} {x['nachname']} ({x['personalnummer']})",
            key="lohnabrechnung_mitarbeiter_select"
        )
    
    with col2:
        jahr = st.number_input(
            "Jahr",
            min_value=2020,
            max_value=2030,
            value=date.today().year
        )
    
    with col3:
        # Monatsnamen-Dictionary
        monatsnamen = {
            1: 'Januar', 2: 'Februar', 3: 'März', 4: 'April',
            5: 'Mai', 6: 'Juni', 7: 'Juli', 8: 'August',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Dezember'
        }
        aktueller_monat = date.today().month
        monat = st.selectbox(
            "Monat",
            options=list(range(1, 13)),
            format_func=lambda x: monatsnamen[x],
            index=aktueller_monat - 1,
            key="lohnabrechnung_monat_select"
        )
    
    col_btn1, col_btn2 = st.columns([2, 1])
    
    with col_btn1:
        if st.button("💰 Lohnabrechnung erstellen", use_container_width=True, type="primary"):
            with st.spinner("Berechne Lohn – lese Zeiterfassung aus Datenbank..."):
                ergebnis = speichereMonatslohn(
                    selected_mitarbeiter['id'],
                    monat,
                    jahr
                )
                
                if ergebnis['ok'] and ergebnis.get('gespeichert'):
                    st.success(
                        f"✅ Lohnabrechnung erstellt! "
                        f"{ergebnis['gesamt_stunden']:.2f} h × {ergebnis['stundenlohn']:.2f} € = "
                        f"**{ergebnis['gesamtbrutto']:.2f} € Brutto** "
                        f"({ergebnis['anzahl_eintraege']} Zeiterfassungs-Einträge aus DB gelesen)"
                    )
                    st.rerun()
                elif ergebnis.get('fehler'):
                    st.error(ergebnis['fehler'])
                else:
                    st.error("Fehler beim Speichern der Lohnabrechnung.")
    
    st.markdown("---")
    
    # DATEV-Export für alle Mitarbeiter
    st.subheader("📄 DATEV-Export für Steuerberater")
    
    st.info("""
    **DATEV-Export** erstellt eine CSV-Datei im DATEV Lohn & Gehalt-Format,
    die direkt von Ihrem Steuerberater importiert werden kann.
    """)
    
    col_export1, col_export2, col_export3 = st.columns(3)
    
    with col_export1:
        export_jahr = st.number_input("Jahr (Export)", min_value=2020, max_value=2030, value=date.today().year, key="export_jahr")
    
    with col_export2:
        export_monat = st.selectbox(
            "Monat (Export)",
            options=list(range(1, 13)),
            format_func=lambda x: monatsnamen[x],
            index=date.today().month - 1,
            key="export_monat"
        )
    
    with col_export3:
        st.write("")
        st.write("")
    
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        if st.button("📊 DATEV-CSV exportieren", use_container_width=True):
            with st.spinner("Erstelle DATEV-Export..."):
                try:
                    supabase_exp = get_supabase_client()
                    
                    # Lade alle Lohnabrechnungen für den Monat
                    alle_abrechnungen = supabase_exp.table('lohnabrechnungen').select(
                        '*, arbeitszeitkonto(ist_stunden, soll_stunden, sonntagsstunden, feiertagsstunden, urlaubstage_genommen)'
                    ).eq('monat', export_monat).eq('jahr', export_jahr).execute()
                    
                    if alle_abrechnungen.data:
                        # Lade alle Mitarbeiter
                        alle_ma = get_all_mitarbeiter()
                        
                        # Merge Arbeitszeitkonto-Daten in Abrechnungen
                        abrechnungen_mit_stunden = []
                        for abr in alle_abrechnungen.data:
                            abr_copy = dict(abr)
                            if abr.get('arbeitszeitkonto'):
                                azk = abr['arbeitszeitkonto']
                                abr_copy['ist_stunden'] = azk.get('ist_stunden', 0)
                                abr_copy['soll_stunden'] = azk.get('soll_stunden', 0)
                                abr_copy['sonntagsstunden'] = azk.get('sonntagsstunden', 0)
                                abr_copy['feiertagsstunden'] = azk.get('feiertagsstunden', 0)
                                abr_copy['urlaubstage_genommen'] = azk.get('urlaubstage_genommen', 0)
                            abrechnungen_mit_stunden.append(abr_copy)
                        
                        datev_bytes = erstelle_datev_lohnexport(
                            alle_ma, abrechnungen_mit_stunden, export_monat, export_jahr
                        )
                        
                        st.download_button(
                            label=f"💾 DATEV-CSV herunterladen ({monatsnamen[export_monat]} {export_jahr})",
                            data=datev_bytes,
                            file_name=f"DATEV_Lohn_{export_jahr}_{export_monat:02d}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.warning(f"Keine Lohnabrechnungen für {monatsnamen[export_monat]} {export_jahr} vorhanden. Bitte zuerst Lohnabrechnungen erstellen.")
                except Exception as e:
                    st.error(f"Fehler beim DATEV-Export: {str(e)}")
    
    with col_dl2:
        if st.button("📊 Lohnübersicht CSV (intern)", use_container_width=True):
            with st.spinner("Erstelle Lohnübersicht..."):
                try:
                    supabase_exp = get_supabase_client()
                    
                    alle_abrechnungen = supabase_exp.table('lohnabrechnungen').select(
                        '*, arbeitszeitkonto(ist_stunden, soll_stunden, sonntagsstunden, feiertagsstunden, urlaubstage_genommen)'
                    ).eq('monat', export_monat).eq('jahr', export_jahr).execute()
                    
                    if alle_abrechnungen.data:
                        alle_ma = get_all_mitarbeiter()
                        
                        abrechnungen_mit_stunden = []
                        for abr in alle_abrechnungen.data:
                            abr_copy = dict(abr)
                            if abr.get('arbeitszeitkonto'):
                                azk = abr['arbeitszeitkonto']
                                abr_copy['ist_stunden'] = azk.get('ist_stunden', 0)
                                abr_copy['soll_stunden'] = azk.get('soll_stunden', 0)
                                abr_copy['sonntagsstunden'] = azk.get('sonntagsstunden', 0)
                                abr_copy['feiertagsstunden'] = azk.get('feiertagsstunden', 0)
                                abr_copy['urlaubstage_genommen'] = azk.get('urlaubstage_genommen', 0)
                            abrechnungen_mit_stunden.append(abr_copy)
                        
                        uebersicht_bytes = erstelle_lohnuebersicht_csv(
                            alle_ma, abrechnungen_mit_stunden, export_monat, export_jahr
                        )
                        
                        st.download_button(
                            label=f"💾 Lohnübersicht herunterladen ({monatsnamen[export_monat]} {export_jahr})",
                            data=uebersicht_bytes,
                            file_name=f"Lohnuebersicht_{export_jahr}_{export_monat:02d}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.warning(f"Keine Lohnabrechnungen für {monatsnamen[export_monat]} {export_jahr} vorhanden.")
                except Exception as e:
                    st.error(f"Fehler beim Export: {str(e)}")
    
    st.markdown("---")
    
    # Zeige vorhandene Lohnabrechnungen
    st.subheader("Vorhandene Lohnabrechnungen")
    
    supabase = get_supabase_client()
    
    try:
        lohnabrechnungen = supabase.table('lohnabrechnungen').select(
            '*, mitarbeiter(vorname, nachname, personalnummer, beschaeftigungsart, minijob_monatsgrenze)'
        ).order('jahr', desc=True).order('monat', desc=True).execute()
        
        if lohnabrechnungen.data:
            for abrechnung in lohnabrechnungen.data:
                mitarbeiter = abrechnung['mitarbeiter']
                ist_minijob = (mitarbeiter or {}).get('beschaeftigungsart') == 'minijob'
                minijob_grenze = float((mitarbeiter or {}).get('minijob_monatsgrenze') or 556.0)
                # DB-Spalte heißt gesamtbrutto, gesamtbetrag als Fallback für ältere Einträge
                gesamtbrutto = float(abrechnung.get('gesamtbrutto') or abrechnung.get('gesamtbetrag') or 0)
                
                # Warnung im Expander-Titel wenn Minijob-Grenze überschritten
                grenze_ueberschritten = ist_minijob and gesamtbrutto > minijob_grenze
                expander_titel = (
                    f"{mitarbeiter['vorname']} {mitarbeiter['nachname']} - "
                    f"{get_monatsnamen(abrechnung['monat'])} {abrechnung['jahr']} - "
                    f"{format_waehrung(gesamtbrutto)}"
                    + (" ⚠️ MINIJOB-GRENZE ÜBERSCHRITTEN" if grenze_ueberschritten else "")
                    + (" 💼 Minijob" if ist_minijob and not grenze_ueberschritten else "")
                )
                
                with st.expander(expander_titel):
                    # Minijob-Warnung
                    if ist_minijob:
                        if grenze_ueberschritten:
                            st.error(
                                f"⚠️ **Minijob-Grenze überschritten!** "
                                f"Gesamtbrutto {format_waehrung(gesamtbrutto)} übersteigt die "
                                f"Minijob-Grenze von {format_waehrung(minijob_grenze)}. "
                                f"Bitte prüfen Sie den Arbeitsvertrag."
                            )
                        else:
                            verbleibend = minijob_grenze - gesamtbrutto
                            st.info(
                                f"💼 **Minijob** – Gesamtbrutto {format_waehrung(gesamtbrutto)} "
                                f"von {format_waehrung(minijob_grenze)} Grenze "
                                f"(noch {format_waehrung(verbleibend)} Spielraum)"
                            )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Grundlohn:** {format_waehrung(abrechnung['grundlohn'])}")
                        if (abrechnung.get('sonntagszuschlag') or 0) > 0:
                            st.write(f"**Sonntagszuschlag:** {format_waehrung(abrechnung['sonntagszuschlag'])}")
                        if (abrechnung.get('feiertagszuschlag') or 0) > 0:
                            st.write(f"**Feiertagszuschlag:** {format_waehrung(abrechnung['feiertagszuschlag'])}")
                        st.write(f"**Arbeitsstunden:** {abrechnung.get('arbeitsstunden', 0):.2f} h")
                    
                    with col2:
                        st.write(f"**Gesamtbrutto:** {format_waehrung(gesamtbrutto)}")
                        st.write(f"**Erstellt am:** {abrechnung.get('erstellt_am', '–')}")
                    
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
                            from utils.lohnkern import speichereMonatslohn
                            ergebnis = speichereMonatslohn(
                                abrechnung['mitarbeiter_id'],
                                abrechnung['monat'],
                                abrechnung['jahr']
                            )
                            if ergebnis['ok'] and ergebnis.get('gespeichert'):
                                st.success(
                                    f"✅ Neu berechnet: {ergebnis['gesamt_stunden']:.2f} h × "
                                    f"{ergebnis['stundenlohn']:.2f} € = {ergebnis['gesamtbrutto']:.2f} € Brutto"
                                )
                                st.rerun()
                            elif ergebnis.get('fehler'):
                                st.error(ergebnis['fehler'])
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
    
    # ============================================================
    # DSGVO-LÖSCHFRISTEN-WARNUNG
    # ============================================================
    try:
        from utils.database import get_supabase_client
        supabase_dsgvo = get_supabase_client()
        heute_str = date.today().isoformat()
        # Mitarbeiter mit fälliger Löschfrist
        faellig = supabase_dsgvo.table('mitarbeiter').select(
            'id, vorname, nachname, loeschfrist_datum, austrittsdatum'
        ).lte('loeschfrist_datum', heute_str).eq('anonymisiert', False).execute()
        if faellig.data:
            st.markdown(f"""
            <div style="background-color:#fef2f2; border-left:5px solid #dc2626; padding:1rem;
                        margin-bottom:1rem; border-radius:5px;">
                <strong>⚠️ DSGVO: {len(faellig.data)} Löschfrist(en) fällig!</strong>
            </div>
            """, unsafe_allow_html=True)
            with st.expander(f"🗑️ {len(faellig.data)} DSGVO-Löschfrist(en) fällig", expanded=True):
                for ma in faellig.data:
                    st.markdown(
                        f"**{ma['vorname']} {ma['nachname']}** – Löschfrist: `{ma.get('loeschfrist_datum', '?')}` "
                        f"| Austritt: `{ma.get('austrittsdatum', '?')}`"
                    )
                    # E-Mail an Admin senden (einmalig pro Session)
                    dsgvo_key = f"dsgvo_email_sent_{ma['id']}"
                    if not st.session_state.get(dsgvo_key):
                        try:
                            from utils.email_service import send_dsgvo_loeschfrist_warnung
                            admin_email = os.environ.get('SMTP_FROM', '')
                            if admin_email:
                                send_dsgvo_loeschfrist_warnung(
                                    admin_email=admin_email,
                                    mitarbeiter_liste=[{
                                        'name': f"{ma['vorname']} {ma['nachname']}",
                                        'loeschfrist': ma.get('loeschfrist_datum', '?'),
                                        'austrittsdatum': ma.get('austrittsdatum', '?')
                                    }]
                                )
                                st.session_state[dsgvo_key] = True
                        except Exception:
                            pass
    except Exception:
        pass  # DSGVO-Check soll Dashboard nicht blockieren


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
        # Korrekte Logik: Urlaub überschneidet sich mit Jahr wenn:
        # von_datum <= letzter_tag UND bis_datum >= erster_tag
        urlaube_response = supabase.table('urlaubsantraege').select(
            'id, mitarbeiter_id, von_datum, bis_datum, status, grund, mitarbeiter(vorname, nachname)'
        ).lte('von_datum', str(letzter_tag)).gte('bis_datum', str(erster_tag)).eq('status', 'genehmigt').execute()
        
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
                    if urlaub['status'] == 'genehmigt':
                        status_badge = "✅ Genehmigt"
                        status_color = "green"
                    elif urlaub['status'] == 'abgelehnt':
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
            genehmigt_count = len([u for urlaube in urlaube_nach_mitarbeiter.values() for u in urlaube if u['status'] == 'genehmigt'])
            st.metric("Genehmigte Anträge", genehmigt_count)
        
        # Jahres-Kalender-Ansicht (12 Monate)
        st.markdown("---")
        st.markdown("### 📆 Jahreskalender-Ansicht")
        
        import calendar
        import locale
        
        # Setze Locale auf Deutsch für Monatsnamen
        try:
            locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'de_DE')
            except:
                pass
        
        monate = [
            "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember"
        ]
        
        # ============================================================
        # MITARBEITER-FARBEN: Jeder Mitarbeiter bekommt eine eindeutige Farbe
        # Sonderregel: Fernando -> #8A2BE2 (Lila/Violett)
        # ============================================================
        FARB_PALETTE = [
            '#2196F3',  # Blau
            '#4CAF50',  # Grün
            '#FF5722',  # Tief-Orange
            '#009688',  # Türkis
            '#E91E63',  # Pink
            '#FF9800',  # Orange
            '#795548',  # Braun
            '#607D8B',  # Blaugrau
            '#3F51B5',  # Indigo
            '#00BCD4',  # Cyan
            '#8BC34A',  # Hellgrün
            '#FFC107',  # Bernstein
        ]
        
        # Weise jedem Mitarbeiter eine Farbe zu
        mitarbeiter_farben = {}
        farb_index = 0
        for ma_name in sorted(urlaube_nach_mitarbeiter.keys()):
            # Sonderregel: Fernando bekommt immer Lila #8A2BE2
            if 'fernando' in ma_name.lower():
                mitarbeiter_farben[ma_name] = '#8A2BE2'
            else:
                mitarbeiter_farben[ma_name] = FARB_PALETTE[farb_index % len(FARB_PALETTE)]
                farb_index += 1
        
        # Legende anzeigen
        st.markdown("**Legende:**")
        legende_html = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;">'
        for ma_name, farbe in sorted(mitarbeiter_farben.items()):
            legende_html += f'<span style="background: {farbe}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">{ma_name}</span>'
        legende_html += '</div>'
        st.markdown(legende_html, unsafe_allow_html=True)
        
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
                                    
                                    # Prüfe welche Mitarbeiter an diesem Tag Urlaub haben
                                    urlaub_heute_namen = []
                                    for urlaub in urlaube_response.data:
                                        von = datetime.strptime(urlaub['von_datum'], '%Y-%m-%d').date()
                                        bis = datetime.strptime(urlaub['bis_datum'], '%Y-%m-%d').date()
                                        if von <= aktuelles_datum <= bis:
                                            ma_name = f"{urlaub['mitarbeiter']['vorname']} {urlaub['mitarbeiter']['nachname']}"
                                            urlaub_heute_namen.append(ma_name)
                                    
                                    # Färbe Zelle mit Mitarbeiter-Farbe
                                    if urlaub_heute_namen:
                                        if len(urlaub_heute_namen) == 1:
                                            # Einzelner Mitarbeiter: dessen persönliche Farbe
                                            bg_color = mitarbeiter_farben.get(urlaub_heute_namen[0], '#2196F3')
                                            text_color = 'white'
                                        else:
                                            # Mehrere Mitarbeiter: Farbverlauf des ersten + Indikator
                                            bg_color = mitarbeiter_farben.get(urlaub_heute_namen[0], '#2196F3')
                                            text_color = 'white'
                                        title = f"{len(urlaub_heute_namen)} im Urlaub: {', '.join(urlaub_heute_namen)}"
                                        multi_indicator = f'+{len(urlaub_heute_namen)-1}' if len(urlaub_heute_namen) > 1 else ''
                                        sup_tag = f'<sup style="font-size:0.6rem;">{multi_indicator}</sup>' if multi_indicator else ''
                                        html += (f'<td style="border: 1px solid #ddd; padding: 4px; background-color: {bg_color}; '
                                                 f'text-align: center; color: {text_color}; font-weight: 700;" '
                                                 f'title="{title}"><strong>{tag}</strong>'
                                                 f'{sup_tag}'
                                                 f'</td>')
                                    else:
                                        html += f'<td style="border: 1px solid #ddd; padding: 4px; text-align: center; color: #333;">{tag}</td>'
                            html += '</tr>'
                        
                        html += '</table>'
                        st.markdown(html, unsafe_allow_html=True)
        
        st.caption("💡 Jeder Mitarbeiter hat eine eindeutige Farbe. Fernando = Lila (■ #8A2BE2). Mehrere Urlaube am gleichen Tag: Farbe des ersten Mitarbeiters + Hochzahl.")
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
