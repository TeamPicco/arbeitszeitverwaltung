"""
Admin-Dienstplanung
Monatliche Dienstplan-Erstellung und Schichtverwaltung
"""

import streamlit as st
from datetime import datetime, date, timedelta
import calendar
from utils.database import get_supabase_client, get_all_mitarbeiter


def show_dienstplanung():
    """Zeigt die Dienstplanung für Administratoren an"""
    
    st.markdown('<div class="section-header">📅 Dienstplanung</div>', unsafe_allow_html=True)
    
    supabase = get_supabase_client()
    
    # Tab-Navigation
    tabs = st.tabs(["📆 Monatsplan", "⚙️ Schichtvorlagen"])
    
    with tabs[0]:
        show_monatsplan(supabase)
    
    with tabs[1]:
        show_schichtvorlagen(supabase)


def show_monatsplan(supabase):
    """Zeigt den monatlichen Dienstplan an"""
    
    st.subheader("📆 Monatlicher Dienstplan")
    
    # Monat auswählen
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024)
    
    with col2:
        monat = st.selectbox("Monat", range(1, 13), index=date.today().month - 1, 
                            format_func=lambda x: calendar.month_name[x])
    
    with col3:
        if st.button("🔄 Aktualisieren", use_container_width=True):
            st.rerun()
    
    # Lade Mitarbeiter
    mitarbeiter_liste = get_all_mitarbeiter()
    
    if not mitarbeiter_liste:
        st.warning("Keine Mitarbeiter gefunden.")
        return
    
    # Lade Schichtvorlagen
    schichtvorlagen = supabase.table('schichtvorlagen').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).execute()
    
    vorlagen_dict = {v['id']: v for v in schichtvorlagen.data} if schichtvorlagen.data else {}
    
    # Lade Dienstpläne für den Monat
    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
    
    dienstplaene = supabase.table('dienstplaene').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).gte('datum', erster_tag.isoformat()).lte('datum', letzter_tag.isoformat()).execute()
    
    # Organisiere Dienstpläne nach Mitarbeiter und Datum
    dienste_map = {}
    if dienstplaene.data:
        for dienst in dienstplaene.data:
            key = (dienst['mitarbeiter_id'], dienst['datum'])
            dienste_map[key] = dienst
    
    st.markdown("---")
    
    # Zeige Kalender-Ansicht
    st.markdown(f"### {calendar.month_name[monat]} {jahr}")
    
    # Mitarbeiter-Auswahl für Schnellplanung
    with st.expander("➥ Schnellplanung - Dienst hinzufügen"):
        st.info("📅 **Betriebszeiten:** Mittwoch - Sonntag | **Ruhetage:** Montag & Dienstag")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            mitarbeiter_id = st.selectbox(
                "Mitarbeiter",
                options=[m['id'] for m in mitarbeiter_liste],
                format_func=lambda x: next((f"{m['vorname']} {m['nachname']}" for m in mitarbeiter_liste if m['id'] == x), "")
            )
        
        with col2:
            dienst_datum = st.date_input(
                "Datum",
                value=erster_tag,
                min_value=erster_tag,
                max_value=letzter_tag,
                format="DD.MM.YYYY"
            )
            
            # Warnung bei Montag/Dienstag
            if dienst_datum.weekday() in [0, 1]:  # 0=Montag, 1=Dienstag
                wochentag = "Montag" if dienst_datum.weekday() == 0 else "Dienstag"
                st.warning(f"⚠️ {wochentag} ist ein Ruhetag!")
        
        with col3:
            if vorlagen_dict:
                vorlage_id = st.selectbox(
                    "Schichtvorlage",
                    options=[None] + list(vorlagen_dict.keys()),
                    format_func=lambda x: "Benutzerdefiniert" if x is None else vorlagen_dict[x]['name']
                )
            else:
                vorlage_id = None
                st.info("Keine Schichtvorlagen vorhanden")
        
        with col4:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("➥ Hinzufügen", use_container_width=True, type="primary"):
                if vorlage_id:
                    vorlage = vorlagen_dict[vorlage_id]
                    try:
                        # Zusätzliche Warnung bei Ruhetagen
                        if dienst_datum.weekday() in [0, 1]:
                            wochentag = "Montag" if dienst_datum.weekday() == 0 else "Dienstag"
                            st.warning(f"⚠️ Hinweis: {wochentag} ist normalerweise ein Ruhetag. Dienst wird trotzdem hinzugefügt.")
                        
                        supabase.table('dienstplaene').insert({
                            'betrieb_id': st.session_state.betrieb_id,
                            'mitarbeiter_id': mitarbeiter_id,
                            'datum': dienst_datum.isoformat(),
                            'schichtvorlage_id': vorlage_id,
                            'start_zeit': vorlage['start_zeit'],
                            'ende_zeit': vorlage['ende_zeit'],
                            'pause_minuten': vorlage['pause_minuten']
                        }).execute()
                        st.success("✅ Dienst hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        if "duplicate key" in str(e).lower():
                            st.error("❌ Für diesen Mitarbeiter existiert bereits ein Dienst an diesem Tag.")
                        else:
                            st.error(f"Fehler: {str(e)}")
                else:
                    st.warning("Bitte wählen Sie eine Schichtvorlage.")
    
    st.markdown("---")
    
    # Zeige Dienstplan-Tabelle
    for mitarbeiter in mitarbeiter_liste:
        with st.expander(f"👤 {mitarbeiter['vorname']} {mitarbeiter['nachname']}", expanded=False):
            
            # Zeige Dienste für diesen Mitarbeiter im Monat
            mitarbeiter_dienste = [d for d in (dienstplaene.data or []) if d['mitarbeiter_id'] == mitarbeiter['id']]
            
            if mitarbeiter_dienste:
                st.markdown(f"**{len(mitarbeiter_dienste)} Dienste im {calendar.month_name[monat]}**")
                
                for dienst in sorted(mitarbeiter_dienste, key=lambda x: x['datum']):
                    datum_obj = datetime.fromisoformat(dienst['datum']).date()
                    wochentag = calendar.day_name[datum_obj.weekday()]
                    
                    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
                    
                    with col1:
                        st.write(f"**{datum_obj.strftime('%d.%m.%Y')}**")
                        st.caption(wochentag)
                    
                    with col2:
                        if dienst.get('schichtvorlage_id') and dienst['schichtvorlage_id'] in vorlagen_dict:
                            vorlage = vorlagen_dict[dienst['schichtvorlage_id']]
                            st.write(f"🏷️ {vorlage['name']}")
                        else:
                            st.write("📝 Benutzerdefiniert")
                    
                    with col3:
                        st.write(f"⏰ {dienst['start_zeit']} - {dienst['ende_zeit']}")
                        if dienst.get('pause_minuten', 0) > 0:
                            st.caption(f"Pause: {dienst['pause_minuten']} Min")
                    
                    with col4:
                        if st.button("🗑️", key=f"del_{dienst['id']}", help="Dienst löschen"):
                            try:
                                supabase.table('dienstplaene').delete().eq('id', dienst['id']).execute()
                                st.success("✅ Dienst gelöscht!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {str(e)}")
            else:
                st.info("Keine Dienste für diesen Monat geplant.")


def show_schichtvorlagen(supabase):
    """Zeigt die Schichtvorlagen-Verwaltung an"""
    
    st.subheader("⚙️ Schichtvorlagen")
    
    st.info("💡 Erstellen Sie wiederverwendbare Schichtvorlagen (z.B. Frühschicht, Spätschicht) für schnellere Dienstplanung.")
    
    # Lade Schichtvorlagen
    vorlagen = supabase.table('schichtvorlagen').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).order('name').execute()
    
    # Neue Vorlage erstellen
    with st.expander("➕ Neue Schichtvorlage erstellen", expanded=False):
        with st.form("neue_vorlage_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name", placeholder="z.B. Frühschicht")
                beschreibung = st.text_area("Beschreibung (optional)", placeholder="z.B. Frühschicht 08:00 - 16:00")
            
            with col2:
                start_zeit = st.time_input("Startzeit", value=datetime.strptime("08:00", "%H:%M").time())
                ende_zeit = st.time_input("Endzeit", value=datetime.strptime("16:00", "%H:%M").time())
                pause_minuten = st.number_input("Pause (Minuten)", min_value=0, max_value=240, value=30, step=15)
            
            farbe = st.color_picker("Farbe für Kalender", value="#0d6efd")
            
            submit = st.form_submit_button("💾 Vorlage speichern", use_container_width=True)
            
            if submit and name:
                try:
                    supabase.table('schichtvorlagen').insert({
                        'betrieb_id': st.session_state.betrieb_id,
                        'name': name,
                        'beschreibung': beschreibung if beschreibung else None,
                        'start_zeit': start_zeit.strftime('%H:%M:%S'),
                        'ende_zeit': ende_zeit.strftime('%H:%M:%S'),
                        'pause_minuten': pause_minuten,
                        'farbe': farbe
                    }).execute()
                    st.success("✅ Schichtvorlage erstellt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {str(e)}")
    
    st.markdown("---")
    
    # Zeige vorhandene Vorlagen
    if vorlagen.data:
        st.markdown(f"**{len(vorlagen.data)} Schichtvorlagen**")
        
        for vorlage in vorlagen.data:
            with st.expander(f"🏷️ {vorlage['name']}", expanded=False):
                # Prüfe ob Bearbeiten-Modus aktiv
                edit_mode = st.session_state.get(f"edit_vorlage_{vorlage['id']}", False)
                
                if edit_mode:
                    # Bearbeiten-Formular
                    with st.form(f"edit_vorlage_form_{vorlage['id']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            name = st.text_input("Name", value=vorlage['name'])
                            beschreibung = st.text_area("Beschreibung (optional)", value=vorlage.get('beschreibung', ''))
                        
                        with col2:
                            start_zeit = st.time_input("Startzeit", value=datetime.strptime(vorlage['start_zeit'], '%H:%M:%S').time())
                            ende_zeit = st.time_input("Endzeit", value=datetime.strptime(vorlage['ende_zeit'], '%H:%M:%S').time())
                            pause_minuten = st.number_input("Pause (Minuten)", min_value=0, max_value=240, value=vorlage.get('pause_minuten', 0), step=15)
                        
                        farbe = st.color_picker("Farbe für Kalender", value=vorlage.get('farbe', '#0d6efd'))
                        
                        col_save, col_cancel = st.columns(2)
                        
                        with col_save:
                            submit = st.form_submit_button("💾 Speichern", use_container_width=True, type="primary")
                        
                        with col_cancel:
                            cancel = st.form_submit_button("❌ Abbrechen", use_container_width=True)
                        
                        if submit and name:
                            try:
                                supabase.table('schichtvorlagen').update({
                                    'name': name,
                                    'beschreibung': beschreibung if beschreibung else None,
                                    'start_zeit': start_zeit.strftime('%H:%M:%S'),
                                    'ende_zeit': ende_zeit.strftime('%H:%M:%S'),
                                    'pause_minuten': pause_minuten,
                                    'farbe': farbe,
                                    'updated_at': 'now()'
                                }).eq('id', vorlage['id']).execute()
                                
                                st.session_state[f"edit_vorlage_{vorlage['id']}"] = False
                                st.success("✅ Vorlage aktualisiert!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {str(e)}")
                        
                        if cancel:
                            st.session_state[f"edit_vorlage_{vorlage['id']}"] = False
                            st.rerun()
                else:
                    # Ansicht-Modus
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**Zeiten:** {vorlage['start_zeit']} - {vorlage['ende_zeit']}")
                        if vorlage.get('pause_minuten', 0) > 0:
                            st.write(f"**Pause:** {vorlage['pause_minuten']} Minuten")
                    
                    with col2:
                        if vorlage.get('beschreibung'):
                            st.write(f"**Beschreibung:** {vorlage['beschreibung']}")
                        st.markdown(f"**Farbe:** <span style='background-color: {vorlage['farbe']}; padding: 2px 10px; border-radius: 3px; color: white;'>{vorlage['farbe']}</span>", unsafe_allow_html=True)
                    
                    with col3:
                        if st.button("✏️", key=f"edit_btn_{vorlage['id']}", help="Bearbeiten"):
                            st.session_state[f"edit_vorlage_{vorlage['id']}"] = True
                            st.rerun()
                        
                        if st.button("🗑️", key=f"del_vorlage_{vorlage['id']}", help="Löschen"):
                            try:
                                supabase.table('schichtvorlagen').delete().eq('id', vorlage['id']).execute()
                                st.success("✅ Vorlage gelöscht!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {str(e)}")
    else:
        st.info("Noch keine Schichtvorlagen vorhanden. Erstellen Sie Ihre erste Vorlage!")
