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


def show():
    """Zeigt das Administrator-Dashboard an"""
    
    st.markdown('<div class="main-header">⚖️ Administrator-Dashboard</div>', unsafe_allow_html=True)
    
    # Tab-Navigation
    tabs = st.tabs([
        "📊 Übersicht",
        "👥 Mitarbeiterverwaltung",
        "🏖️ Urlaubsgenehmigung",
        "⏰ Zeiterfassung",
        "💰 Lohnabrechnung",
        "⚙️ Einstellungen"
    ])
    
    with tabs[0]:
        show_uebersicht()
    
    with tabs[1]:
        show_mitarbeiterverwaltung()
    
    with tabs[2]:
        show_urlaubsgenehmigung()
    
    with tabs[3]:
        show_zeiterfassung_admin()
    
    with tabs[4]:
        show_lohnabrechnung()
    
    with tabs[5]:
        show_einstellungen()


def show_uebersicht():
    """Zeigt die Übersicht mit wichtigen Kennzahlen"""
    
    st.subheader("📊 Übersicht")
    
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
                    col1, col2, col3 = st.columns([2, 3, 1])
                    
                    with col1:
                        st.write(f"**{mitarbeiter['vorname']} {mitarbeiter['nachname']}**")
                    
                    with col2:
                        st.write(f"{antrag['von_datum']} bis {antrag['bis_datum']} ({antrag['anzahl_tage']} Tage)")
                    
                    with col3:
                        if st.button("Bearbeiten", key=f"urlaub_{antrag['id']}"):
                            st.session_state.selected_urlaub = antrag['id']
                            st.rerun()
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
            st.markdown("**Zuschläge**")
            sonntagszuschlag_aktiv = st.checkbox(
                "50% Sonntagszuschlag",
                value=mitarbeiter_data.get('sonntagszuschlag_aktiv', False) if is_edit else False
            )
            feiertagszuschlag_aktiv = st.checkbox(
                "100% Feiertagszuschlag",
                value=mitarbeiter_data.get('feiertagszuschlag_aktiv', False) if is_edit else False
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
                'feiertagszuschlag_aktiv': feiertagszuschlag_aktiv
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
                user_id = create_user(username, password, 'mitarbeiter')
                
                if user_id:
                    # Erstelle Mitarbeiter
                    mitarbeiter_id = create_mitarbeiter(user_id, mitarbeiter_daten)
                    
                    if mitarbeiter_id:
                        st.success(f"Mitarbeiter {vorname} {nachname} erfolgreich angelegt!")
                        st.session_state.show_mitarbeiter_form = False
                        st.rerun()


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
    
    # Bearbeiten-Button
    if st.button("✏️ Mitarbeiter bearbeiten", key=f"edit_{mitarbeiter['id']}", use_container_width=True):
        st.session_state.edit_mitarbeiter_id = mitarbeiter['id']
        st.session_state.show_mitarbeiter_form = True
        st.rerun()
    
    st.markdown("---")
    
    # Arbeitsvertrag
    st.markdown("**📄 Arbeitsvertrag**")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Arbeitsvertrag hochladen (PDF)",
            type=['pdf'],
            key=f"vertrag_{mitarbeiter['id']}"
        )
    
    with col2:
        if st.button("Hochladen", key=f"upload_{mitarbeiter['id']}"):
            if uploaded_file:
                # Lade Datei hoch
                file_path = f"{mitarbeiter['id']}/{mitarbeiter['personalnummer']}_vertrag.pdf"
                result = upload_file_to_storage('arbeitsvertraege', file_path, uploaded_file.getvalue())
                
                if result:
                    # Aktualisiere Mitarbeiter-Datensatz
                    update_mitarbeiter(mitarbeiter['id'], {'vertrag_pdf_path': file_path})
                    st.success("Arbeitsvertrag erfolgreich hochgeladen!")
                    st.rerun()
            else:
                st.warning("Bitte wählen Sie eine PDF-Datei aus.")
    
    # Zeige vorhandenen Vertrag
    if mitarbeiter.get('vertrag_pdf_path'):
        st.info(f"✅ Vertrag vorhanden: {mitarbeiter['vertrag_pdf_path']}")
        
        col_dl, col_view = st.columns(2)
        
        with col_dl:
            # Download-Button
            try:
                pdf_data = download_file_from_storage('arbeitsvertraege', mitarbeiter['vertrag_pdf_path'])
                if pdf_data:
                    st.download_button(
                        label="📥 Vertrag herunterladen",
                        data=pdf_data,
                        file_name=f"{mitarbeiter['personalnummer']}_vertrag.pdf",
                        mime="application/pdf",
                        key=f"download_{mitarbeiter['id']}",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Fehler beim Herunterladen: {str(e)}")
        
        with col_view:
            # Anzeige-Button
            if st.button("👁️ Vertrag anzeigen", key=f"view_{mitarbeiter['id']}", use_container_width=True):
                st.session_state[f"show_vertrag_{mitarbeiter['id']}"] = True
        
        # PDF anzeigen wenn Button geklickt
        if st.session_state.get(f"show_vertrag_{mitarbeiter['id']}", False):
            try:
                pdf_data = download_file_from_storage('arbeitsvertraege', mitarbeiter['vertrag_pdf_path'])
                if pdf_data:
                    st.markdown("---")
                    st.markdown("**Vertragsansicht**")
                    
                    # PDF in einem iframe anzeigen
                    import base64
                    base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    
                    if st.button("❌ Ansicht schließen", key=f"close_{mitarbeiter['id']}"):
                        st.session_state[f"show_vertrag_{mitarbeiter['id']}"] = False
                        st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Anzeigen: {str(e)}")


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
    
    st.subheader("⏰ Zeiterfassung (Übersicht)")
    
    st.info("Diese Funktion zeigt die Zeiterfassungen aller Mitarbeiter an.")
    
    # Wird in Phase 5 vollständig implementiert
    st.write("Implementierung erfolgt in der nächsten Phase.")


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
