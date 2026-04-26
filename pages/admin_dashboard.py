import json
import os
import re
from datetime import date, datetime

import streamlit as st

from utils.absences import delete_absence, store_absence, update_absence
from utils.absence_policy import (
    load_absence_compensation_policy,
    save_absence_compensation_policy,
)
from utils.cache_manager import clear_app_caches
from utils.database import (
    get_supabase_client,
    get_service_role_client,
    update_mitarbeiter,
    upload_file_to_storage_result,
)
from utils.session import require_betrieb_id
from utils.styles import apply_custom_css
from utils.work_accounts import (
    close_work_account_month,
    set_work_account_opening_balance,
    sync_work_account_for_month,
    validate_work_account_month,
)
from utils.branding import BRAND_APP_NAME, BRAND_LOGO_IMAGE


ADMIN_MITARBEITER_COLUMNS = (
    "id, betrieb_id, vorname, nachname, personalnummer, email, telefon, "
    "beschaeftigungsart, strasse, plz, ort, eintrittsdatum, austrittsdatum, geburtsdatum, "
    "monatliche_soll_stunden, monatliche_brutto_verguetung, jahres_urlaubstage, resturlaub_vorjahr, "
    "sonntagszuschlag_aktiv, feiertagszuschlag_aktiv"
)
ADMIN_MITARBEITER_COLUMNS_FALLBACK = (
    "id, betrieb_id, vorname, nachname, personalnummer, email, telefon, "
    "beschaeftigungsart, strasse, plz, ort, eintrittsdatum, austrittsdatum, geburtsdatum, "
    "monatliche_soll_stunden, jahres_urlaubstage, resturlaub_vorjahr, "
    "sonntagszuschlag_aktiv, feiertagszuschlag_aktiv"
)
STUNDENLOHN_PERSONAL_COLUMNS = (
    "stundenlohn_personalakte",
    "stundenlohn_brutto",
    "stundenlohn",
)
ADMIN_NAV_OPTIONS = (
    "Dienstplanung",
    "Personalakte",
    "Abwesenheiten",
    "Arbeitszeitkonten",
    "Zeitauswertung",
    "Verträge",
    "Premium",
    "Datenschutz",
    "Sicherheit",
    "Leads",
)
ADMIN_NAV_ALIASES = {
    "Vertraege": "Verträge",
    "Mitarbeiter": "Personalakte",
}


@st.cache_data(ttl=600, show_spinner=False)
def _resolve_stundenlohn_personal_column() -> str:
    """
    Ermittelt eine optionale Stundenlohn-Spalte für die Personalakte.
    Diese Spalte ist rein dokumentarisch und wird NICHT für Zeitberechnungen verwendet.
    """
    supabase = get_supabase_client()
    for col in STUNDENLOHN_PERSONAL_COLUMNS:
        try:
            supabase.table("mitarbeiter").select(f"id,{col}").limit(1).execute()
            return col
        except Exception:
            continue
    return ""


def _load_admin_mitarbeiter():
    betrieb_id = st.session_state.get("betrieb_id")
    return _cached_admin_mitarbeiter(betrieb_id)


@st.cache_data(ttl=600, show_spinner=False)
def _cached_admin_mitarbeiter(betrieb_id):
    supabase = get_supabase_client()
    stundenlohn_col = _resolve_stundenlohn_personal_column()
    extra = f", {stundenlohn_col}" if stundenlohn_col else ""

    def _run_query(columns: str):
        q = supabase.table("mitarbeiter").select(columns).order("nachname")
        if betrieb_id is not None:
            q = q.eq("betrieb_id", betrieb_id)
        return q.execute().data or []

    try:
        rows = _run_query(ADMIN_MITARBEITER_COLUMNS + extra)
    except Exception:
        try:
            rows = _run_query(ADMIN_MITARBEITER_COLUMNS_FALLBACK + extra)
        except Exception:
            rows = _run_query(ADMIN_MITARBEITER_COLUMNS_FALLBACK)
        for row in rows:
            row.setdefault("monatliche_brutto_verguetung", 0.0)

    for row in rows:
        row["akten_stundenlohn"] = _to_float(row.get(stundenlohn_col), 0.0) if stundenlohn_col else 0.0

    return rows


@st.cache_data(ttl=600, show_spinner=False)
def _cached_arbeitszeitkonten_rows(betrieb_id: int | None):
    supabase = get_supabase_client()
    base_q = (
        supabase.table("arbeitszeit_konten")
        .select(
            "mitarbeiter_id, soll_stunden, ist_stunden, ueberstunden_saldo, "
            "urlaubstage_gesamt, urlaubstage_genommen, krankheitstage_gesamt"
        )
        .order("mitarbeiter_id")
    )
    q = base_q
    if betrieb_id is not None:
        q = base_q.eq("betrieb_id", int(betrieb_id))
    try:
        return q.execute().data or []
    except Exception:
        # Legacy-Schema-Fallback ohne betrieb_id-Filter.
        try:
            return base_q.execute().data or []
        except Exception:
            return []


@st.cache_data(ttl=600, show_spinner=False)
def _cached_azk_closed_rows(betrieb_id: int | None, monat: int, jahr: int):
    supabase = get_supabase_client()
    base_q = (
        supabase.table("azk_monatsabschluesse")
        .select("mitarbeiter_id, ueberstunden_saldo_start, korrektur_grund, manuelle_korrektur_saldo")
        .eq("monat", int(monat))
        .eq("jahr", int(jahr))
    )
    q = base_q
    if betrieb_id is not None:
        q = base_q.eq("betrieb_id", int(betrieb_id))
    try:
        return q.execute().data or []
    except Exception:
        try:
            return base_q.execute().data or []
        except Exception:
            return []


@st.cache_data(ttl=600, show_spinner=False)
def _cached_existing_init_marker(mitarbeiter_id: int):
    supabase = get_supabase_client()
    try:
        existing_init_res = (
            supabase.table("azk_monatsabschluesse")
            .select("id, monat, jahr")
            .eq("mitarbeiter_id", int(mitarbeiter_id))
            .eq("jahr", 2026)
            .eq("ist_initialisierung", True)
            .limit(1)
            .execute()
        )
        return (existing_init_res.data or [None])[0]
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def _cached_system_counts(betrieb_id: int | None) -> tuple[int, int, int]:
    supabase = get_supabase_client()
    try:
        users_q = supabase.table("users").select("id", count="exact")
        ma_q = supabase.table("mitarbeiter").select("id", count="exact")
        zeit_q = supabase.table("zeiterfassung").select("id", count="exact")
        if betrieb_id is not None:
            users_q = users_q.eq("betrieb_id", int(betrieb_id))
            ma_q = ma_q.eq("betrieb_id", int(betrieb_id))
            zeit_q = zeit_q.eq("betrieb_id", int(betrieb_id))
        users_count = users_q.limit(1).execute().count or 0
        ma_count = ma_q.limit(1).execute().count or 0
        zeit_count = zeit_q.limit(1).execute().count or 0
        return int(users_count), int(ma_count), int(zeit_count)
    except Exception:
        return 0, 0, 0


def _refresh_after_write() -> None:
    clear_app_caches()


def _normalize_admin_nav(selection: str | None) -> str:
    normalized = ADMIN_NAV_ALIASES.get(str(selection or ""), str(selection or "Dienstplanung"))
    if normalized not in ADMIN_NAV_OPTIONS:
        return "Dienstplanung"
    return normalized


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


def _to_int(value, default: int = 0) -> int:
    try:
        return int(round(float(value if value is not None else default)))
    except Exception:
        return int(default)


def _upload_status_key(mitarbeiter_id: int) -> str:
    return f"personalakte_upload_status_{int(mitarbeiter_id)}"


def _set_upload_status(
    mitarbeiter_id: int,
    *,
    level: str,
    message: str,
    details: str = "",
) -> None:
    st.session_state[_upload_status_key(mitarbeiter_id)] = {
        "level": str(level or "info"),
        "message": str(message or ""),
        "details": str(details or ""),
        "ts": datetime.now().isoformat(timespec="seconds"),
    }


def _clear_upload_status(mitarbeiter_id: int) -> None:
    st.session_state.pop(_upload_status_key(mitarbeiter_id), None)


def _render_upload_status(mitarbeiter_id: int) -> None:
    status = st.session_state.get(_upload_status_key(mitarbeiter_id))
    if not status:
        return
    level = str(status.get("level") or "info").lower()
    message = str(status.get("message") or "")
    details = str(status.get("details") or "")
    ts = str(status.get("ts") or "")

    if level == "error":
        st.error(message or "Letzter Upload fehlgeschlagen.")
    elif level == "warning":
        st.warning(message or "Letzter Upload mit Hinweisen.")
    elif level == "success":
        st.success(message or "Letzter Upload erfolgreich.")
    else:
        st.info(message or "Letzte Upload-Meldung.")

    if ts:
        st.caption(f"Zeitpunkt: {ts}")
    if details:
        st.caption("Fehler-/Statusdetails (kopierbar):")
        st.code(details, language="text")

    if st.button(
        "Upload-Meldung ausblenden",
        key=f"clear_upload_status_{int(mitarbeiter_id)}",
        use_container_width=True,
    ):
        _clear_upload_status(mitarbeiter_id)
        st.rerun()


def _update_mitarbeiter_stammdaten_robust(
    *,
    mitarbeiter_id: int,
    betrieb_id: int | None,
    payload: dict,
) -> tuple[bool, str, list[str]]:
    """
    Aktualisiert Stammdaten robust über unterschiedliche DB-Schemas:
    - versucht primären Client + optional Service-Role-Client
    - entfernt unbekannte Spalten automatisch aus dem Payload
    """
    working_payload = dict(payload)
    dropped_columns: list[str] = []
    last_error = "unbekannter Fehler"

    clients: list[tuple[str, object]] = [("primary", get_supabase_client())]
    try:
        clients.append(("service_role", get_service_role_client()))
    except Exception:
        pass

    max_attempts = max(1, len(working_payload) + 2)
    for _ in range(max_attempts):
        if not working_payload:
            return False, "Keine speicherbaren Felder im Payload vorhanden.", dropped_columns

        missing_column_handled = False
        for client_name, client in clients:
            try:
                q = client.table("mitarbeiter").update(working_payload).eq("id", mitarbeiter_id)
                if betrieb_id is not None:
                    q = q.eq("betrieb_id", betrieb_id)
                q.execute()
                info = f"update_ok client={client_name}"
                if dropped_columns:
                    info += f" dropped={','.join(dropped_columns)}"
                return True, info, dropped_columns
            except Exception as exc:
                last_error = f"update_fail client={client_name}: {exc}"
                msg = str(exc)
                col_match = re.search(r'column\s+"?([a-zA-Z0-9_]+)"?\s+does not exist', msg, flags=re.IGNORECASE)
                if col_match:
                    col = str(col_match.group(1) or "").strip()
                    if col and col in working_payload:
                        working_payload.pop(col, None)
                        dropped_columns.append(col)
                        missing_column_handled = True
                        break
        if not missing_column_handled:
            break

    return False, last_error, dropped_columns


def _insert_mitarbeiter_dokument_robust(
    supabase,
    base_payload: dict,
) -> tuple[bool, str]:
    """
    Speichert Dokument-Metadaten robust über unterschiedliche DB-Schemas:
    - versucht mehrere Payload-Varianten (legacy/new)
    - versucht bei Bedarf Service-Role-Client
    """
    variants: list[tuple[str, dict]] = []
    full = dict(base_payload)
    variants.append(("full", full))

    v_no_ersteller = dict(full)
    v_no_ersteller.pop("erstellt_von", None)
    variants.append(("no_erstellt_von", v_no_ersteller))

    v_no_meta = dict(full)
    v_no_meta.pop("metadaten", None)
    variants.append(("no_metadaten", v_no_meta))

    v_no_status = dict(full)
    v_no_status.pop("status", None)
    variants.append(("no_status", v_no_status))

    v_status_aktiv = dict(full)
    v_status_aktiv["status"] = "aktiv"
    variants.append(("status_aktiv", v_status_aktiv))

    v_minimal = {
        k: full.get(k)
        for k in ("betrieb_id", "mitarbeiter_id", "name", "typ", "file_path", "file_url")
        if full.get(k) is not None
    }
    variants.append(("minimal", v_minimal))

    v_minimal_no_betrieb = {
        k: full.get(k)
        for k in ("mitarbeiter_id", "name", "typ", "file_path", "file_url")
        if full.get(k) is not None
    }
    variants.append(("minimal_no_betrieb", v_minimal_no_betrieb))

    # Duplikate nach normalisierter Signatur vermeiden.
    # Payload kann verschachtelte dicts enthalten (z. B. metadaten) und ist
    # damit nicht direkt als tuple(payload.items()) hashbar.
    dedup_variants: list[tuple[str, dict]] = []
    seen: set[str] = set()
    for label, payload in variants:
        try:
            sig = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
        except Exception:
            sig = str(payload)
        if sig in seen:
            continue
        seen.add(sig)
        dedup_variants.append((label, payload))

    clients: list[tuple[str, object]] = [("primary", supabase)]
    try:
        svc = get_service_role_client()
        clients.append(("service_role", svc))
    except Exception:
        pass

    last_error = "unbekannter Fehler"
    for client_name, client in clients:
        for variant_name, payload in dedup_variants:
            try:
                client.table("mitarbeiter_dokumente").insert(payload).execute()
                return True, f"insert_ok client={client_name} variant={variant_name}"
            except Exception as exc:
                last_error = (
                    f"insert_fail client={client_name} variant={variant_name}: {exc}"
                )
                continue
    return False, last_error


def _show_zeitauswertung_tab():
    from pages import zeitauswertung

    st.subheader("Zeitauswertung und Lohn")
    alle_ma = _load_admin_mitarbeiter()
    if not alle_ma:
        st.info("Keine Mitarbeiter für die Auswertung gefunden.")
        return

    namen = [f"{m.get('nachname', '')} {m.get('vorname', '')}".strip() or f"ID {m.get('id')}" for m in alle_ma]
    idx = st.selectbox(
        "Mitarbeiter auswählen",
        range(len(namen)),
        format_func=lambda i: namen[i],
        key="zeitauswertung_ma_idx",
    )
    zeitauswertung.show_zeitauswertung(alle_ma[idx], admin_modus=True)


def _show_absenzen_tab():
    st.subheader("Abwesenheiten und Atteste")
    supabase = get_supabase_client()
    alle_ma = _load_admin_mitarbeiter()
    if not alle_ma:
        st.info("Keine Mitarbeiter gefunden.")
        return

    betrieb_id = st.session_state.get("betrieb_id")
    # Konfigurierbare Bezahl-Logik pro Betrieb.
    paid_types = load_absence_compensation_policy(
        supabase,
        betrieb_id=int(betrieb_id or 0) if betrieb_id is not None else None,
    )
    with st.expander("Bezahl-Logik konfigurieren", expanded=False):
        st.caption("Diese Einstellung steuert, welche Abwesenheitstypen als bezahlt gelten.")
        c1, c2 = st.columns(2)
        with c1:
            paid_urlaub = st.checkbox(
                "Urlaub ist bezahlt",
                value=bool(paid_types.get("urlaub", True)),
                key="abwesen_paid_cfg_urlaub",
            )
            paid_krankheit = st.checkbox(
                "Krankheit (LFZ) ist bezahlt",
                value=bool(paid_types.get("krankheit", True)),
                key="abwesen_paid_cfg_krankheit",
            )
        with c2:
            paid_sonderurlaub = st.checkbox(
                "Sonderurlaub ist bezahlt",
                value=bool(paid_types.get("sonderurlaub", True)),
                key="abwesen_paid_cfg_sonderurlaub",
            )
            paid_unbezahlt = st.checkbox(
                "Unbezahlter Urlaub ist bezahlt",
                value=bool(paid_types.get("unbezahlter_urlaub", False)),
                key="abwesen_paid_cfg_unbezahlter",
            )
        if st.button("Bezahl-Logik speichern", key="abwesen_paid_types_save", use_container_width=True):
            policy_payload = {
                "urlaub": bool(paid_urlaub),
                "krankheit": bool(paid_krankheit),
                "sonderurlaub": bool(paid_sonderurlaub),
                "unbezahlter_urlaub": bool(paid_unbezahlt),
            }
            ok, msg = save_absence_compensation_policy(
                supabase,
                betrieb_id=int(betrieb_id or 0) if betrieb_id is not None else None,
                policy=policy_payload,
            )
            if ok:
                st.success("Bezahl-Logik gespeichert.")
                paid_types = dict(policy_payload)
                st.rerun()
            else:
                st.error(f"Konfiguration konnte nicht gespeichert werden: {msg}")
    abs_query = (
        supabase.table("abwesenheiten")
        .select(
            "id, mitarbeiter_id, typ, start_datum, ende_datum, datum, "
            "stunden_gutschrift, attest_pfad, grund, status, created_at, betrieb_id"
        )
        .order("created_at", desc=True)
        .limit(200)
    )
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

    with st.expander("Neue Abwesenheit erfassen", expanded=True):
        with st.form("abwesenheit_form"):
            c1, c2, c3 = st.columns([1, 1, 1.2])
            with c1:
                typ = st.selectbox("Typ", ["urlaub", "krankheit", "unbezahlter_urlaub", "sonderurlaub"])
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
                        betrieb_id=require_betrieb_id(),
                        mitarbeiter_id=mitarbeiter["id"],
                        typ=typ,
                        start=start,
                        end=ende,
                        monthly_target_hours=float(mitarbeiter.get("monatliche_soll_stunden") or 0.0),
                        attest_pfad=attest_pfad,
                        grund=grund or None,
                        paid_type_config=paid_types,
                        created_by=st.session_state.get("user_id"),
                    )
                    st.success(
                        f"Abwesenheit gespeichert: {result['tage']:.1f} Tage, "
                        f"{result['stunden_gutschrift']:.2f}h Gutschrift."
                    )
                    _refresh_after_write()
                    st.rerun()

    st.markdown("#### Letzte Abwesenheiten")
    if not abwesenheiten:
        st.info("Noch keine Abwesenheiten gespeichert.")
        return

    typ_labels = {
        "urlaub": "Urlaub",
        "krankheit": "Krankheit",
        "krank": "Krankheit",
        "unbezahlter_urlaub": "Unbezahlter Urlaub",
        "sonderurlaub": "Sonderurlaub",
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

    st.markdown("#### Abwesenheit aendern oder loeschen (mit Begruendung)")
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
                ["urlaub", "krankheit", "unbezahlter_urlaub", "sonderurlaub"],
                index=["urlaub", "krankheit", "unbezahlter_urlaub", "sonderurlaub"].index(default_typ),
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
                "Aenderung speichern",
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
                            paid_type_config=paid_types,
                        )
                        st.success("Abwesenheit wurde aktualisiert.")
                        _refresh_after_write()
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
                "Eintrag loeschen",
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
                        _refresh_after_write()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Löschen fehlgeschlagen: {e}")


def _show_mitarbeiter_stammdaten_tab():
    st.subheader("Mitarbeiter-Stammdaten und Dokumente")
    supabase = get_supabase_client()
    # Schritt 1: Verbindung prüfen, bevor Stammdaten-UI gerendert wird.
    try:
        supabase.table("mitarbeiter").select("id").limit(1).execute()
    except Exception as exc:
        st.error(f"Datenbankverbindung für Personalakte fehlgeschlagen: {exc}")
        return

    stundenlohn_col = _resolve_stundenlohn_personal_column()
    alle_ma = _load_admin_mitarbeiter()
    st.caption(
        "Hinweis: 'Stundenlohn' ist ein Personalakten-Feld und hat keinen Einfluss auf Dienstplan- oder Zeiterfassungsberechnungen."
    )

    with st.expander("Mitarbeiter neu anlegen", expanded=False):
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
                new_monatsbrutto = st.number_input("Monatliche Brutto-Vergütung", min_value=0.0, value=0.0, step=50.0)

            n13, n14, n15, n16 = st.columns(4)
            with n13:
                new_urlaub = st.number_input("Urlaubstage/Jahr", min_value=0.0, value=28.0, step=0.5)
            with n14:
                new_resturlaub = st.number_input("Resturlaub Vorjahr", min_value=0.0, value=0.0, step=0.5)
            with n15:
                new_geburtsdatum = st.date_input("Geburtsdatum", value=date(1990, 1, 1), format="DD.MM.YYYY")
            with n16:
                new_stundenlohn = st.number_input(
                    "Stundenlohn (Personalakte)",
                    min_value=0.0,
                    value=0.0,
                    step=0.5,
                    format="%.2f",
                )

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
                        "monatliche_brutto_verguetung": float(new_monatsbrutto),
                        "jahres_urlaubstage": _to_int(new_urlaub, 28),
                        "resturlaub_vorjahr": float(new_resturlaub),
                        "sonntagszuschlag_aktiv": False,
                        "feiertagszuschlag_aktiv": False,
                    }
                    if stundenlohn_col:
                        payload[stundenlohn_col] = float(new_stundenlohn)
                    try:
                        supabase.table("mitarbeiter").insert(payload).execute()
                        _refresh_after_write()
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
    _render_upload_status(int(ma["id"]))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Personalnummer", ma.get("personalnummer") or "-")
    c2.metric("Soll (Monat)", f"{_to_float(ma.get('monatliche_soll_stunden')):.2f} h")
    c3.metric("Monatsbrutto", f"{_to_float(ma.get('monatliche_brutto_verguetung')):.2f} EUR")
    c4.metric("Urlaub/Jahr", f"{_to_float(ma.get('jahres_urlaubstage')):.1f} Tg")
    c5.metric("Stundenlohn (Akte)", f"{_to_float(ma.get('akten_stundenlohn')):.2f} EUR")
    if not stundenlohn_col:
        st.info(
            "Im aktuellen DB-Schema wurde keine Stundenlohn-Spalte gefunden. "
            "Das Feld wird angezeigt, aber erst nach Hinzufügen einer passenden Spalte dauerhaft gespeichert."
        )

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
            monatliche_brutto_verguetung = st.number_input(
                "Monatliche Brutto-Vergütung",
                min_value=0.0,
                value=_to_float(ma.get("monatliche_brutto_verguetung")),
                step=50.0,
            )
        with l3:
            jahres_urlaubstage = st.number_input(
                "Urlaubstage/Jahr",
                min_value=0.0,
                value=_to_float(ma.get("jahres_urlaubstage")),
                step=1.0,
                format="%.0f",
            )

        z1, z2, z3, z4 = st.columns(4)
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
        with z4:
            akten_stundenlohn = st.number_input(
                "Stundenlohn (Personalakte)",
                min_value=0.0,
                value=_to_float(ma.get("akten_stundenlohn")),
                step=0.5,
                format="%.2f",
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
                "monatliche_brutto_verguetung": float(monatliche_brutto_verguetung),
                "jahres_urlaubstage": _to_int(jahres_urlaubstage, _to_int(ma.get("jahres_urlaubstage"), 28)),
                "resturlaub_vorjahr": float(resturlaub_vorjahr),
                "sonntagszuschlag_aktiv": bool(sonntagszuschlag_aktiv),
                "feiertagszuschlag_aktiv": bool(feiertagszuschlag_aktiv),
            }
            if stundenlohn_col:
                payload[stundenlohn_col] = float(akten_stundenlohn)
            ok, info, dropped_columns = _update_mitarbeiter_stammdaten_robust(
                mitarbeiter_id=int(ma["id"]),
                betrieb_id=st.session_state.get("betrieb_id"),
                payload=payload,
            )
            if ok:
                _refresh_after_write()
                st.success("Stammdaten gespeichert.")
                if dropped_columns:
                    st.warning(
                        "Speichern war nur teilweise möglich. Nicht im DB-Schema vorhandene Felder wurden ausgelassen: "
                        + ", ".join(dropped_columns)
                    )
                st.rerun()
            else:
                st.error("Speichern fehlgeschlagen. Bitte Felder/Schema prüfen.")
                st.caption("Technische Details (kopierbar):")
                st.code(info, language="text")

    with st.expander("Vertrag oder Dokument hochladen", expanded=True):
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
                vertrag_monatsbrutto = st.number_input(
                    "Monatliche Brutto-Vergütung (Vertrag)",
                    min_value=0.0,
                    value=float(ma.get("monatliche_brutto_verguetung") or 0.0),
                    step=50.0,
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
                _clear_upload_status(int(ma["id"]))
                if upload is None:
                    _set_upload_status(
                        int(ma["id"]),
                        level="error",
                        message="Bitte zuerst eine Datei auswählen.",
                    )
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
                        details = (
                            f"bucket=dokumente|arbeitsvertraege\n"
                            f"path={file_path}\n"
                            f"status_code={upload_result.get('status_code') or '-'}\n"
                            f"error={upload_result.get('error') or 'unbekannt'}"
                        )
                        _set_upload_status(
                            int(ma["id"]),
                            level="error",
                            message="Upload in Supabase Storage fehlgeschlagen.",
                            details=details,
                        )
                        st.error(
                            "Upload in Supabase Storage fehlgeschlagen. "
                            f"Details: {upload_result.get('status_code') or '-'} "
                            f"{upload_result.get('error') or ''}"
                        )
                    else:
                        used_bucket = upload_result.get("bucket") or "dokumente"
                        file_url = _storage_public_url(used_bucket, file_path)
                        metadata_saved = True
                        warning_details: list[str] = []
                        meta_payload = {
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
                        meta_ok, meta_msg = _insert_mitarbeiter_dokument_robust(
                            supabase, meta_payload
                        )
                        if not meta_ok:
                            metadata_saved = False
                            details = (
                                f"bucket={used_bucket}\n"
                                f"path={file_path}\n"
                                f"file_name={safe_name}\n"
                                f"metadata_error={meta_msg}"
                            )
                            _set_upload_status(
                                int(ma["id"]),
                                level="error",
                                message=(
                                    "Datei wurde in Storage geladen, aber Dokument-Metadaten "
                                    "konnten nicht gespeichert werden."
                                ),
                                details=details,
                            )
                            st.error(
                                "Datei wurde hochgeladen, aber die Zuordnung zur Personalakte "
                                "ist fehlgeschlagen. Details stehen oben dauerhaft."
                            )
                        elif "variant=full" not in meta_msg or "client=primary" not in meta_msg:
                            warning_details.append(f"metadata_fallback={meta_msg}")

                        if metadata_saved and dokument_typ == "arbeitsvertrag":
                            try:
                                payload_vertrag = {
                                    "betrieb_id": ma.get("betrieb_id") or st.session_state.get("betrieb_id"),
                                    "mitarbeiter_id": ma["id"],
                                    "gueltig_ab": gueltig_ab.isoformat(),
                                    "gueltig_bis": gueltig_bis.isoformat() if befristet else None,
                                    "wochenstunden": float(vertrag_wochenstunden or 0.0),
                                    "soll_stunden_monat": float(vertrag_soll_monat or 0.0),
                                    "urlaubstage_jahr": float(vertrag_urlaub or 0.0),
                                    "monatsbrutto_verguetung": float(vertrag_monatsbrutto or 0.0),
                                    "vertrag_dokument_pfad": file_path,
                                }
                                supabase.table("vertraege").insert(payload_vertrag).execute()
                            except Exception as e:
                                warning_details.append(f"vertraege_insert_error={str(e)}")
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

                        if metadata_saved:
                            if warning_details:
                                _set_upload_status(
                                    int(ma["id"]),
                                    level="warning",
                                    message=(
                                        "Dokument hochgeladen, aber Vertrags-Metadaten konnten "
                                        "nicht vollständig gespeichert werden."
                                    ),
                                    details=(
                                        f"bucket={used_bucket}\npath={file_path}\n"
                                        + "\n".join(warning_details)
                                    ),
                                )
                            else:
                                _set_upload_status(
                                    int(ma["id"]),
                                    level="success",
                                    message="Dokument erfolgreich hochgeladen.",
                                    details=f"bucket={used_bucket}\npath={file_path}\nfile_name={safe_name}",
                                )
                            _refresh_after_write()
                            st.success("Dokument erfolgreich hochgeladen.")
                            st.rerun()

    st.markdown("#### Hinterlegte Verträge")
    try:
        vertr_res = (
            supabase.table("vertraege")
            .select(
                "id, gueltig_ab, gueltig_bis, soll_stunden_monat, "
                "wochenstunden, urlaubstage_jahr, monatsbrutto_verguetung"
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
                    "Monatsbrutto": float(v.get("monatsbrutto_verguetung") or 0.0),
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

                    vg_monatsbrutto = st.number_input(
                        "Monatliche Brutto-Vergütung",
                        min_value=0.0,
                        value=float(v.get("monatsbrutto_verguetung") or 0.0),
                        step=50.0,
                        key=f"vg_monatsbrutto_{vid}",
                    )

                    s_col, d_col = st.columns(2)
                    with s_col:
                        save_vertrag = st.form_submit_button("Vertrag speichern", type="primary", use_container_width=True)
                    with d_col:
                        delete_vertrag = st.form_submit_button("Vertrag löschen", use_container_width=True)

                    if save_vertrag:
                        try:
                            update_payload = {
                                "gueltig_ab": vg_ab.isoformat(),
                                "gueltig_bis": vg_bis.isoformat() if vg_befristet else None,
                                "wochenstunden": float(vg_wochen),
                                "soll_stunden_monat": float(vg_soll),
                                "urlaubstage_jahr": float(vg_urlaub),
                                "monatsbrutto_verguetung": float(vg_monatsbrutto),
                            }
                            supabase.table("vertraege").update(update_payload).eq("id", vid).eq("mitarbeiter_id", ma["id"]).execute()
                            _refresh_after_write()
                            st.success("Vertrag aktualisiert.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Vertrag konnte nicht gespeichert werden: {e}")

                    if delete_vertrag:
                        try:
                            supabase.table("vertraege").delete().eq("id", vid).eq("mitarbeiter_id", ma["id"]).execute()
                            _refresh_after_write()
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


def _show_vertrag_generator_tab():
    from modules.vertraege.ui import show_vertraege
    show_vertraege()


def _show_system_tab():
    st.subheader("Systemstatus")
    supabase = get_supabase_client()
    betrieb_id = st.session_state.get("betrieb_id")

    col1, col2, col3 = st.columns(3)
    users_count, ma_count, zeit_count = _cached_system_counts(
        int(betrieb_id) if betrieb_id is not None else None
    )

    with col1:
        st.metric("Benutzer", users_count)
    with col2:
        st.metric("Mitarbeiter", ma_count)
    with col3:
        st.metric("Zeiteinträge", zeit_count)

    st.caption(f"Berichtsdatum: {date.today().strftime('%d.%m.%Y')}")

    st.markdown("---")
    st.markdown("### Geschlossener Kreislauf – AZK Konsistenzcheck")
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

    if st.button("Kreislauf prüfen", use_container_width=True, key="sys_cycle_check"):
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
                    betrieb_id=require_betrieb_id(),
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
    st.subheader("Arbeitszeitkonten")
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
                    betrieb_id=require_betrieb_id(),
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
                    betrieb_id=require_betrieb_id(),
                    mitarbeiter_id=ma["id"],
                    monat=int(monat),
                    jahr=int(jahr),
                    created_by=st.session_state.get("user_id"),
                )
            except Exception:
                pass
        st.success(f"Monat {int(monat):02d}/{int(jahr)} wurde abgeschlossen.")

    st.markdown("---")
    with st.expander("Einmalige Initialisierung 2026 (Altdaten-Vorträge)", expanded=False):
        st.caption(
            "Erfasst den Startbestand für 2026 (Produktivstart April/Mai): "
            "Überstunden-Saldo, bereits genommene Urlaubstage und Krankheitstage."
        )
        init_ma_options = {
            f"{m.get('vorname', '')} {m.get('nachname', '')} ({m.get('personalnummer', '-')})": m
            for m in alle_ma
        }
        init_label = st.selectbox(
            "Mitarbeiter für Initialisierung",
            list(init_ma_options.keys()),
            key="azk_init_ma",
        )
        init_ma = init_ma_options[init_label]
        c_init_1, c_init_2 = st.columns(2)
        with c_init_1:
            init_monat = st.selectbox(
                "Startmonat 2026",
                options=[4, 5],
                format_func=lambda m: f"{m:02d}/2026",
                key="azk_init_monat_2026",
            )
        with c_init_2:
            init_jahr = st.number_input(
                "Startjahr",
                min_value=2026,
                max_value=2026,
                value=2026,
                step=1,
                key="azk_init_jahr_2026",
            )

        k_i1, k_i2, k_i3 = st.columns(3)
        with k_i1:
            init_saldo = st.number_input(
                "Übertrag Überstunden (+/-)",
                value=0.0,
                step=0.5,
                format="%.2f",
                key="azk_init_saldo",
            )
        with k_i2:
            init_urlaub_genommen = st.number_input(
                "Urlaubstage bereits genommen (Jan-Startmonat)",
                min_value=0.0,
                value=0.0,
                step=0.5,
                format="%.2f",
                key="azk_init_urlaub_genommen",
            )
        with k_i3:
            init_krank_tage = st.number_input(
                "Krankheitstage bisher",
                min_value=0.0,
                value=0.0,
                step=0.5,
                format="%.2f",
                key="azk_init_krank_tage",
            )

        init_reason = st.text_area(
            "Begründung / Nachweis *",
            placeholder="Pflichtfeld: z.B. Übernahme Planungsstand bis 31.03.2026 aus Vorzeitsystem",
            key="azk_init_reason",
        )

        existing_init = _cached_existing_init_marker(int(init_ma["id"]))

        start_month_editable = int(init_jahr) == 2026 and int(init_monat) in (4, 5)
        if not start_month_editable:
            st.warning("Initialisierung ist nur für den Startmonat 04/2026 oder 05/2026 erlaubt.")
        if existing_init:
            st.info(
                f"Für diesen Mitarbeiter existiert bereits eine Initialisierung "
                f"({int(existing_init.get('monat') or 0):02d}/{int(existing_init.get('jahr') or 0)}). "
                "Die Einmal-Initialisierung ist damit gesperrt."
            )

        do_init = st.button(
            "Einmal-Initialisierung speichern",
            type="primary",
            use_container_width=True,
            disabled=(not start_month_editable) or bool(existing_init),
            key="azk_init_save_btn",
        )
        if do_init:
            if not (init_reason or "").strip():
                st.error("Bitte eine Begründung eintragen (Pflicht für Audit/GoBD).")
            else:
                try:
                    set_work_account_opening_balance(
                        supabase,
                        betrieb_id=require_betrieb_id(),
                        mitarbeiter_id=int(init_ma["id"]),
                        monat=int(init_monat),
                        jahr=int(init_jahr),
                        opening_hours=float(init_saldo),
                        opening_vacation_taken=float(init_urlaub_genommen),
                        opening_sick_days=float(init_krank_tage),
                        correction_reason=init_reason.strip(),
                        created_by=st.session_state.get("user_id"),
                        is_initialization=True,
                    )
                    _refresh_after_write()
                    st.success("Einmal-Initialisierung gespeichert.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Initialisierung fehlgeschlagen: {exc}")

    rows = _cached_arbeitszeitkonten_rows(st.session_state.get("betrieb_id"))
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
    closed_meta = {}
    try:
        closed_rows = _cached_azk_closed_rows(
            st.session_state.get("betrieb_id"),
            int(monat),
            int(jahr),
        )
        closed_ids = {int(r.get("mitarbeiter_id")) for r in closed_rows if r.get("mitarbeiter_id") is not None}
        for r in closed_rows:
            ma_id = r.get("mitarbeiter_id")
            if ma_id is not None:
                closed_meta[int(ma_id)] = r
    except Exception:
        closed_ids = set()
        closed_meta = {}

    ma_lookup = {m["id"]: f"{m['vorname']} {m['nachname']}" for m in alle_ma}
    view_rows = []
    for row in rows:
        ma_id = row.get("mitarbeiter_id")
        ist_h = float(row.get("ist_stunden") or 0.0)
        soll_h = float(row.get("soll_stunden") or 0.0)
        saldo_h = float(row.get("ueberstunden_saldo") or 0.0)
        differenz_h = round(ist_h - soll_h, 2)
        saldenvortrag = round(saldo_h - differenz_h, 2)
        meta_row = closed_meta.get(int(ma_id)) if ma_id is not None else None
        manuelle_korr = saldenvortrag
        if meta_row is not None and meta_row.get("manuelle_korrektur_saldo") is not None:
            try:
                manuelle_korr = float(meta_row.get("manuelle_korrektur_saldo") or 0.0)
            except Exception:
                manuelle_korr = saldenvortrag
        view_rows.append(
            {
                "Mitarbeiter": ma_lookup.get(ma_id, str(ma_id)),
                "Monat fixiert": "Ja" if ma_id in closed_ids else "Nein",
                "Soll (h)": soll_h,
                "Ist (h)": ist_h,
                "Manuelle Korrekturen / Saldenvortrag (h)": round(manuelle_korr, 2),
                "Saldo (h)": saldo_h,
                "Urlaub gesamt": float(row.get("urlaubstage_gesamt") or 0),
                "Urlaub genommen": float(row.get("urlaubstage_genommen") or 0),
                "Krankheitstage": float(row.get("krankheitstage_gesamt") or 0),
            }
        )
    st.dataframe(view_rows, use_container_width=True, hide_index=True)


def _show_premium_tab():
    """Premium-Module – nur bei Buchung aktiv."""
    from modules.hazard.hazard_ui import show_hazard_modul
    from modules.hazard.rechtsstand_admin import show_rechtsstand_admin
    from utils.feature_flags import get_user_plan

    supabase = st.session_state.get("supabase")
    betrieb_id = st.session_state.get("betrieb_id", "")
    user_id = st.session_state.get("user_id", "")

    user_plan = get_user_plan(supabase, betrieb_id)

    st.markdown("## 🛡️ Premium-Module")
    st.caption(f"Dein aktueller Plan: **{user_plan.capitalize()}**")
    st.markdown("---")

    modul_tab1, modul_tab2, modul_tab3, modul_tab4, modul_tab5 = st.tabs([
        "🔍 Gefährdungsbeurteilung",
        "📄 Vorlagen & Nachweise",
        "⏰ ArbZG-Wächter",
        "📤 DATEV-Export",
        "⚖️ Rechtsstand"
    ])

    with modul_tab1:
        show_hazard_modul(supabase, betrieb_id, user_id, user_plan)

    with modul_tab2:
        from modules.documents.ui import show_document_center
        show_document_center()

    with modul_tab3:
        st.markdown("### ⏰ ArbZG-Wächter")
        st.caption("Automatische Erkennung von Arbeitszeitverstößen")
        st.info("Dieses Modul wird in Kürze verfügbar.")

    with modul_tab4:
        st.markdown("### 📤 DATEV-Export")
        st.caption("Lohnabrechnung für deinen Steuerberater")
        st.info("DATEV-Export wird in Kürze verfügbar.")

    with modul_tab5:
        show_rechtsstand_admin(supabase)


def _show_datenschutz_tab():
    """DSGVO-Compliance: AVV-Register + Löschprotokoll."""
    from modules.datenschutz.avv_ui import show_avv_register
    from modules.datenschutz.loeschung_ui import show_loeschprotokoll

    tab1, tab2 = st.tabs(["AVV-Register", "Löschroutine"])
    with tab1:
        show_avv_register()
    with tab2:
        show_loeschprotokoll()


def _show_sicherheit_tab():
    """Sicherheits-Tools des Admins (Passwort-Reset, etc.)."""
    from modules.admin.password_reset import show_password_reset

    show_password_reset()


def _show_leads_tab():
    """Outreach-Leads und Akquise-Dashboard."""
    from modules.leads.leads_ui import show_leads_dashboard
    show_leads_dashboard()


def show_admin_dashboard():
    apply_custom_css()
    if st.session_state.get("admin_nav") is None:
        st.session_state["admin_nav"] = "Dienstplanung"

    st.markdown("<div class='complio-topbar'>", unsafe_allow_html=True)
    top_logo, top_nav = st.columns([1.2, 5], vertical_alignment="center")
    with top_logo:
        with st.container(key="header_logo"):
            st.image(BRAND_LOGO_IMAGE, width=230)
    with top_nav:
        current_nav = _normalize_admin_nav(st.session_state.get("admin_nav", "Dienstplanung"))
        nav_cols = st.columns(len(ADMIN_NAV_OPTIONS))
        selected = current_nav
        for col, opt in zip(nav_cols, ADMIN_NAV_OPTIONS):
            with col:
                is_active = selected == opt
                if st.button(
                    opt,
                    key=f"nav_{opt}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    selected = opt
        st.session_state["admin_nav"] = _normalize_admin_nav(selected)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='complio-card'>", unsafe_allow_html=True)
    selected = _normalize_admin_nav(st.session_state.get("admin_nav"))
    if selected == "Dienstplanung":
        from pages import admin_dienstplan

        admin_dienstplan.show_dienstplanung()
    else:
        section_handlers = {
            "Personalakte": _show_mitarbeiter_stammdaten_tab,
            "Abwesenheiten": _show_absenzen_tab,
            "Arbeitszeitkonten": _show_arbeitszeitkonten_tab,
            "Zeitauswertung": _show_zeitauswertung_tab,
            "Verträge": _show_vertrag_generator_tab,
            "Premium": _show_premium_tab,
            "Datenschutz": _show_datenschutz_tab,
            "Sicherheit": _show_sicherheit_tab,
            "Leads": _show_leads_tab,
        }
        handler = section_handlers.get(selected)
        if handler is None:
            st.warning("Unbekannter Bereich. Es wird Dienstplanung geladen.")
            st.session_state["admin_nav"] = "Dienstplanung"
            from pages import admin_dienstplan
            admin_dienstplan.show_dienstplanung()
        else:
            handler()
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    show_admin_dashboard()
