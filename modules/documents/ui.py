"""
Complio Document Center - UI für Download von PDF-Vorlagen.
Wird im Premium-Tab eingebunden.
"""
import streamlit as st
from datetime import datetime
from modules.documents.templates.generators import TEMPLATES


def show_document_center():
    """Hauptansicht: Alle Druckvorlagen zum Download."""
    st.markdown("### 📄 Druckvorlagen & Nachweise")
    st.caption(
        "Rechtssichere A4-Vorlagen für deinen Betrieb. Alle Dokumente entsprechen "
        "dem aktuellen Rechtsstand 2026 (DGUV V2, ArbSchG, LMHV, IfSG)."
    )
    
    # Info-Box
    st.info(
        "💡 **So nutzt du die Vorlagen:** Klicke auf einen Download-Button - "
        "die PDF wird sofort generiert und du kannst sie direkt ausdrucken oder "
        "speichern. Alle Vorlagen sind druckbereit auf A4."
    )
    
    # Gruppiere nach Kategorie
    kategorien = {}
    for key, data in TEMPLATES.items():
        kat = data["kategorie"]
        if kat not in kategorien:
            kategorien[kat] = []
        kategorien[kat].append((key, data))
    
    # Reihenfolge der Kategorien
    reihenfolge = ["Checklisten", "Formulare", "Nachweise", "Betriebsanweisungen"]
    
    for kat_name in reihenfolge:
        if kat_name not in kategorien:
            continue
        
        st.markdown(f"#### {kat_name}")
        
        items = kategorien[kat_name]
        
        # 2-Spalten-Layout
        for i in range(0, len(items), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(items):
                    break
                key, data = items[idx]
                with col:
                    _render_document_card(key, data)
        
        st.markdown("")
    
    # Footer mit Hinweis
    st.markdown("---")
    st.caption(
        "⚖️ Hinweis: Diese Vorlagen ersetzen keine individuelle Rechtsberatung. "
        "Bei spezifischen Fragen wende dich an die BGN (0621 4456-3232) oder "
        "deinen Steuerberater."
    )


def _render_document_card(key, data):
    """Zeigt eine einzelne Vorlage als Card mit Download-Button."""
    with st.container(border=True):
        st.markdown(f"**{data['name']}**")
        st.caption(data["beschreibung"])
        
        # Download-Button
        try:
            pdf_bytes = data["generator"]()
            st.download_button(
                label="📥 PDF herunterladen",
                data=pdf_bytes,
                file_name=data["dateiname"],
                mime="application/pdf",
                key=f"download_{key}",
                use_container_width=True,
                type="primary"
            )
        except Exception as e:
            st.error(f"Fehler bei PDF-Generierung: {str(e)[:100]}")
