import streamlit as st
from modules.hazard.hazard_db import (
    get_alle_beurteilungen,
    get_beurteilung_mit_schritten,
    erstelle_beurteilung,
    speichere_schritt,
    get_status_farbe
)
from modules.hazard.hazard_ai import generiere_ki_vorschlag, pruefe_api_key


def _format_review_date(value) -> str:
    """Formatiert next_review_due sicher für die Anzeige."""
    if value is None:
        return "–"
    text = str(value).strip()
    if not text or text.lower() == "none":
        return "–"
    return text[:10]


def show_upgrade_prompt():
    """Zeigt einen Hinweis wenn das Feature nicht gebucht ist."""
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔒 Premium-Feature")
        st.markdown(
            "**Gefährdungsbeurteilung KI** ist in deinem "
            "aktuellen Plan nicht enthalten."
        )
        st.markdown(
            "Mit diesem Modul erstellst du rechtssichere "
            "Gefährdungsbeurteilungen nach §5 ArbSchG – "
            "mit KI-Unterstützung. Fehlende Dokumentation "
            "kann Bußgelder bis zu **30.000 €** kosten."
        )
        st.markdown("**✅ Was du bekommst:**")
        st.markdown("- KI-Vorschläge für alle 5 Pflichtschritte")
        st.markdown("- Automatische Fristüberwachung (jährlich)")
        st.markdown("- PDF-Export für Behörden und Berufsgenossenschaft")
        st.markdown("")
        st.markdown("**39 € / Monat**")
        if st.button("🚀 Jetzt freischalten", type="primary",
                     use_container_width=True):
            st.info("Bitte wende dich an den Support zur Freischaltung.")
    st.markdown("---")


def show_beurteilungs_liste(supabase, betrieb_id: str, user_id: str):
    """Zeigt die Übersichtsliste aller Beurteilungen."""
    st.markdown("## 📋 Gefährdungsbeurteilungen")
    st.caption("Rechtspflicht nach §5 ArbSchG – jährliche Überprüfung erforderlich")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Neue Beurteilung", type="primary",
                     use_container_width=True):
            st.session_state["hazard_ansicht"] = "neu"
            st.rerun()

    beurteilungen = get_alle_beurteilungen(supabase, betrieb_id)

    if not beurteilungen:
        st.info(
            "Noch keine Gefährdungsbeurteilungen vorhanden. "
            "Erstelle jetzt deine erste Beurteilung."
        )
        return

    for b in beurteilungen:
        review_due = _format_review_date(b.get("next_review_due"))
        status_text, status_farbe = get_status_farbe(
            b.get("status", "entwurf"),
            b.get("next_review_due") or ""
        )
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{b.get('title', 'Unbekannt')}**")
                st.caption(
                    f"Branche: {b.get('industry', '–')} · "
                    f"Nächste Prüfung: "
                    f"{review_due}"
                )
            with col2:
                st.markdown(
                    f"<span style='color:{status_farbe}'>"
                    f"{status_text}</span>",
                    unsafe_allow_html=True
                )
            with col3:
                if st.button("✏️ Bearbeiten",
                             key=f"edit_{b['id']}",
                             use_container_width=True):
                    st.session_state["hazard_ansicht"] = "bearbeiten"
                    st.session_state["hazard_id"] = b["id"]
                    st.rerun()


def show_neue_beurteilung(supabase, betrieb_id: str, user_id: str):
    """Formular zum Erstellen einer neuen Beurteilung."""
    st.markdown("## ➕ Neue Gefährdungsbeurteilung")

    if st.button("← Zurück zur Übersicht"):
        st.session_state["hazard_ansicht"] = "liste"
        st.rerun()

    with st.form("neue_beurteilung_form"):
        titel = st.text_input(
            "Titel der Beurteilung *",
            placeholder="z.B. Küchenarbeitsplatz, Lagerbereich..."
        )
        branche = st.selectbox(
            "Branche *",
            options=[
                "gastronomie", "einzelhandel",
                "handwerk", "buero", "sonstiges"
            ],
            format_func=lambda x: {
                "gastronomie": "🍽️ Gastronomie / Restaurant",
                "einzelhandel": "🛒 Einzelhandel",
                "handwerk": "🔧 Handwerk",
                "buero": "💼 Büro",
                "sonstiges": "🏢 Sonstiges"
            }[x]
        )
        submitted = st.form_submit_button(
            "Beurteilung erstellen", type="primary"
        )

        if submitted:
            if not titel.strip():
                st.error("Bitte einen Titel eingeben.")
            else:
                assessment_id = erstelle_beurteilung(
                    supabase, betrieb_id, titel, branche, user_id
                )
                if assessment_id:
                    st.session_state["hazard_ansicht"] = "bearbeiten"
                    st.session_state["hazard_id"] = assessment_id
                    st.success("Beurteilung erstellt!")
                    st.rerun()
                else:
                    st.error("Fehler beim Erstellen. Bitte erneut versuchen.")


def show_beurteilung_bearbeiten(supabase, betrieb_id: str):
    """Zeigt das Bearbeitungsformular mit allen 5 Schritten."""
    assessment_id = st.session_state.get("hazard_id")
    if not assessment_id:
        st.session_state["hazard_ansicht"] = "liste"
        st.rerun()
        return

    if st.button("← Zurück zur Übersicht"):
        st.session_state["hazard_ansicht"] = "liste"
        st.rerun()

    daten = get_beurteilung_mit_schritten(supabase, assessment_id)
    beurteilung = daten.get("beurteilung")
    schritte = daten.get("schritte", [])

    if not beurteilung:
        st.error("Beurteilung nicht gefunden.")
        return

    st.markdown(f"## ✏️ {beurteilung.get('title', '')}")
    review_due = _format_review_date(beurteilung.get("next_review_due"))
    st.caption(
        f"Branche: {beurteilung.get('industry', '–')} · "
        f"Nächste Prüfung: {review_due}"
    )

    fertige_schritte = sum(1 for s in schritte if s.get("completed"))
    gesamt_schritte = len(schritte) if schritte else 6
    fortschritt = fertige_schritte / gesamt_schritte if gesamt_schritte > 0 else 0
    st.progress(
        fortschritt,
        text=f"Fortschritt: {fertige_schritte}/{gesamt_schritte} Schritte"
    )

    ki_verfuegbar = pruefe_api_key()
    if not ki_verfuegbar:
        st.warning(
            "⚠️ KI-Vorschläge nicht verfügbar. "
            "Bitte ANTHROPIC_API_KEY in der .env Datei eintragen."
        )

    st.markdown("---")

    for schritt in schritte:
        nr = schritt.get("step_number", 0)
        name = schritt.get("step_name", "")
        content = schritt.get("content", "")
        completed = schritt.get("completed", False)

        status_icon = "✅" if completed else "⬜"

        with st.expander(
            f"{status_icon} Schritt {nr}: {name}",
            expanded=(nr == 1 and not completed)
        ):
            if nr == 6:
                st.info(
                    "🆕 **Neu ab Januar 2026 – Pflichtbestandteil**\n\n"
                    "Psychische Belastungen müssen jetzt genauso dokumentiert "
                    "werden wie körperliche Gefahren. Dazu zählen: Zeitdruck, "
                    "Schichtarbeit, schwierige Gäste, fehlende Pausen und "
                    "Personalengpässe. Einfach aufschreiben was euer Team belastet."
                )

            neuer_text = st.text_area(
                "Inhalt",
                value=content,
                height=150,
                key=f"schritt_{assessment_id}_{nr}",
                label_visibility="collapsed",
                placeholder=f"Beschreibe hier: {name}..."
            )

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button(
                    "💾 Speichern",
                    key=f"save_{assessment_id}_{nr}",
                    use_container_width=True
                ):
                    if speichere_schritt(
                        supabase, assessment_id, nr, neuer_text
                    ):
                        st.success("Gespeichert!")
                        st.rerun()
                    else:
                        st.error("Fehler beim Speichern.")

            with col2:
                if ki_verfuegbar:
                    if st.button(
                        "🤖 KI-Vorschlag",
                        key=f"ki_{assessment_id}_{nr}",
                        use_container_width=True
                    ):
                        with st.spinner("KI generiert Vorschlag..."):
                            vorschlag = generiere_ki_vorschlag(
                                nr,
                                beurteilung.get("industry", "sonstiges"),
                                neuer_text,
                                supabase_client=supabase
                            )
                        st.info(f"**KI-Vorschlag:**\n\n{vorschlag}")
                        st.caption(
                            "Vorschlag prüfen, anpassen und "
                            "dann oben einfügen und speichern."
                        )


def show_hazard_modul(supabase, betrieb_id: str,
                      user_id: str, user_plan: str):
    """
    Haupteinstiegspunkt für das Gefährdungsbeurteilungs-Modul.
    Wird von admin_dashboard.py aufgerufen.
    """
    from utils.feature_flags import is_feature_enabled

    if not is_feature_enabled("HAZARD_ASSESSMENT", user_plan):
        show_upgrade_prompt()
        return

    if "hazard_ansicht" not in st.session_state:
        st.session_state["hazard_ansicht"] = "liste"

    ansicht = st.session_state.get("hazard_ansicht", "liste")

    if ansicht == "liste":
        show_beurteilungs_liste(supabase, betrieb_id, user_id)
    elif ansicht == "neu":
        show_neue_beurteilung(supabase, betrieb_id, user_id)
    elif ansicht == "bearbeiten":
        show_beurteilung_bearbeiten(supabase, betrieb_id)
