import os
from datetime import date, datetime

import streamlit as st

from pages import admin_dienstplan, admin_mastergeraete, zeitauswertung
from utils.absences import delete_absence, store_absence, update_absence
from utils.database import (
    get_supabase_client,
    update_mitarbeiter,
    upload_file_to_storage_result,
)
from utils.historischer_import import (
    dry_run_import_summary,
    importiere_in_crewbase,
    lese_upload_datei,
)
from utils.styles import apply_custom_css
from utils.work_accounts import close_work_account_month, sync_work_account_for_month, validate_work_account_month


def _load_admin_mitarbeiter():
    supabase = get_supabase_client()
    query = supabase.table("mitarbeiter").select("*").order("nachname")
    betrieb_id = st.session_state.get("betrieb_id")
    if betrieb_id is not None:
        query = query.eq("betrieb_id", betrieb_id)
    res = query.execute()
    return res.data or []


def _safe_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _storage_public_url(bucket: str, path: str | None) -> str | None:
    if not path:
        return None
    base_url = os.getenv("SUPABASE_URL")
    if not base_url:
        return None
    return f"{base_url}/storage/v1/object/public/{bucket}/{path}"


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


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

    betrieb_id = st.session_state.get("betrieb_id")
    abs_query = supabase.table("abwesenheiten").select("*").order("created_at", desc=True).limit(200)
    if betrieb_id is not None:
        abs_query = abs_query.eq("betrieb_id", betrieb_id)
    abs_res = abs_query.execute()
    abwesenheiten = abs_res.data or []
    atteste_count = sum(1 for a in abwesenheiten if a.get("attest_pfad"))
    krank_count = sum(1 for a in abwesenheiten if str(a.get("typ") or "").lower() in ("krankheit", "krank"))
    urlaub_count = sum(1 for a in abwesenheiten if a.get("typ") == "urlaub")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Einträge gesamt", len(abwesenheiten))
    m2.metric("Urlaub", urlaub_count)
    m3.metric("Krankheit", krank_count)
    m4.metric("Atteste hinterlegt", atteste_count)
    st.markdown("---")

    ma_options = {f"{m['vorname']} {m['nachname']}": m for m in alle_ma}
    selected_label = st.selectbox(
        "Mitarbeiter auswählen",
        list(ma_options.keys()),
        key="abwesen_ma",
        help="Neue Abwesenheit für diesen Mitarbeiter erfassen",
    )
    mitarbeiter = ma_options[selected_label]

    with st.expander("➕ Neue Abwesenheit erfassen", expanded=True):
        with st.form("abwesenheit_form"):
            c1, c2, c3 = st.columns([1, 1, 1.2])
            with c1:
                typ = st.selectbox("Typ", ["urlaub", "krankheit", "sonderurlaub"])
            with c2:
                start = st.date_input("Von", value=date.today(), format="DD.MM.YYYY")
            with c3:
                ende = st.date_input("Bis", value=date.today(), format="DD.MM.YYYY")

            attest = st.file_uploader("Attest (optional)", type=["pdf", "jpg", "jpeg", "png"])
            grund = st.text_area("Grund / Kommentar", placeholder="Optionaler Hinweis")
            submit = st.form_submit_button("Abwesenheit speichern", type="primary", use_container_width=True)

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
                        attest_upload = upload_file_to_storage_result(
                            "dokumente",
                            attest_pfad,
                            att_bytes,
                            fallback_buckets=["arbeitsvertraege"],
                        )
                        if not attest_upload.get("ok"):
                            st.warning(
                                "Attest konnte nicht hochgeladen werden, Abwesenheit wird trotzdem gespeichert. "
                                f"Details: {attest_upload.get('status_code') or '-'} "
                                f"{attest_upload.get('error') or ''}"
                            )
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
                    st.rerun()

    st.markdown("#### Letzte Abwesenheiten")
    if not abwesenheiten:
        st.info("Noch keine Abwesenheiten gespeichert.")
        return

    typ_labels = {
        "urlaub": "🏖️ Urlaub",
        "krankheit": "🤒 Krankheit",
        "krank": "🤒 Krankheit",
        "sonderurlaub": "🎗️ Sonderurlaub",
    }
    ma_lookup = {m["id"]: f"{m['vorname']} {m['nachname']}" for m in alle_ma}
    rows = []
    for a in abwesenheiten[:50]:
        rows.append(
            {
                "Mitarbeiter": ma_lookup.get(a.get("mitarbeiter_id"), str(a.get("mitarbeiter_id"))),
                "Typ": typ_labels.get(a.get("typ"), a.get("typ")),
                "Von": a.get("start_datum"),
                "Bis": a.get("ende_datum"),
                "Gutschrift (h)": float(a.get("stunden_gutschrift") or 0.0),
                "Attest": "Ja" if a.get("attest_pfad") else "Nein",
                "Status": a.get("status") or "-",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("#### ✏️ Abwesenheit ändern / 🗑️ löschen (mit Begründung)")
    select_options = {}
    for a in abwesenheiten[:200]:
        a_id = a.get("id")
        if a_id is None:
            continue
        ma_name = ma_lookup.get(a.get("mitarbeiter_id"), str(a.get("mitarbeiter_id")))
        start_iso = a.get("start_datum") or a.get("datum") or "-"
        end_iso = a.get("ende_datum") or a.get("datum") or "-"
        typ_raw = str(a.get("typ") or "").lower()
        typ_display = typ_labels.get(typ_raw, typ_raw or "-")
        label = f"#{a_id} | {ma_name} | {typ_display} | {start_iso} bis {end_iso}"
        select_options[label] = a

    if not select_options:
        st.info("Keine bearbeitbaren Abwesenheits-Einträge vorhanden.")
        return

    selected_label = st.selectbox(
        "Eintrag auswählen",
        list(select_options.keys()),
        key="abwesenheit_edit_delete_select",
    )
    selected_absence = select_options[selected_label]

    selected_id = int(selected_absence.get("id"))
    selected_ma_id = int(selected_absence.get("mitarbeiter_id"))
    selected_ma = next((m for m in alle_ma if int(m.get("id")) == selected_ma_id), {})
    default_typ_raw = str(selected_absence.get("typ") or "").lower()
    default_typ = "krankheit" if default_typ_raw == "krank" else default_typ_raw
    if default_typ not in ("urlaub", "krankheit", "sonderurlaub"):
        default_typ = "urlaub"
    default_start = _safe_date(selected_absence.get("start_datum") or selected_absence.get("datum")) or date.today()
    default_end = _safe_date(selected_absence.get("ende_datum") or selected_absence.get("datum")) or default_start

    e1, e2 = st.columns(2)
    with e1:
        with st.form(f"abwesenheit_update_form_{selected_id}"):
            st.markdown("**Abwesenheit bearbeiten**")
            existing_attest = selected_absence.get("attest_pfad")
            st.caption(f"Aktuelles Attest: {existing_attest or 'kein Attest hinterlegt'}")
            new_typ = st.selectbox(
                "Typ",
                ["urlaub", "krankheit", "sonderurlaub"],
                index=["urlaub", "krankheit", "sonderurlaub"].index(default_typ),
                key=f"abwesen_update_typ_{selected_id}",
            )
            new_start = st.date_input(
                "Von",
                value=default_start,
                format="DD.MM.YYYY",
                key=f"abwesen_update_start_{selected_id}",
            )
            new_end = st.date_input(
                "Bis",
                value=default_end,
                format="DD.MM.YYYY",
                key=f"abwesen_update_end_{selected_id}",
            )
            new_grund = st.text_area(
                "Grund / Kommentar",
                value=selected_absence.get("grund") or "",
                key=f"abwesen_update_grund_{selected_id}",
            )
            new_attest = st.file_uploader(
                "Attest nachträglich hochladen/ersetzen (optional)",
                type=["pdf", "jpg", "jpeg", "png"],
                key=f"abwesen_update_attest_{selected_id}",
            )
            edit_reason = st.text_area(
                "Begründung der Änderung *",
                placeholder="Pflichtfeld für Nachvollziehbarkeit / Audit",
                key=f"abwesen_update_reason_{selected_id}",
            )
            save_edit = st.form_submit_button(
                "✅ Änderung speichern",
                type="primary",
                use_container_width=True,
            )
            if save_edit:
                if new_end < new_start:
                    st.error("Enddatum muss >= Startdatum sein.")
                elif not (edit_reason or "").strip():
                    st.error("Bitte eine Begründung für die Änderung angeben.")
                else:
                    try:
                        attest_pfad = existing_attest
                        if new_attest is not None:
                            att_bytes = new_attest.read()
                            att_name = new_attest.name.replace(" ", "_")
                            attest_pfad_neu = (
                                f"atteste/{selected_ma_id}/{date.today().strftime('%Y%m%d')}_{selected_id}_{att_name}"
                            )
                            attest_upload = upload_file_to_storage_result(
                                "dokumente",
                                attest_pfad_neu,
                                att_bytes,
                                fallback_buckets=["arbeitsvertraege"],
                            )
                            if attest_upload.get("ok"):
                                attest_pfad = attest_pfad_neu
                            else:
                                st.warning(
                                    "Attest-Upload fehlgeschlagen, Änderung wird ohne neues Attest gespeichert. "
                                    f"Details: {attest_upload.get('status_code') or '-'} "
                                    f"{attest_upload.get('error') or ''}"
                                )

                        update_absence(
                            supabase,
                            absence_id=selected_id,
                            typ=new_typ,
                            start=new_start,
                            end=new_end,
                            monthly_target_hours=float(selected_ma.get("monatliche_soll_stunden") or 0.0),
                            change_reason=edit_reason.strip(),
                            changed_by=st.session_state.get("user_id"),
                            attest_pfad=attest_pfad,
                            grund=new_grund or None,
                        )
                        st.success("Abwesenheit wurde aktualisiert.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Änderung fehlgeschlagen: {e}")

    with e2:
        with st.form(f"abwesenheit_delete_form_{selected_id}"):
            st.markdown("**Abwesenheit löschen**")
            st.warning("Diese Aktion entfernt den Eintrag inkl. gespiegeltem Legacy-Zeiteintrag.")
            delete_reason = st.text_area(
                "Begründung der Löschung *",
                placeholder="Pflichtfeld für Nachvollziehbarkeit / Audit",
                key=f"abwesen_delete_reason_{selected_id}",
            )
            confirm_delete = st.checkbox(
                "Ich bestätige die Löschung",
                key=f"abwesen_delete_confirm_{selected_id}",
            )
            do_delete = st.form_submit_button(
                "🗑️ Eintrag löschen",
                use_container_width=True,
            )
            if do_delete:
                if not confirm_delete:
                    st.error("Bitte zuerst die Löschung bestätigen.")
                elif not (delete_reason or "").strip():
                    st.error("Bitte eine Begründung für die Löschung angeben.")
                else:
                    try:
                        delete_absence(
                            supabase,
                            absence_id=selected_id,
                            delete_reason=delete_reason.strip(),
                            deleted_by=st.session_state.get("user_id"),
                        )
                        st.success("Abwesenheit wurde gelöscht.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Löschen fehlgeschlagen: {e}")


def _show_mitarbeiter_stammdaten_tab():
    st.subheader("👥 Mitarbeiter-Stammdaten & Dokumente")
    supabase = get_supabase_client()
    alle_ma = _load_admin_mitarbeiter()

    with st.expander("➕ Mitarbeiter neu anlegen", expanded=False):
        with st.form("neuer_mitarbeiter_form"):
            n1, n2, n3 = st.columns(3)
            with n1:
                new_vorname = st.text_input("Vorname*", value="")
            with n2:
                new_nachname = st.text_input("Nachname*", value="")
            with n3:
                new_personalnummer = st.text_input("Personalnummer*", value="")

            n4, n5, n6 = st.columns(3)
            with n4:
                new_email = st.text_input("E-Mail", value="")
            with n5:
                new_telefon = st.text_input("Telefon", value="")
            with n6:
                new_beschaeftigungsart = st.text_input("Beschäftigungsart", value="")

            n7, n8, n9 = st.columns(3)
            with n7:
                new_strasse = st.text_input("Straße", value="")
            with n8:
                new_plz = st.text_input("PLZ", value="")
            with n9:
                new_ort = st.text_input("Ort", value="")

            n10, n11, n12 = st.columns(3)
            with n10:
                new_eintritt = st.date_input("Eintrittsdatum", value=date.today(), format="DD.MM.YYYY")
            with n11:
                new_soll = st.number_input("Monatliche Sollstunden", min_value=0.0, value=160.0, step=0.5)
            with n12:
                new_lohn = st.number_input("Stundenlohn (brutto)", min_value=0.0, value=0.0, step=0.5)

            n13, n14, n15 = st.columns(3)
            with n13:
                new_urlaub = st.number_input("Urlaubstage/Jahr", min_value=0.0, value=28.0, step=0.5)
            with n14:
                new_resturlaub = st.number_input("Resturlaub Vorjahr", min_value=0.0, value=0.0, step=0.5)
            with n15:
                new_geburtsdatum = st.date_input("Geburtsdatum", value=date(1990, 1, 1), format="DD.MM.YYYY")

            create = st.form_submit_button("Mitarbeiter anlegen", type="primary", use_container_width=True)
            if create:
                if not new_vorname.strip() or not new_nachname.strip() or not new_personalnummer.strip():
                    st.error("Bitte Vorname, Nachname und Personalnummer ausfüllen.")
                else:
                    payload = {
                        "betrieb_id": st.session_state.get("betrieb_id"),
                        "vorname": new_vorname.strip(),
                        "nachname": new_nachname.strip(),
                        "personalnummer": new_personalnummer.strip(),
                        "email": new_email.strip() or None,
                        "telefon": new_telefon.strip() or None,
                        "beschaeftigungsart": new_beschaeftigungsart.strip() or None,
                        "strasse": new_strasse.strip() or None,
                        "plz": new_plz.strip() or None,
                        "ort": new_ort.strip() or None,
                        "eintrittsdatum": new_eintritt.isoformat(),
                        "geburtsdatum": new_geburtsdatum.isoformat(),
                        "monatliche_soll_stunden": float(new_soll),
                        "stundenlohn_brutto": float(new_lohn),
                        "jahres_urlaubstage": float(new_urlaub),
                        "resturlaub_vorjahr": float(new_resturlaub),
                        "sonntagszuschlag_aktiv": False,
                        "feiertagszuschlag_aktiv": False,
                    }
                    try:
                        supabase.table("mitarbeiter").insert(payload).execute()
                        st.success("Mitarbeiter erfolgreich angelegt.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Anlage fehlgeschlagen: {e}")

    alle_ma = _load_admin_mitarbeiter()
    if not alle_ma:
        st.info("Keine Mitarbeiter vorhanden.")
        return

    ma_options = {f"{m.get('vorname', '')} {m.get('nachname', '')} ({m.get('personalnummer', '-')})": m for m in alle_ma}
    selected_label = st.selectbox(
        "Mitarbeiter auswählen",
        list(ma_options.keys()),
        key="stammdaten_ma",
    )
    ma = ma_options[selected_label]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Personalnummer", ma.get("personalnummer") or "-")
    c2.metric("Soll (Monat)", f"{_to_float(ma.get('monatliche_soll_stunden')):.2f} h")
    c3.metric("Stundenlohn", f"{_to_float(ma.get('stundenlohn_brutto')):.2f} EUR")
    c4.metric("Urlaub/Jahr", f"{_to_float(ma.get('jahres_urlaubstage')):.1f} Tg")

    eintritt_default = _safe_date(ma.get("eintrittsdatum")) or date.today()
    austritt_default = _safe_date(ma.get("austrittsdatum"))

    with st.form(f"stammdaten_form_{ma['id']}"):
        st.markdown("#### Stammdaten bearbeiten")
        p1, p2, p3 = st.columns(3)
        with p1:
            vorname = st.text_input("Vorname", value=ma.get("vorname") or "")
        with p2:
            nachname = st.text_input("Nachname", value=ma.get("nachname") or "")
        with p3:
            personalnummer = st.text_input("Personalnummer", value=ma.get("personalnummer") or "")

        a1, a2, a3 = st.columns(3)
        with a1:
            email = st.text_input("E-Mail", value=ma.get("email") or "")
        with a2:
            telefon = st.text_input("Telefon", value=ma.get("telefon") or "")
        with a3:
            beschaeftigungsart = st.text_input("Beschäftigungsart", value=ma.get("beschaeftigungsart") or "")

        adr1, adr2, adr3 = st.columns(3)
        with adr1:
            strasse = st.text_input("Straße", value=ma.get("strasse") or "")
        with adr2:
            plz = st.text_input("PLZ", value=ma.get("plz") or "")
        with adr3:
            ort = st.text_input("Ort", value=ma.get("ort") or "")

        d1, d2, d3 = st.columns(3)
        with d1:
            eintrittsdatum = st.date_input("Eintrittsdatum", value=eintritt_default, format="DD.MM.YYYY")
        with d2:
            hat_austritt = st.checkbox("Austrittsdatum gesetzt", value=austritt_default is not None)
        with d3:
            austrittsdatum = st.date_input(
                "Austrittsdatum",
                value=austritt_default or date.today(),
                format="DD.MM.YYYY",
                disabled=not hat_austritt,
            )

        l1, l2, l3 = st.columns(3)
        with l1:
            monatliche_soll_stunden = st.number_input(
                "Monatliche Sollstunden",
                min_value=0.0,
                value=_to_float(ma.get("monatliche_soll_stunden")),
                step=0.5,
            )
        with l2:
            stundenlohn_brutto = st.number_input(
                "Stundenlohn (brutto)",
                min_value=0.0,
                value=_to_float(ma.get("stundenlohn_brutto")),
                step=0.5,
            )
        with l3:
            jahres_urlaubstage = st.number_input(
                "Urlaubstage/Jahr",
                min_value=0.0,
                value=_to_float(ma.get("jahres_urlaubstage")),
                step=0.5,
            )

        z1, z2, z3 = st.columns(3)
        with z1:
            resturlaub_vorjahr = st.number_input(
                "Resturlaub Vorjahr",
                min_value=0.0,
                value=_to_float(ma.get("resturlaub_vorjahr")),
                step=0.5,
            )
        with z2:
            sonntagszuschlag_aktiv = st.checkbox(
                "Sonntagszuschlag aktiv",
                value=bool(ma.get("sonntagszuschlag_aktiv")),
            )
        with z3:
            feiertagszuschlag_aktiv = st.checkbox(
                "Feiertagszuschlag aktiv",
                value=bool(ma.get("feiertagszuschlag_aktiv")),
            )

        save = st.form_submit_button("Stammdaten speichern", type="primary", use_container_width=True)
        if save:
            payload = {
                "vorname": vorname,
                "nachname": nachname,
                "personalnummer": personalnummer,
                "email": email,
                "telefon": telefon,
                "beschaeftigungsart": beschaeftigungsart,
                "strasse": strasse,
                "plz": plz,
                "ort": ort,
                "eintrittsdatum": eintrittsdatum.isoformat(),
                "austrittsdatum": austrittsdatum.isoformat() if hat_austritt else None,
                "monatliche_soll_stunden": float(monatliche_soll_stunden),
                "stundenlohn_brutto": float(stundenlohn_brutto),
                "jahres_urlaubstage": float(jahres_urlaubstage),
                "resturlaub_vorjahr": float(resturlaub_vorjahr),
                "sonntagszuschlag_aktiv": bool(sonntagszuschlag_aktiv),
                "feiertagszuschlag_aktiv": bool(feiertagszuschlag_aktiv),
            }
            ok = update_mitarbeiter(ma["id"], payload)
            if ok:
                st.success("Stammdaten gespeichert.")
                st.rerun()
            else:
                st.error("Speichern fehlgeschlagen. Bitte Felder/Schema prüfen.")

    with st.expander("📎 Vertrag oder Dokument hochladen", expanded=True):
        with st.form(f"dokument_upload_form_{ma['id']}"):
            u1, u2, u3 = st.columns(3)
            with u1:
                dokument_typ = st.selectbox(
                    "Dokumenttyp",
                    ["arbeitsvertrag", "zusatzvereinbarung", "attest", "bescheinigung", "sonstiges"],
                )
            with u2:
                gueltig_ab = st.date_input("Gültig ab", value=date.today(), format="DD.MM.YYYY")
            with u3:
                befristet = st.checkbox("Befristet", value=False)

            u4, u5, u6 = st.columns(3)
            with u4:
                gueltig_bis = st.date_input(
                    "Gültig bis",
                    value=date.today(),
                    format="DD.MM.YYYY",
                    disabled=not befristet,
                )
            with u5:
                vertrag_wochenstunden = st.number_input("Wochenstunden", min_value=0.0, value=0.0, step=0.5)
            with u6:
                vertrag_soll_monat = st.number_input(
                    "Sollstunden/Monat",
                    min_value=0.0,
                    value=float(ma.get("monatliche_soll_stunden") or 0.0),
                    step=0.5,
                )

            u7, u8, u9 = st.columns(3)
            with u7:
                vertrag_urlaub = st.number_input(
                    "Urlaub/Jahr (Vertrag)",
                    min_value=0.0,
                    value=float(ma.get("jahres_urlaubstage") or 0.0),
                    step=0.5,
                )
            with u8:
                vertrag_lohn = st.number_input(
                    "Stundenlohn (Vertrag)",
                    min_value=0.0,
                    value=float(ma.get("stundenlohn_brutto") or 0.0),
                    step=0.5,
                )
            with u9:
                dokument_status = st.selectbox("Status", ["aktiv", "abgelaufen", "fehlend"])

            notiz = st.text_input("Dokumentname / Notiz", value=f"{dokument_typ}_{datetime.now().strftime('%Y%m%d')}")
            upload = st.file_uploader(
                "Datei auswählen",
                type=["pdf", "png", "jpg", "jpeg", "doc", "docx"],
                key=f"dokument_file_{ma['id']}",
            )
            save_upload = st.form_submit_button("Dokument hochladen", type="primary", use_container_width=True)

            if save_upload:
                if upload is None:
                    st.error("Bitte zuerst eine Datei auswählen.")
                else:
                    file_bytes = upload.read()
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = upload.name.replace(" ", "_")
                    file_path = f"mitarbeiter/{ma['id']}/{ts}_{safe_name}"
                    upload_result = upload_file_to_storage_result(
                        "dokumente",
                        file_path,
                        file_bytes,
                        fallback_buckets=["arbeitsvertraege"],
                    )
                    if not upload_result.get("ok"):
                        st.error(
                            "Upload in Supabase Storage fehlgeschlagen. "
                            f"Details: {upload_result.get('status_code') or '-'} "
                            f"{upload_result.get('error') or ''}"
                        )
                    else:
                        used_bucket = upload_result.get("bucket") or "dokumente"
                        file_url = _storage_public_url(used_bucket, file_path)
                        try:
                            supabase.table("mitarbeiter_dokumente").insert(
                                {
                                    "betrieb_id": ma.get("betrieb_id") or st.session_state.get("betrieb_id"),
                                    "mitarbeiter_id": ma["id"],
                                    "name": notiz or upload.name,
                                    "typ": dokument_typ,
                                    "file_path": file_path,
                                    "file_url": file_url,
                                    "status": dokument_status,
                                    "gueltig_bis": gueltig_bis.isoformat() if befristet else None,
                                    "metadaten": {
                                        "uploaded_at": datetime.now().isoformat(),
                                        "source": "admin_dashboard",
                                    },
                                    "erstellt_von": st.session_state.get("user_id"),
                                }
                            ).execute()
                        except Exception as e:
                            st.warning(f"Dokument-Metadaten konnten nicht gespeichert werden: {e}")

                        if dokument_typ == "arbeitsvertrag":
                            try:
                                supabase.table("vertraege").insert(
                                    {
                                        "betrieb_id": ma.get("betrieb_id") or st.session_state.get("betrieb_id"),
                                        "mitarbeiter_id": ma["id"],
                                        "gueltig_ab": gueltig_ab.isoformat(),
                                        "gueltig_bis": gueltig_bis.isoformat() if befristet else None,
                                        "wochenstunden": float(vertrag_wochenstunden or 0.0),
                                        "soll_stunden_monat": float(vertrag_soll_monat or 0.0),
                                        "urlaubstage_jahr": float(vertrag_urlaub or 0.0),
                                        "stundenlohn_brutto": float(vertrag_lohn or 0.0),
                                        "vertrag_dokument_pfad": file_path,
                                    }
                                ).execute()
                            except Exception as e:
                                st.warning(f"Vertragseintrag konnte nicht gespeichert werden: {e}")

                            # Legacy-Fallback-Felder
                            try:
                                update_mitarbeiter(ma["id"], {"vertrag_pdf_path": file_path})
                            except Exception:
                                pass
                            try:
                                update_mitarbeiter(ma["id"], {"arbeitsvertrag_pfad": file_path})
                            except Exception:
                                pass

                        st.success("Dokument erfolgreich hochgeladen.")
                        st.rerun()

    st.markdown("#### Hinterlegte Verträge")
    try:
        vertr_res = (
            supabase.table("vertraege")
            .select(
                "id, gueltig_ab, gueltig_bis, soll_stunden_monat, "
                "wochenstunden, urlaubstage_jahr, stundenlohn_brutto"
            )
            .eq("mitarbeiter_id", ma["id"])
            .order("gueltig_ab", desc=True)
            .limit(20)
            .execute()
        )
        vertraege = vertr_res.data or []
    except Exception:
        vertraege = []

    if vertraege:
        st.dataframe(
            [
                {
                    "ID": v.get("id"),
                    "Gültig ab": v.get("gueltig_ab"),
                    "Gültig bis": v.get("gueltig_bis") or "unbefristet",
                    "Soll (Monat)": float(v.get("soll_stunden_monat") or 0.0),
                    "Wochenstunden": float(v.get("wochenstunden") or 0.0),
                    "Urlaub/Jahr": float(v.get("urlaubstage_jahr") or 0.0),
                    "Stundenlohn": float(v.get("stundenlohn_brutto") or 0.0),
                }
                for v in vertraege
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Vertragsversionen bearbeiten")
        for v in vertraege:
            vid = v.get("id")
            if vid is None:
                continue
            with st.expander(
                f"Vertrag #{vid} | ab {v.get('gueltig_ab')} | Soll {float(v.get('soll_stunden_monat') or 0):.2f}h",
                expanded=False,
            ):
                with st.form(f"vertrag_edit_{vid}"):
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        vg_ab = st.date_input(
                            "Gültig ab",
                            value=_safe_date(v.get("gueltig_ab")) or date.today(),
                            format="DD.MM.YYYY",
                            key=f"vg_ab_{vid}",
                        )
                    with e2:
                        vg_befristet = st.checkbox(
                            "Befristet",
                            value=bool(v.get("gueltig_bis")),
                            key=f"vg_bef_{vid}",
                        )
                    with e3:
                        vg_bis = st.date_input(
                            "Gültig bis",
                            value=_safe_date(v.get("gueltig_bis")) or date.today(),
                            format="DD.MM.YYYY",
                            disabled=not vg_befristet,
                            key=f"vg_bis_{vid}",
                        )

                    e4, e5, e6 = st.columns(3)
                    with e4:
                        vg_wochen = st.number_input(
                            "Wochenstunden",
                            min_value=0.0,
                            value=float(v.get("wochenstunden") or 0.0),
                            step=0.5,
                            key=f"vg_wochen_{vid}",
                        )
                    with e5:
                        vg_soll = st.number_input(
                            "Sollstunden/Monat",
                            min_value=0.0,
                            value=float(v.get("soll_stunden_monat") or 0.0),
                            step=0.5,
                            key=f"vg_soll_{vid}",
                        )
                    with e6:
                        vg_urlaub = st.number_input(
                            "Urlaub/Jahr",
                            min_value=0.0,
                            value=float(v.get("urlaubstage_jahr") or 0.0),
                            step=0.5,
                            key=f"vg_urlaub_{vid}",
                        )

                    vg_lohn = st.number_input(
                        "Stundenlohn",
                        min_value=0.0,
                        value=float(v.get("stundenlohn_brutto") or 0.0),
                        step=0.5,
                        key=f"vg_lohn_{vid}",
                    )

                    s_col, d_col = st.columns(2)
                    with s_col:
                        save_vertrag = st.form_submit_button("Vertrag speichern", type="primary", use_container_width=True)
                    with d_col:
                        delete_vertrag = st.form_submit_button("Vertrag löschen", use_container_width=True)

                    if save_vertrag:
                        try:
                            supabase.table("vertraege").update(
                                {
                                    "gueltig_ab": vg_ab.isoformat(),
                                    "gueltig_bis": vg_bis.isoformat() if vg_befristet else None,
                                    "wochenstunden": float(vg_wochen),
                                    "soll_stunden_monat": float(vg_soll),
                                    "urlaubstage_jahr": float(vg_urlaub),
                                    "stundenlohn_brutto": float(vg_lohn),
                                }
                            ).eq("id", vid).eq("mitarbeiter_id", ma["id"]).execute()
                            st.success("Vertrag aktualisiert.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Vertrag konnte nicht gespeichert werden: {e}")

                    if delete_vertrag:
                        try:
                            supabase.table("vertraege").delete().eq("id", vid).eq("mitarbeiter_id", ma["id"]).execute()
                            st.success("Vertrag gelöscht.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Vertrag konnte nicht gelöscht werden: {e}")
    else:
        st.info("Keine Verträge gespeichert.")

    st.markdown("#### Mitarbeiter-Dokumente")
    try:
        docs_res = (
            supabase.table("mitarbeiter_dokumente")
            .select("name, typ, status, gueltig_bis, file_path, file_url, created_at")
            .eq("mitarbeiter_id", ma["id"])
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        docs = docs_res.data or []
    except Exception:
        docs = []

    if docs:
        rows = []
        for d in docs:
            url = d.get("file_url") or _storage_public_url("dokumente", d.get("file_path"))
            rows.append(
                {
                    "Name": d.get("name"),
                    "Typ": d.get("typ"),
                    "Status": d.get("status"),
                    "Gültig bis": d.get("gueltig_bis"),
                    "Upload": d.get("created_at"),
                    "Link": url or "-",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Keine Dokumente für diesen Mitarbeiter vorhanden.")


def _show_planovo_import_tab():
    st.subheader("📥 Planovo-Import (historische Daten)")
    supabase = get_supabase_client()
    alle_ma = _load_admin_mitarbeiter()
    if not alle_ma:
        st.info("Keine Mitarbeiter vorhanden.")
        return

    ma_options = {f"{m.get('vorname', '')} {m.get('nachname', '')} ({m.get('personalnummer', '-')})": m for m in alle_ma}
    selected_label = st.selectbox(
        "Ziel-Mitarbeiter",
        list(ma_options.keys()),
        key="planovo_target_ma",
        help="Importierte Planovo-Daten werden diesem Mitarbeiter zugeordnet.",
    )
    ma = ma_options[selected_label]
    ueberschreiben = st.checkbox(
        "Import-Monat vollständig überschreiben (empfohlen)",
        value=True,
        help="Löscht bestehende Importdaten im Zielmonat und schreibt den Monat neu, damit keine Doppeleinträge entstehen.",
    )
    upload = st.file_uploader(
        "Planovo Datei (.xlsx oder .csv)",
        type=["xlsx", "csv"],
        key="planovo_import_upload",
    )

    if upload is None:
        st.info("Bitte eine Planovo-Exportdatei hochladen.")
        return

    parsed = lese_upload_datei(upload)
    fehler = parsed.get("fehler") or []
    if fehler:
        st.error("Datei konnte nicht verarbeitet werden.")
        for f in fehler:
            st.write(f"- {f}")
        return

    zeitraum = parsed.get("zeitraum", {})
    tage = parsed.get("tage", [])
    startsaldo = float(parsed.get("startsaldo") or 0.0)
    k1, k2, k3 = st.columns(3)
    k1.metric("Tage erkannt", len(tage))
    k2.metric("Zeitraum", f"{zeitraum.get('monat', '-')}/{zeitraum.get('jahr', '-')}")
    k3.metric("Startsaldo", f"{startsaldo:+.2f} h")

    if tage:
        preview_rows = []
        for row in tage[:20]:
            preview_rows.append(
                {
                    "Datum": row.get("datum").strftime("%d.%m.%Y") if row.get("datum") else "-",
                    "Ist": float(row.get("ist") or 0.0),
                    "Soll": float(row.get("soll") or 0.0),
                    "Saldo": float(row.get("saldo") or 0.0),
                    "Notiz": row.get("korrektur_notiz") or "",
                }
            )
        st.markdown("#### Vorschau (erste 20 Zeilen)")
        st.dataframe(preview_rows, use_container_width=True, hide_index=True)

    st.markdown("#### Trockenlauf (vor Import)")
    dryrun = dry_run_import_summary(
        parsed,
        mitarbeiter_id=ma["id"],
        supabase_client=supabase,
    )
    if dryrun.get("ok"):
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Würde importieren", int(dryrun.get("would_import") or 0))
        d2.metric("Würde überspringen", int(dryrun.get("would_skip") or 0))
        d3.metric("Würde löschen (Zeit)", int(dryrun.get("would_delete_zeiterfassung") or 0))
        d4.metric("Würde löschen (Krank)", int(dryrun.get("would_delete_krankheitstage") or 0))
        st.caption(
            f"Zeitraum: {dryrun.get('range_start')} bis {dryrun.get('range_end')} | "
            f"Legacy-Konto-Löschung: {int(dryrun.get('would_delete_arbeitszeitkonto') or 0)}"
        )
    else:
        for err in dryrun.get("fehler", []):
            st.warning(err)

    if st.button("Planovo-Daten importieren", type="primary", use_container_width=True):
        with st.spinner("Import läuft..."):
            result = importiere_in_crewbase(
                parsed,
                mitarbeiter_id=ma["id"],
                betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
                supabase_client=supabase,
                ueberschreiben=ueberschreiben,
            )
        if result.get("ok"):
            st.success("Import abgeschlossen.")
        else:
            st.warning("Import mit Fehlern abgeschlossen.")

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Importiert", int(result.get("importiert") or 0))
        r2.metric("Übersprungen", int(result.get("uebersprungen") or 0))
        r3.metric("Kranktage", int(result.get("kranktage_importiert") or 0))
        r4.metric("AZK Sync-Monate", int(result.get("azk_sync_monate") or 0))

        if result.get("fehler"):
            st.markdown("#### Fehlerdetails")
            for err in result["fehler"]:
                st.write(f"- {err}")


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

    st.markdown("---")
    st.markdown("### 🔄 Geschlossener Kreislauf – AZK Konsistenzcheck")
    st.caption(
        "Prüft, ob Zeiteinträge/Abwesenheiten und berechneter AZK-Snapshot zueinander passen. "
        "Abweichungen weisen auf Dateninkonsistenzen oder fehlerhafte Zweckzuordnung hin."
    )

    cc1, cc2 = st.columns([1, 1])
    with cc1:
        check_monat = st.number_input(
            "Prüfmonat",
            min_value=1,
            max_value=12,
            value=date.today().month,
            key="sys_check_monat",
        )
    with cc2:
        check_jahr = st.number_input(
            "Prüfjahr",
            min_value=2024,
            max_value=2100,
            value=date.today().year,
            key="sys_check_jahr",
        )

    if st.button("🔍 Kreislauf prüfen", use_container_width=True, key="sys_cycle_check"):
        ma_list = _load_admin_mitarbeiter()
        if not ma_list:
            st.info("Keine Mitarbeiter für den Konsistenzcheck gefunden.")
            return

        findings = []
        ok_count = 0
        for ma in ma_list:
            try:
                validation = validate_work_account_month(
                    supabase,
                    betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
                    mitarbeiter_id=ma["id"],
                    monat=int(check_monat),
                    jahr=int(check_jahr),
                )
                if validation.get("ok"):
                    ok_count += 1
                else:
                    findings.append(
                        {
                            "Mitarbeiter": f"{ma.get('vorname', '')} {ma.get('nachname', '')}".strip(),
                            "Monat": f"{int(check_monat):02d}/{int(check_jahr)}",
                            "Details": "; ".join(validation.get("issues") or ["Unbekannte Abweichung"]),
                        }
                    )
            except Exception as exc:
                findings.append(
                    {
                        "Mitarbeiter": f"{ma.get('vorname', '')} {ma.get('nachname', '')}".strip(),
                        "Monat": f"{int(check_monat):02d}/{int(check_jahr)}",
                        "Details": f"Prüfung fehlgeschlagen: {exc}",
                    }
                )

        if findings:
            st.warning(
                f"Kreislauf-Check abgeschlossen: {ok_count} konsistent, {len(findings)} mit Abweichung."
            )
            st.dataframe(findings, use_container_width=True, hide_index=True)
        else:
            st.success(f"Kreislauf-Check erfolgreich: alle {ok_count} Mitarbeiter konsistent.")


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

    if st.button("Konten synchronisieren", type="primary", use_container_width=True):
        closed_count = 0
        for ma in alle_ma:
            try:
                snapshot = sync_work_account_for_month(
                    supabase,
                    betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
                    mitarbeiter_id=ma["id"],
                    monat=int(monat),
                    jahr=int(jahr),
                )
                if snapshot.monat_abgeschlossen:
                    closed_count += 1
            except Exception:
                pass
        st.success("Arbeitszeitkonten synchronisiert.")
        if closed_count:
            st.info(f"{closed_count} Konten stammen aus unveränderlichen Monatsabschlüssen.")

    if st.button("Monat abschließen (unveränderlich)", use_container_width=True):
        for ma in alle_ma:
            try:
                close_work_account_month(
                    supabase,
                    betrieb_id=ma.get("betrieb_id") or st.session_state.get("betrieb_id") or 1,
                    mitarbeiter_id=ma["id"],
                    monat=int(monat),
                    jahr=int(jahr),
                    created_by=st.session_state.get("user_id"),
                )
            except Exception:
                pass
        st.success(f"Monat {int(monat):02d}/{int(jahr)} wurde abgeschlossen.")

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

    positive = sum(1 for r in rows if float(r.get("ueberstunden_saldo") or 0) >= 0)
    negative = len(rows) - positive
    total_ist = sum(float(r.get("ist_stunden") or 0) for r in rows)
    total_soll = sum(float(r.get("soll_stunden") or 0) for r in rows)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Konten", len(rows))
    s2.metric("Saldo ≥ 0", positive)
    s3.metric("Saldo < 0", negative)
    s4.metric("Ist / Soll", f"{total_ist:.1f}h / {total_soll:.1f}h")
    st.markdown("---")

    closed_ids = set()
    try:
        closed_q = supabase.table("azk_monatsabschluesse").select("mitarbeiter_id").eq("monat", int(monat)).eq("jahr", int(jahr))
        betrieb_id = st.session_state.get("betrieb_id")
        if betrieb_id is not None:
            closed_q = closed_q.eq("betrieb_id", betrieb_id)
        closed_rows = closed_q.execute().data or []
        closed_ids = {int(r.get("mitarbeiter_id")) for r in closed_rows if r.get("mitarbeiter_id") is not None}
    except Exception:
        closed_ids = set()

    ma_lookup = {m["id"]: f"{m['vorname']} {m['nachname']}" for m in alle_ma}
    view_rows = []
    for row in rows:
        ma_id = row.get("mitarbeiter_id")
        view_rows.append(
            {
                "Mitarbeiter": ma_lookup.get(ma_id, str(ma_id)),
                "Monat fixiert": "Ja" if ma_id in closed_ids else "Nein",
                "Soll (h)": float(row.get("soll_stunden") or 0),
                "Ist (h)": float(row.get("ist_stunden") or 0),
                "Saldo (h)": float(row.get("ueberstunden_saldo") or 0),
                "Urlaub gesamt": float(row.get("urlaubstage_gesamt") or 0),
                "Urlaub genommen": float(row.get("urlaubstage_genommen") or 0),
                "Krankheitstage": float(row.get("krankheitstage_gesamt") or 0),
            }
        )
    st.dataframe(view_rows, use_container_width=True, hide_index=True)


def show_admin_dashboard():
    st.set_page_config(page_title="Admin-Zentrale", layout="wide")
    apply_custom_css()
    st.title("🇩🇪 CrewBase – Admin")

    tabs = st.tabs(
        [
            "📅 Dienstplanung",
            "🏖️ Abwesenheiten",
            "👥 Mitarbeiter",
            "📁 Planovo-Import",
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
        _show_mitarbeiter_stammdaten_tab()
    with tabs[3]:
        _show_planovo_import_tab()
    with tabs[4]:
        _show_zeitauswertung_tab()
    with tabs[5]:
        _show_arbeitszeitkonten_tab()
    with tabs[6]:
        admin_mastergeraete.show_mastergeraete()
    with tabs[7]:
        _show_system_tab()


if __name__ == "__main__":
    show_admin_dashboard()
