"""
Mitarbeiter-Dienstplan-Ansicht
Zeigt nur die eigenen Dienste des eingeloggten Mitarbeiters
"""

import streamlit as st
from datetime import datetime, date, timedelta
import calendar
import locale
from utils.database import get_supabase_client

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


def show_mitarbeiter_dienstplan(mitarbeiter: dict):
    """Zeigt den Dienstplan für den eingeloggten Mitarbeiter"""
    
    st.subheader("📅 Mein Dienstplan")
    
    supabase = get_supabase_client()
    
    # Monat auswählen
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024, key="mitarbeiter_dienstplan_jahr")
    
    with col2:
        monat = st.selectbox("Monat", range(1, 13), index=date.today().month - 1, 
                            format_func=lambda x: MONATE_DE[x], key="mitarbeiter_dienstplan_monat")
    
    with col3:
        if st.button("🔄 Aktualisieren", use_container_width=True, key="mitarbeiter_dienstplan_refresh"):
            st.rerun()
    
    # Lade Dienstpläne für den Monat (nur eigene!)
    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
    
    dienstplaene = supabase.table('dienstplaene').select(
        '*, schichtvorlagen(name, farbe)'
    ).eq('mitarbeiter_id', mitarbeiter['id']).gte(
        'datum', erster_tag.isoformat()
    ).lte('datum', letzter_tag.isoformat()).order('datum').execute()
    
    st.markdown("---")
    
    if dienstplaene.data and len(dienstplaene.data) > 0:
        st.success(f"✅ **{len(dienstplaene.data)} Dienste** im {MONATE_DE[monat]} {jahr}")
        
        # Zeige Kalender-Ansicht
        show_kalender_ansicht(dienstplaene.data, jahr, monat)
        
        st.markdown("---")
        
        # Zeige Listen-Ansicht
        st.markdown("### 📋 Detaillierte Übersicht")
        
        # Berechne Gesamtstunden
        total_stunden = 0
        
        for dienst in dienstplaene.data:
            datum_obj = datetime.fromisoformat(dienst['datum']).date()
            wochentag = calendar.day_name[datum_obj.weekday()]
            
            # Berechne Arbeitsstunden
            start = datetime.strptime(dienst['start_zeit'], '%H:%M:%S').time()
            ende = datetime.strptime(dienst['ende_zeit'], '%H:%M:%S').time()
            
            start_dt = datetime.combine(date.today(), start)
            ende_dt = datetime.combine(date.today(), ende)
            
            # Wenn Ende vor Start liegt, ist es am nächsten Tag
            if ende_dt <= start_dt:
                ende_dt += timedelta(days=1)
            
            stunden = (ende_dt - start_dt).total_seconds() / 3600
            stunden -= dienst.get('pause_minuten', 0) / 60
            total_stunden += stunden
            
            # Farbe der Schichtvorlage
            farbe = "#6c757d"  # Standard-Grau
            schicht_name = "Benutzerdefiniert"
            
            if dienst.get('schichtvorlagen'):
                schicht_name = dienst['schichtvorlagen']['name']
                farbe = dienst['schichtvorlagen'].get('farbe', '#6c757d')
            
            # Zeige Dienst
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                
                with col1:
                    st.markdown(f"**{datum_obj.strftime('%d.%m.%Y')}**")
                    st.caption(wochentag)
                
                with col2:
                    st.markdown(f"<span style='background-color: {farbe}; padding: 2px 8px; border-radius: 3px; color: white;'>{schicht_name}</span>", unsafe_allow_html=True)
                
                with col3:
                    st.write(f"⏰ {dienst['start_zeit'][:5]} - {dienst['ende_zeit'][:5]}")
                    if dienst.get('pause_minuten', 0) > 0:
                        st.caption(f"☕ Pause: {dienst['pause_minuten']} Min")
                
                with col4:
                    st.write(f"📊 {stunden:.2f}h")
                
                if dienst.get('notiz'):
                    st.caption(f"📝 {dienst['notiz']}")
                
                st.markdown("---")
        
        # Zeige Gesamtstunden
        st.info(f"📊 **Gesamtstunden im {MONATE_DE[monat]}:** {total_stunden:.2f} Stunden")
        
    else:
        st.info(f"ℹ️ Keine Dienste für {MONATE_DE[monat]} {jahr} geplant.")
        st.caption("Ihr Administrator hat noch keine Dienste für Sie eingetragen.")


def show_kalender_ansicht(dienstplaene: list, jahr: int, monat: int):
    """Zeigt eine Kalender-Ansicht der Dienste"""
    
    st.markdown("### 📆 Kalender-Ansicht")
    
    # Erstelle Kalender-Dict
    dienste_dict = {datetime.fromisoformat(d['datum']).date(): d for d in dienstplaene}
    
    # Kalender-Grid
    erster_tag = date(jahr, monat, 1)
    letzter_tag = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
    
    # Wochentage als Header
    wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    cols = st.columns(7)
    for i, tag in enumerate(wochentage):
        with cols[i]:
            st.markdown(f"**{tag}**")
    
    # Kalender-Tage
    aktueller_tag = erster_tag
    
    # Fülle erste Woche mit leeren Zellen
    wochentag_start = erster_tag.weekday()  # 0 = Montag
    
    cols = st.columns(7)
    for i in range(wochentag_start):
        with cols[i]:
            st.write("")
    
    # Zeige alle Tage
    while aktueller_tag <= letzter_tag:
        wochentag = aktueller_tag.weekday()
        
        if wochentag == 0:  # Neue Woche
            cols = st.columns(7)
        
        with cols[wochentag]:
            if aktueller_tag in dienste_dict:
                dienst = dienste_dict[aktueller_tag]
                
                # Farbe der Schichtvorlage
                farbe = "#198754"  # Standard-Grün
                if dienst.get('schichtvorlagen'):
                    farbe = dienst['schichtvorlagen'].get('farbe', '#198754')
                
                st.markdown(f"""
                <div style="background-color: {farbe}; padding: 5px; border-radius: 5px; text-align: center; color: white;">
                    <strong>{aktueller_tag.day}</strong><br>
                    <small>{dienst['start_zeit'][:5]}</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 5px; border-radius: 5px; text-align: center; color: #6c757d; border: 1px solid #dee2e6;">
                    {aktueller_tag.day}
                </div>
                """, unsafe_allow_html=True)
        
        aktueller_tag += timedelta(days=1)
