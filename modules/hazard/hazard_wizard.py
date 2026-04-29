import streamlit as st
from typing import Optional
from datetime import datetime

GASTRO_WIZARD_SCHRITTE = {
    1: {
        "titel": "Objekt-Analyse",
        "beschreibung": "Beschreibe deinen Betrieb",
        "fragen": [
            {
                "key": "betriebs_typ",
                "frage": "Welche Art von Gastronomie betreibst du?",
                "typ": "single_choice",
                "optionen": ["Restaurant", "Café", "Bar/Kneipe", "Imbiss/Snackbar", "Hotel-Restaurant", "Catering", "Foodtruck"]
            },
            {
                "key": "anzahl_mitarbeiter",
                "frage": "Wie viele Mitarbeiter hast du?",
                "typ": "single_choice",
                "optionen": ["1-5", "6-10", "11-20", "21-50", "Über 50"]
            },
            {
                "key": "betrieb_groesse_qm",
                "frage": "Wie groß ist dein Betrieb (in m²)?",
                "typ": "single_choice",
                "optionen": ["Bis 50 m²", "51-100 m²", "101-200 m²", "201-500 m²", "Über 500 m²"]
            }
        ]
    },
    2: {
        "titel": "Räumlichkeiten",
        "beschreibung": "Welche Räume gibt es?",
        "fragen": [
            {
                "key": "etagen",
                "frage": "Über wie viele Etagen erstreckt sich dein Betrieb?",
                "typ": "single_choice",
                "optionen": ["Nur ebenerdig", "2 Etagen", "3 Etagen", "Mehr als 3 Etagen", "Mit Keller/Untergeschoss"]
            },
            {
                "key": "raeume",
                "frage": "Welche Räumlichkeiten hast du?",
                "typ": "multi_choice",
                "optionen": ["Hauptküche", "Vorbereitungsküche", "Lagerraum (trocken)", "Kühlraum", "Tiefkühlraum", "Personalräume", "Gastraum", "Theke/Bar", "Spülküche", "Toiletten Gäste", "Toiletten Personal", "Büro", "Außenbereich/Freisitz"]
            },
            {
                "key": "treppen_vorhanden",
                "frage": "Gibt es Treppen im Betrieb?",
                "typ": "single_choice",
                "optionen": ["Keine Treppen", "1-2 Treppen", "Mehrere Treppen", "Wendeltreppe", "Steile Kellertreppe"]
            }
        ]
    },
    3: {
        "titel": "Geräte & Maschinen",
        "beschreibung": "Welche Geräte werden genutzt?",
        "fragen": [
            {
                "key": "kuechen_geraete",
                "frage": "Welche Küchengeräte sind im Einsatz?",
                "typ": "multi_choice",
                "optionen": ["Gas-Herd", "Elektro-Herd", "Induktion", "Fritteuse", "Pizzaofen", "Konvektomat", "Grill (offen)", "Grill (geschlossen)", "Mikrowelle", "Salamander", "Wok-Brenner", "Dampfgarer"]
            },
            {
                "key": "schneide_geraete",
                "frage": "Welche Schneidegeräte werden verwendet?",
                "typ": "multi_choice",
                "optionen": ["Aufschnittmaschine", "Fleischwolf", "Cutter/Mixer", "Brotschneidemaschine", "Großmesser", "Stabmixer"]
            },
            {
                "key": "reinigung_geraete",
                "frage": "Welche Reinigungsmittel/Maschinen werden eingesetzt?",
                "typ": "multi_choice",
                "optionen": ["Spülmaschine (Industrie)", "Hochdruckreiniger", "Aggressive Reiniger (Backofen, Fritteuse)", "Desinfektionsmittel", "Säurehaltige Reiniger"]
            }
        ]
    },
    4: {
        "titel": "Arbeitsabläufe",
        "beschreibung": "Wie wird gearbeitet?",
        "fragen": [
            {
                "key": "schichtbetrieb",
                "frage": "In welchem Schichtbetrieb arbeitet ihr?",
                "typ": "single_choice",
                "optionen": ["Nur Tagschicht", "Tag + Abend", "Auch Nachtschicht", "Durchgehend (24/7)", "Wechselschicht"]
            },
            {
                "key": "schwere_lasten",
                "frage": "Werden schwere Lasten gehoben/getragen?",
                "typ": "single_choice",
                "optionen": ["Nein, nur leichte Lasten", "Gelegentlich (bis 15 kg)", "Regelmäßig (15-25 kg)", "Häufig (über 25 kg)"]
            },
            {
                "key": "kundenkontakt",
                "frage": "Wie ist der Kundenkontakt?",
                "typ": "multi_choice",
                "optionen": ["Direkt am Tisch", "An der Theke", "Telefonisch", "Lieferung außer Haus", "Catering vor Ort"]
            }
        ]
    },
    5: {
        "titel": "Besondere Risiken",
        "beschreibung": "Gibt es spezielle Gefahren?",
        "fragen": [
            {
                "key": "alkoholausschank",
                "frage": "Wird Alkohol ausgeschenkt?",
                "typ": "single_choice",
                "optionen": ["Nein", "Ja, gelegentlich", "Ja, regelmäßig", "Ja, Hauptgeschäft (Bar/Kneipe)"]
            },
            {
                "key": "junge_mitarbeiter",
                "frage": "Beschäftigst du Mitarbeiter unter 18?",
                "typ": "single_choice",
                "optionen": ["Nein", "Ja, 1-2 Jugendliche", "Ja, mehrere Jugendliche", "Ja, hauptsächlich Auszubildende"]
            },
            {
                "key": "schwangere",
                "frage": "Sind aktuell schwangere/stillende Mitarbeiterinnen beschäftigt?",
                "typ": "single_choice",
                "optionen": ["Nein, aktuell nicht", "Ja, eine Person", "Ja, mehrere Personen"]
            },
            {
                "key": "stress_faktoren",
                "frage": "Welche Stressfaktoren gibt es?",
                "typ": "multi_choice",
                "optionen": ["Hohes Gästeaufkommen zu Stoßzeiten", "Personalmangel", "Konflikte mit Gästen", "Zeitdruck bei Bestellungen", "Schichtwechsel", "Wenige Pausen"]
            }
        ]
    },
    6: {
        "titel": "Bestehende Maßnahmen",
        "beschreibung": "Was ist bereits vorhanden?",
        "fragen": [
            {
                "key": "schutzausruestung",
                "frage": "Welche Schutzausrüstung wird gestellt?",
                "typ": "multi_choice",
                "optionen": ["Schnittschutzhandschuhe", "Hitzeschutzhandschuhe", "Rutschfeste Schuhe", "Schürzen", "Haarnetze/Mützen", "Augenschutz (für Reinigung)", "Gehörschutz"]
            },
            {
                "key": "schulungen",
                "frage": "Welche Schulungen werden durchgeführt?",
                "typ": "multi_choice",
                "optionen": ["HACCP-Schulung", "Erste-Hilfe-Schulung", "Brandschutz-Unterweisung", "Hygiene-Schulung (jährlich)", "Maschinen-Einweisung", "Keine regelmäßigen Schulungen"]
            },
            {
                "key": "notfall_ausstattung",
                "frage": "Welche Notfall-Ausstattung ist vorhanden?",
                "typ": "multi_choice",
                "optionen": ["Erste-Hilfe-Kasten", "Feuerlöscher", "Löschdecke (Küche)", "Notausgang gekennzeichnet", "Notbeleuchtung", "Augendusche", "Verbandbuch"]
            }
        ]
    }
}


def show_wizard(supabase, betrieb_id: int, user_id: int, assessment_id: Optional[int] = None):
    """Hauptfunktion für den Gefährdungsbeurteilung-Wizard."""
    
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 0
    if "wizard_antworten" not in st.session_state:
        st.session_state.wizard_antworten = {}
    if "wizard_assessment_id" not in st.session_state:
        st.session_state.wizard_assessment_id = assessment_id
    
    schritt = st.session_state.wizard_step
    total_schritte = len(GASTRO_WIZARD_SCHRITTE)
    
    if schritt == 0:
        _show_intro()
    elif schritt <= total_schritte:
        _show_schritt(schritt)
    else:
        _show_auswertung(supabase, betrieb_id, user_id)


def _show_intro():
    st.markdown("## 🛡️ Gefährdungsbeurteilung Wizard")
    st.caption("Erstelle eine rechtssichere Beurteilung nach §5 ArbSchG in nur 6 Schritten")
    
    st.markdown("""
    ### So funktioniert's:
    
    1. **Objekt-Analyse** – Beschreibe deinen Betrieb
    2. **Räumlichkeiten** – Welche Räume gibt es?
    3. **Geräte & Maschinen** – Was wird verwendet?
    4. **Arbeitsabläufe** – Wie wird gearbeitet?
    5. **Besondere Risiken** – Spezielle Gefahren
    6. **Bestehende Maßnahmen** – Was ist vorhanden?
    
    Anschließend analysiert die KI deine Antworten und erstellt eine 
    **vollständige rechtssichere Gefährdungsbeurteilung** für deinen Betrieb.
    
    ⏱️ Zeitaufwand: ca. 10-15 Minuten
    """)
    
    if st.button("🚀 Wizard starten", type="primary", use_container_width=True):
        st.session_state.wizard_step = 1
        st.rerun()


def _show_schritt(schritt: int):
    config = GASTRO_WIZARD_SCHRITTE[schritt]
    total = len(GASTRO_WIZARD_SCHRITTE)
    
    st.progress(schritt / total)
    st.caption(f"Schritt {schritt} von {total}")
    
    st.markdown(f"## {config['titel']}")
    st.markdown(f"_{config['beschreibung']}_")
    st.markdown("---")
    
    for frage in config["fragen"]:
        _render_frage(frage)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if schritt > 1:
            if st.button("← Zurück", use_container_width=True, key=f"back_{schritt}"):
                st.session_state.wizard_step -= 1
                st.rerun()
    with col2:
        is_last = schritt == total
        button_label = "🤖 KI-Auswertung starten" if is_last else "Weiter →"
        if st.button(button_label, type="primary", use_container_width=True, key=f"next_{schritt}"):
            st.session_state.wizard_step += 1
            st.rerun()


def _render_frage(frage: dict):
    key = f"wizard_{frage['key']}"
    
    st.markdown(f"**{frage['frage']}**")
    
    if frage["typ"] == "single_choice":
        antwort = st.radio(
            "Antwort",
            frage["optionen"],
            key=key,
            label_visibility="collapsed",
            index=None
        )
        if antwort:
            st.session_state.wizard_antworten[frage["key"]] = {
                "frage": frage["frage"],
                "antwort": antwort,
                "typ": "single_choice"
            }
    
    elif frage["typ"] == "multi_choice":
        antworten = []
        cols = st.columns(2)
        for i, opt in enumerate(frage["optionen"]):
            with cols[i % 2]:
                if st.checkbox(opt, key=f"{key}_{i}"):
                    antworten.append(opt)
        if antworten:
            st.session_state.wizard_antworten[frage["key"]] = {
                "frage": frage["frage"],
                "antwort": antworten,
                "typ": "multi_choice"
            }
    
    st.markdown("")


def _show_auswertung(supabase, betrieb_id: int, user_id: int):
    st.markdown("## 🤖 KI-Auswertung läuft...")
    
    with st.spinner("Die KI analysiert deine Antworten und erstellt deine Gefährdungsbeurteilung..."):
        from modules.hazard.hazard_ai import generiere_komplette_beurteilung
        
        antworten = st.session_state.wizard_antworten
        ergebnis = generiere_komplette_beurteilung(antworten, "gastronomie")
        
        if ergebnis:
            _speichere_ergebnis(supabase, betrieb_id, user_id, antworten, ergebnis)
            st.success("✅ Gefährdungsbeurteilung erstellt!")
            st.session_state.wizard_step = 0
            st.session_state.wizard_antworten = {}
            st.markdown("### Deine Auswertung:")
            st.markdown(ergebnis)
            
            if st.button("📋 Zurück zur Übersicht", type="primary"):
                st.session_state["hazard_ansicht"] = "liste"
                st.rerun()
        else:
            st.error("Fehler bei der KI-Auswertung. Bitte versuche es erneut.")
            if st.button("← Zurück"):
                st.session_state.wizard_step = 6
                st.rerun()


def _speichere_ergebnis(supabase, betrieb_id, user_id, antworten, ergebnis):
    """Speichert das Wizard-Ergebnis in der Datenbank."""
    try:
        result = supabase.table("hazard_assessments").insert({
            "betrieb_id": int(betrieb_id) if betrieb_id else 1,
            "industry": "gastronomie",
            "title": f"Gefährdungsbeurteilung {datetime.now().strftime('%Y-%m-%d')}",
            "status": "aktiv",
            "wizard_completed": True,
            "objekt_analyse": antworten,
            "ki_auswertung": {"text": ergebnis, "erstellt_am": datetime.now().isoformat()},
            "created_by": int(user_id) if user_id else None,
            "last_reviewed_at": datetime.now().strftime("%Y-%m-%d")
        }).execute()
        
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")
        return None
