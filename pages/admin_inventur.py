"""
Inventur-Modul für Administratoren
Jahresbasierte Inventur mit Kategorien und Artikeln
"""

import streamlit as st
from datetime import datetime, date
from utils.database import get_supabase_client
import pandas as pd


def show_inventur():
    """Zeigt das Inventur-Modul für Administratoren"""
    
    st.subheader("📦 Inventur")
    
    supabase = get_supabase_client()
    betrieb_id = st.session_state.get('betrieb_id')
    
    # Tabs
    tabs = st.tabs([
        "📋 Inventur durchführen",
        "📊 Inventur-Historie",
        "🏷️ Artikel verwalten",
        "📁 Kategorien verwalten"
    ])
    
    with tabs[0]:
        show_inventur_durchfuehren(supabase, betrieb_id)
    
    with tabs[1]:
        show_inventur_historie(supabase, betrieb_id)
    
    with tabs[2]:
        show_artikel_verwalten(supabase, betrieb_id)
    
    with tabs[3]:
        show_kategorien_verwalten(supabase, betrieb_id)


def show_inventur_durchfuehren(supabase, betrieb_id):
    """Inventur durchführen"""
    
    st.markdown("### 📋 Inventur durchführen")
    
    # Jahr auswählen
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        jahr = st.selectbox("Jahr", range(2024, 2031), index=date.today().year - 2024, key="inventur_jahr")
    
    with col2:
        inventur_datum = st.date_input("Inventurdatum", value=date.today(), key="inventur_datum")
    
    with col3:
        if st.button("🔄 Aktualisieren", use_container_width=True):
            st.rerun()
    
    # Prüfe ob Inventur für dieses Jahr existiert
    inventur = supabase.table('inventuren').select('*').eq('betrieb_id', betrieb_id).eq('jahr', jahr).execute()
    
    if not inventur.data or len(inventur.data) == 0:
        # Neue Inventur erstellen
        st.info(f"ℹ️ Noch keine Inventur für {jahr} vorhanden.")
        
        if st.button("➕ Neue Inventur erstellen", use_container_width=True, type="primary"):
            try:
                # Erstelle Inventur
                neue_inventur = supabase.table('inventuren').insert({
                    'betrieb_id': betrieb_id,
                    'jahr': jahr,
                    'datum': inventur_datum.isoformat(),
                    'erstellt_von': st.session_state.get('user_id'),
                    'status': 'offen'
                }).execute()
                
                st.success(f"✅ Inventur für {jahr} erstellt!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fehler beim Erstellen der Inventur: {e}")
        
        return
    
    # Inventur vorhanden
    inventur_data = inventur.data[0]
    inventur_id = inventur_data['id']
    status = inventur_data['status']
    
    # Status-Badge
    if status == 'offen':
        st.info(f"📋 **Inventur {jahr}** - Status: Offen")
    else:
        st.success(f"✅ **Inventur {jahr}** - Status: Abgeschlossen")
    
    st.markdown("---")
    
    # Lade Kategorien
    kategorien = supabase.table('inventur_kategorien').select('*').eq('betrieb_id', betrieb_id).order('sortierung').execute()
    
    if not kategorien.data or len(kategorien.data) == 0:
        st.warning("⚠️ Keine Kategorien vorhanden. Bitte zuerst Kategorien anlegen.")
        return
    
    # Zeige Kategorien als Expander
    for kategorie in kategorien.data:
        kategorie_id = kategorie['id']
        kategorie_name = kategorie['name']
        
        with st.expander(f"📦 {kategorie_name}", expanded=False):
            show_kategorie_inventur(supabase, inventur_id, kategorie_id, kategorie_name, status)
    
    st.markdown("---")
    
    # Aktionen
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if status == 'offen':
            if st.button("✅ Inventur abschließen", use_container_width=True, type="primary"):
                try:
                    supabase.table('inventuren').update({'status': 'abgeschlossen'}).eq('id', inventur_id).execute()
                    st.success("✅ Inventur abgeschlossen!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fehler: {e}")
    
    with col2:
        if st.button("📥 Als CSV exportieren", use_container_width=True):
            export_inventur_csv(supabase, inventur_id, jahr)
    
    with col3:
        if st.button("📄 Als PDF exportieren", use_container_width=True):
            st.info("PDF-Export wird implementiert...")


def show_kategorie_inventur(supabase, inventur_id, kategorie_id, kategorie_name, status):
    """Zeigt Inventur-Erfassung für eine Kategorie"""
    
    # Lade Artikel der Kategorie
    artikel = supabase.table('inventur_artikel').select('*').eq('kategorie_id', kategorie_id).order('sortierung').execute()
    
    if not artikel.data or len(artikel.data) == 0:
        st.info("Keine Artikel in dieser Kategorie.")
        return
    
    # Lade vorhandene Positionen
    positionen = supabase.table('inventur_positionen').select('*').eq('inventur_id', inventur_id).execute()
    positionen_dict = {p['artikel_id']: p for p in positionen.data} if positionen.data else {}
    
    # Zeige Artikel als Tabelle
    for artikel_data in artikel.data:
        artikel_id = artikel_data['id']
        artikel_name = artikel_data['name']
        einheit = artikel_data['einheit']
        
        # Hole vorhandene Position
        position = positionen_dict.get(artikel_id, {})
        soll_bestand = position.get('soll_bestand', 0)
        ist_bestand = position.get('ist_bestand', 0)
        
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.write(f"**{artikel_name}**")
        
        with col2:
            st.caption(f"Einheit: {einheit}")
        
        with col3:
            if status == 'offen':
                neuer_bestand = st.number_input(
                    "Ist-Bestand",
                    min_value=0.0,
                    value=float(ist_bestand),
                    step=0.1,
                    key=f"bestand_{artikel_id}",
                    label_visibility="collapsed"
                )
                
                # Speichere automatisch bei Änderung
                if neuer_bestand != ist_bestand:
                    try:
                        if artikel_id in positionen_dict:
                            # Update
                            supabase.table('inventur_positionen').update({
                                'ist_bestand': neuer_bestand
                            }).eq('inventur_id', inventur_id).eq('artikel_id', artikel_id).execute()
                        else:
                            # Insert
                            supabase.table('inventur_positionen').insert({
                                'inventur_id': inventur_id,
                                'artikel_id': artikel_id,
                                'soll_bestand': 0,
                                'ist_bestand': neuer_bestand
                            }).execute()
                    except Exception as e:
                        st.error(f"Fehler: {e}")
            else:
                st.write(f"{ist_bestand} {einheit}")
        
        with col4:
            differenz = ist_bestand - soll_bestand
            if differenz > 0:
                st.success(f"+{differenz}")
            elif differenz < 0:
                st.error(f"{differenz}")
            else:
                st.info("0")


def show_inventur_historie(supabase, betrieb_id):
    """Zeigt Inventur-Historie"""
    
    st.markdown("### 📊 Inventur-Historie")
    
    # Lade alle Inventuren
    inventuren = supabase.table('inventuren').select('*').eq('betrieb_id', betrieb_id).order('jahr', desc=True).execute()
    
    if not inventuren.data or len(inventuren.data) == 0:
        st.info("Noch keine Inventuren vorhanden.")
        return
    
    # Zeige als Tabelle
    for inv in inventuren.data:
        jahr = inv['jahr']
        datum = inv['datum']
        status = inv['status']
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        
        with col1:
            st.write(f"**{jahr}**")
        
        with col2:
            st.write(datum)
        
        with col3:
            if status == 'offen':
                st.info("📋 Offen")
            else:
                st.success("✅ Abgeschlossen")
        
        with col4:
            if st.button(f"📄 Anzeigen", key=f"show_{inv['id']}"):
                st.info("Wird implementiert...")


def show_artikel_verwalten(supabase, betrieb_id):
    """Artikel verwalten"""
    
    st.markdown("### 🏷️ Artikel verwalten")
    
    # Lade Kategorien
    kategorien = supabase.table('inventur_kategorien').select('*').eq('betrieb_id', betrieb_id).order('sortierung').execute()
    
    if not kategorien.data or len(kategorien.data) == 0:
        st.warning("⚠️ Keine Kategorien vorhanden. Bitte zuerst Kategorien anlegen.")
        return
    
    # Neuen Artikel hinzufügen
    with st.expander("➕ Neuen Artikel hinzufügen", expanded=False):
        with st.form("neuer_artikel"):
            kategorie_auswahl = st.selectbox(
                "Kategorie",
                options=[(k['id'], k['name']) for k in kategorien.data],
                format_func=lambda x: x[1]
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Artikelname", placeholder="z.B. Becks Pils 30l")
            
            with col2:
                einheit = st.text_input("Einheit", placeholder="z.B. 30L-Fass, kg, Fl")
            
            beschreibung = st.text_area("Beschreibung (optional)")
            
            if st.form_submit_button("💾 Artikel speichern", use_container_width=True):
                if name and einheit:
                    try:
                        supabase.table('inventur_artikel').insert({
                            'betrieb_id': betrieb_id,
                            'kategorie_id': kategorie_auswahl[0],
                            'name': name,
                            'einheit': einheit,
                            'beschreibung': beschreibung
                        }).execute()
                        st.success(f"✅ Artikel '{name}' hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Fehler: {e}")
                else:
                    st.error("Bitte Name und Einheit angeben!")
    
    st.markdown("---")
    
    # Zeige vorhandene Artikel
    for kategorie in kategorien.data:
        with st.expander(f"📦 {kategorie['name']}", expanded=False):
            artikel = supabase.table('inventur_artikel').select('*').eq('kategorie_id', kategorie['id']).order('sortierung').execute()
            
            if artikel.data and len(artikel.data) > 0:
                for art in artikel.data:
                    col1, col2, col3 = st.columns([4, 2, 1])
                    
                    with col1:
                        st.write(f"**{art['name']}**")
                    
                    with col2:
                        st.caption(f"Einheit: {art['einheit']}")
                    
                    with col3:
                        if st.button("🗑️", key=f"del_art_{art['id']}"):
                            try:
                                supabase.table('inventur_artikel').delete().eq('id', art['id']).execute()
                                st.success("Gelöscht!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {e}")
            else:
                st.info("Keine Artikel in dieser Kategorie.")


def show_kategorien_verwalten(supabase, betrieb_id):
    """Kategorien verwalten"""
    
    st.markdown("### 📁 Kategorien verwalten")
    
    # Neue Kategorie hinzufügen
    with st.expander("➕ Neue Kategorie hinzufügen", expanded=False):
        with st.form("neue_kategorie"):
            name = st.text_input("Kategoriename", placeholder="z.B. Fassbiere")
            beschreibung = st.text_area("Beschreibung (optional)")
            
            if st.form_submit_button("💾 Kategorie speichern", use_container_width=True):
                if name:
                    try:
                        supabase.table('inventur_kategorien').insert({
                            'betrieb_id': betrieb_id,
                            'name': name,
                            'beschreibung': beschreibung
                        }).execute()
                        st.success(f"✅ Kategorie '{name}' hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Fehler: {e}")
                else:
                    st.error("Bitte Name angeben!")
    
    st.markdown("---")
    
    # Zeige vorhandene Kategorien
    kategorien = supabase.table('inventur_kategorien').select('*').eq('betrieb_id', betrieb_id).order('sortierung').execute()
    
    if kategorien.data and len(kategorien.data) > 0:
        for kat in kategorien.data:
            col1, col2 = st.columns([6, 1])
            
            with col1:
                st.write(f"**📦 {kat['name']}**")
                if kat.get('beschreibung'):
                    st.caption(kat['beschreibung'])
            
            with col2:
                if st.button("🗑️", key=f"del_kat_{kat['id']}"):
                    try:
                        supabase.table('inventur_kategorien').delete().eq('id', kat['id']).execute()
                        st.success("Gelöscht!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")
    else:
        st.info("Noch keine Kategorien vorhanden.")


def export_inventur_csv(supabase, inventur_id, jahr):
    """Exportiert Inventur als CSV"""
    
    try:
        # Lade Inventur-Daten
        positionen = supabase.table('inventur_positionen').select(
            '*, inventur_artikel(name, einheit, inventur_kategorien(name))'
        ).eq('inventur_id', inventur_id).execute()
        
        if not positionen.data:
            st.warning("Keine Daten vorhanden.")
            return
        
        # Erstelle DataFrame
        data = []
        for pos in positionen.data:
            artikel = pos['inventur_artikel']
            kategorie = artikel['inventur_kategorien']['name']
            
            data.append({
                'Kategorie': kategorie,
                'Artikel': artikel['name'],
                'Einheit': artikel['einheit'],
                'Soll-Bestand': pos['soll_bestand'],
                'Ist-Bestand': pos['ist_bestand'],
                'Differenz': pos['differenz']
            })
        
        df = pd.DataFrame(data)
        
        # CSV-Download
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV herunterladen",
            data=csv,
            file_name=f"inventur_{jahr}.csv",
            mime="text/csv"
        )
    
    except Exception as e:
        st.error(f"❌ Fehler beim Export: {e}")
