"""
Zeitauswertung / Lohn – Modul für Mitarbeiter und Admin
=========================================================
Archiv-Ansicht, Monatsauswertung, Soll-Ist-Vergleich,
Zuschlagsaufschlüsselung (Sachsen), Korrektur-Markierungen,
Audit-Log, Feiertag-Warnungen, PDF-Export
"""

import streamlit as st
from datetime import datetime, date, time, timedelta
from calendar import monthrange
import io
import os

from utils.database import get_supabase_client
from utils.planning_tables import resolve_planning_table
from utils.audit_log import log_aktion, log_zeitkorrektur, log_zeitloeschung
from utils.branding import BRAND_COMPANY_NAME, BRAND_LOGO_IMAGE
from utils.lohnberechnung import (
    berechne_monat_cached,
    berechne_eintrag,
    pruefe_feiertag_warnungen,
    get_feiertage_sachsen,
    ist_feiertag_sachsen,
    ist_sonntag,
    format_stunden,
    format_euro,
    get_feiertage_monat,
)
from utils.calculations import (
    berechne_arbeitsstunden,
    parse_zeit,
    get_wochentag,
    get_monatsnamen,
)
from utils.work_accounts import sync_work_account_for_month

MONATE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


def _effective_hourly_rate(ma: dict) -> float:
    """Leitet den Stundenwert aus Monatsbrutto und Sollstunden ab."""
    try:
        monat_brutto = float(ma.get("monatliche_brutto_verguetung") or 0.0)
        monat_soll = float(ma.get("monatliche_soll_stunden") or 0.0)
    except Exception:
        return 0.0
    if monat_brutto > 0 and monat_soll > 0:
        return round(monat_brutto / monat_soll, 4)
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# DATEN LADEN
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _cached_zeiterfassungen(mitarbeiter_id: int, monat: int, jahr: int) -> list:
    """Lädt alle Zeiterfassungen für einen Mitarbeiter in einem Monat."""
    supabase = get_supabase_client()
    erster = date(jahr, monat, 1).isoformat()
    letzter = date(jahr, monat, monthrange(jahr, monat)[1]).isoformat()
    select_variants = [
        # Vollsatz für korrekte Urlaub/Krank-Bewertung inkl. Stunden-Gutschrift.
        (
            'id,datum,start_zeit,ende_zeit,pause_minuten,arbeitsstunden,stunden,'
            'quelle,ist_krank,abwesenheitstyp,created_at,updated_at,manuell_kommentar,korrektur_grund'
        ),
        # Legacy ohne abwesenheitstyp / Korrekturfelder.
        'id,datum,start_zeit,ende_zeit,pause_minuten,arbeitsstunden,stunden,quelle,ist_krank,created_at,updated_at',
        # Minimal-Fallback.
        'id,datum,start_zeit,ende_zeit,pause_minuten,quelle,ist_krank,created_at,updated_at',
    ]
    for cols in select_variants:
        try:
            r = (
                supabase.table('zeiterfassung')
                .select(cols)
                .eq('mitarbeiter_id', mitarbeiter_id)
                .gte('datum', erster)
                .lte('datum', letzter)
                .order('datum')
                .execute()
            )
            return r.data or []
        except Exception:
            continue
    return []


def _lade_zeiterfassungen(mitarbeiter_id: int, monat: int, jahr: int) -> list:
    return _cached_zeiterfassungen(mitarbeiter_id, monat, jahr)


@st.cache_data(ttl=600, show_spinner=False)
def _cached_dienstplan_startzeiten(mitarbeiter_id: int, monat: int, jahr: int) -> dict:
    """Lädt pro Datum die früheste geplante Startzeit (für Kappungslogik)."""
    supabase = get_supabase_client()
    erster = date(jahr, monat, 1).isoformat()
    letzter = date(jahr, monat, monthrange(jahr, monat)[1]).isoformat()
    start_map: dict[str, str] = {}
    # Rückwärtskompatibel beide möglichen Tabellen lesen.
    # So greift die Kappung auch dann korrekt, wenn die Instanz noch Legacy-Daten nutzt.
    for planning_table in ("dienstplaene", "dienstplan"):
        try:
            r = (
                supabase.table(planning_table)
                .select("datum,schichttyp,start_zeit")
                .eq("mitarbeiter_id", mitarbeiter_id)
                .gte("datum", erster)
                .lte("datum", letzter)
                .order("datum")
                .order("start_zeit")
                .execute()
            )
        except Exception:
            continue
        for row in (r.data or []):
            if str(row.get("schichttyp") or "arbeit") != "arbeit":
                continue
            d = str(row.get("datum") or "")
            s = str(row.get("start_zeit") or "")
            if not d or not s:
                continue
            if d not in start_map or s < start_map[d]:
                start_map[d] = s
    return start_map


@st.cache_data(ttl=600, show_spinner=False)
def _cached_dienstplan_startzeiten_with_fallback(mitarbeiter_id: int, monat: int, jahr: int) -> dict:
    """
    Lädt Kappungs-Startzeiten robust aus beiden Tabellenvarianten:
    - bevorzugt neue Tabelle via resolve_planning_table
    - fallback auf jeweils andere Variante, falls leer
    """
    supabase = get_supabase_client()
    primary = resolve_planning_table(supabase)
    fallback = "dienstplan" if primary == "dienstplaene" else "dienstplaene"
    start_map = _cached_dienstplan_startzeiten(mitarbeiter_id, monat, jahr)
    # Ergänzend immer auch die alternative Struktur lesen, damit tageweise Lücken
    # (z. B. gemischte Legacy-Daten in dienstplan/dienstplaene) geschlossen werden.
    try:
        erster = date(jahr, monat, 1).isoformat()
        letzter = date(jahr, monat, monthrange(jahr, monat)[1]).isoformat()
        r = (
            supabase.table(fallback)
            .select("datum,schichttyp,start_zeit")
            .eq("mitarbeiter_id", mitarbeiter_id)
            .gte("datum", erster)
            .lte("datum", letzter)
            .order("datum")
            .order("start_zeit")
            .execute()
        )
        fb_map: dict[str, str] = {}
        for row in (r.data or []):
            if str(row.get("schichttyp") or "arbeit") != "arbeit":
                continue
            d = str(row.get("datum") or "")
            s = str(row.get("start_zeit") or "")
            if not d or not s:
                continue
            if d not in fb_map or s < fb_map[d]:
                fb_map[d] = s
        # Merge: pro Tag immer die früheste Startzeit.
        merged = dict(start_map or {})
        for d, s in fb_map.items():
            if d not in merged or s < merged[d]:
                merged[d] = s
        return merged
    except Exception:
        return start_map


@st.cache_data(ttl=600, show_spinner=False)
def _cached_admin_mitarbeiter_za(betrieb_id: int) -> list:
    supabase = get_supabase_client()
    query = (
        supabase.table("mitarbeiter")
        .select(
            "id,vorname,nachname,monatliche_soll_stunden,monatliche_brutto_verguetung,"
            "sonntagszuschlag_aktiv,feiertagszuschlag_aktiv,personalnummer,beschaeftigungsart"
        )
        .eq("betrieb_id", betrieb_id)
        .order("nachname")
    )
    try:
        return query.execute().data or []
    except Exception:
        # Nur verpflichtende Kernfelder laden (kein Legacy-Lohnfeld-Fallback).
        fallback = (
            supabase.table("mitarbeiter")
            .select(
                "id,vorname,nachname,monatliche_soll_stunden,"
                "sonntagszuschlag_aktiv,feiertagszuschlag_aktiv,personalnummer,beschaeftigungsart"
            )
            .eq("betrieb_id", betrieb_id)
            .order("nachname")
            .execute()
        )
        rows = fallback.data or []
        for row in rows:
            row["monatliche_brutto_verguetung"] = float(row.get("monatliche_brutto_verguetung") or 0.0)
        return rows


def _clear_zeitauswertung_caches() -> None:
    _cached_zeiterfassungen.clear()
    _cached_dienstplan_startzeiten.clear()
    _cached_dienstplan_startzeiten_with_fallback.clear()
    _cached_admin_mitarbeiter_za.clear()
    berechne_monat_cached.clear()


def _build_data_hash(zeiterfassungen: list, dienstplan_start_map: dict) -> str:
    """Erzeugt einen stabilen Hash als Cache-Key für die Monatsberechnung."""
    relevant = []
    for z in zeiterfassungen:
        relevant.append(
            {
                "id": z.get("id"),
                "datum": z.get("datum"),
                "start_zeit": z.get("start_zeit"),
                "ende_zeit": z.get("ende_zeit"),
                "pause_minuten": z.get("pause_minuten"),
                "quelle": z.get("quelle"),
                "ist_krank": z.get("ist_krank"),
                "abwesenheitstyp": z.get("abwesenheitstyp"),
                "updated_at": z.get("updated_at"),
            }
        )
    payload = {"zeiterfassung": relevant, "dienstplan_start_map": dienstplan_start_map or {}}
    import json
    import hashlib

    canonical = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _is_auto_timeout_entry(raw: dict) -> bool:
    """Erkennt automatisch gekappte Schichten (vergessenes Logout)."""
    quelle = str(raw.get("quelle") or "").strip().lower()
    kommentar = str(raw.get("manuell_kommentar") or "").strip().lower()
    grund = str(raw.get("korrektur_grund") or "").strip().lower()
    return (
        quelle == "system_auto_close"
        or "auto_timeout_10h" in kommentar
        or "auto-close" in kommentar
        or "forgotten_logout_timeout_10h" in grund
    )


def _is_sick_row(raw: dict) -> bool:
    quelle = str(raw.get("quelle") or "").strip().lower()
    abw_typ = str(raw.get("abwesenheitstyp") or "").strip().lower()
    kommentar = str(raw.get("manuell_kommentar") or "").strip().lower()
    return bool(raw.get("ist_krank")) or quelle == "au_bescheinigung" or abw_typ in {
        "krank",
        "krankheit",
    } or kommentar.startswith("manuelle_korrektur_krank:")


def _collect_sick_day_conflicts(rows: list[dict]) -> tuple[set[int], dict[str, int]]:
    """
    Liefert IDs von Zeilen, die wegen Kranktag-Priorität in der Berechnung ignoriert werden.
    """
    by_day: dict[str, list[dict]] = {}
    for raw in rows or []:
        day = str(raw.get("datum") or "").strip()[:10]
        if not day:
            continue
        by_day.setdefault(day, []).append(raw)

    ignored_ids: set[int] = set()
    conflict_counts: dict[str, int] = {}
    for day, day_rows in by_day.items():
        krank_rows = [r for r in day_rows if _is_sick_row(r)]
        if not krank_rows:
            continue
        chosen = krank_rows[0]
        ignored = [r for r in day_rows if r is not chosen]
        if not ignored:
            continue
        for r in ignored:
            try:
                rid = int(r.get("id"))
            except Exception:
                continue
            ignored_ids.add(rid)
        conflict_counts[day] = len(ignored)
    return ignored_ids, conflict_counts


def _show_manual_outdoor_entry_form(
    *,
    ma_liste: list[dict],
    default_ma_id: int,
    jahr: int,
    monat: int,
) -> None:
    """
    Admin-Form für nachträgliche, vollständige Zeiterfassung (Außendienst).
    GoBD: Pflichtbegründung + Zeitstempel + Audit-Log.
    """
    if not ma_liste:
        st.info("Keine Mitarbeiter-Stammdaten verfügbar.")
        return

    ma_options = {
        f"{m.get('vorname', '').strip()} {m.get('nachname', '').strip()}".strip(): m
        for m in ma_liste
    }
    ma_labels = list(ma_options.keys())
    default_index = 0
    for idx, label in enumerate(ma_labels):
        if int(ma_options[label].get("id") or 0) == int(default_ma_id or 0):
            default_index = idx
            break

    with st.expander("Außendienst-Modul: Manuelle Zeiterfassung anlegen", expanded=False):
        st.caption(
            "Vollständige manuelle Anlage eines Zeiteintrags mit Pflichtbegründung "
            "(GoBD/Audit). Doppelungen pro Mitarbeiter/Datum werden blockiert."
        )
        selected_label = st.selectbox(
            "Mitarbeiter",
            ma_labels,
            index=default_index,
            key=f"za_manual_create_ma_{jahr}_{monat}",
        )
        selected_ma = ma_options[selected_label]
        selected_ma_id = int(selected_ma.get("id") or 0)
        betrieb_id = int(st.session_state.get("betrieb_id") or selected_ma.get("betrieb_id") or 1)

        today = date.today()
        default_date = today if (today.year == jahr and today.month == monat) else date(jahr, monat, 1)
        manual_date = st.date_input(
            "Datum",
            value=default_date,
            key=f"za_manual_create_date_{jahr}_{monat}",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            start_time = st.time_input(
                "Startzeit",
                value=time(8, 0),
                step=300,
                key=f"za_manual_create_start_{jahr}_{monat}",
            )
        with c2:
            end_time = st.time_input(
                "Endzeit",
                value=time(17, 0),
                step=300,
                key=f"za_manual_create_end_{jahr}_{monat}",
            )
        with c3:
            pause_min = st.number_input(
                "Pause (Minuten)",
                min_value=0,
                max_value=240,
                value=0,
                step=5,
                key=f"za_manual_create_pause_{jahr}_{monat}",
            )

        reason = st.text_area(
            "Begründung der manuellen Anlage *",
            placeholder="Pflichtfeld, z.B. Außendienst ohne Gerätezugang",
            key=f"za_manual_create_reason_{jahr}_{monat}",
        )

        if st.button(
            "Außendienst-Eintrag speichern",
            type="primary",
            use_container_width=True,
            key=f"za_manual_create_save_{jahr}_{monat}",
        ):
            reason_clean = (reason or "").strip()
            if not reason_clean:
                st.error("Bitte eine Begründung der manuellen Anlage angeben.")
                return

            start_dt = datetime.combine(manual_date, start_time)
            end_dt = datetime.combine(manual_date, end_time)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            brutto_min = int((end_dt - start_dt).total_seconds() // 60)
            if brutto_min > (10 * 60):
                st.error(
                    "Die manuelle Anlage überschreitet 10 Stunden. "
                    "Bitte Eintrag aufteilen oder als Korrektur mit Admin-Prüfung erfassen."
                )
                return
            netto_min = max(0, brutto_min - int(pause_min))
            if netto_min <= 0:
                st.error("Start-/Endzeit und Pause ergeben keine gültige Arbeitszeit.")
                return

            supabase = get_supabase_client()
            datum_iso = manual_date.isoformat()
            dup = (
                supabase.table("zeiterfassung")
                .select("id,start_zeit,ende_zeit,quelle")
                .eq("mitarbeiter_id", selected_ma_id)
                .eq("datum", datum_iso)
                .limit(10)
                .execute()
            )
            if dup.data:
                existing = ", ".join(
                    f"#{int(d.get('id'))} {str(d.get('start_zeit') or '--:--')[:5]}-{str(d.get('ende_zeit') or 'offen')[:5]}"
                    for d in dup.data
                )
                st.error(
                    f"Für {selected_label} existiert am {manual_date.strftime('%d.%m.%Y')} "
                    f"bereits ein Eintrag: {existing}. Anlage wurde zur Dublettenvermeidung gestoppt."
                )
                return

            created_ts = datetime.now().isoformat(timespec="seconds")
            payload = {
                "betrieb_id": betrieb_id,
                "mitarbeiter_id": selected_ma_id,
                "datum": datum_iso,
                "start_zeit": start_time.strftime("%H:%M:%S"),
                "ende_zeit": end_time.strftime("%H:%M:%S"),
                "pause_minuten": int(pause_min),
                "arbeitsstunden": round(netto_min / 60.0, 2),
                "quelle": "manuell_admin",
                "korrektur_grund": reason_clean,
                "manuell_kommentar": f"manuelle_anlage_admin@{created_ts}",
            }
            try:
                try:
                    ins = supabase.table("zeiterfassung").insert(payload).execute()
                except Exception:
                    payload_fallback = {
                        "betrieb_id": payload["betrieb_id"],
                        "mitarbeiter_id": payload["mitarbeiter_id"],
                        "datum": payload["datum"],
                        "start_zeit": payload["start_zeit"],
                        "ende_zeit": payload["ende_zeit"],
                        "pause_minuten": payload["pause_minuten"],
                        "arbeitsstunden": payload["arbeitsstunden"],
                        "quelle": payload["quelle"],
                    }
                    ins = supabase.table("zeiterfassung").insert(payload_fallback).execute()

                new_row_id = int((ins.data or [{}])[0].get("id") or 0)
                try:
                    log_aktion(
                        admin_user_id=int(st.session_state.get("user_id") or 0),
                        admin_name=str(st.session_state.get("username") or st.session_state.get("user_name") or "Admin"),
                        aktion="manuelle_zeiterfassung_anlage",
                        tabelle="zeiterfassung",
                        datensatz_id=new_row_id if new_row_id > 0 else selected_ma_id,
                        mitarbeiter_id=selected_ma_id,
                        mitarbeiter_name=selected_label,
                        alter_wert=None,
                        neuer_wert={
                            "datum": datum_iso,
                            "start_zeit": payload["start_zeit"],
                            "ende_zeit": payload["ende_zeit"],
                            "pause_minuten": payload["pause_minuten"],
                            "arbeitsstunden": payload["arbeitsstunden"],
                        },
                        begruendung=reason_clean,
                        betrieb_id=betrieb_id,
                    )
                except Exception:
                    pass

                _clear_zeitauswertung_caches()
                st.success(
                    f"Außendienst-Eintrag für {selected_label} am "
                    f"{manual_date.strftime('%d.%m.%Y')} wurde erfolgreich gespeichert."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Speichern fehlgeschlagen: {exc}")


def _show_manual_account_adjustment(
    *,
    aktiver_ma: dict,
    monat: int,
    jahr: int,
    saldo: float,
) -> None:
    """Inline-Korrektur im Auswertungsflow mit Pflichtbegründung."""
    def _next_unique_marker_start_time(mitarbeiter_id: int, datum_iso: str) -> str:
        """
        Ermittelt eine kollisionsfreie start_zeit für Markerzeilen
        (UNIQUE-Key: mitarbeiter_id + datum + start_zeit).
        """
        try:
            rows = (
                supabase.table("zeiterfassung")
                .select("start_zeit")
                .eq("mitarbeiter_id", int(mitarbeiter_id))
                .eq("datum", str(datum_iso))
                .execute()
                .data
                or []
            )
        except Exception:
            rows = []

        used = set()
        for r in rows:
            raw = str((r or {}).get("start_zeit") or "").strip()
            if not raw:
                continue
            used.add(raw[:8] if len(raw) >= 8 else raw)

        for sec in range(0, 24 * 60 * 60):
            h = sec // 3600
            m = (sec % 3600) // 60
            s = sec % 60
            candidate = f"{h:02d}:{m:02d}:{s:02d}"
            if candidate not in used:
                return candidate
        # Praktisch unerreichbar, aber defensiv:
        return "23:59:59"

    with st.popover("Manuelle Korrektur (Stunden/Urlaub/Krankheit)"):
        st.caption("Jede manuelle Anpassung erfordert eine Begründung (Audit/GoBD).")
        supabase = get_supabase_client()
        ma_id = int(aktiver_ma.get("id") or 0)
        betrieb_id = int(st.session_state.get("betrieb_id") or aktiver_ma.get("betrieb_id") or 1)

        corr_mode = st.selectbox(
            "Korrekturtyp",
            options=["Saldo", "Urlaub genommen", "Krankheitstage"],
            key=f"za_manual_corr_mode_{ma_id}_{jahr}_{monat}",
        )
        corr_value = st.number_input(
            "Wert",
            value=0.0,
            step=0.5,
            format="%.2f",
            key=f"za_manual_corr_value_{ma_id}_{jahr}_{monat}",
        )
        corr_reason = st.text_area(
            "Begründung *",
            placeholder="Pflichtfeld, z.B. Nachtrag Korrektur aus unterschriebener Liste",
            key=f"za_manual_corr_reason_{ma_id}_{jahr}_{monat}",
        )

        st.caption(f"Aktueller Saldo: {saldo:+.2f} h")

        if st.button(
            "Korrektur speichern",
            use_container_width=True,
            key=f"za_manual_corr_save_{ma_id}_{jahr}_{monat}",
            type="primary",
        ):
            reason = (corr_reason or "").strip()
            if not reason:
                st.error("Bitte eine Begründung angeben.")
                return
            try:
                month_start = date(int(jahr), int(monat), 1)
                if corr_mode == "Saldo":
                    target_prev_monat = 12 if int(monat) == 1 else int(monat) - 1
                    target_prev_jahr = int(jahr) - 1 if int(monat) == 1 else int(jahr)
                    existing = (
                        supabase.table("azk_monatsabschluesse")
                        .select("id")
                        .eq("mitarbeiter_id", ma_id)
                        .eq("monat", target_prev_monat)
                        .eq("jahr", target_prev_jahr)
                        .limit(1)
                        .execute()
                    )
                    payload = {
                        "betrieb_id": betrieb_id,
                        "mitarbeiter_id": ma_id,
                        "monat": target_prev_monat,
                        "jahr": target_prev_jahr,
                        "soll_stunden": 0.0,
                        "ist_stunden": 0.0,
                        "differenz_stunden": 0.0,
                        "ueberstunden_saldo_start": round(float(corr_value), 2),
                        "ueberstunden_saldo_ende": round(float(corr_value), 2),
                        "manuelle_korrektur_saldo": round(float(corr_value), 2),
                        "korrektur_grund": reason,
                        "urlaubstage_gesamt": 0.0,
                        "urlaubstage_genommen": 0.0,
                        "krankheitstage_gesamt": 0.0,
                        "created_by": st.session_state.get("user_id"),
                    }
                    payload_legacy = {
                        "betrieb_id": betrieb_id,
                        "mitarbeiter_id": ma_id,
                        "monat": target_prev_monat,
                        "jahr": target_prev_jahr,
                        "soll_stunden": 0.0,
                        "ist_stunden": 0.0,
                        "differenz_stunden": 0.0,
                        "ueberstunden_saldo_start": round(float(corr_value), 2),
                        "ueberstunden_saldo_ende": round(float(corr_value), 2),
                        "urlaubstage_gesamt": 0.0,
                        "urlaubstage_genommen": 0.0,
                        "krankheitstage_gesamt": 0.0,
                        "created_by": st.session_state.get("user_id"),
                    }
                    if existing.data:
                        try:
                            supabase.table("azk_monatsabschluesse").update(payload).eq(
                                "id", int(existing.data[0]["id"])
                            ).execute()
                        except Exception:
                            supabase.table("azk_monatsabschluesse").update(payload_legacy).eq(
                                "id", int(existing.data[0]["id"])
                            ).execute()
                    else:
                        try:
                            supabase.table("azk_monatsabschluesse").insert(payload).execute()
                        except Exception:
                            supabase.table("azk_monatsabschluesse").insert(payload_legacy).execute()
                else:
                    src = "manuelle_korrektur_urlaub" if corr_mode == "Urlaub genommen" else "manuelle_korrektur_krank"
                    marker_start = _next_unique_marker_start_time(ma_id, month_start.isoformat())
                    z_payload = {
                        "betrieb_id": betrieb_id,
                        "mitarbeiter_id": ma_id,
                        "datum": month_start.isoformat(),
                        "start_zeit": marker_start,
                        "ende_zeit": marker_start,
                        "pause_minuten": 0,
                        "arbeitsstunden": 0.0,
                        "quelle": "manuell_admin",
                        "korrektur_grund": reason,
                        "manuell_kommentar": f"{src}:{float(corr_value):.2f}",
                    }
                    if corr_mode == "Krankheitstage":
                        z_payload["ist_krank"] = True
                    try:
                        supabase.table("zeiterfassung").insert(z_payload).execute()
                    except Exception:
                        # Bei Rennen auf UNIQUE-Key (gleicher Tag/Startzeit) einmal mit neuer Startzeit wiederholen.
                        marker_start_retry = _next_unique_marker_start_time(ma_id, month_start.isoformat())
                        fallback_payload = {
                            "betrieb_id": betrieb_id,
                            "mitarbeiter_id": ma_id,
                            "datum": month_start.isoformat(),
                            "start_zeit": marker_start_retry,
                            "ende_zeit": marker_start_retry,
                            "pause_minuten": 0,
                            "arbeitsstunden": 0.0,
                            "quelle": "manuell_admin",
                        }
                        if corr_mode == "Krankheitstage":
                            fallback_payload["ist_krank"] = True
                        supabase.table("zeiterfassung").insert(fallback_payload).execute()

                    # Spiegelung in Monatsabschluss, sofern vorhanden.
                    closed = (
                        supabase.table("azk_monatsabschluesse")
                        .select("id, urlaubstage_genommen, krankheitstage_gesamt")
                        .eq("mitarbeiter_id", ma_id)
                        .eq("monat", int(monat))
                        .eq("jahr", int(jahr))
                        .limit(1)
                        .execute()
                    )
                    if closed.data:
                        c0 = closed.data[0]
                        if corr_mode == "Urlaub genommen":
                            new_ur = round(float(c0.get("urlaubstage_genommen") or 0.0) + float(corr_value), 2)
                            try:
                                supabase.table("azk_monatsabschluesse").update(
                                    {"urlaubstage_genommen": new_ur, "korrektur_grund": reason}
                                ).eq("id", int(c0["id"])).execute()
                            except Exception:
                                supabase.table("azk_monatsabschluesse").update(
                                    {"urlaubstage_genommen": new_ur}
                                ).eq("id", int(c0["id"])).execute()
                        else:
                            new_kr = round(float(c0.get("krankheitstage_gesamt") or 0.0) + float(corr_value), 2)
                            try:
                                supabase.table("azk_monatsabschluesse").update(
                                    {"krankheitstage_gesamt": new_kr, "korrektur_grund": reason}
                                ).eq("id", int(c0["id"])).execute()
                            except Exception:
                                supabase.table("azk_monatsabschluesse").update(
                                    {"krankheitstage_gesamt": new_kr}
                                ).eq("id", int(c0["id"])).execute()

                try:
                    log_aktion(
                        admin_user_id=int(st.session_state.get("user_id") or 0),
                        admin_name=str(st.session_state.get("username") or st.session_state.get("user_name") or "Admin"),
                        aktion="manuelle_azk_korrektur",
                        tabelle="arbeitszeit_konten",
                        datensatz_id=ma_id,
                        mitarbeiter_id=ma_id,
                        mitarbeiter_name=f"{aktiver_ma.get('vorname', '')} {aktiver_ma.get('nachname', '')}".strip(),
                        alter_wert={"saldo_alt": float(saldo)},
                        neuer_wert={"modus": corr_mode, "wert": float(corr_value)},
                        begruendung=reason,
                        betrieb_id=betrieb_id,
                    )
                except Exception:
                    pass

                _clear_zeitauswertung_caches()
                st.success("Korrektur gespeichert.")
                st.rerun()
            except Exception as exc:
                st.error(f"Korrektur konnte nicht gespeichert werden: {exc}")


def _korrigiere_zeiterfassung_popup(
    *,
    entry: dict,
    aktiver_ma: dict,
    monat: int,
    jahr: int,
) -> None:
    @st.dialog("Zeiteintrag bearbeiten oder loeschen")
    def _dialog():
        supabase = get_supabase_client()
        entry_id = int(entry.get("id"))
        datum = str(entry.get("datum") or "")
        st.markdown(
            f"**{aktiver_ma.get('vorname','')} {aktiver_ma.get('nachname','')}** · "
            f"Eintrag #{entry_id} · {datum}"
        )

        current_start = str(entry.get("start_zeit") or "")[:5] or "08:00"
        current_end = str(entry.get("ende_zeit") or "")[:5] if entry.get("ende_zeit") else ""
        current_pause = int(entry.get("pause_minuten") or 0)

        with st.form(key=f"zeit_edit_form_{entry_id}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_start = st.text_input("Start (HH:MM)", value=current_start, key=f"zeit_edit_start_{entry_id}")
            with c2:
                new_end = st.text_input("Ende (HH:MM)", value=current_end, key=f"zeit_edit_end_{entry_id}")
            with c3:
                new_pause = st.number_input(
                    "Pause (Min)",
                    min_value=0,
                    max_value=240,
                    value=current_pause,
                    step=5,
                    key=f"zeit_edit_pause_{entry_id}",
                )
            reason = st.text_area(
                "Begründung der Änderung *",
                placeholder="Pflicht für Audit / GoBD-Nachvollziehbarkeit",
                key=f"zeit_edit_reason_{entry_id}",
            )
            s1, s2 = st.columns(2)
            with s1:
                do_save = st.form_submit_button("Speichern", use_container_width=True, type="primary")
            with s2:
                do_delete = st.form_submit_button("Löschen", use_container_width=True)

            if do_save:
                if not reason.strip():
                    st.error("Bitte eine Begründung eingeben.")
                elif len(new_start.strip()) < 4:
                    st.error("Bitte eine gültige Startzeit eingeben.")
                else:
                    try:
                        payload = {
                            "start_zeit": (new_start.strip()[:5] + ":00"),
                            "ende_zeit": (new_end.strip()[:5] + ":00") if new_end.strip() else None,
                            "pause_minuten": int(new_pause),
                            "quelle": "manuell_admin",
                            "korrektur_grund": reason.strip(),
                        }
                        try:
                            supabase.table("zeiterfassung").update(payload).eq("id", entry_id).execute()
                        except Exception:
                            payload_fallback = {
                                "start_zeit": payload["start_zeit"],
                                "ende_zeit": payload["ende_zeit"],
                                "pause_minuten": payload["pause_minuten"],
                                "quelle": payload["quelle"],
                            }
                            supabase.table("zeiterfassung").update(payload_fallback).eq("id", entry_id).execute()
                        log_zeitkorrektur(
                            admin_user_id=int(st.session_state.get("user_id") or 0),
                            admin_name=str(st.session_state.get("username") or st.session_state.get("user_name") or "Admin"),
                            mitarbeiter_id=int(aktiver_ma.get("id")),
                            mitarbeiter_name=f"{aktiver_ma.get('vorname','')} {aktiver_ma.get('nachname','')}".strip(),
                            zeiterfassung_id=entry_id,
                            alter_wert={
                                "start_zeit": entry.get("start_zeit"),
                                "ende_zeit": entry.get("ende_zeit"),
                                "pause_minuten": entry.get("pause_minuten"),
                            },
                            neuer_wert=payload,
                            begruendung=reason.strip(),
                            betrieb_id=int(st.session_state.get("betrieb_id") or 0),
                        )
                        _clear_zeitauswertung_caches()
                        st.success("Zeiteintrag gespeichert.")
                        st.session_state.pop("za_edit_entry", None)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Speichern fehlgeschlagen: {exc}")

            if do_delete:
                if not reason.strip():
                    st.error("Bitte eine Begründung eingeben.")
                else:
                    try:
                        supabase.table("zeiterfassung").delete().eq("id", entry_id).execute()
                        log_zeitloeschung(
                            admin_user_id=int(st.session_state.get("user_id") or 0),
                            admin_name=str(st.session_state.get("username") or st.session_state.get("user_name") or "Admin"),
                            mitarbeiter_id=int(aktiver_ma.get("id")),
                            mitarbeiter_name=f"{aktiver_ma.get('vorname','')} {aktiver_ma.get('nachname','')}".strip(),
                            zeiterfassung_id=entry_id,
                            alter_wert={
                                "start_zeit": entry.get("start_zeit"),
                                "ende_zeit": entry.get("ende_zeit"),
                                "pause_minuten": entry.get("pause_minuten"),
                            },
                            begruendung=reason.strip(),
                            betrieb_id=int(st.session_state.get("betrieb_id") or 0),
                        )
                        _clear_zeitauswertung_caches()
                        st.success("Zeiteintrag gelöscht.")
                        st.session_state.pop("za_edit_entry", None)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Löschen fehlgeschlagen: {exc}")

        if st.button("Schließen", use_container_width=True, key=f"zeit_edit_close_{entry_id}"):
            st.session_state.pop("za_edit_entry", None)
            st.rerun()

    _dialog()


def _berechne_soll_stunden(dienstplaene: list) -> float:
    """Berechnet die Soll-Stunden aus dem Dienstplan."""
    soll = 0.0
    for d in dienstplaene:
        if d.get('schichttyp') == 'arbeit' and d.get('start_zeit') and d.get('ende_zeit'):
            s, _ = parse_zeit(d['start_zeit'])
            e, nt = parse_zeit(d['ende_zeit'])
            pause = d.get('pause_minuten', 0) or 0
            soll += berechne_arbeitsstunden(s, e, pause, naechster_tag=nt)
        elif d.get('schichttyp') == 'urlaub' and d.get('urlaub_stunden'):
            soll += float(d['urlaub_stunden'])
    return soll


# ─────────────────────────────────────────────────────────────────────────────
# PDF-EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def _erstelle_pdf(
    mitarbeiter: dict,
    monat: int,
    jahr: int,
    monat_ergebnis: dict,
    soll_stunden: float,
    zeiterfassungen: list,
) -> bytes:
    """Erstellt eine kompakte 1-Seiten-A4-Zeitauswertung (ohne Geldwerte) via fpdf2."""
    from pathlib import Path

    from fpdf import FPDF

    def safe_str(value) -> str:
        if value is None:
            return "-"
        text = str(value)
        replacements = {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "Ä": "Ae",
            "Ö": "Oe",
            "Ü": "Ue",
            "ß": "ss",
            "–": "-",
            "—": "-",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def fmt_hhmm(value) -> str:
        if value is None:
            return "-"
        raw = str(value).strip()
        if not raw:
            return "-"
        if "T" in raw:
            raw = raw.split("T", 1)[-1]
        if len(raw) >= 5 and raw[2] == ":":
            return raw[:5]
        return raw[:5] if ":" in raw else raw

    def resolve_logo_path() -> str:
        root = Path(__file__).resolve().parents[1]
        candidates = [
            root / "assets" / "Piccolo Logo.jpeg",
            root / "assets" / "Piccolo Logo.jpg",
            root / "assets" / "piccolo_logo.jpeg",
            root / "assets" / "piccolo_logo.jpg",
        ]
        if BRAND_LOGO_IMAGE:
            candidates.append(Path(BRAND_LOGO_IMAGE))
        for candidate in candidates:
            try:
                if candidate and candidate.exists():
                    return str(candidate)
            except Exception:
                continue
        return ""

    raw_map = {int(r.get("id")): r for r in (zeiterfassungen or []) if r.get("id") is not None}

    rows: list[list[str]] = []
    zeilen = monat_ergebnis.get("zeilen", [])
    for z in zeilen:
        if z.get("fehler") == "Eintrag offen (kein Ende)":
            continue
        datum = z.get("datum")
        datum_str = datum.strftime("%d.%m.%Y") if isinstance(datum, date) else str(datum or "-")
        if isinstance(datum, date):
            tag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][datum.weekday()]
        else:
            tag = "-"
        raw = raw_map.get(int(z.get("id") or 0), {})
        ist_krank = bool(z.get("ist_krank") or _is_sick_row(raw))

        if ist_krank:
            von, bis = "LFZ", "LFZ"
            typ = "Krank"
        else:
            von = fmt_hhmm(raw.get("start_zeit") or z.get("berechneter_start_zeit"))
            bis = fmt_hhmm(raw.get("ende_zeit")) if raw.get("ende_zeit") else "-"
            typ = "Arbeit"
            if z.get("ist_feiertag"):
                typ = "Feiertag"
            elif z.get("ist_sonntag"):
                typ = "Sonntag"
        rows.append(
            [
                safe_str(datum_str),
                safe_str(tag),
                safe_str(von),
                safe_str(bis),
                safe_str(str(int(z.get("pause_minuten") or 0))),
                safe_str(f"{float(z.get('netto_stunden') or 0.0):.2f}"),
                safe_str(typ),
            ]
        )

    ist_stunden = float(monat_ergebnis.get("gesamt_stunden") or 0.0)
    diff = ist_stunden - float(soll_stunden or 0.0)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    margin = 7.0
    pdf.set_margins(margin, margin, margin)
    pdf.add_page()

    logo_path = resolve_logo_path()
    if logo_path:
        try:
            pdf.image(logo_path, x=pdf.w - margin - 34, y=margin, w=34)
        except Exception:
            pass

    name = f"{mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}".strip()
    monat_name = MONATE[monat - 1] if 1 <= int(monat) <= 12 else str(monat)
    personal_nr = safe_str(mitarbeiter.get("personalnummer") or "-")

    pdf.set_xy(margin, margin + 0.5)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(125, 6.5, safe_str("Zeitauswertung / Monatsnachweis"), ln=1)
    pdf.set_x(margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(125, 5.2, safe_str(f"{monat_name} {jahr}"), ln=1)
    pdf.set_x(margin)
    pdf.set_font("Helvetica", "", 8.8)
    pdf.cell(125, 4.8, safe_str(f"Mitarbeiter: {name}"), ln=1)
    pdf.set_x(margin)
    pdf.cell(125, 4.8, safe_str(f"Personal-Nr.: {personal_nr}"), ln=1)

    table_start_y = max(pdf.get_y() + 2.5, margin + 30.0)
    pdf.set_y(table_start_y)

    headers = ["Datum", "Tag", "Von", "Bis", "Pause", "Netto-h", "Typ"]
    col_widths = [28, 10, 20, 20, 18, 22, 78]  # Summe = 196 mm (A4 mit 7mm Rändern)
    row_count = len(rows) + 2  # Header + Summe
    bottom_limit = 276.0  # Platz für Footer
    available_h = max(80.0, bottom_limit - table_start_y)
    row_h = max(2.4, min(5.0, available_h / max(row_count, 1)))
    header_h = min(5.4, row_h + 0.8)

    pdf.set_font("Helvetica", "B", 8.0)
    pdf.set_fill_color(0, 0, 0)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], header_h, safe_str(h), border=1, align="C", fill=True)
    pdf.ln()

    row_font = 7.0 if row_h >= 3.8 else (6.2 if row_h >= 3.0 else 5.4)
    pdf.set_font("Helvetica", "", row_font)
    pdf.set_text_color(0, 0, 0)
    alt_fill = (245, 245, 245)
    for idx, row in enumerate(rows):
        fill = idx % 2 == 0
        if fill:
            pdf.set_fill_color(*alt_fill)
        else:
            pdf.set_fill_color(255, 255, 255)
        for i, val in enumerate(row):
            align = "L" if i == 6 else "C"
            pdf.cell(col_widths[i], row_h, safe_str(val), border=1, align=align, fill=fill)
        pdf.ln()

    # Deutlich hervorgehobene Summenzeile
    summary_h = max(4.2, row_h + 0.8)
    pdf.set_font("Helvetica", "B", max(7.0, row_font))
    pdf.set_fill_color(0, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(col_widths[:5]), summary_h, safe_str("Gesamtsumme Netto-Stunden"), border=1, align="L", fill=True)
    pdf.cell(col_widths[5], summary_h, safe_str(f"{ist_stunden:.2f} h"), border=1, align="C", fill=True)
    pdf.cell(
        col_widths[6],
        summary_h,
        safe_str(f"Soll {float(soll_stunden or 0.0):.2f} h | Differenz {diff:+.2f} h"),
        border=1,
        align="L",
        fill=True,
    )
    pdf.ln()

    pdf.set_y(-9.5)
    pdf.set_font("Helvetica", "", 6.6)
    pdf.set_text_color(70, 70, 70)
    pdf.cell(
        0,
        3.8,
        safe_str(f"Erstellt am: {date.today().strftime('%d.%m.%Y')} | {BRAND_COMPANY_NAME}"),
        align="C",
    )

    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin-1")
    return bytes(output)


# ─────────────────────────────────────────────────────────────────────────────
# HAUPTFUNKTION
# ─────────────────────────────────────────────────────────────────────────────

def show_zeitauswertung(mitarbeiter: dict, admin_modus: bool = False,
                        filter_mitarbeiter_id: int = None):
    """
    Hauptfunktion: Zeitauswertung / Lohn
    - admin_modus=True: Admin sieht alle Mitarbeiter + Audit-Log + Warnungen
    - filter_mitarbeiter_id: Für Admin-Filterung auf einen Mitarbeiter
    """

    st.subheader("Zeitauswertung / Lohn")

    # ── Monat / Jahr Auswahl ──────────────────────────────────────────────────
    heute = date.today()
    col1, col2 = st.columns(2)
    with col1:
        jahr = st.selectbox("Jahr", list(range(heute.year - 2, heute.year + 2)),
                            index=2, key="za_jahr")
    with col2:
        monat = st.selectbox("Monat", list(range(1, 13)),
                             format_func=lambda x: MONATE[x - 1],
                             index=heute.month - 1, key="za_monat")

    # ── Mitarbeiter-Auswahl (nur Admin) ──────────────────────────────────────
    ma_liste: list[dict] = []
    if admin_modus:
        ma_liste = _cached_admin_mitarbeiter_za(int(st.session_state.betrieb_id))
        ma_optionen = {f"{m['vorname']} {m['nachname']}": m for m in ma_liste}

        ausgewaehlter_name = st.selectbox(
            "Mitarbeiter auswählen",
            list(ma_optionen.keys()),
            key="za_ma_select"
        )
        aktiver_ma = ma_optionen[ausgewaehlter_name]
    else:
        aktiver_ma = mitarbeiter

    st.markdown("---")

    if admin_modus:
        _show_manual_outdoor_entry_form(
            ma_liste=ma_liste,
            default_ma_id=int(aktiver_ma.get("id") or 0),
            jahr=int(jahr),
            monat=int(monat),
        )
        st.markdown("---")

    # ── Daten laden ──────────────────────────────────────────────────────────
    zeiterfassungen = _lade_zeiterfassungen(aktiver_ma['id'], monat, jahr)
    dienstplan_start_map = _cached_dienstplan_startzeiten_with_fallback(aktiver_ma['id'], monat, jahr)

    # ── Lohnberechnung mit neuem Modul ───────────────────────────────────────
    data_hash = _build_data_hash(zeiterfassungen, dienstplan_start_map)
    monat_ergebnis = berechne_monat_cached(
        zeiterfassungen,
        aktiver_ma,
        auto_pause=False,
        dienstplan_start_map=dienstplan_start_map,
        data_hash=data_hash,
    )

    # ── Soll-Stunden ─────────────────────────────────────────────────────────
    # Für Endanzeige und Arbeitszeitkonto dieselbe Vertragslogik verwenden.
    # Dadurch bleiben Zeitauswertung und Konto deterministisch synchron.
    snap_preview = None
    try:
        snap_preview = sync_work_account_for_month(
            get_supabase_client(),
            betrieb_id=int(st.session_state.get("betrieb_id") or aktiver_ma.get("betrieb_id") or 1),
            mitarbeiter_id=int(aktiver_ma["id"]),
            monat=int(monat),
            jahr=int(jahr),
        )
    except Exception:
        snap_preview = None
    soll_stunden = float(snap_preview.soll_stunden) if snap_preview else float(aktiver_ma.get('monatliche_soll_stunden', 0) or 0)

    ist_stunden = monat_ergebnis["gesamt_stunden"]
    differenz = ist_stunden - soll_stunden
    gesamtbrutto = monat_ergebnis["gesamtbrutto"]
    zeilen = monat_ergebnis["zeilen"]
    warnungen = monat_ergebnis["warnungen"]

    # Korrekturen zählen (Zeilen mit updated_at != created_at)
    korrektur_count = sum(
        1 for z_raw in zeiterfassungen
        if z_raw.get('updated_at') and z_raw.get('created_at')
        and z_raw['updated_at'] != z_raw['created_at']
    )

    # ── Feiertag-Warnungen (Admin) ────────────────────────────────────────────
    if admin_modus and warnungen:
        for warnung in warnungen:
            st.warning(warnung)

    if korrektur_count > 0:
        st.warning(
            f"**{korrektur_count} Eintrag/Einträge** in diesem Monat wurden vom Administrator "
            f"korrigiert und sind in der Tabelle **gelb markiert**."
        )

    # ── Kennzahlen-Kacheln ────────────────────────────────────────────────────
    with st.container():
        st.markdown("<div class='coreo-card'>", unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Soll-Stunden", f"{soll_stunden:.2f} h")
        with k2:
            st.metric("Ist-Stunden", f"{ist_stunden:.2f} h")
        with k3:
            delta_color = "normal" if differenz >= 0 else "inverse"
            st.metric(
                "Differenz",
                f"{abs(differenz):.2f} h",
                delta=f"{'Überstunden' if differenz >= 0 else 'Minusstunden'}",
                delta_color=delta_color
            )
        with k4:
            st.metric("Bruttolohn gesamt", f"{gesamtbrutto:.2f} €")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Detailtabelle ─────────────────────────────────────────────────────────
    st.markdown(f"### Zeiterfassungen – {MONATE[monat-1]} {jahr}")

    # Feiertage des Monats für Tooltip
    feiertage_monat = get_feiertage_monat(monat, jahr)

    if not zeilen:
        st.info(f"Keine Zeiterfassungen für {MONATE[monat-1]} {jahr} vorhanden.")
    else:
        # Rohdaten für Zeiten (start_zeit, ende_zeit)
        raw_map = {z.get("id"): z for z in zeiterfassungen}

        df_rows = []
        for idx, z in enumerate(zeilen):
            # Korrektur-Flag aus Rohdaten
            raw = raw_map.get(z.get("id"), {})
            korrigiert = bool(
                raw.get('updated_at') and raw.get('created_at')
                and raw['updated_at'] != raw['created_at']
            )
            timeout_auto = _is_auto_timeout_entry(raw)

            datum = z["datum"]
            datum_str = datum.strftime('%d.%m.%Y') if isinstance(datum, date) else str(datum)
            wochentag = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][datum.weekday()] if isinstance(datum, date) else "–"

            ist_krank_eintrag = bool(z.get("ist_krank") or _is_sick_row(raw))
            if ist_krank_eintrag:
                start_str = "LFZ"
                ende_str = "LFZ"
            else:
                calc_start = str(z.get("berechneter_start_zeit") or "")[:5] if z.get("berechneter_start_zeit") else ""
                start_str = calc_start or (str(raw.get("start_zeit", "–"))[:5] if raw.get("start_zeit") else "–")
                ende_str = str(raw.get("ende_zeit", ""))[:5] if raw.get("ende_zeit") else "Offen"

            # Typ
            if ist_krank_eintrag:
                lfz_h = z.get("lfz_stunden", z.get("netto_stunden", 0))
                typ_str = f"Krank (LFZ {lfz_h:.2f}h)"
            elif z.get("ist_feiertag"):
                ft_name = z.get("feiertag_name", "Feiertag")
                typ_str = f"Feiertag {ft_name[:15]}"
            elif z.get("ist_sonntag"):
                typ_str = "Sonntag"
            else:
                typ_str = "Arbeit"

            if korrigiert:
                typ_str += " Korrigiert"

            # Manuell angelegter Eintrag kennzeichnen
            if raw.get('quelle') == 'manuell_admin':
                typ_str += " Manuell"
            if timeout_auto:
                typ_str += " Auto-Timeout"

            # Zuschlag-Info
            so_z = z.get("sonntagszuschlag", 0)
            ft_z = z.get("feiertagszuschlag", 0)
            zuschlag_str = ""
            if so_z > 0:
                zuschlag_str += f"+{so_z:.2f}€ So"
            if ft_z > 0:
                zuschlag_str += f" +{ft_z:.2f}€ Ft"

            # Warnung
            if z.get("hat_zuschlag_aber_kein_haekchen"):
                typ_str += " Hinweis"

            # Offener Eintrag
            if z.get("fehler"):
                netto_str = "Offen"
                gesamt_str = "–"
            else:
                netto_str = f"{z.get('netto_stunden', 0):.2f} h"
                gesamt_str = f"{z.get('gesamtlohn', 0):.2f} €"

            grundlohn_str = f"{z.get('grundlohn', 0):.2f} €"
            if zuschlag_str:
                grundlohn_str += f" ({zuschlag_str.strip()})"

            df_rows.append({
                "Datum": datum_str,
                "Tag": wochentag[:2],
                "Von": start_str,
                "Bis": ende_str,
                "Pause": f"{z.get('pause_minuten', 0)} Min",
                "Netto-h": netto_str,
                "Typ": typ_str,
                "Status": "Timeout (Auto-Kappung 10h)" if timeout_auto else "",
                "Grundlohn": grundlohn_str,
                "Gesamt": gesamt_str,
                "__auto_timeout": timeout_auto,
            })

        # Summenzeile
        df_rows.append({
            "Datum": "── Monatssumme ──",
            "Tag": "",
            "Von": "",
            "Bis": "",
            "Pause": "",
            "Netto-h": f"{ist_stunden:.2f} h",
            "Typ": "",
            "Status": "",
            "Grundlohn": "",
            "Gesamt": f"{gesamtbrutto:.2f} €",
            "__auto_timeout": False,
        })
        timeout_count = sum(1 for row in df_rows if bool(row.get("__auto_timeout")))
        display_rows = [{k: v for k, v in row.items() if not k.startswith("__")} for row in df_rows]
        try:
            import pandas as pd

            df_display = pd.DataFrame(display_rows)

            def _timeout_row_style(row):
                is_timeout = "Timeout (Auto-Kappung 10h)" in str(row.get("Status") or "")
                style = "background-color: #ff9800; color: #000000; font-weight: 700;" if is_timeout else ""
                return [style] * len(row)

            st.dataframe(
                df_display.style.apply(_timeout_row_style, axis=1),
                use_container_width=True,
                hide_index=True,
            )
        except Exception:
            st.dataframe(display_rows, use_container_width=True, hide_index=True)
        if timeout_count > 0:
            st.warning(
                f"{timeout_count} Eintrag/Einträge wurden durch Auto-Timeout (10h) beendet "
                "und sind in der Tabelle orange markiert."
            )

        if admin_modus:
            st.markdown("#### Zeiteinträge interaktiv korrigieren")
            st.caption("Direkt auf Bearbeiten klicken, um den Eintrag im Popup zu ändern oder zu löschen (mit Pflichtbegründung).")
            ignored_conflict_ids, conflict_days = _collect_sick_day_conflicts(zeiterfassungen)
            if conflict_days:
                details = " | ".join([f"{d}: {n} ignoriert" for d, n in sorted(conflict_days.items())])
                st.warning(
                    "Kranktag-Konflikte erkannt. Zusätzliche Stempelzeiten an diesen Tagen "
                    "werden in der Berechnung nicht berücksichtigt: "
                    f"{details}"
                )

            editable_entries = []
            for raw in zeiterfassungen:
                rid = raw.get("id")
                if rid is None:
                    continue
                editable_entries.append(raw)

            editable_entries.sort(
                key=lambda x: (str(x.get("datum") or ""), str(x.get("start_zeit") or "")),
                reverse=True,
            )

            if not editable_entries:
                st.info("Keine Zeiteinträge für den gewählten Zeitraum vorhanden.")
            else:
                st.markdown("<div class='coreo-card'>", unsafe_allow_html=True)
                for raw in editable_entries:
                    rid = int(raw.get("id"))
                    d = str(raw.get("datum") or "")
                    s = str(raw.get("start_zeit") or "")[:5] if raw.get("start_zeit") else "--:--"
                    e = str(raw.get("ende_zeit") or "")[:5] if raw.get("ende_zeit") else "offen"
                    ignored_label = " (Konflikt: in Berechnung ignoriert)" if rid in ignored_conflict_ids else ""

                    c_info, c_action = st.columns([5, 1])
                    with c_info:
                        st.markdown(f"**#{rid}** · {d} · {s}–{e}{ignored_label}")
                    with c_action:
                        if st.button("Bearbeiten", key=f"za_edit_btn_{rid}", use_container_width=True):
                            st.session_state["za_edit_entry"] = raw
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            active_edit = st.session_state.get("za_edit_entry")
            if active_edit:
                _korrigiere_zeiterfassung_popup(
                    entry=active_edit,
                    aktiver_ma=aktiver_ma,
                    monat=monat,
                    jahr=jahr,
                )

    st.markdown("---")

    # ── Lohnaufschlüsselung ───────────────────────────────────────────────────
    st.markdown("### Lohnaufschlüsselung – Zuschlagsübersicht")

    effective_rate = _effective_hourly_rate(aktiver_ma)
    so_stunden = monat_ergebnis["sonntags_stunden"]
    ft_stunden = monat_ergebnis["feiertags_stunden"]
    normal_stunden = max(0, ist_stunden - so_stunden - ft_stunden)
    grundlohn = monat_ergebnis["grundlohn"]
    so_zuschlag = monat_ergebnis["sonntagszuschlag"]
    ft_zuschlag = monat_ergebnis["feiertagszuschlag"]

    with st.container():
        st.markdown("<div class='coreo-card'>", unsafe_allow_html=True)
        lohn_cols = st.columns(3)
        with lohn_cols[0]:
            st.metric(
                label="Normalstunden",
                value=f"{normal_stunden:.2f} h",
                help=f"× {effective_rate:.2f} €/h"
            )
            st.caption(f"{grundlohn:.2f} € Grundlohn")

        with lohn_cols[1]:
            so_aktiv = aktiver_ma.get("sonntagszuschlag_aktiv", False)
            so_label = "Sonntagsstunden (+50%)" if so_aktiv else "Sonntagsstunden (inaktiv)"
            st.metric(
                label=so_label,
                value=f"{so_stunden:.2f} h",
                help="Sonntag 00:00–24:00 Uhr"
            )
            st.caption(f"+{so_zuschlag:.2f} € Zuschlag")

        with lohn_cols[2]:
            ft_aktiv = aktiver_ma.get("feiertagszuschlag_aktiv", False)
            ft_label = "Feiertagsstunden (+100%)" if ft_aktiv else "Feiertagsstunden (inaktiv)"
            st.metric(
                label=ft_label,
                value=f"{ft_stunden:.2f} h",
                help="Gesetzliche Feiertage Sachsen (SN)"
            )
            st.caption(f"+{ft_zuschlag:.2f} € Zuschlag")
        st.markdown("</div>", unsafe_allow_html=True)

    # Gesamtlohn-Box als native Streamlit-Komponenten (kein HTML wegen Streamlit 1.40+ Bug)
    st.markdown("---")
    gl_col1, gl_col2 = st.columns([2, 1])
    with gl_col1:
        detail_parts = [f"{grundlohn:.2f} € Grundlohn"]
        if so_zuschlag > 0:
            detail_parts.append(f"+ {so_zuschlag:.2f} € So-Zuschlag")
        if ft_zuschlag > 0:
            detail_parts.append(f"+ {ft_zuschlag:.2f} € Ft-Zuschlag")
        st.markdown(f"**Gesamt-Bruttolohn {MONATE[monat-1]} {jahr}**")
        st.caption(" • ".join(detail_parts))
    with gl_col2:
        st.metric(label="Bruttolohn gesamt", value=f"{gesamtbrutto:.2f} €")

    st.markdown("---")

    # ── Soll-Ist-Vergleich ────────────────────────────────────────────────────
    st.markdown("### Soll-Ist-Vergleich")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div style="background:#000000;color:#ffffff;padding:1rem;border-radius:8px;border:1px solid #ffffff;border-left:4px solid #ffffff;">
            <div style="font-size:0.85rem;color:#ffffff;">Soll-Stunden (Dienstplan/Profil)</div>
            <div style="font-size:1.5rem;font-weight:700;color:#ffffff;">{soll_stunden:.2f} h</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        diff_color = "#198754" if differenz >= 0 else "#dc3545"
        diff_icon = "▲" if differenz >= 0 else "▼"
        st.markdown(f"""
        <div style="background:#000000;color:#ffffff;padding:1rem;border-radius:8px;border:1px solid #ffffff;border-left:4px solid {diff_color};">
            <div style="font-size:0.85rem;color:#ffffff;">Ist-Stunden vs. Soll</div>
            <div style="font-size:1.5rem;font-weight:700;color:{diff_color};">{diff_icon} {abs(differenz):.2f} h</div>
            <div style="font-size:0.8rem;color:#ffffff;">{'Überstunden' if differenz >= 0 else 'Minusstunden'}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Arbeitszeitkonto & Überstunden-Saldo ────────────────────────────────────────────────────
    if admin_modus:
        st.markdown("### Arbeitszeitkonto")
        try:
            supabase_konto = get_supabase_client()
            snap = snap_preview or sync_work_account_for_month(
                supabase_konto,
                betrieb_id=int(st.session_state.get("betrieb_id") or aktiver_ma.get("betrieb_id") or 1),
                mitarbeiter_id=int(aktiver_ma["id"]),
                monat=int(monat),
                jahr=int(jahr),
            )
            if snap:
                saldo = float(snap.ueberstunden_saldo or 0.0)
                diff_mon = float(snap.differenz_stunden or 0.0)
                vortrag = round(saldo - diff_mon, 2)
                
                col_k1, col_k2, col_k3 = st.columns(3)
                with col_k1:
                    st.metric("Vortrag Vormonat", f"{vortrag:+.2f} h")
                with col_k2:
                    st.metric("Differenz diesen Monat", f"{diff_mon:+.2f} h")
                with col_k3:
                    st.metric("Aktueller Saldo", f"{saldo:+.2f} h")
                st.caption(
                    f"Neuer Saldo = (Ist - Soll) + Saldenvortrag = "
                    f"({snap.ist_stunden:.2f} - {snap.soll_stunden:.2f}) + {vortrag:.2f}"
                )
                if getattr(snap, "korrektur_grund", None):
                    st.info(f"Manuelle Korrekturgrundlage: {snap.korrektur_grund}")

                _show_manual_account_adjustment(
                    aktiver_ma=aktiver_ma,
                    monat=int(monat),
                    jahr=int(jahr),
                    saldo=saldo,
                )
                
                # Korrekturbuchung: Überstunden auszahlen
                if saldo > 0:
                    st.markdown("---")
                    st.markdown("#### Überstunden auszahlen (Korrekturbuchung)")
                    st.info(f"Aktuelles Guthaben: **{saldo:.2f} Überstunden**. Sie können einen Teil oder alle Stunden zur Auszahlung freigeben.")
                    
                    col_korr1, col_korr2 = st.columns(2)
                    with col_korr1:
                        auszahl_stunden = st.number_input(
                            "Stunden zur Auszahlung",
                            min_value=0.0,
                            max_value=float(saldo),
                            value=0.0,
                            step=0.5,
                            format="%.2f",
                            key=f"auszahl_stunden_{monat}_{jahr}"
                        )
                    with col_korr2:
                        effective_rate = _effective_hourly_rate(aktiver_ma)
                        auszahl_betrag = round(auszahl_stunden * effective_rate, 2)
                        st.metric("Auszahlungsbetrag", f"{auszahl_betrag:.2f} €")
                    
                    korr_grund = st.text_input(
                        "Begründung",
                        placeholder="z.B. Auszahlung 20 Überstunden März 2026",
                        key=f"korr_grund_{monat}_{jahr}"
                    )
                    
                    if st.button("Korrekturbuchung speichern", type="primary", key=f"korr_save_{monat}_{jahr}"):
                        if auszahl_stunden <= 0:
                            st.error("Bitte Stunden > 0 eingeben.")
                        elif not korr_grund.strip():
                            st.error("Bitte eine Begründung angeben.")
                        else:
                            try:
                                supabase_k = get_supabase_client()
                                supabase_k.table('ueberstunden_korrekturen').insert({
                                    'mitarbeiter_id': aktiver_ma['id'],
                                    'betrieb_id': st.session_state.betrieb_id,
                                    'monat': monat,
                                    'jahr': jahr,
                                    'stunden': auszahl_stunden,
                                    'betrag': auszahl_betrag,
                                    'grund': korr_grund.strip(),
                                    'erstellt_am': datetime.now().isoformat()
                                }).execute()
                                st.success(f"Korrekturbuchung gespeichert: {auszahl_stunden:.2f} h = {auszahl_betrag:.2f} € werden ausgezahlt. Saldo reduziert sich auf {saldo - auszahl_stunden:.2f} h.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Speichern: {str(e)}")
        except Exception as e:
            st.warning(f"Arbeitszeitkonto konnte nicht geladen werden: {str(e)}")
        st.markdown("---")

    st.markdown("---")

    # ── Feiertage des Monats (Info) ─────────────────────────────────────────────────────
    if feiertage_monat:
        st.markdown(f"### Feiertage in Sachsen – {MONATE[monat-1]} {jahr}")
        ft_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:1rem;">'
        for ft_datum, ft_name in sorted(feiertage_monat.items()):
            wt = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][ft_datum.weekday()]
            ruhetag = ft_datum.weekday() in (0, 1)
            bg = "#000000" if ruhetag else "#dc3545"
            border = "1px solid #ffffff" if ruhetag else "1px solid #dc3545"
            hinweis = " (Ruhetag)" if ruhetag else ""
            ft_html += f'<span style="background:{bg};border:{border};color:#ffffff;padding:4px 10px;border-radius:6px;font-size:0.82rem;">{ft_datum.strftime("%d.%m.")} {wt} - {ft_name}{hinweis}</span>'
        ft_html += '</div>'
        st.markdown(ft_html, unsafe_allow_html=True)
        st.markdown("---")

    # ── Audit-Log (nur Admin) ─────────────────────────────────────────────────
    if admin_modus:
        with st.expander("Audit-Log (Berechnungsprotokoll)", expanded=False):
            st.markdown("""
            <div style="background:#000000;color:#ffffff;padding:0.5rem;border-radius:6px;border:1px solid #ffffff;margin-bottom:0.5rem;">
                <small style="color:#ffffff;">Das Audit-Log protokolliert jeden Rechenschritt für Revisionszwecke.
                Es zeigt welcher Zuschlag an welchem Tag durch welche Regel ausgelöst wurde.</small>
            </div>
            """, unsafe_allow_html=True)
            audit_text = "\n".join(monat_ergebnis.get("audit_log_gesamt", []))
            st.code(audit_text, language=None)

            # Download-Button für Audit-Log
            if audit_text:
                st.download_button(
                    label="Audit-Log als TXT herunterladen",
                    data=audit_text.encode("utf-8"),
                    file_name=f"AuditLog_{aktiver_ma.get('nachname','MA')}_{jahr}_{monat:02d}.txt",
                    mime="text/plain"
                )

    # ── PDF-Export ────────────────────────────────────────────────────────────
    st.markdown("### Monatsauswertung exportieren")

    col_pdf, col_info = st.columns([1, 2])
    with col_pdf:
        if st.button("PDF-Monatsauswertung erstellen", type="primary", use_container_width=True):
            try:
                pdf_bytes = _erstelle_pdf(
                    aktiver_ma,
                    monat,
                    jahr,
                    monat_ergebnis,
                    soll_stunden,
                    zeiterfassungen,
                )
                dateiname = (
                    f"Zeitauswertung_{aktiver_ma['nachname']}_{aktiver_ma['vorname']}_"
                    f"{jahr}_{monat:02d}.pdf"
                )
                st.download_button(
                    label="PDF herunterladen",
                    data=pdf_bytes,
                    file_name=dateiname,
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("PDF erfolgreich erstellt.")
            except Exception as e:
                st.error(f"Fehler beim Erstellen der PDF: {str(e)}")

    with col_info:
        st.info(
            "Die Monatsauswertung enthält alle Zeiterfassungen und den Soll-Ist-Vergleich "
            "als reinen Zeitnachweis (ohne Euro-/Lohnwerte)."
        )

    if korrektur_count > 0:
        st.markdown(f"""
        <div style="background:#000000;color:#ffffff;padding:0.8rem;border-radius:6px;border:1px solid #ffffff;border-left:4px solid #ffffff;margin-top:0.5rem;">
            <strong>Hinweis zu Korrekturen:</strong> {korrektur_count} Zeiterfassung(en)
            wurden in diesem Monat durch den Administrator angepasst.
            Diese sind in der Tabelle markiert.
        </div>
        """, unsafe_allow_html=True)

    # Offene Einträge
    if monat_ergebnis.get("offene_eintraege", 0) > 0:
        st.warning(
            f"**{monat_ergebnis['offene_eintraege']} offene Einträge** (kein Ende gestempelt) "
            f"wurden nicht in die Lohnberechnung einbezogen."
        )
