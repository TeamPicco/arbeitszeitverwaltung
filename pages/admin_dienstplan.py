"""
Admin-Dienstplanung
Monatliche Dienstplan-Erstellung und Schichtverwaltung
"""

import streamlit as st
from datetime import datetime, date, timedelta
import calendar
import locale
from utils.database import get_supabase_client, get_all_mitarbeiter
from utils.calculations import berechne_arbeitsstunden_mit_pause

# Deutsche Monatsnamen
MONATE_DE = [
    "",  # Index 0 (leer, da Monate 1-12 sind)
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

# Setze Locale auf Deutsch für Monatsnamen
try:
    locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'de_DE')
    except:
        pass  # Fallback: Englisch bleibt


def show_dienstplanung():
    """Zeigt die Dienstplanung für Administratoren an"""
    
    st.markdown('<div class="section-header">📅 Dienstplanung</div>', unsafe_allow_html=True)
    
    supabase = get_supabase_client()
    
    # Tab-Navigation
    tabs = st.tabs(["📆 Monatsplan", "📊 Monatsübersicht (Tabelle)", "⚙️ Schichtvorlagen"])
    
    with tabs[0]:
        show_monatsplan(supabase)
    
    with tabs[1]:
        show_monatsuebersicht_tabelle(supabase)
    
    with tabs[2]:
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
                            format_func=lambda x: MONATE_DE[x])
    
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
    st.markdown(f"### {MONATE_DE[monat]} {jahr}")
    
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
                st.markdown(f"**{len(mitarbeiter_dienste)} Dienste im {MONATE_DE[monat]}**")
                
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
    
    st.info("💡 Erstellen Sie wiederverwendbare Schichtvorlagen (z.B. Frühschicht, Spätschicht, Urlaub) für schnellere Dienstplanung.")
    
    # Lade Schichtvorlagen
    vorlagen = supabase.table('schichtvorlagen').select('*').eq(
        'betrieb_id', st.session_state.betrieb_id
    ).order('name').execute()
    
    # Neue Vorlage erstellen
    with st.expander("➕ Neue Schichtvorlage erstellen", expanded=False):
        with st.form("neue_vorlage_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name", placeholder="z.B. Frühschicht oder Urlaub")
                beschreibung = st.text_area("Beschreibung (optional)", placeholder="z.B. Frühschicht 08:00 - 16:00")
                ist_urlaub = st.checkbox("🏖️ Urlaub-Schicht (keine festen Zeiten)", help="Für Urlaubstage - Stunden werden automatisch berechnet")
            
            with col2:
                if not ist_urlaub:
                    start_zeit = st.time_input("Startzeit", value=datetime.strptime("08:00", "%H:%M").time(), key="neue_vorlage_start")
                    ende_zeit = st.time_input("Endzeit", value=datetime.strptime("16:00", "%H:%M").time(), key="neue_vorlage_ende")
                    
                    # Berechne automatische Pause nach ArbZG
                    if start_zeit and ende_zeit:
                        brutto_stunden, vorgeschlagene_pause = berechne_arbeitsstunden_mit_pause(start_zeit, ende_zeit)
                        st.info(f"⚙️ **Gesetzliche Pause:** {vorgeschlagene_pause} Min (bei {brutto_stunden:.1f}h Arbeitszeit)")
                        pause_minuten = st.number_input("Pause (Minuten)", min_value=0, max_value=240, value=vorgeschlagene_pause, step=15, help="Gesetzlich vorgeschrieben nach § 4 ArbZG")
                    else:
                        pause_minuten = st.number_input("Pause (Minuten)", min_value=0, max_value=240, value=30, step=15)
                else:
                    st.info("💡 Bei Urlaub werden Zeiten automatisch aus Mitarbeiterprofil berechnet")
                    start_zeit = datetime.strptime("00:00", "%H:%M").time()
                    ende_zeit = datetime.strptime("00:00", "%H:%M").time()
                    pause_minuten = 0
            
            farbe = st.color_picker("Farbe für Kalender", value="#ffeb3b" if ist_urlaub else "#0d6efd")
            
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
                        'farbe': farbe,
                        'ist_urlaub': ist_urlaub
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



def show_monatsuebersicht_tabelle(supabase):
    """Zeigt Monatsübersicht aller Mitarbeiter in Tabellenform"""
    
    st.subheader("📊 Monatsübersicht (Tabelle)")
    
    st.info("💡 Übersicht aller Mitarbeiter und deren Schichten für den gesamten Monat in Tabellenform.")
    
    # Monat auswählen
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024, key="tabelle_jahr")
    
    with col2:
        monat = st.selectbox("Monat", range(1, 13), index=date.today().month - 1, 
                            format_func=lambda x: MONATE_DE[x], key="tabelle_monat")
    
    with col3:
        if st.button("🔄 Aktualisieren", use_container_width=True, key="tabelle_refresh"):
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
    
    # Lade Urlaubsanträge für den Monat
    urlaube = supabase.table('urlaubsantraege').select('*').eq(
        'status', 'Genehmigt'
    ).gte('bis_datum', erster_tag.isoformat()).lte('von_datum', letzter_tag.isoformat()).execute()
    
    # Organisiere Dienstpläne nach Mitarbeiter und Datum
    dienste_map = {}
    if dienstplaene.data:
        for dienst in dienstplaene.data:
            key = (dienst['mitarbeiter_id'], dienst['datum'])
            dienste_map[key] = dienst
    
    # Organisiere Urlaube nach Mitarbeiter
    urlaub_map = {}
    if urlaube.data:
        for urlaub in urlaube.data:
            von = datetime.fromisoformat(urlaub['von_datum']).date()
            bis = datetime.fromisoformat(urlaub['bis_datum']).date()
            
            # Erstelle Eintrag für jeden Urlaubstag
            aktuelles_datum = von
            while aktuelles_datum <= bis:
                if erster_tag <= aktuelles_datum <= letzter_tag:
                    key = (urlaub['mitarbeiter_id'], aktuelles_datum.isoformat())
                    urlaub_map[key] = urlaub
                aktuelles_datum += timedelta(days=1)
    
    st.markdown("---")
    
    # Erstelle Tabelle
    anzahl_tage = calendar.monthrange(jahr, monat)[1]
    
    # HTML-Tabelle erstellen
    html = '<div style="overflow-x: auto;"><table style="width:100%; border-collapse: collapse; font-size: 0.85rem;">'
    
    # Header-Zeile
    html += '<thead><tr>'
    html += '<th style="border: 1px solid #ddd; padding: 8px; background-color: #1e3a5f; color: white; position: sticky; left: 0; z-index: 10;">Mitarbeiter</th>'
    
    for tag in range(1, anzahl_tage + 1):
        tag_datum = date(jahr, monat, tag)
        wochentag_kurz = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][tag_datum.weekday()]
        
        # Ruhetage (Mo/Di) hervorheben
        if tag_datum.weekday() in [0, 1]:
            bg_color = '#f0f0f0'
        else:
            bg_color = '#1e3a5f'
        
        html += f'<th style="border: 1px solid #ddd; padding: 6px; background-color: {bg_color}; color: white; text-align: center; min-width: 60px;">{tag}<br><small>{wochentag_kurz}</small></th>'
    
    html += '</tr></thead>'
    
    # Body - Mitarbeiter-Zeilen
    html += '<tbody>'
    
    for mitarbeiter in mitarbeiter_liste:
        html += '<tr>'
        html += f'<td style="border: 1px solid #ddd; padding: 8px; background-color: #f8f9fa; font-weight: bold; position: sticky; left: 0; z-index: 5;">{mitarbeiter["vorname"]} {mitarbeiter["nachname"]}</td>'
        
        for tag in range(1, anzahl_tage + 1):
            tag_datum = date(jahr, monat, tag)
            key = (mitarbeiter['id'], tag_datum.isoformat())
            
            # Prüfe ob Urlaub
            if key in urlaub_map:
                html += '<td style="border: 1px solid #ddd; padding: 6px; text-align: center; background-color: #ffeb3b;" title="Urlaub"><strong>U</strong></td>'
            # Prüfe ob Dienst
            elif key in dienste_map:
                dienst = dienste_map[key]
                
                # Hole Schichtvorlage
                if dienst.get('schichtvorlage_id') and dienst['schichtvorlage_id'] in vorlagen_dict:
                    vorlage = vorlagen_dict[dienst['schichtvorlage_id']]
                    kuerzel = vorlage['name'][:1].upper()  # Erster Buchstabe
                    zeiten = f"{dienst['start_zeit'][:5]}-{dienst['ende_zeit'][:5]}"
                    farbe = vorlage.get('farbe', '#0d6efd')
                    title = f"{vorlage['name']}: {zeiten}"
                else:
                    kuerzel = 'D'
                    zeiten = f"{dienst['start_zeit'][:5]}-{dienst['ende_zeit'][:5]}"
                    farbe = '#6c757d'
                    title = f"Dienst: {zeiten}"
                
                html += f'<td style="border: 1px solid #ddd; padding: 6px; text-align: center; background-color: {farbe}20;" title="{title}"><strong>{kuerzel}</strong><br><small>{zeiten}</small></td>'
            # Ruhetag (Mo/Di)
            elif tag_datum.weekday() in [0, 1]:
                html += '<td style="border: 1px solid #ddd; padding: 6px; text-align: center; background-color: #f0f0f0; color: #999;">-</td>'
            # Frei
            else:
                html += '<td style="border: 1px solid #ddd; padding: 6px; text-align: center;"></td>'
        
        html += '</tr>'
    
    html += '</tbody></table></div>'
    
    st.markdown(html, unsafe_allow_html=True)
    
    # Legende
    st.markdown("---")
    st.markdown("### 📋 Legende")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**U** = Urlaub")
    
    with col2:
        st.markdown("**-** = Ruhetag (Mo/Di)")
    
    with col3:
        st.markdown("**Kürzel** = Schichtname")
    
    with col4:
        st.markdown("**Zeiten** = Start-Ende")
    
    # Export-Optionen
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Als CSV exportieren", use_container_width=True):
            # Erstelle CSV
            csv_data = "Mitarbeiter," + ",".join([str(tag) for tag in range(1, anzahl_tage + 1)]) + "\n"
            
            for mitarbeiter in mitarbeiter_liste:
                row = f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}"
                
                for tag in range(1, anzahl_tage + 1):
                    tag_datum = date(jahr, monat, tag)
                    key = (mitarbeiter['id'], tag_datum.isoformat())
                    
                    if key in urlaub_map:
                        row += ",U"
                    elif key in dienste_map:
                        dienst = dienste_map[key]
                        if dienst.get('schichtvorlage_id') and dienst['schichtvorlage_id'] in vorlagen_dict:
                            vorlage = vorlagen_dict[dienst['schichtvorlage_id']]
                            row += f",{vorlage['name'][:1]} {dienst['start_zeit'][:5]}-{dienst['ende_zeit'][:5]}"
                        else:
                            row += f",D {dienst['start_zeit'][:5]}-{dienst['ende_zeit'][:5]}"
                    elif tag_datum.weekday() in [0, 1]:
                        row += ",-"
                    else:
                        row += ","
                
                csv_data += row + "\n"
            
            st.download_button(
                label="💾 CSV herunterladen",
                data=csv_data,
                file_name=f"dienstplan_{MONATE_DE[monat]}_{jahr}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col2:
        st.info("💡 PDF-Export folgt in Kürze")
