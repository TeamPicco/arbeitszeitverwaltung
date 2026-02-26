"""
Mitarbeiter-Dashboard
Zeiterfassung, Urlaubsanträge und persönliche Daten
"""

import streamlit as st
from datetime import datetime, date, time, timedelta
from typing import Optional

from utils.database import (
    get_supabase_client,
    get_mitarbeiter_by_user_id,
    download_file_from_storage,
    change_password
)
from utils.calculations import (
    berechne_arbeitsstunden,
    berechne_urlaubstage,
    berechne_verfuegbare_urlaubstage,
    is_sonntag,
    is_feiertag,
    format_stunden,
    format_waehrung,
    get_wochentag,
    get_monatsnamen
)
from utils.session import get_current_user_id
from utils.push_notifications import show_notifications_widget
from utils.chat_notifications import get_unread_chat_count
from utils.styles import apply_custom_css, get_icon, COLORS


def show():
    """Zeigt das Mitarbeiter-Dashboard an"""
    
    # Wende Custom CSS an
    apply_custom_css()
    
    # Zeige Benachrichtigungen in Sidebar
    if hasattr(st.session_state, 'user_id'):
        show_notifications_widget(st.session_state.user_id)
    
    # Lade Mitarbeiterdaten
    mitarbeiter = get_mitarbeiter_by_user_id(get_current_user_id())
    
    if not mitarbeiter:
        st.error("Mitarbeiterdaten konnten nicht geladen werden.")
        return
    
    # Speichere in Session State für schnelleren Zugriff
    st.session_state.mitarbeiter_data = mitarbeiter
    
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
    
    st.title(f"{get_icon('mitarbeiter')} Willkommen, {mitarbeiter['vorname']} {mitarbeiter['nachname']}")
    
    # Zähle ungelesene Chat-Nachrichten
    last_read = st.session_state.get('chat_last_read', None)
    unread_count = get_unread_chat_count(st.session_state.user_id, st.session_state.betrieb_id, last_read)
    chat_badge = f" ({unread_count})" if unread_count > 0 else ""
    
    # Tab-Navigation mit einheitlichen Icons
    tabs = st.tabs([
        f"{get_icon('dashboard')} Dashboard",
        f"{get_icon('zeit')} Zeiterfassung",
        f"{get_icon('dienstplan')} Mein Dienstplan",
        f"{get_icon('urlaub')} Urlaub",
        f"{get_icon('dienstplan')} Urlaubskalender",
        f"{get_icon('chat')} Plauderecke{chat_badge}",
        f"{get_icon('dokument')} Dokumente",
        f"{get_icon('einstellungen')} Einstellungen"
    ])
    
    with tabs[0]:
        show_dashboard(mitarbeiter)
    
    with tabs[1]:
        show_zeiterfassung(mitarbeiter)
    
    with tabs[2]:
        from pages.mitarbeiter_dienstplan import show_mitarbeiter_dienstplan
        show_mitarbeiter_dienstplan(mitarbeiter)
    
    with tabs[3]:
        show_urlaub(mitarbeiter)
    
    with tabs[4]:
        show_urlaubskalender()
    
    with tabs[5]:
        show_plauderecke()
    
    with tabs[6]:
        show_dokumente(mitarbeiter)
    
    with tabs[7]:
        show_einstellungen_mitarbeiter()


def show_dashboard(mitarbeiter: dict):
    """Zeigt das Dashboard mit Übersicht an"""
    
    st.subheader("📊 Mein Dashboard")
    
    supabase = get_supabase_client()
    
    # Berechne Kennzahlen
    try:
        # Aktueller Monat
        heute = date.today()
        monat = heute.month
        jahr = heute.year
        
        # Arbeitszeitkonto für aktuellen Monat
        arbeitszeitkonto = supabase.table('arbeitszeitkonto').select('*').eq(
            'mitarbeiter_id', mitarbeiter['id']
        ).eq('monat', monat).eq('jahr', jahr).execute()
        
        if arbeitszeitkonto.data and len(arbeitszeitkonto.data) > 0:
            konto = arbeitszeitkonto.data[0]
            soll_stunden = konto['soll_stunden']
            ist_stunden = konto['ist_stunden']
            differenz = konto['differenz_stunden']
        else:
            soll_stunden = mitarbeiter['monatliche_soll_stunden']
            ist_stunden = 0
            differenz = -soll_stunden
        
        # Urlaubstage
        urlaub_genommen = supabase.table('urlaubsantraege').select('anzahl_tage').eq(
            'mitarbeiter_id', mitarbeiter['id']
        ).eq('status', 'genehmigt').execute()
        
        genommene_tage = sum([u['anzahl_tage'] for u in urlaub_genommen.data]) if urlaub_genommen.data else 0
        
        verfuegbare_tage = berechne_verfuegbare_urlaubstage(
            mitarbeiter['jahres_urlaubstage'],
            mitarbeiter['resturlaub_vorjahr'],
            genommene_tage
        )
        
        # Zeige Kennzahlen
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Soll-Stunden (Monat)",
                format_stunden(soll_stunden)
            )
        
        with col2:
            st.metric(
                "Ist-Stunden (Monat)",
                format_stunden(ist_stunden)
            )
        
        with col3:
            delta_color = "normal" if differenz >= 0 else "inverse"
            st.metric(
                "Zeitkonto",
                format_stunden(abs(differenz)),
                delta=f"{'Plus' if differenz >= 0 else 'Minus'}",
                delta_color=delta_color
            )
        
        with col4:
            st.metric(
                "Verfügbarer Urlaub",
                f"{verfuegbare_tage} Tage"
            )
        
        st.markdown("---")
        
        # Letzte Zeiterfassungen
        st.subheader("🕐 Letzte Zeiterfassungen")
        
        zeiterfassungen = supabase.table('zeiterfassung').select('*').eq(
            'mitarbeiter_id', mitarbeiter['id']
        ).order('datum', desc=True).limit(7).execute()
        
        if zeiterfassungen.data:
            df_data = []
            for z in zeiterfassungen.data:
                if z['ende_zeit']:
                    stunden = berechne_arbeitsstunden(
                        datetime.strptime(z['start_zeit'], '%H:%M:%S').time(),
                        datetime.strptime(z['ende_zeit'], '%H:%M:%S').time(),
                        z['pause_minuten']
                    )
                else:
                    stunden = 0
                
                df_data.append({
                    'Datum': z['datum'],
                    'Wochentag': get_wochentag(datetime.fromisoformat(z['datum']).date()),
                    'Start': z['start_zeit'],
                    'Ende': z['ende_zeit'] or 'Offen',
                    'Pause (Min)': z['pause_minuten'],
                    'Stunden': format_stunden(stunden) if stunden > 0 else '-'
                })
            
            st.dataframe(df_data, use_container_width=True, hide_index=True)
        else:
            st.info("Noch keine Zeiterfassungen vorhanden.")
        
        # Urlaubsanträge
        st.subheader("🏖️ Meine Urlaubsanträge")
        
        urlaub_antraege = supabase.table('urlaubsantraege').select('*').eq(
            'mitarbeiter_id', mitarbeiter['id']
        ).order('beantragt_am', desc=True).limit(5).execute()
        
        if urlaub_antraege.data:
            for antrag in urlaub_antraege.data:
                status_emoji = {
                    'beantragt': '⏳',
                    'genehmigt': '✅',
                    'abgelehnt': '❌'
                }
                
                status_color = {
                    'beantragt': 'warning-box',
                    'genehmigt': 'success-box',
                    'abgelehnt': 'error-box'
                }
                
                st.markdown(f"""
                <div class="{status_color[antrag['status']]}">
                    {status_emoji[antrag['status']]} <strong>{antrag['von_datum']} bis {antrag['bis_datum']}</strong> 
                    ({antrag['anzahl_tage']} Tage) - Status: {antrag['status'].upper()}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Noch keine Urlaubsanträge gestellt.")
    
    except Exception as e:
        st.error(f"Fehler beim Laden des Dashboards: {str(e)}")


def show_zeiterfassung(mitarbeiter: dict):
    """Zeigt die Zeiterfassung an"""
    from utils.device_management import check_device_or_mobile_permission, show_device_activation_dialog
    
    st.subheader("⏰ Zeiterfassung")
    
    # Prüfe Mastergerät oder mobile Berechtigung
    allowed, reason = check_device_or_mobile_permission(mitarbeiter, st.session_state.betrieb_id)
    
    if not allowed:
        st.error("❌ Zeiterfassung auf diesem Gerät nicht erlaubt.")
        st.info("📱 Sie haben keine mobile Zeiterfassung aktiviert und dieses Gerät ist kein registriertes Mastergerät.")
        
        # Zeige Aktivierungs-Dialog
        show_device_activation_dialog(st.session_state.betrieb_id)
        return
    
    # Zeige Info über Zugriffsmethode
    if mitarbeiter.get('mobile_zeiterfassung', False):
        st.success(f"✅ {reason}")
    else:
        st.info(f"🖥️ {reason}")
    
    supabase = get_supabase_client()
    
    # Neue Zeiterfassung
    st.markdown("**Neue Zeiterfassung**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        datum = st.date_input(
            "Datum",
            value=date.today(),
            max_value=date.today(),
            format="DD.MM.YYYY"
        )
    
    with col2:
        # Prüfe, ob bereits eine offene Zeiterfassung für heute existiert
        offene_zeit = supabase.table('zeiterfassung').select('*').eq(
            'mitarbeiter_id', mitarbeiter['id']
        ).eq('datum', datum.isoformat()).is_('ende_zeit', 'null').execute()
        
        if offene_zeit.data and len(offene_zeit.data) > 0:
            st.info("⏱️ Es gibt eine offene Zeiterfassung für diesen Tag.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_zeit = st.time_input("Startzeit", value=time(8, 0))
    
    with col2:
        ende_zeit = st.time_input("Endzeit", value=time(17, 0))
    
    with col3:
        pause_minuten = st.number_input(
            "Pause (Minuten)",
            min_value=0,
            max_value=240,
            value=30,
            step=15
        )
    
    # Berechne Stunden
    if ende_zeit:
        stunden = berechne_arbeitsstunden(start_zeit, ende_zeit, pause_minuten)
        st.info(f"📊 Arbeitsstunden: **{format_stunden(stunden)}**")
    
    # Prüfe Sonntag/Feiertag
    ist_sonntag_tag = is_sonntag(datum)
    ist_feiertag_tag = is_feiertag(datum)
    
    if ist_sonntag_tag:
        st.warning("⚠️ Sonntag - Sonntagszuschlag wird berechnet (falls aktiviert)")
    
    if ist_feiertag_tag:
        st.warning("⚠️ Feiertag - Feiertagszuschlag wird berechnet (falls aktiviert)")
    
    notiz = st.text_area("Notiz (optional)")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("💾 Speichern", use_container_width=True):
            try:
                # Prüfe, ob bereits eine Zeiterfassung für diesen Tag existiert
                existing = supabase.table('zeiterfassung').select('*').eq(
                    'mitarbeiter_id', mitarbeiter['id']
                ).eq('datum', datum.isoformat()).execute()
                
                zeiterfassung_data = {
                    'mitarbeiter_id': mitarbeiter['id'],
                    'datum': datum.isoformat(),
                    'start_zeit': start_zeit.strftime('%H:%M:%S'),
                    'ende_zeit': ende_zeit.strftime('%H:%M:%S'),
                    'pause_minuten': pause_minuten,
                    'ist_sonntag': ist_sonntag_tag,
                    'ist_feiertag': ist_feiertag_tag,
                    'notiz': notiz if notiz else None
                }
                
                if existing.data and len(existing.data) > 0:
                    # Aktualisiere bestehende Zeiterfassung
                    supabase.table('zeiterfassung').update(zeiterfassung_data).eq(
                        'id', existing.data[0]['id']
                    ).execute()
                    st.success("✅ Zeiterfassung aktualisiert!")
                else:
                    # Erstelle neue Zeiterfassung
                    supabase.table('zeiterfassung').insert(zeiterfassung_data).execute()
                    st.success("✅ Zeiterfassung gespeichert!")
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Fehler beim Speichern: {str(e)}")
    
    st.markdown("---")
    
    # Zeiterfassungen anzeigen
    st.markdown("**Meine Zeiterfassungen**")
    
    # Datumsbereich auswählen
    col1, col2 = st.columns(2)
    
    with col1:
        von_datum = st.date_input(
            "Von",
            value=date.today() - timedelta(days=30),
            key="zeit_von",
            format="DD.MM.YYYY"
        )
    
    with col2:
        bis_datum = st.date_input(
            "Bis",
            value=date.today(),
            key="zeit_bis",
            format="DD.MM.YYYY"
        )
    
    # Lade Zeiterfassungen
    try:
        zeiterfassungen = supabase.table('zeiterfassung').select('*').eq(
            'mitarbeiter_id', mitarbeiter['id']
        ).gte('datum', von_datum.isoformat()).lte('datum', bis_datum.isoformat()).order('datum', desc=True).execute()
        
        if zeiterfassungen.data:
            df_data = []
            gesamt_stunden = 0
            
            for z in zeiterfassungen.data:
                if z['ende_zeit']:
                    stunden = berechne_arbeitsstunden(
                        datetime.strptime(z['start_zeit'], '%H:%M:%S').time(),
                        datetime.strptime(z['ende_zeit'], '%H:%M:%S').time(),
                        z['pause_minuten']
                    )
                    gesamt_stunden += stunden
                else:
                    stunden = 0
                
                df_data.append({
                    'Datum': z['datum'],
                    'Wochentag': get_wochentag(datetime.fromisoformat(z['datum']).date()),
                    'Start': z['start_zeit'][:5],
                    'Ende': z['ende_zeit'][:5] if z['ende_zeit'] else 'Offen',
                    'Pause': f"{z['pause_minuten']} min",
                    'Stunden': format_stunden(stunden) if stunden > 0 else '-',
                    'Sonntag': '✅' if z['ist_sonntag'] else '',
                    'Feiertag': '✅' if z['ist_feiertag'] else ''
                })
            
            st.dataframe(df_data, use_container_width=True, hide_index=True)
            
            st.info(f"📊 **Gesamt:** {format_stunden(gesamt_stunden)} Stunden")
        else:
            st.info("Keine Zeiterfassungen im ausgewählten Zeitraum.")
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Zeiterfassungen: {str(e)}")


def show_urlaub(mitarbeiter: dict):
    """Zeigt Urlaubsverwaltung an"""
    
    st.subheader("🏖️ Urlaubsverwaltung")
    
    supabase = get_supabase_client()
    
    # Berechne verfügbare Urlaubstage
    try:
        urlaub_genommen = supabase.table('urlaubsantraege').select('anzahl_tage').eq(
            'mitarbeiter_id', mitarbeiter['id']
        ).eq('status', 'genehmigt').execute()
        
        genommene_tage = sum([u['anzahl_tage'] for u in urlaub_genommen.data]) if urlaub_genommen.data else 0
        
        verfuegbare_tage = berechne_verfuegbare_urlaubstage(
            mitarbeiter['jahres_urlaubstage'],
            mitarbeiter['resturlaub_vorjahr'],
            genommene_tage
        )
        
        # Zeige Urlaubsübersicht
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Jahresanspruch", f"{mitarbeiter['jahres_urlaubstage']} Tage")
        
        with col2:
            st.metric("Resturlaub Vorjahr", f"{mitarbeiter['resturlaub_vorjahr']} Tage")
        
        with col3:
            st.metric("Genommen", f"{genommene_tage} Tage")
        
        with col4:
            st.metric("Verfügbar", f"{verfuegbare_tage} Tage")
        
        st.markdown("---")
        
        # Neuer Urlaubsantrag
        st.markdown("**Neuer Urlaubsantrag**")
        
        with st.form("urlaubsantrag_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                von_datum = st.date_input(
                    "Von",
                    value=date.today() + timedelta(days=7),
                    min_value=date.today(),
                    format="DD.MM.YYYY"
                )
            
            with col2:
                bis_datum = st.date_input(
                    "Bis",
                    value=date.today() + timedelta(days=7),
                    min_value=date.today(),
                    format="DD.MM.YYYY"
                )
            
            # Berechne Urlaubstage
            if bis_datum >= von_datum:
                anzahl_tage = berechne_urlaubstage(von_datum, bis_datum)
                st.info(f"📊 Urlaubstage: **{anzahl_tage}** (ohne Wochenenden und Feiertage)")
                
                if anzahl_tage > verfuegbare_tage:
                    st.warning(f"⚠️ Sie haben nur noch {verfuegbare_tage} Urlaubstage verfügbar!")
            else:
                anzahl_tage = 0
                st.error("Das End-Datum muss nach dem Start-Datum liegen.")
            
            bemerkung = st.text_area("Bemerkung (optional)")
            
            submit = st.form_submit_button("Urlaubsantrag stellen")
            
            if submit:
                if anzahl_tage <= 0:
                    st.error("Bitte wählen Sie einen gültigen Zeitraum.")
                elif anzahl_tage > verfuegbare_tage:
                    st.error("Sie haben nicht genügend Urlaubstage verfügbar.")
                else:
                    try:
                        # Erstelle Urlaubsantrag
                        result = supabase.table('urlaubsantraege').insert({
                            'mitarbeiter_id': mitarbeiter['id'],
                            'von_datum': von_datum.isoformat(),
                            'bis_datum': bis_datum.isoformat(),
                            'anzahl_tage': anzahl_tage,
                            'status': 'beantragt',
                            'bemerkung_mitarbeiter': bemerkung if bemerkung else None,
                            'betrieb_id': st.session_state.betrieb_id
                        }).execute()
                        
                        # Erstelle Benachrichtigung für Admin
                        admin_users = supabase.table('users').select('id').eq('role', 'admin').eq('betrieb_id', st.session_state.betrieb_id).execute()
                        if admin_users.data:
                            for admin in admin_users.data:
                                supabase.table('benachrichtigungen').insert({
                                    'user_id': admin['id'],
                                    'typ': 'urlaubsantrag',
                                    'titel': 'Neuer Urlaubsantrag',
                                    'nachricht': f"{mitarbeiter['vorname']} {mitarbeiter['nachname']} hat einen Urlaubsantrag gestellt ({von_datum.strftime('%d.%m.%Y')} - {bis_datum.strftime('%d.%m.%Y')}, {anzahl_tage} Tage)",
                                    'gelesen': False,
                                    'betrieb_id': st.session_state.betrieb_id
                                }).execute()
                        
                        # E-Mail an Admin senden
                        try:
                            from utils.email_service import send_urlaubsantrag_email
                            ma_name = f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}"
                            send_urlaubsantrag_email(
                                ma_name,
                                von_datum.strftime('%d.%m.%Y'),
                                bis_datum.strftime('%d.%m.%Y'),
                                anzahl_tage,
                                bemerkung if bemerkung else None
                            )
                        except Exception as mail_err:
                            pass  # E-Mail-Fehler soll App nicht blockieren
                        
                        st.success("✅ Urlaubsantrag erfolgreich gestellt! Der Administrator wurde benachrichtigt.")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Fehler beim Erstellen des Urlaubsantrags: {str(e)}")
        
        st.markdown("---")
        
        # Urlaubsanträge anzeigen
        st.markdown("**Meine Urlaubsanträge**")
        
        urlaub_antraege = supabase.table('urlaubsantraege').select('*').eq(
            'mitarbeiter_id', mitarbeiter['id']
        ).order('beantragt_am', desc=True).execute()
        
        if urlaub_antraege.data:
            for antrag in urlaub_antraege.data:
                status_emoji = {
                    'beantragt': '⏳',
                    'genehmigt': '✅',
                    'abgelehnt': '❌'
                }
                
                with st.expander(
                    f"{status_emoji[antrag['status']]} {antrag['von_datum']} bis {antrag['bis_datum']} "
                    f"({antrag['anzahl_tage']} Tage) - {antrag['status'].upper()}"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Zeitraum:** {antrag['von_datum']} bis {antrag['bis_datum']}")
                        st.write(f"**Anzahl Tage:** {antrag['anzahl_tage']}")
                        st.write(f"**Status:** {antrag['status'].upper()}")
                    
                    with col2:
                        st.write(f"**Beantragt am:** {antrag['beantragt_am']}")
                        if antrag.get('bearbeitet_am'):
                            st.write(f"**Bearbeitet am:** {antrag['bearbeitet_am']}")
                    
                    if antrag.get('bemerkung_mitarbeiter'):
                        st.write(f"**Meine Bemerkung:** {antrag['bemerkung_mitarbeiter']}")
                    
                    if antrag.get('bemerkung_admin'):
                        st.write(f"**Bemerkung Administrator:** {antrag['bemerkung_admin']}")
        else:
            st.info("Noch keine Urlaubsanträge gestellt.")
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Urlaubsdaten: {str(e)}")


def show_dokumente(mitarbeiter: dict):
    """Zeigt Dokumente an"""
    
    st.subheader("📄 Meine Dokumente")
    
    # Arbeitsvertrag
    st.markdown("**Arbeitsvertrag**")
    
    if mitarbeiter.get('vertrag_pdf_path'):
        st.success("✅ Ihr Arbeitsvertrag ist hinterlegt.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Download-Button
            try:
                pdf_data = download_file_from_storage('arbeitsvertraege', mitarbeiter['vertrag_pdf_path'])
                if pdf_data:
                    st.download_button(
                        label="📥 Arbeitsvertrag herunterladen",
                        data=pdf_data,
                        file_name=f"Arbeitsvertrag_{mitarbeiter['personalnummer']}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Fehler beim Herunterladen: {str(e)}")
        
        with col2:
            # Anzeige-Button
            if st.button("👁️ Vertrag anzeigen", use_container_width=True):
                st.session_state.show_vertrag = True
        
        # PDF anzeigen wenn Button geklickt
        if st.session_state.get('show_vertrag', False):
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
                    
                    if st.button("❌ Ansicht schließen"):
                        st.session_state.show_vertrag = False
                        st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Anzeigen: {str(e)}")
    else:
        st.info("Noch kein Arbeitsvertrag hinterlegt. Bitte wenden Sie sich an Ihren Administrator.")
    
    st.markdown("---")
    
    # Lohnabrechnungen
    # Lohnabrechnungen
    st.markdown("**Lohnabrechnungen**")
    
    try:
        supabase = get_supabase_client()
        
        # Lade Lohnabrechnungen für diesen Mitarbeiter
        lohnabrechnungen = supabase.table('lohnabrechnungen').select(
            '*'
        ).eq('mitarbeiter_id', mitarbeiter['id']).order('jahr', desc=True).order('monat', desc=True).execute()
        
        if lohnabrechnungen.data and len(lohnabrechnungen.data) > 0:
            # Zeige jede Lohnabrechnung in einem Expander
            for abrechnung in lohnabrechnungen.data:
                monat_name = {
                    1: 'Januar', 2: 'Februar', 3: 'März', 4: 'April',
                    5: 'Mai', 6: 'Juni', 7: 'Juli', 8: 'August',
                    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Dezember'
                }.get(abrechnung['monat'], str(abrechnung['monat']))
                
                with st.expander(f"📄 {monat_name} {abrechnung['jahr']}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Bruttolohn:** {abrechnung.get('bruttolohn', 0):.2f} €")
                        st.write(f"**Nettolohn:** {abrechnung.get('nettolohn', 0):.2f} €")
                        st.write(f"**Arbeitsstunden:** {abrechnung.get('arbeitsstunden', 0):.2f} h")
                        
                        if abrechnung.get('sonntagsstunden', 0) > 0:
                            st.write(f"**Sonntagsstunden:** {abrechnung['sonntagsstunden']:.2f} h")
                        if abrechnung.get('feiertagsstunden', 0) > 0:
                            st.write(f"**Feiertagsstunden:** {abrechnung['feiertagsstunden']:.2f} h")
                    
                    with col2:
                        # PDF Download
                        if abrechnung.get('pdf_path'):
                            try:
                                pdf_data = download_file_from_storage('lohnabrechnungen', abrechnung['pdf_path'])
                                if pdf_data:
                                    st.download_button(
                                        label="📥 PDF herunterladen",
                                        data=pdf_data,
                                        file_name=f"Lohnabrechnung_{abrechnung['jahr']}_{abrechnung['monat']:02d}.pdf",
                                        mime="application/pdf",
                                        key=f"download_lohn_ma_{abrechnung['id']}",
                                        use_container_width=True
                                    )
                                else:
                                    st.warning("PDF nicht verfügbar")
                            except Exception as e:
                                st.error(f"Fehler beim Laden: {str(e)}")
                        else:
                            st.info("PDF wird erstellt...")
        else:
            st.info("Noch keine Lohnabrechnungen vorhanden.")
            
    except Exception as e:
        st.error(f"Fehler beim Laden der Lohnabrechnungen: {str(e)}")



def show_einstellungen_mitarbeiter():
    """Zeigt Einstellungen für Mitarbeiter an"""
    
    st.subheader("⚙️ Einstellungen")
    
    # Lade Mitarbeiterdaten
    mitarbeiter = st.session_state.get('mitarbeiter_data')
    if not mitarbeiter:
        st.error("Mitarbeiterdaten nicht gefunden.")
        return
    
    # Tabs für verschiedene Einstellungen
    settings_tabs = st.tabs(["Stammdaten", "Passwort"])
    
    with settings_tabs[0]:
        show_stammdaten_bearbeitung(mitarbeiter)
    
    with settings_tabs[1]:
        show_passwort_aendern()


def show_stammdaten_bearbeitung(mitarbeiter: dict):
    """Zeigt Formular zur Bearbeitung der Stammdaten"""
    from utils.notifications import update_mitarbeiter_stammdaten, create_aenderungsanfrage
    
    st.markdown("**Meine Stammdaten bearbeiten**")
    st.info("📝 Änderungen werden dem Administrator zur Kenntnis gebracht. Änderungen des Nachnamens benötigen eine Genehmigung.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Kontaktdaten**")
        new_email = st.text_input("E-Mail", value=mitarbeiter.get('email', ''), key="edit_email")
        new_telefon = st.text_input("Telefon", value=mitarbeiter.get('telefon', ''), key="edit_telefon")
    
    with col2:
        st.markdown("**Adresse**")
        new_strasse = st.text_input("Straße & Hausnummer", value=mitarbeiter.get('strasse', ''), key="edit_strasse")
        new_plz = st.text_input("PLZ", value=mitarbeiter.get('plz', ''), key="edit_plz")
        new_ort = st.text_input("Ort", value=mitarbeiter.get('ort', ''), key="edit_ort")
    
    st.markdown("---")
    st.markdown("**Namensänderung (benötigt Genehmigung)**")
    st.caption("z.B. nach Heirat")
    
    col_name1, col_name2 = st.columns(2)
    with col_name1:
        new_nachname = st.text_input("Neuer Nachname", value="", key="edit_nachname", placeholder="Nur ausfüllen bei Änderung")
    with col_name2:
        grund = st.text_input("Grund der Änderung", value="", key="edit_grund", placeholder="z.B. Heirat")
    
    if st.button("💾 Änderungen speichern", type="primary", use_container_width=True):
        changes_made = False
        
        # E-Mail
        if new_email != mitarbeiter.get('email', ''):
            if update_mitarbeiter_stammdaten(mitarbeiter['id'], 'email', new_email, mitarbeiter.get('email')):
                changes_made = True
        
        # Telefon
        if new_telefon != mitarbeiter.get('telefon', ''):
            if update_mitarbeiter_stammdaten(mitarbeiter['id'], 'telefon', new_telefon, mitarbeiter.get('telefon')):
                changes_made = True
        
        # Straße
        if new_strasse != mitarbeiter.get('strasse', ''):
            if update_mitarbeiter_stammdaten(mitarbeiter['id'], 'strasse', new_strasse, mitarbeiter.get('strasse')):
                changes_made = True
        
        # PLZ
        if new_plz != mitarbeiter.get('plz', ''):
            if update_mitarbeiter_stammdaten(mitarbeiter['id'], 'plz', new_plz, mitarbeiter.get('plz')):
                changes_made = True
        
        # Ort
        if new_ort != mitarbeiter.get('ort', ''):
            if update_mitarbeiter_stammdaten(mitarbeiter['id'], 'ort', new_ort, mitarbeiter.get('ort')):
                changes_made = True
        
        # Nachname (benötigt Genehmigung)
        if new_nachname and new_nachname != mitarbeiter.get('nachname', ''):
            if not grund:
                st.error("⚠️ Bitte geben Sie einen Grund für die Namensänderung an.")
            else:
                if create_aenderungsanfrage(mitarbeiter['id'], 'nachname', mitarbeiter.get('nachname'), new_nachname, grund):
                    st.success("✅ Änderungsanfrage für Nachname wurde an den Administrator gesendet!")
                    changes_made = True
        
        if changes_made:
            st.success("✅ Ihre Änderungen wurden gespeichert und der Administrator wurde benachrichtigt!")
            st.rerun()
        else:
            st.info("💬 Keine Änderungen vorgenommen.")


def show_passwort_aendern():
    """Zeigt Formular zum Passwort ändern"""
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
                    st.success("✅ Passwort erfolgreich geändert!")
                else:
                    st.error("Fehler beim Ändern des Passworts.")


def show_plauderecke():
    """Zeigt die Plauderecke (interner Chat) an"""
    from utils.chat import get_chat_nachrichten, send_chat_nachricht, delete_chat_nachricht
    from utils.chat_notifications import mark_chat_as_read
    
    # Markiere Chat als gelesen
    mark_chat_as_read(st.session_state.user_id)
    
    st.subheader("💬 Plauderecke")
    st.caption("Interner Chat für alle Mitarbeiter und Administrator")
    
    # Lade Chat-Nachrichten
    nachrichten = get_chat_nachrichten(limit=100, betrieb_id=st.session_state.betrieb_id)
    
    # Chat-Container mit fester Höhe
    chat_container = st.container()
    
    with chat_container:
        if nachrichten:
            for msg in nachrichten:
                # Hole Mitarbeiter-Info
                mitarbeiter_info = msg.get('mitarbeiter', {})
                if mitarbeiter_info:
                    vorname = mitarbeiter_info.get('vorname', 'Unbekannt')
                    nachname = mitarbeiter_info.get('nachname', '')
                else:
                    vorname = msg.get('users', {}).get('username', 'Unbekannt')
                    nachname = ''
                
                # Eigene Nachricht?
                is_own = msg['user_id'] == st.session_state.user_id
                
                # Zeitstempel formatieren
                timestamp = msg['erstellt_am'][:16].replace('T', ' ')
                
                if is_own:
                    # Eigene Nachricht rechts
                    col1, col2 = st.columns([1, 3])
                    with col2:
                        st.markdown(f"""
                        <div style="background-color: #0d6efd; padding: 0.75rem; border-radius: 10px; margin-bottom: 0.5rem; text-align: right;">
                            <strong style="color: #ffffff;">Sie</strong><br>
                            <span style="color: #ffffff;">{msg['nachricht']}</span><br>
                            <small style="color: #e0e0e0;">{timestamp}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("🗑️", key=f"delete_{msg['id']}", help="Nachricht löschen"):
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
            st.info("Noch keine Nachrichten. Seien Sie der Erste!")
    
    st.markdown("---")
    
    # Nachricht senden
    with st.form("send_message_form", clear_on_submit=True):
        nachricht = st.text_area("Nachricht schreiben", placeholder="Ihre Nachricht...", height=100)
        submit = st.form_submit_button("📤 Senden", use_container_width=True)
        
        if submit and nachricht.strip():
            if send_chat_nachricht(st.session_state.user_id, nachricht.strip(), st.session_state.betrieb_id):
                st.success("✅ Nachricht gesendet!")
                st.rerun()
            else:
                st.error("Fehler beim Senden der Nachricht.")


def show_urlaubskalender():
    """Zeigt Urlaubskalender aller Mitarbeiter an"""
    st.markdown('<div class="section-header">📅 Urlaubskalender - Übersicht aller Mitarbeiter</div>', unsafe_allow_html=True)
    
    st.info("ℹ️ Hier siehst du alle genehmigten Urlaube aller Mitarbeiter. So kannst du deine eigenen Urlaubsanträge besser planen.")
    
    # Zeitraum-Auswahl
    col1, col2 = st.columns(2)
    
    with col1:
        # Aktueller Monat als Standard
        heute = date.today()
        jahr = st.selectbox("Jahr", range(heute.year - 1, heute.year + 2), index=1)
    
    with col2:
        monate = [
            "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember"
        ]
        monat = st.selectbox("Monat", range(1, 13), format_func=lambda x: monate[x-1], index=heute.month-1)
    
    # Lade alle genehmigten Urlaube für den gewählten Zeitraum
    supabase = get_supabase_client()
    
    # Berechne Start- und Enddatum des Monats
    from calendar import monthrange
    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, monthrange(jahr, monat)[1])
    
    try:
        # Lade alle genehmigten Urlaubsanträge
        urlaube_response = supabase.table('urlaubsantraege').select(
            'id, mitarbeiter_id, von_datum, bis_datum, status, mitarbeiter(vorname, nachname)'
        ).eq('status', 'genehmigt').gte('bis_datum', str(erster_tag)).lte('von_datum', str(letzter_tag)).execute()
        
        if not urlaube_response.data:
            st.info(f"📭 Keine genehmigten Urlaube im {monate[monat-1]} {jahr}")
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
                    
                    # Zeige Urlaub
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"📅 **Von:** {von_str}")
                    with col2:
                        st.write(f"📅 **Bis:** {bis_str}")
                    with col3:
                        st.write(f"🗓️ **{tage} Tag{'e' if tage != 1 else ''}**")
                    
                    st.markdown("---")
        
        # Statistik
        st.markdown("### 📊 Statistik")
        col1, col2 = st.columns(2)
        
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
        
        # Kalender-Ansicht (optional)
        st.markdown("---")
        st.markdown("### 📆 Kalender-Ansicht")
        
        # Erstelle einfache Kalender-Tabelle
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
        
        cal = calendar.monthcalendar(jahr, monat)
        
        # Wochentage als Header
        wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        
        # Erstelle HTML-Tabelle
        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr>' + ''.join([f'<th style="border: 1px solid #ddd; padding: 8px; text-align: center;">{tag}</th>' for tag in wochentage]) + '</tr>'
        
        for woche in cal:
            html += '<tr>'
            for tag in woche:
                if tag == 0:
                    html += '<td style="border: 1px solid #ddd; padding: 8px;"></td>'
                else:
                    aktuelles_datum = date(jahr, monat, tag)
                    
                    # Prüfe ob an diesem Tag jemand im Urlaub ist
                    urlaub_heute = []
                    for urlaub in urlaube_response.data:
                        von = datetime.strptime(urlaub['von_datum'], '%Y-%m-%d').date()
                        bis = datetime.strptime(urlaub['bis_datum'], '%Y-%m-%d').date()
                        if von <= aktuelles_datum <= bis:
                            urlaub_heute.append(urlaub['mitarbeiter']['vorname'][0] + urlaub['mitarbeiter']['nachname'][0])
                    
                    # Färbe Zelle wenn Urlaub
                    if urlaub_heute:
                        bg_color = '#ffeb3b'  # Gelb für Urlaub
                        title = f"{len(urlaub_heute)} im Urlaub: {', '.join(urlaub_heute)}"
                        html += f'<td style="border: 1px solid #ddd; padding: 8px; background-color: {bg_color}; text-align: center;" title="{title}"><strong>{tag}</strong><br><small>🏖️ {len(urlaub_heute)}</small></td>'
                    else:
                        html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{tag}</td>'
            html += '</tr>'
        
        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)
        
        st.caption("💡 Tipp: Gelb markierte Tage zeigen an, dass Mitarbeiter im Urlaub sind. Fahre mit der Maus über die Zelle für Details.")
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Urlaube: {str(e)}")
