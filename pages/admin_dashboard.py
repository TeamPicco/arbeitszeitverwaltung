from datetime import date

import streamlit as st

from pages import admin_dienstplan, admin_mastergeraete, zeitauswertung
from utils.database import get_supabase_client


def _load_admin_mitarbeiter():
    supabase = get_supabase_client()
    query = supabase.table("mitarbeiter").select(
        "id, vorname, nachname, monatliche_soll_stunden, stundenlohn_brutto, "
        "sonntagszuschlag_aktiv, feiertagszuschlag_aktiv, personalnummer, "
        "beschaeftigungsart, betrieb_id"
    ).order("nachname")
    betrieb_id = st.session_state.get("betrieb_id")
    if betrieb_id is not None:
        query = query.eq("betrieb_id", betrieb_id)
    res = query.execute()
    return res.data or []


def _show_zeitauswertung_tab():
    st.subheader("📊 Zeitauswertung & Lohn")
    alle_ma = _load_admin_mitarbeiter()
    if not alle_ma:
        st.info("Keine Mitarbeiter für die Auswertung gefunden.")
        return

    ma_options = {f"{m['vorname']} {m['nachname']}": m for m in alle_ma}
    selected_label = st.selectbox("Mitarbeiter auswählen", list(ma_options.keys()))
    aktiver_ma = ma_options[selected_label]
    zeitauswertung.show_zeitauswertung(aktiver_ma, admin_modus=True)


def _show_system_tab():
    st.subheader("🛠️ Systemstatus")
    supabase = get_supabase_client()
    betrieb_id = st.session_state.get("betrieb_id")

    col1, col2, col3 = st.columns(3)
    try:
        users_q = supabase.table("users").select("id", count="exact")
        ma_q = supabase.table("mitarbeiter").select("id", count="exact")
        zeit_q = supabase.table("zeiterfassung").select("id", count="exact")
        if betrieb_id is not None:
            users_q = users_q.eq("betrieb_id", betrieb_id)
            ma_q = ma_q.eq("betrieb_id", betrieb_id)
            zeit_q = zeit_q.eq("betrieb_id", betrieb_id)

        users_count = users_q.limit(1).execute().count or 0
        ma_count = ma_q.limit(1).execute().count or 0
        zeit_count = zeit_q.limit(1).execute().count or 0
    except Exception:
        users_count = ma_count = zeit_count = 0

    with col1:
        st.metric("Benutzer", users_count)
    with col2:
        st.metric("Mitarbeiter", ma_count)
    with col3:
        st.metric("Zeiteinträge", zeit_count)

    st.caption(f"Berichtsdatum: {date.today().strftime('%d.%m.%Y')}")


def show_admin_dashboard():
    st.set_page_config(page_title="Admin-Zentrale", layout="wide")
    st.title("🇩🇪 CrewBase – Admin")

    tabs = st.tabs(
        [
            "📅 Dienstplanung",
            "📊 Zeitauswertung",
            "🖥️ Mastergeräte",
            "⚙️ System",
        ]
    )

    with tabs[0]:
        admin_dienstplan.show_dienstplanung()
    with tabs[1]:
        _show_zeitauswertung_tab()
    with tabs[2]:
        admin_mastergeraete.show_mastergeraete()
    with tabs[3]:
        _show_system_tab()


if __name__ == "__main__":
    show_admin_dashboard()
