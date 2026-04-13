from datetime import date
import streamlit as st
from modules.hazard.hazard_ai import (
    lade_aktuelle_rechtsinfos,
    trage_rechtsaenderung_ein
)


def show_rechtsstand_admin(supabase) -> None:
    """
    Admin-Seite zum Verwalten des Rechtsstands.
    Nur für Complio-Admins sichtbar.
    """
    st.markdown("## ⚖️ Rechtsstand verwalten")
    st.caption(
        "Hier trägst du Gesetzesänderungen ein. "
        "Die KI nutzt diese Infos automatisch bei jedem Aufruf."
    )

    # Aktueller Stand anzeigen
    with st.expander("📋 Aktueller Rechtsstand anzeigen", expanded=False):
        aktuell = lade_aktuelle_rechtsinfos(supabase)
        st.code(aktuell, language=None)

    st.markdown("---")
    st.markdown("### ➕ Neue Rechtsänderung eintragen")
    st.caption(
        "Zum Beispiel: Mindestlohnerhöhung, neue DGUV-Vorschrift, "
        "geändertes Bußgeld etc."
    )

    with st.form("rechtsaenderung_form"):
        law_name = st.text_input(
            "Gesetz / Vorschrift *",
            placeholder="z.B. Mindestlohn, DGUV Vorschrift 2, §5 ArbSchG"
        )
        col1, col2 = st.columns(2)
        with col1:
            old_value = st.text_input(
                "Alter Wert",
                placeholder="z.B. 12,41 Euro/Stunde"
            )
        with col2:
            new_value = st.text_input(
                "Neuer Wert *",
                placeholder="z.B. 12,82 Euro/Stunde"
            )
        valid_from = st.date_input(
            "Gültig ab *",
            value=date.today()
        )

        submitted = st.form_submit_button(
            "✅ Rechtsänderung speichern",
            type="primary",
            use_container_width=True
        )

    if submitted:
        fehler = []
        if not law_name.strip():
            fehler.append("Bitte Gesetz/Vorschrift eingeben.")
        if not new_value.strip():
            fehler.append("Bitte neuen Wert eingeben.")

        if fehler:
            for f in fehler:
                st.error(f)
        else:
            ok = trage_rechtsaenderung_ein(
                supabase,
                law_name=law_name.strip(),
                old_value=old_value.strip(),
                new_value=new_value.strip(),
                valid_from=valid_from.isoformat()
            )
            if ok:
                st.success(
                    f"✅ Gespeichert! Die KI nutzt ab sofort: "
                    f"{law_name} → {new_value}"
                )
                st.rerun()
            else:
                st.error("Fehler beim Speichern. Bitte erneut versuchen.")

    st.markdown("---")
    st.markdown("### 📜 Letzte Änderungen")

    try:
        history = supabase.table("legal_update_log")\
            .select("law_name, old_value, new_value, valid_from, created_at")\
            .order("valid_from", desc=True)\
            .limit(10)\
            .execute()

        if not history.data:
            st.info("Noch keine Änderungen eingetragen.")
        else:
            for eintrag in history.data:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(
                            f"**{eintrag.get('law_name')}**"
                        )
                        if eintrag.get('old_value'):
                            st.caption(
                                f"Vorher: {eintrag.get('old_value')}"
                            )
                    with col2:
                        st.markdown(
                            f"✅ {eintrag.get('new_value')}"
                        )
                    with col3:
                        st.caption(
                            f"ab {eintrag.get('valid_from', '')[:10]}"
                        )
    except Exception:
        st.warning("Verlauf konnte nicht geladen werden.")
