"""
AVV-Register (Auftragsverarbeitungsverträge) – Admin-UI
DSGVO Art. 28: Verzeichnis aller Auftragsverarbeiter des Betriebs.
"""
from datetime import date
import streamlit as st
from utils.database import get_service_role_client


def _betrieb_id() -> int | None:
    return st.session_state.get("betrieb_id")


def _lade_avv_eintraege():
    betrieb_id = _betrieb_id()
    if not betrieb_id:
        return []
    supabase = get_service_role_client()
    res = (
        supabase.table("avv_register")
        .select("*")
        .eq("betrieb_id", betrieb_id)
        .order("auftragsverarbeiter")
        .execute()
    )
    return res.data or []


def _speichere_avv(daten: dict) -> bool:
    betrieb_id = _betrieb_id()
    if not betrieb_id:
        return False
    try:
        supabase = get_service_role_client()
        daten["betrieb_id"] = betrieb_id
        if daten.get("id"):
            row_id = daten.pop("id")
            daten.pop("betrieb_id", None)
            supabase.table("avv_register").update(daten).eq("id", row_id).execute()
        else:
            supabase.table("avv_register").insert(daten).execute()
        return True
    except Exception as exc:
        st.error(f"Fehler beim Speichern: {exc}")
        return False


def _loesche_avv(avv_id: int) -> bool:
    try:
        supabase = get_service_role_client()
        supabase.table("avv_register").delete().eq("id", avv_id).execute()
        return True
    except Exception as exc:
        st.error(f"Fehler beim Löschen: {exc}")
        return False


def show_avv_register() -> None:
    st.markdown("### AVV-Register (Art. 28 DSGVO)")
    st.caption(
        "Verzeichnis aller Dienstleister, die in Ihrem Auftrag personenbezogene Daten verarbeiten. "
        "Für jeden Auftragsverarbeiter muss ein unterzeichneter AVV vorliegen."
    )

    eintraege = _lade_avv_eintraege()

    # Statusübersicht
    gesamt = len(eintraege)
    unterzeichnet = sum(1 for e in eintraege if e.get("avv_unterzeichnet"))
    ausstehend = gesamt - unterzeichnet

    col1, col2, col3 = st.columns(3)
    col1.metric("Auftragsverarbeiter", gesamt)
    col2.metric("AVV unterzeichnet", unterzeichnet, delta=None)
    col3.metric("AVV ausstehend", ausstehend, delta=f"-{ausstehend}" if ausstehend else None)

    if ausstehend > 0:
        st.warning(
            f"⚠️ {ausstehend} Auftragsverarbeiter ohne unterzeichneten AVV. "
            "Bitte schnellstmöglich nachholen (Bußgeldrisiko nach Art. 83 DSGVO)."
        )

    st.markdown("---")

    # Bestehende Einträge
    for eintrag in eintraege:
        avv_ok = eintrag.get("avv_unterzeichnet", False)
        icon = "✅" if avv_ok else "⚠️"
        with st.expander(f"{icon} {eintrag.get('auftragsverarbeiter', '—')} — {eintrag.get('zweck', '')}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Zweck:** {eintrag.get('zweck', '—')}")
                st.markdown(f"**Datenkategorien:** {eintrag.get('datenkategorien', '—')}")
                st.markdown(f"**Serverstandort:** {eintrag.get('server_standort', '—')}")
            with col_b:
                st.markdown(f"**AVV unterzeichnet:** {'Ja' if avv_ok else 'Nein'}")
                st.markdown(f"**Unterzeichnet am:** {eintrag.get('unterzeichnet_am') or '—'}")
                st.markdown(f"**Gültig bis:** {eintrag.get('gueltig_bis') or '—'}")

            if eintrag.get("notizen"):
                st.info(eintrag["notizen"])

            form_key = f"avv_edit_{eintrag['id']}"
            with st.form(form_key):
                st.markdown("**Bearbeiten**")
                c1, c2 = st.columns(2)
                neu_unterzeichnet = c1.checkbox(
                    "AVV unterzeichnet",
                    value=avv_ok,
                    key=f"cb_{eintrag['id']}"
                )
                neu_datum = c2.date_input(
                    "Unterzeichnet am",
                    value=date.fromisoformat(eintrag["unterzeichnet_am"])
                    if eintrag.get("unterzeichnet_am")
                    else date.today(),
                    key=f"dat_{eintrag['id']}"
                )
                neu_gueltig = st.date_input(
                    "Gültig bis",
                    value=date.fromisoformat(eintrag["gueltig_bis"])
                    if eintrag.get("gueltig_bis")
                    else None,
                    key=f"guel_{eintrag['id']}"
                )
                neu_notizen = st.text_area(
                    "Notizen",
                    value=eintrag.get("notizen", ""),
                    key=f"not_{eintrag['id']}"
                )
                col_save, col_del = st.columns(2)
                save = col_save.form_submit_button("Speichern", type="primary")
                delete = col_del.form_submit_button("Löschen", type="secondary")

            if save:
                payload = {
                    "id": eintrag["id"],
                    "avv_unterzeichnet": neu_unterzeichnet,
                    "unterzeichnet_am": neu_datum.isoformat() if neu_unterzeichnet else None,
                    "gueltig_bis": neu_gueltig.isoformat() if neu_gueltig else None,
                    "notizen": neu_notizen.strip() or None,
                    "updated_at": "now()",
                }
                if _speichere_avv(payload):
                    st.success("Gespeichert.")
                    st.rerun()

            if delete:
                if _loesche_avv(eintrag["id"]):
                    st.success("Eintrag gelöscht.")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### Neuen Auftragsverarbeiter hinzufügen")

    with st.form("avv_neu"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Auftragsverarbeiter *", placeholder="z.B. Lexware GmbH")
        zweck = c2.text_input("Zweck *", placeholder="z.B. Lohnabrechnung")
        kategorien = st.text_input(
            "Datenkategorien",
            placeholder="z.B. Lohndaten, Sozialversicherungsnummern"
        )
        c3, c4 = st.columns(2)
        standort = c3.text_input("Serverstandort", value="EU")
        unterzeichnet = c4.checkbox("AVV bereits unterzeichnet")
        datum = st.date_input("Unterzeichnet am", value=date.today()) if unterzeichnet else None
        notizen = st.text_area("Notizen / Dokument-Pfad")
        submit = st.form_submit_button("Hinzufügen", type="primary")

    if submit:
        if not name.strip() or not zweck.strip():
            st.error("Name und Zweck sind Pflichtfelder.")
        else:
            payload = {
                "auftragsverarbeiter": name.strip(),
                "zweck": zweck.strip(),
                "datenkategorien": kategorien.strip() or None,
                "server_standort": standort.strip() or "EU",
                "avv_unterzeichnet": unterzeichnet,
                "unterzeichnet_am": datum.isoformat() if datum and unterzeichnet else None,
                "notizen": notizen.strip() or None,
            }
            if _speichere_avv(payload):
                st.success("Auftragsverarbeiter hinzugefügt.")
                st.rerun()
