from datetime import date

import streamlit as st

from pages import admin_dienstplan, admin_mastergeraete, zeitauswertung
from utils.absences import store_absence
from utils.database import get_supabase_client
from utils.work_accounts import sync_work_account_for_month


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


def _show_absenzen_tab():
    st.subheader("🏖️ Abwesenheiten & Atteste")
    supabase = get_supabase_client()
    alle_ma = _load_admin_mitarbeiter()
    if not alle_ma:
        st.info("Keine Mitarbeiter gefunden.")
        return

    ma_options = {f"{m['vorname']} {m['nachname']}": m for m in alle_ma}
    selected_label = st.selectbox("Mitarbeiter", list(ma_options.keys()), key="abwesen_ma")
    mitarbeiter = ma_options[selected_label]

    with st.form("abwesenheit_form"):
        typ = st.selectbox("Typ", ["urlaub", "krankheit", "sonderurlaub"])
        start = st.date_input("Von", value=date.today(), format="DD.MM.YYYY")
        ende = st.date_input("Bis", value=date.today(), format="DD.MM.YYYY")
        attest = st.file_uploader("Attest (optional)", type=["pdf", "jpg", "jpeg", "png"])
        grund = st.text_area("Grund / Kommentar", placeholder="Optionaler Hinweis")
        submit = st.form_submit_button("Abwesenheit speichern")

        if submit:
            if ende < start:
                st.error("Enddatum muss >= Startdatum sein.")
            else:
                attest_pfad = None
                if attest is not None:
                    att_bytes = attest.read()
                    attest_pfad = (
                        f"atteste/{mitarbeiter['id']}/{date.today().strftime('%Y%m%d')}_{attest.name}"
                    )
                    from utils.database import upload_file_to_storage
                    ok = upload_file_to_storage("dokumente", attest_pfad, att_bytes)
                    if not ok:
                        st.warning("Attest konnte nicht hochgeladen werden, Abwesenheit wird trotzdem gespeichert.")
                        attest_pfad = None

                result = store_absence(
                    supabase,
                    betrieb_id=mitarbeiter.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
                    mitarbeiter_id=mitarbeiter["id"],
                    typ=typ,
                    start=start,
                    end=ende,
                    monthly_target_hours=float(mitarbeiter.get("monatliche_soll_stunden") or 0.0),
                    attest_pfad=attest_pfad,
                    grund=grund or None,
                    created_by=st.session_state.get("user_id"),
                )
                st.success(
                    f"Abwesenheit gespeichert: {result['tage']:.1f} Tage, "
                    f"{result['stunden_gutschrift']:.2f}h Gutschrift."
                )


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


def _show_arbeitszeitkonten_tab():
    st.subheader("📅 Arbeitszeitkonten (neu)")
    supabase = get_supabase_client()
    alle_ma = _load_admin_mitarbeiter()
    if not alle_ma:
        st.info("Keine Mitarbeiter vorhanden.")
        return

    col_a, col_b = st.columns([1, 1])
    with col_a:
        monat = st.number_input("Monat", min_value=1, max_value=12, value=date.today().month)
    with col_b:
        jahr = st.number_input("Jahr", min_value=2024, max_value=2100, value=date.today().year)

    if st.button("Konten synchronisieren", type="primary"):
        for ma in alle_ma:
            try:
                sync_work_account_for_month(
                    supabase,
                    betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
                    mitarbeiter_id=ma["id"],
                    monat=int(monat),
                    jahr=int(jahr),
                )
            except Exception:
                pass
        st.success("Arbeitszeitkonten synchronisiert.")

    konto_res = (
        supabase.table("arbeitszeit_konten")
        .select("*")
        .order("mitarbeiter_id")
        .execute()
    )
    rows = konto_res.data or []
    if not rows:
        st.info("Keine Einträge in arbeitszeit_konten vorhanden.")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)


def show_admin_dashboard():
    st.set_page_config(page_title="Admin-Zentrale", layout="wide")
    st.title("🇩🇪 CrewBase – Admin")

    tabs = st.tabs(
        [
            "📅 Dienstplanung",
            "🏖️ Abwesenheiten",
            "📊 Zeitauswertung",
            "⏱️ Arbeitszeitkonten",
            "🖥️ Mastergeräte",
            "⚙️ System",
        ]
    )

    with tabs[0]:
        admin_dienstplan.show_dienstplanung()
    with tabs[1]:
        _show_absenzen_tab()
    with tabs[2]:
        _show_zeitauswertung_tab()
    with tabs[3]:
        _show_arbeitszeitkonten_tab()
    with tabs[4]:
        admin_mastergeraete.show_mastergeraete()
    with tabs[5]:
        _show_system_tab()


if __name__ == "__main__":
    show_admin_dashboard()
