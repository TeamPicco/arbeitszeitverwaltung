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

from utils.database import get_supabase_client
from utils.planning_tables import resolve_planning_table
from utils.audit_log import log_aktion, log_zeitkorrektur, log_zeitloeschung
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

def _lade_zeiterfassungen(mitarbeiter_id: int, monat: int, jahr: int) -> list:
    """Lädt alle Zeiterfassungen für einen Mitarbeiter in einem Monat."""
    supabase = get_supabase_client()
    erster = date(jahr, monat, 1).isoformat()
    letzter = date(jahr, monat, monthrange(jahr, monat)[1]).isoformat()
    r = supabase.table('zeiterfassung').select(
        'id,datum,start_zeit,ende_zeit,pause_minuten,quelle,ist_krank,created_at,updated_at'
    ).eq(
        'mitarbeiter_id', mitarbeiter_id
    ).gte('datum', erster).lte('datum', letzter).order('datum').execute()
    return r.data or []


@st.cache_data(ttl=30, show_spinner=False)
def _cached_dienstplan_startzeiten(mitarbeiter_id: int, monat: int, jahr: int) -> dict:
    """Lädt pro Datum die früheste geplante Startzeit (für Kappungslogik)."""
    supabase = get_supabase_client()
    planning_table = resolve_planning_table(supabase)
    erster = date(jahr, monat, 1).isoformat()
    letzter = date(jahr, monat, monthrange(jahr, monat)[1]).isoformat()
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
    start_map: dict[str, str] = {}
    for row in (r.data or []):
        if str(row.get("schichttyp") or "arbeit") != "arbeit":
            continue
        d = str(row.get("datum") or "")
        s = str(row.get("start_zeit") or "")
        if not d or not s:
            continue
        if d not in start_map:
            start_map[d] = s
    return start_map


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
                "updated_at": z.get("updated_at"),
            }
        )
    payload = {"zeiterfassung": relevant, "dienstplan_start_map": dienstplan_start_map or {}}
    import json
    import hashlib

    canonical = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _show_manual_account_adjustment(
    *,
    aktiver_ma: dict,
    monat: int,
    jahr: int,
    saldo: float,
) -> None:
    """Inline-Korrektur im Auswertungsflow mit Pflichtbegründung."""
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
                    z_payload = {
                        "betrieb_id": betrieb_id,
                        "mitarbeiter_id": ma_id,
                        "datum": month_start.isoformat(),
                        "start_zeit": "00:00:00",
                        "ende_zeit": "00:00:00",
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
                        fallback_payload = {
                            "betrieb_id": betrieb_id,
                            "mitarbeiter_id": ma_id,
                            "datum": month_start.isoformat(),
                            "start_zeit": "00:00:00",
                            "ende_zeit": "00:00:00",
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
                        _cached_dienstplan_startzeiten.clear()
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
                        _cached_dienstplan_startzeiten.clear()
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

def _erstelle_pdf(mitarbeiter: dict, monat: int, jahr: int, monat_ergebnis: dict,
                  soll_stunden: float) -> bytes:
    """Erstellt eine PDF-Monatsauswertung mit vollständiger Zuschlagsaufschlüsselung."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    def safe_str(s):
        """Konvertiert beliebige Werte sicher zu ReportLab-kompatiblen Strings (Umlaute korrekt)."""
        if s is None:
            return "-"
        try:
            text = str(s)
            # Umlaute und Sonderzeichen für ReportLab (latin-1 Subset) ersetzen
            replacements = {
                'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
                'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
                'ß': 'ss', '€': 'EUR', '–': '-', '—': '-',
            }
            for orig, repl in replacements.items():
                text = text.replace(orig, repl)
            # Alle verbleibenden nicht-ASCII-Zeichen entfernen
            return text.encode('ascii', errors='replace').decode('ascii')
        except Exception:
            return str(s)[:50]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    titel_style = ParagraphStyle('titel', parent=styles['Heading1'],
                                  fontSize=16, alignment=TA_CENTER, spaceAfter=6)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'],
                                fontSize=11, alignment=TA_CENTER, spaceAfter=4)
    info_style = ParagraphStyle('info', parent=styles['Normal'],
                                 fontSize=9, spaceAfter=2)

    story.append(Paragraph("Zeitauswertung / Monatsnachweis", titel_style))
    story.append(Paragraph(f"{MONATE[monat-1]} {jahr}", sub_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"<b>Mitarbeiter:</b> {safe_str(mitarbeiter['vorname'])} {safe_str(mitarbeiter['nachname'])} &nbsp;&nbsp; "
        f"<b>Personal-Nr.:</b> {safe_str(mitarbeiter.get('personalnummer', '-'))} &nbsp;&nbsp; "
        f"<b>Abgeleiteter Stundenwert:</b> {_effective_hourly_rate(mitarbeiter):.2f} EUR",
        info_style))
    story.append(Spacer(1, 0.5*cm))

    # Detailtabelle
    header = ['Datum', 'Tag', 'Von', 'Bis', 'Pause', 'Netto-h', 'Typ', 'Grundlohn', 'Zuschlag', 'Gesamt']
    data = [header]

    zeilen = monat_ergebnis.get("zeilen", [])
    for z in zeilen:
        if z.get("fehler") and z["fehler"] == "Eintrag offen (kein Ende)":
            continue

        datum = z["datum"]
        datum_str = datum.strftime('%d.%m.%Y') if isinstance(datum, date) else str(datum)
        wochentag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][datum.weekday()] if isinstance(datum, date) else "–"

        typ = "Arbeit"
        if z.get("ist_feiertag"):
            typ = f"Feiertag"
        elif z.get("ist_sonntag"):
            typ = "Sonntag"

        zuschlag_gesamt = z.get("sonntagszuschlag", 0) + z.get("feiertagszuschlag", 0)

        data.append([
            datum_str,
            wochentag,
            str(z.get("datum", ""))[:5] if False else "–",  # Platzhalter
            "–",
            f"{z.get('pause_minuten', 0)} Min",
            f"{z.get('netto_stunden', 0):.2f}",
            typ,
            f"{z.get('grundlohn', 0):.2f} €",
            f"+{zuschlag_gesamt:.2f} €" if zuschlag_gesamt > 0 else "–",
            f"{z.get('gesamtlohn', 0):.2f} €",
        ])

    # Wir bauen die Tabelle aus den Zeiterfassungs-Rohdaten neu auf (mit Zeiten)
    # Dazu nutzen wir die zeilen-Daten direkt
    data = [header]
    for z in zeilen:
        if z.get("fehler") and z["fehler"] == "Eintrag offen (kein Ende)":
            continue
        datum = z["datum"]
        datum_str = datum.strftime('%d.%m.%Y') if isinstance(datum, date) else str(datum)
        wochentag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][datum.weekday()] if isinstance(datum, date) else "–"
        typ = "Arbeit"
        if z.get("ist_feiertag"):
            typ = f"Feiertag"
        elif z.get("ist_sonntag"):
            typ = "Sonntag"
        zuschlag_gesamt = z.get("sonntagszuschlag", 0) + z.get("feiertagszuschlag", 0)
        data.append([
            datum_str, wochentag, "–", "–",
            f"{z.get('pause_minuten', 0)} Min",
            f"{z.get('netto_stunden', 0):.2f}",
            typ,
            f"{z.get('grundlohn', 0):.2f} €",
            f"+{zuschlag_gesamt:.2f} €" if zuschlag_gesamt > 0 else "–",
            f"{z.get('gesamtlohn', 0):.2f} €",
        ])

    ist_stunden = monat_ergebnis.get("gesamt_stunden", 0)
    gesamtbrutto = monat_ergebnis.get("gesamtbrutto", 0)
    data.append(['', '', '', '', 'Gesamt:', f"{ist_stunden:.2f}", '', '', '',
                 f"{gesamtbrutto:.2f} €"])

    col_widths = [1.9*cm, 0.9*cm, 1.2*cm, 1.2*cm, 1.5*cm, 1.4*cm, 1.8*cm, 2.0*cm, 1.8*cm, 2.0*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ])
    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 0.8*cm))

    # Zusammenfassung mit Zuschlagsaufschlüsselung
    diff = ist_stunden - soll_stunden
    diff_str = f"+{diff:.2f} h" if diff >= 0 else f"{diff:.2f} h"

    zusammen = [
        ['Soll-Stunden:', f"{soll_stunden:.2f} h"],
        ['Ist-Stunden (Netto):', f"{ist_stunden:.2f} h"],
        ['Differenz:', diff_str],
        ['', ''],
        ['Grundlohn:', f"{monat_ergebnis.get('grundlohn', 0):.2f} €"],
    ]
    if monat_ergebnis.get("sonntags_stunden", 0) > 0:
        zusammen.append([
            f"Sonntagszuschlag ({monat_ergebnis['sonntags_stunden']:.2f} h × 50%):",
            f"+{monat_ergebnis.get('sonntagszuschlag', 0):.2f} €"
        ])
    if monat_ergebnis.get("feiertags_stunden", 0) > 0:
        zusammen.append([
            f"Feiertagszuschlag ({monat_ergebnis['feiertags_stunden']:.2f} h × 100%):",
            f"+{monat_ergebnis.get('feiertagszuschlag', 0):.2f} €"
        ])
    zusammen.append(['Gesamt-Bruttolohn:', f"{gesamtbrutto:.2f} €"])

    t2 = Table(zusammen, colWidths=[7*cm, 4*cm])
    t2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)
    story.append(Spacer(1, 1*cm))

    story.append(Paragraph(
        f"Erstellt am: {date.today().strftime('%d.%m.%Y')} | "
        f"Bundesland: Sachsen (SN) | CrewBase Arbeitszeitverwaltung",
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=7,
                       alignment=TA_CENTER, textColor=colors.grey)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


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
    if admin_modus:
        supabase = get_supabase_client()
        try:
            alle_ma = supabase.table('mitarbeiter').select(
                'id,vorname,nachname,monatliche_soll_stunden,monatliche_brutto_verguetung,'
                'sonntagszuschlag_aktiv,feiertagszuschlag_aktiv,personalnummer,beschaeftigungsart'
            ).eq('betrieb_id', st.session_state.betrieb_id).order('nachname').execute()
            ma_liste = alle_ma.data or []
        except Exception:
            # Rückwärtskompatibilität: ältere DBs mit stundenlohn_brutto statt Monatsbrutto.
            alle_ma = supabase.table('mitarbeiter').select(
                'id,vorname,nachname,monatliche_soll_stunden,stundenlohn_brutto,'
                'sonntagszuschlag_aktiv,feiertagszuschlag_aktiv,personalnummer,beschaeftigungsart'
            ).eq('betrieb_id', st.session_state.betrieb_id).order('nachname').execute()
            ma_liste = alle_ma.data or []
            for m in ma_liste:
                try:
                    m["monatliche_brutto_verguetung"] = round(
                        float(m.get("monatliche_soll_stunden") or 0.0) * float(m.get("stundenlohn_brutto") or 0.0),
                        2,
                    )
                except Exception:
                    m["monatliche_brutto_verguetung"] = 0.0
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

    # ── Daten laden ──────────────────────────────────────────────────────────
    zeiterfassungen = _lade_zeiterfassungen(aktiver_ma['id'], monat, jahr)
    dienstplan_start_map = _cached_dienstplan_startzeiten(aktiver_ma['id'], monat, jahr)

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
    # Soll-Stunden immer aus Stammdaten (Vertrag), nicht aus Dienstplan
    soll_stunden = float(aktiver_ma.get('monatliche_soll_stunden', 0) or 0)

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

            datum = z["datum"]
            datum_str = datum.strftime('%d.%m.%Y') if isinstance(datum, date) else str(datum)
            wochentag = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][datum.weekday()] if isinstance(datum, date) else "–"

            ist_krank_eintrag = z.get("ist_krank") or raw.get("ist_krank") or raw.get("quelle") == "au_bescheinigung"
            if ist_krank_eintrag:
                start_str = "LFZ"
                ende_str = "LFZ"
            else:
                start_str = str(raw.get("start_zeit", "–"))[:5] if raw.get("start_zeit") else "–"
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
                "Grundlohn": grundlohn_str,
                "Gesamt": gesamt_str,
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
            "Grundlohn": "",
            "Gesamt": f"{gesamtbrutto:.2f} €",
        })

        st.dataframe(df_rows, use_container_width=True, hide_index=True)

        if admin_modus:
            st.markdown("#### Zeiteinträge interaktiv korrigieren")
            st.caption("Klicken Sie auf einen Eintrag, um ihn in einem Popup zu bearbeiten oder zu löschen (mit Pflichtbegründung).")
            edit_options = {}
            for raw in zeiterfassungen:
                rid = raw.get("id")
                if rid is None:
                    continue
                d = str(raw.get("datum") or "")
                s = str(raw.get("start_zeit") or "")[:5] if raw.get("start_zeit") else "--:--"
                e = str(raw.get("ende_zeit") or "")[:5] if raw.get("ende_zeit") else "offen"
                label = f"#{rid} · {d} · {s}–{e}"
                edit_options[label] = raw

            if edit_options:
                selected_label = st.selectbox(
                    "Zeiteintrag auswählen",
                    options=list(edit_options.keys()),
                    key="za_edit_select",
                )
                if st.button("Eintrag öffnen", use_container_width=True, key="za_edit_open_btn"):
                    st.session_state["za_edit_entry"] = edit_options[selected_label]
                    st.rerun()

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
        <div style="background:#f8f9fa;padding:1rem;border-radius:8px;border-left:4px solid #1f2937;">
            <div style="font-size:0.85rem;color:#1f2937;">Soll-Stunden (Dienstplan/Profil)</div>
            <div style="font-size:1.5rem;font-weight:700;">{soll_stunden:.2f} h</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        diff_color = "#198754" if differenz >= 0 else "#dc3545"
        diff_icon = "▲" if differenz >= 0 else "▼"
        st.markdown(f"""
        <div style="background:#f8f9fa;padding:1rem;border-radius:8px;border-left:4px solid {diff_color};">
            <div style="font-size:0.85rem;color:#1f2937;">Ist-Stunden vs. Soll</div>
            <div style="font-size:1.5rem;font-weight:700;color:{diff_color};">{diff_icon} {abs(differenz):.2f} h</div>
            <div style="font-size:0.8rem;color:#1f2937;">{'Überstunden' if differenz >= 0 else 'Minusstunden'}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Arbeitszeitkonto & Überstunden-Saldo ────────────────────────────────────────────────────
    if admin_modus:
        st.markdown("### Arbeitszeitkonto")
        try:
            supabase_konto = get_supabase_client()
            snap = sync_work_account_for_month(
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
            bg = "#dee2e6" if ruhetag else "#dc3545"
            opacity = "0.5" if ruhetag else "1"
            hinweis = " (Ruhetag)" if ruhetag else ""
            ft_html += f'<span style="background:{bg};color:white;padding:4px 10px;border-radius:6px;font-size:0.82rem;opacity:{opacity};">{ft_datum.strftime("%d.%m.")} {wt} – {ft_name}{hinweis}</span>'
        ft_html += '</div>'
        st.markdown(ft_html, unsafe_allow_html=True)
        st.markdown("---")

    # ── Audit-Log (nur Admin) ─────────────────────────────────────────────────
    if admin_modus:
        with st.expander("Audit-Log (Berechnungsprotokoll)", expanded=False):
            st.markdown("""
            <div style="background:#f8f9fa;padding:0.5rem;border-radius:6px;margin-bottom:0.5rem;">
                <small style="color:#1f2937;">Das Audit-Log protokolliert jeden Rechenschritt für Revisionszwecke.
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
                pdf_bytes = _erstelle_pdf(aktiver_ma, monat, jahr, monat_ergebnis, soll_stunden)
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
            "Die Monatsauswertung enthält alle Zeiterfassungen, den Soll-Ist-Vergleich, "
            "Zuschlagsberechnungen nach Sachsen-Feiertagskalender und dient als Grundlage "
            "für die Lohnabrechnung."
        )

    if korrektur_count > 0:
        st.markdown(f"""
        <div style="background:#fff3cd;color:#000000;padding:0.8rem;border-radius:6px;border-left:4px solid #ffc107;margin-top:0.5rem;">
            <strong>Hinweis zu Korrekturen:</strong> {korrektur_count} Zeiterfassung(en)
            wurden in diesem Monat durch den Administrator angepasst.
            Diese sind in der Tabelle gelb markiert.
        </div>
        """, unsafe_allow_html=True)

    # Offene Einträge
    if monat_ergebnis.get("offene_eintraege", 0) > 0:
        st.warning(
            f"**{monat_ergebnis['offene_eintraege']} offene Einträge** (kein Ende gestempelt) "
            f"wurden nicht in die Lohnberechnung einbezogen."
        )
