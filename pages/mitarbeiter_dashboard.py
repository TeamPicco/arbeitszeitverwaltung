from __future__ import annotations

import io
import os
from datetime import date, datetime, timedelta

import streamlit as st

from pages.mitarbeiter_dienstplan import erstelle_dienstplan_pdf
from utils.branding import BRAND_APP_NAME, BRAND_ICON_IMAGE, BRAND_LOGO_IMAGE
from utils.database import get_supabase_client
from utils.lohnberechnung import summarize_employee_month
from utils.session import require_betrieb_id
from utils.styles import apply_custom_css
from utils.work_accounts import compute_work_account_snapshot

ABSENCE_TYPE_OPTIONS = ["urlaub", "krankheit", "unbezahlter_urlaub"]
ABSENCE_LABELS = {
    "urlaub": "Urlaub",
    "krankheit": "Krank",
    "unbezahlter_urlaub": "Unbezahlter Urlaub",
}
WEEKDAY_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _to_date(raw_value, fallback: date | None = None) -> date:
    if isinstance(raw_value, date):
        return raw_value
    raw = str(raw_value or "").strip()
    if len(raw) >= 10:
        try:
            return date.fromisoformat(raw[:10])
        except Exception:
            pass
    return fallback or date.today()


def _to_float(raw_value, default: float = 0.0) -> float:
    try:
        return float(raw_value if raw_value is not None else default)
    except Exception:
        return float(default)


def _base_public_url() -> str:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not base:
        return ""
    return f"{base}/storage/v1/object/public"


def _public_file_url(bucket: str, file_path: str | None) -> str | None:
    if not file_path:
        return None
    base = _base_public_url()
    if not base:
        return None
    return f"{base}/{bucket}/{file_path}"


def _safe_select_first(table, columns: str, *, filters: list[tuple[str, str, object]] | None = None) -> dict | None:
    try:
        q = table.select(columns).limit(1)
        for op, field, value in (filters or []):
            if op == "eq":
                q = q.eq(field, value)
            elif op == "gte":
                q = q.gte(field, value)
            elif op == "lte":
                q = q.lte(field, value)
        res = q.execute()
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def _load_current_mitarbeiter(user_id: int | None, betrieb_id: int | None) -> dict | None:
    if user_id is None:
        return None
    supabase = get_supabase_client()
    base = supabase.table("mitarbeiter")

    # 1) user_id-Spalte
    row = _safe_select_first(
        base,
        (
            "id,betrieb_id,vorname,nachname,personalnummer,email,telefon,"
            "strasse,plz,ort,geburtsdatum,eintrittsdatum,monatliche_soll_stunden,jahres_urlaubstage"
        ),
        filters=[("eq", "user_id", int(user_id))],
    )
    if row:
        return row

    # 2) Legacy-Zuordnung über users.username == mitarbeiter.personalnummer
    try:
        user_res = (
            supabase.table("users")
            .select("id,username,betrieb_id")
            .eq("id", int(user_id))
            .limit(1)
            .execute()
        )
        urow = (user_res.data or [None])[0]
        username = str((urow or {}).get("username") or "").strip()
        u_betrieb = (urow or {}).get("betrieb_id")
        if username:
            q = base.select(
                "id,betrieb_id,vorname,nachname,personalnummer,email,telefon,"
                "strasse,plz,ort,geburtsdatum,eintrittsdatum,monatliche_soll_stunden,jahres_urlaubstage"
            ).eq("personalnummer", username).limit(1)
            if u_betrieb is not None:
                q = q.eq("betrieb_id", u_betrieb)
            legacy_res = q.execute()
            legacy_rows = legacy_res.data or []
            if legacy_rows:
                return legacy_rows[0]
    except Exception:
        pass

    # 3) Letzter Fallback: nur bei genau einem Mitarbeiter im Betrieb
    if betrieb_id is not None:
        try:
            mres = (
                base.select(
                    "id,betrieb_id,vorname,nachname,personalnummer,email,telefon,"
                    "strasse,plz,ort,geburtsdatum,eintrittsdatum,monatliche_soll_stunden,jahres_urlaubstage"
                )
                .eq("betrieb_id", int(betrieb_id))
                .limit(2)
                .execute()
            )
            mrows = mres.data or []
            if len(mrows) == 1:
                return mrows[0]
        except Exception:
            pass

    return None


@st.cache_data(ttl=600, show_spinner=False)
def _load_personal_documents(mitarbeiter_id: int, betrieb_id: int | None) -> list[dict]:
    supabase = get_supabase_client()
    q = (
        supabase.table("mitarbeiter_dokumente")
        .select("id,name,typ,status,gueltig_bis,file_path,file_url,created_at")
        .eq("mitarbeiter_id", int(mitarbeiter_id))
        .order("created_at", desc=True)
        .limit(200)
    )
    if betrieb_id is not None:
        q = q.eq("betrieb_id", int(betrieb_id))
    try:
        return q.execute().data or []
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def _load_my_urlaubsantraege(mitarbeiter_id: int, betrieb_id: int | None) -> list[dict]:
    supabase = get_supabase_client()
    q = (
        supabase.table("urlaubsantraege")
        .select("id,von_datum,bis_datum,anzahl_tage,status,bemerkung_mitarbeiter,bemerkung_admin,beantragt_am")
        .eq("mitarbeiter_id", int(mitarbeiter_id))
        .order("beantragt_am", desc=True)
        .limit(300)
    )
    if betrieb_id is not None:
        q = q.eq("betrieb_id", int(betrieb_id))
    try:
        return q.execute().data or []
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def _load_my_absences(mitarbeiter_id: int, jahr: int, betrieb_id: int | None) -> list[dict]:
    supabase = get_supabase_client()
    start = date(int(jahr), 1, 1).isoformat()
    end = date(int(jahr), 12, 31).isoformat()
    q = (
        supabase.table("abwesenheiten")
        .select("id,typ,start_datum,ende_datum,status,stunden_gutschrift,grund,created_at")
        .eq("mitarbeiter_id", int(mitarbeiter_id))
        .lte("start_datum", end)
        .gte("ende_datum", start)
        .order("start_datum")
    )
    if betrieb_id is not None:
        q = q.eq("betrieb_id", int(betrieb_id))
    try:
        return q.execute().data or []
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def _load_my_dienstplaene_month(mitarbeiter_id: int, jahr: int, monat: int, betrieb_id: int | None) -> list[dict]:
    supabase = get_supabase_client()
    first = date(int(jahr), int(monat), 1)
    last = date(int(jahr), int(monat), 1) + timedelta(days=32)
    last = date(last.year, last.month, 1) - timedelta(days=1)

    def _fetch_from(table_name: str) -> list[dict]:
        select_variants = [
            "id,datum,schichttyp,start_zeit,ende_zeit,betrieb_id,status",
            "id,datum,schichttyp,start_zeit,ende_zeit,betrieb_id",
            "id,datum,schichttyp,start_zeit,ende_zeit",
        ]
        for cols in select_variants:
            try:
                q = (
                    supabase.table(table_name)
                    .select(cols)
                    .eq("mitarbeiter_id", int(mitarbeiter_id))
                    .gte("datum", first.isoformat())
                    .lte("datum", last.isoformat())
                    .order("datum")
                    .order("start_zeit")
                )
                if betrieb_id is not None:
                    q = q.eq("betrieb_id", int(betrieb_id))
                return q.execute().data or []
            except Exception:
                continue
        return []

    rows = _fetch_from("dienstplaene")
    if not rows:
        rows = _fetch_from("dienstplan")
    return rows


def _notify_admin_simple(
    *,
    betrieb_id: int | None,
    mitarbeiter_id: int,
    title: str,
    message: str,
    notif_type: str = "info",
    link: str | None = None,
) -> None:
    supabase = get_supabase_client()
    try:
        admin_users = supabase.table("users").select("id").eq("role", "admin").eq("is_active", True).execute().data or []
    except Exception:
        admin_users = []
    for admin in admin_users:
        try:
            payload = {
                "user_id": str(admin.get("id")),
                "titel": title,
                "nachricht": message,
                "typ": notif_type,
                "link": link or "/admin_dashboard",
                "gelesen": False,
            }
            if betrieb_id is not None:
                payload["betrieb_id"] = int(betrieb_id)
            supabase.table("benachrichtigungen").insert(payload).execute()
        except Exception:
            # Fallback auf altes Benachrichtigungs-Schema
            try:
                supabase.table("benachrichtigungen").insert(
                    {
                        "mitarbeiter_id": int(mitarbeiter_id),
                        "typ": notif_type,
                        "nachricht": f"{title}: {message}",
                        "gelesen": False,
                    }
                ).execute()
            except Exception:
                continue


def _store_dienstplanwunsch(
    *,
    mitarbeiter: dict,
    wunsch_datum: date,
    start_zeit: str,
    ende_zeit: str,
    grund: str,
) -> tuple[bool, str]:
    supabase = get_supabase_client()
    betrieb_id = require_betrieb_id()
    user_id = st.session_state.get("user_id")
    # Primär: dedizierte Wunsch-Tabelle (falls Migration aktiv)
    try:
        supabase.table("dienstplanwuensche").insert(
            {
                "betrieb_id": betrieb_id,
                "mitarbeiter_id": int(mitarbeiter["id"]),
                "user_id": int(user_id) if user_id is not None else None,
                "monat": int(wunsch_datum.month),
                "jahr": int(wunsch_datum.year),
                "wunsch_typ": "schichtzeit",
                "von_datum": wunsch_datum.isoformat(),
                "bis_datum": wunsch_datum.isoformat(),
                "details": f"{start_zeit}-{ende_zeit} | {str(grund or '').strip()}",
                "status": "offen",
            }
        ).execute()
        return True, "ok"
    except Exception:
        pass

    # Fallback: Änderungsanfragen
    payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": int(mitarbeiter["id"]),
        "feld": "dienstplanwunsch",
        "alter_wert": "",
        "neuer_wert": f"{wunsch_datum.isoformat()} {start_zeit}-{ende_zeit}",
        "grund": str(grund or "").strip(),
        "status": "offen",
        "user_id": str(user_id or ""),
    }
    try:
        supabase.table("aenderungsanfragen").insert(payload).execute()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _store_urlaubsantrag(
    *,
    mitarbeiter: dict,
    von: date,
    bis: date,
    bemerkung: str,
) -> tuple[bool, str]:
    if bis < von:
        return False, "Enddatum muss >= Startdatum sein."
    days = 0.0
    cur = von
    while cur <= bis:
        if cur.weekday() not in (0, 1):
            days += 1.0
        cur += timedelta(days=1)
    if days <= 0:
        return False, "Der gewählte Zeitraum enthält keine Arbeitstage."

    supabase = get_supabase_client()
    payload = {
        "betrieb_id": require_betrieb_id(),
        "mitarbeiter_id": int(mitarbeiter["id"]),
        "von_datum": von.isoformat(),
        "bis_datum": bis.isoformat(),
        "anzahl_tage": float(days),
        "status": "beantragt",
        "bemerkung_mitarbeiter": str(bemerkung or "").strip() or None,
    }
    try:
        supabase.table("urlaubsantraege").insert(payload).execute()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _store_personal_data_change_request(
    *,
    mitarbeiter: dict,
    field_name: str,
    old_value: str,
    new_value: str,
    reason: str,
) -> tuple[bool, str]:
    if not str(reason or "").strip():
        return False, "Bitte eine Begründung angeben."
    if str(new_value or "").strip() == str(old_value or "").strip():
        return False, "Neuer Wert entspricht dem aktuellen Wert."

    supabase = get_supabase_client()
    payload = {
        "betrieb_id": require_betrieb_id(),
        "mitarbeiter_id": int(mitarbeiter["id"]),
        "feld": field_name,
        "alter_wert": str(old_value or ""),
        "neuer_wert": str(new_value or ""),
        "grund": str(reason or "").strip(),
        "status": "offen",
        "user_id": str(st.session_state.get("user_id") or ""),
    }
    try:
        supabase.table("aenderungsanfragen").insert(payload).execute()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _build_urlaub_jahrespdf(mitarbeiter: dict, jahr: int, absences: list[dict], approved_requests: list[dict]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    rows = [["Von", "Bis", "Typ", "Status", "Tage"]]
    total_days = 0.0

    absence_ranges: set[tuple[str, str]] = set()
    for a in absences:
        typ = str(a.get("typ") or "").lower()
        if typ != "urlaub":
            continue
        v = str(a.get("start_datum") or "")[:10]
        b = str(a.get("ende_datum") or "")[:10]
        absence_ranges.add((v, b))
        tage = 0.0
        try:
            start = date.fromisoformat(v)
            end = date.fromisoformat(b)
            cur = start
            while cur <= end:
                if cur.weekday() not in (0, 1):
                    tage += 1.0
                cur += timedelta(days=1)
        except Exception:
            tage = 0.0
        total_days += tage
        rows.append([v, b, "Urlaub", str(a.get("status") or "genehmigt"), f"{tage:.1f}"])

    for r in approved_requests:
        v = str(r.get("von_datum") or "")[:10]
        b = str(r.get("bis_datum") or "")[:10]
        if (v, b) in absence_ranges:
            continue
        tage = _to_float(r.get("anzahl_tage"), 0.0)
        total_days += tage
        rows.append([v, b, "Urlaubsantrag", str(r.get("status") or "genehmigt"), f"{tage:.1f}"])

    if len(rows) == 1:
        rows.append(["-", "-", "Keine Einträge", "-", "0.0"])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"{BRAND_APP_NAME} – Jahresübersicht Urlaub {int(jahr)}", styles["Title"]),
        Spacer(1, 0.4 * cm),
        Paragraph(
            f"Mitarbeiter: {mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}",
            styles["Normal"],
        ),
        Spacer(1, 0.3 * cm),
    ]
    table = Table(rows, colWidths=[3.2 * cm, 3.2 * cm, 4.0 * cm, 3.0 * cm, 2.2 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"Summe Urlaubstage im Jahr: {total_days:.1f}", styles["Heading3"]))
    doc.build(story)
    return buffer.getvalue()


def _render_requests_tab(mitarbeiter: dict) -> None:
    st.markdown("### Anträge und Wünsche")
    left, right = st.columns(2)

    with left:
        with st.expander("Dienstplanwunsch an Admin senden", expanded=True):
            d = st.date_input("Datum", value=date.today(), format="DD.MM.YYYY", key="mdp_wunsch_datum")
            c1, c2 = st.columns(2)
            with c1:
                start = st.text_input("Start (HH:MM)", value="16:00", key="mdp_wunsch_start")
            with c2:
                end = st.text_input("Ende (HH:MM)", value="22:00", key="mdp_wunsch_ende")
            reason = st.text_area("Begründung", key="mdp_wunsch_reason")
            if st.button("Dienstplanwunsch senden", use_container_width=True, key="mdp_wunsch_send"):
                ok, msg = _store_dienstplanwunsch(
                    mitarbeiter=mitarbeiter,
                    wunsch_datum=d,
                    start_zeit=start.strip(),
                    ende_zeit=end.strip(),
                    grund=reason,
                )
                if ok:
                    _notify_admin_simple(
                        betrieb_id=mitarbeiter.get("betrieb_id"),
                        mitarbeiter_id=int(mitarbeiter["id"]),
                        title="Neuer Dienstplanwunsch",
                        message=(
                            f"{mitarbeiter.get('vorname','')} {mitarbeiter.get('nachname','')}: "
                            f"{d.isoformat()} {start}-{end}"
                        ),
                        notif_type="info",
                        link="/admin_dashboard",
                    )
                    st.success("Dienstplanwunsch wurde an den Admin übertragen.")
                else:
                    st.error(f"Senden fehlgeschlagen: {msg}")

    with right:
        with st.expander("Urlaubsantrag an Admin stellen", expanded=True):
            v = st.date_input("Von", value=date.today(), format="DD.MM.YYYY", key="mua_von")
            b = st.date_input("Bis", value=date.today(), format="DD.MM.YYYY", key="mua_bis")
            remark = st.text_area("Bemerkung", key="mua_remark")
            if st.button("Urlaubsantrag senden", type="primary", use_container_width=True, key="mua_send"):
                ok, msg = _store_urlaubsantrag(mitarbeiter=mitarbeiter, von=v, bis=b, bemerkung=remark)
                if ok:
                    _notify_admin_simple(
                        betrieb_id=mitarbeiter.get("betrieb_id"),
                        mitarbeiter_id=int(mitarbeiter["id"]),
                        title="Neuer Urlaubsantrag",
                        message=(
                            f"{mitarbeiter.get('vorname','')} {mitarbeiter.get('nachname','')}: "
                            f"{v.isoformat()} bis {b.isoformat()}"
                        ),
                        notif_type="warning",
                        link="/admin_dashboard",
                    )
                    st.success("Urlaubsantrag wurde an den Admin gesendet.")
                else:
                    st.error(f"Senden fehlgeschlagen: {msg}")

    rows = _load_my_urlaubsantraege(int(mitarbeiter["id"]), mitarbeiter.get("betrieb_id"))
    if rows:
        st.markdown("#### Meine Urlaubsanträge")
        st.dataframe(
            [
                {
                    "Von": r.get("von_datum"),
                    "Bis": r.get("bis_datum"),
                    "Tage": _to_float(r.get("anzahl_tage"), 0.0),
                    "Status": r.get("status"),
                    "Bemerkung MA": r.get("bemerkung_mitarbeiter"),
                    "Bemerkung Admin": r.get("bemerkung_admin"),
                    "Beantragt am": r.get("beantragt_am"),
                }
                for r in rows
            ],
            use_container_width=True,
            hide_index=True,
        )


def _render_urlaubsuebersicht_tab(mitarbeiter: dict) -> None:
    st.markdown("### Jahresübersicht Urlaub")
    jahr = st.number_input("Jahr", min_value=2024, max_value=2100, value=date.today().year, step=1, key="mur_jahr")
    absences = _load_my_absences(int(mitarbeiter["id"]), int(jahr), mitarbeiter.get("betrieb_id"))
    requests = _load_my_urlaubsantraege(int(mitarbeiter["id"]), mitarbeiter.get("betrieb_id"))
    requests_approved_year = [
        r
        for r in requests
        if str(r.get("status") or "").lower() == "genehmigt" and str(r.get("von_datum") or "").startswith(str(int(jahr)))
    ]

    used = 0.0
    absence_ranges: set[tuple[str, str]] = set()
    for a in absences:
        if str(a.get("typ") or "").lower() != "urlaub":
            continue
        s = _to_date(a.get("start_datum"))
        e = _to_date(a.get("ende_datum"), fallback=s)
        absence_ranges.add((str(a.get("start_datum") or "")[:10], str(a.get("ende_datum") or "")[:10]))
        cur = s
        while cur <= e:
            if cur.weekday() not in (0, 1):
                used += 1.0
            cur += timedelta(days=1)
    for r in requests_approved_year:
        key = (str(r.get("von_datum") or "")[:10], str(r.get("bis_datum") or "")[:10])
        if key in absence_ranges:
            continue
        used += _to_float(r.get("anzahl_tage"), 0.0)

    annual_target = _to_float(mitarbeiter.get("jahres_urlaubstage"), 28.0)
    remaining = max(0.0, annual_target - used)
    c1, c2, c3 = st.columns(3)
    c1.metric("Urlaubstage/Jahr", f"{annual_target:.1f}")
    c2.metric("Genommen", f"{used:.1f}")
    c3.metric("Verfügbar", f"{remaining:.1f}")

    pdf = _build_urlaub_jahrespdf(mitarbeiter, int(jahr), absences, requests_approved_year)
    st.download_button(
        "Jahresübersicht Urlaub als PDF herunterladen",
        data=pdf,
        file_name=f"Urlaubsuebersicht_{mitarbeiter.get('nachname','Mitarbeiter')}_{int(jahr)}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="mur_download_pdf",
    )


def _render_dienstplan_tab(mitarbeiter: dict) -> None:
    st.markdown("### Meine Monatsdienstpläne")
    col1, col2 = st.columns(2)
    with col1:
        jahr = st.number_input("Jahr", min_value=2024, max_value=2100, value=date.today().year, step=1, key="md_jahr")
    with col2:
        monat = st.number_input("Monat", min_value=1, max_value=12, value=date.today().month, step=1, key="md_monat")

    dienste = _load_my_dienstplaene_month(
        int(mitarbeiter["id"]),
        int(jahr),
        int(monat),
        mitarbeiter.get("betrieb_id"),
    )
    if not dienste:
        try:
            supabase = get_supabase_client()
            pdf_rel = (
                supabase.table("dienstplan_pdf_freigaben")
                .select("titel,file_path,file_url,erstellt_am")
                .eq("mitarbeiter_id", int(mitarbeiter["id"]))
                .eq("monat", int(monat))
                .eq("jahr", int(jahr))
                .limit(1)
                .execute()
            )
            pdf_row = (pdf_rel.data or [None])[0]
        except Exception:
            pdf_row = None
        if not pdf_row:
            st.info("Für den gewählten Monat sind noch keine Dienste veröffentlicht.")
            return
        ext_url = pdf_row.get("file_url") or _public_file_url("dokumente", pdf_row.get("file_path"))
        if ext_url:
            st.success("Für diesen Monat liegt ein veröffentlichter Dienstplan vor.")
            st.link_button(
                "Veröffentlichten Monatsdienstplan herunterladen",
                ext_url,
                use_container_width=True,
            )
        else:
            st.warning("Dienstplan-Freigabe gefunden, aber kein Download-Link hinterlegt.")
        return

    status_values = {str(d.get("status") or "").strip().lower() for d in dienste if d.get("status") is not None}
    if status_values:
        published = {"veroeffentlicht", "veröffentlicht", "fertig", "abgeschlossen", "final", "published"}
        dienste = [d for d in dienste if str(d.get("status") or "").strip().lower() in published]
        if not dienste:
            st.info("Für diesen Monat gibt es zwar Planstände, aber noch keine veröffentlichte Freigabe.")
            return
    else:
        st.caption("Hinweis: Diese Instanz nutzt kein Veröffentlichungs-Statusfeld im Dienstplan. Es werden alle Monatseinträge angezeigt.")

    summary = summarize_employee_month(year=int(jahr), month=int(monat), entries=dienste)
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Geplant", summary.geplant)
    s2.metric("Urlaub", summary.urlaub)
    s3.metric("Frei", summary.frei)
    s4.metric("Krank", summary.krank)

    st.dataframe(
        [
            {
                "Datum": str(d.get("datum") or "")[:10],
                "Tag": WEEKDAY_SHORT[_to_date(d.get("datum")).weekday()],
                "Typ": str(d.get("schichttyp") or "arbeit").capitalize(),
                "Von": str(d.get("start_zeit") or "")[:5],
                "Bis": str(d.get("ende_zeit") or "")[:5],
            }
            for d in dienste
        ],
        use_container_width=True,
        hide_index=True,
    )

    pdf = erstelle_dienstplan_pdf(mitarbeiter, dienste, int(jahr), int(monat))
    st.download_button(
        "Monatsdienstplan (nur meine Dienste) als PDF",
        data=pdf,
        file_name=f"Dienstplan_{mitarbeiter.get('nachname','Mitarbeiter')}_{int(jahr)}_{int(monat):02d}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="md_download_pdf",
    )


def _render_data_changes_tab(mitarbeiter: dict) -> None:
    st.markdown("### Persönliche Daten – Änderungsantrag")
    field_map = {
        "Straße": "strasse",
        "PLZ": "plz",
        "Ort": "ort",
        "Telefon": "telefon",
        "E-Mail": "email",
    }
    label = st.selectbox("Feld", list(field_map.keys()), key="mchange_field")
    key = field_map[label]
    old_value = str(mitarbeiter.get(key) or "")
    st.caption(f"Aktueller Wert: {old_value or '-'}")
    new_value = st.text_input("Neuer Wert", value="", key="mchange_new_value")
    reason = st.text_area("Begründung *", key="mchange_reason")
    if st.button("Änderung beim Admin beantragen", use_container_width=True, key="mchange_send"):
        ok, msg = _store_personal_data_change_request(
            mitarbeiter=mitarbeiter,
            field_name=key,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
        if ok:
            _notify_admin_simple(
                betrieb_id=mitarbeiter.get("betrieb_id"),
                mitarbeiter_id=int(mitarbeiter["id"]),
                title="Stammdaten-Änderung beantragt",
                message=(
                    f"{mitarbeiter.get('vorname','')} {mitarbeiter.get('nachname','')}: "
                    f"{label} → {new_value}"
                ),
                notif_type="warning",
                link="/admin_dashboard",
            )
            st.success("Änderungsantrag wurde an den Admin gesendet.")
        else:
            st.error(f"Antrag fehlgeschlagen: {msg}")


def _render_documents_tab(mitarbeiter: dict) -> None:
    st.markdown("### Persönliche Unterlagen")
    p1, p2, p3 = st.columns(3)
    p1.text_input("Name", value=f"{mitarbeiter.get('vorname','')} {mitarbeiter.get('nachname','')}".strip(), disabled=True)
    p2.text_input("Adresse", value=f"{mitarbeiter.get('strasse','')} | {mitarbeiter.get('plz','')} {mitarbeiter.get('ort','')}".strip(), disabled=True)
    p3.text_input("Eintritt", value=str(mitarbeiter.get("eintrittsdatum") or ""), disabled=True)
    docs = _load_personal_documents(int(mitarbeiter["id"]), mitarbeiter.get("betrieb_id"))
    if not docs:
        st.info("Keine Dokumente vorhanden.")
        return
    for d in docs:
        raw_type = str(d.get("typ") or "").strip().lower()
        bucket = "dokumente"
        if raw_type in {"lohnzettel", "lohnabrechnung"}:
            bucket = "lohnabrechnungen"
        url = d.get("file_url") or _public_file_url(bucket, d.get("file_path"))
        c1, c2, c3, c4, c5 = st.columns([2.2, 1.2, 1.1, 1.5, 1.2])
        c1.write(f"**{d.get('name') or '-'}**")
        c2.write(str(d.get("typ") or "-"))
        c3.write(str(d.get("status") or "-"))
        c4.write(str(d.get("gueltig_bis") or "-"))
        if url:
            c5.link_button("PDF öffnen", url, use_container_width=True)
        else:
            c5.caption("Kein Link")

    st.markdown("---")
    st.markdown("#### Persönliche Daten – Änderungsantrag")
    _render_data_changes_tab(mitarbeiter)


def _render_zeitkonto_tab(mitarbeiter: dict) -> None:
    st.markdown("### Arbeitszeitkonto")
    today = date.today()
    try:
        snap = compute_work_account_snapshot(
            get_supabase_client(),
            mitarbeiter_id=int(mitarbeiter["id"]),
            monat=int(today.month),
            jahr=int(today.year),
        )
        soll = float(snap.soll_stunden or 0.0)
        ist = float(snap.ist_stunden or 0.0)
        saldo = float(snap.ueberstunden_saldo or 0.0)
        urlaub_genommen = float(snap.urlaubstage_genommen or 0.0)
        urlaub_gesamt = float(snap.urlaubstage_gesamt or 0.0)
    except Exception:
        supabase = get_supabase_client()
        acc = (
            supabase.table("arbeitszeit_konten")
            .select("soll_stunden,ist_stunden,ueberstunden_saldo,urlaubstage_genommen,urlaubstage_gesamt")
            .eq("mitarbeiter_id", int(mitarbeiter["id"]))
            .limit(1)
            .execute()
        )
        row = (acc.data or [{}])[0]
        soll = _to_float(row.get("soll_stunden"), 0.0)
        ist = _to_float(row.get("ist_stunden"), 0.0)
        saldo = _to_float(row.get("ueberstunden_saldo"), 0.0)
        urlaub_genommen = _to_float(row.get("urlaubstage_genommen"), 0.0)
        urlaub_gesamt = _to_float(row.get("urlaubstage_gesamt"), _to_float(mitarbeiter.get("jahres_urlaubstage"), 28.0))

    urlaub_verfuegbar = max(0.0, urlaub_gesamt - urlaub_genommen)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Soll-Stunden", f"{soll:.2f} h")
    c2.metric("Ist-Stunden", f"{ist:.2f} h")
    c3.metric("Saldo (laufend)", f"{saldo:+.2f} h")
    c4.metric("Urlaub genommen", f"{urlaub_genommen:.1f} Tg")
    c5.metric("Urlaub verfügbar", f"{urlaub_verfuegbar:.1f} Tg")


def show_mitarbeiter_dashboard() -> None:
    apply_custom_css()

    if not st.session_state.get("logged_in"):
        st.error("Bitte zuerst einloggen.")
        return
    if str(st.session_state.get("role") or "") != "mitarbeiter":
        st.error("Dieser Bereich ist nur für Mitarbeiter verfügbar.")
        return

    user_id = st.session_state.get("user_id")
    betrieb_id = st.session_state.get("betrieb_id")
    mitarbeiter = _load_current_mitarbeiter(user_id, betrieb_id)
    if not mitarbeiter:
        st.error("Mitarbeiterprofil konnte nicht geladen werden. Bitte Admin informieren.")
        return

    st.markdown("<div class='complio-topbar'>", unsafe_allow_html=True)
    top_l, top_r = st.columns([1.2, 5], vertical_alignment="center")
    with top_l:
        with st.container(key="header_logo"):
            st.image(BRAND_LOGO_IMAGE, width=210)
    with top_r:
        st.markdown(
            f"### Willkommen {mitarbeiter.get('vorname', '')} {mitarbeiter.get('nachname', '')}",
            unsafe_allow_html=False,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    tabs = st.tabs(
        [
            "Anträge & Wünsche",
            "Urlaubsjahresübersicht",
            "Monatsdienstpläne",
            "Persönliche Unterlagen",
            "Daten ändern beantragen",
            "Arbeitszeitkonto",
        ]
    )
    with tabs[0]:
        _render_requests_tab(mitarbeiter)
    with tabs[1]:
        _render_urlaubsuebersicht_tab(mitarbeiter)
    with tabs[2]:
        _render_dienstplan_tab(mitarbeiter)
    with tabs[3]:
        _render_documents_tab(mitarbeiter)
    with tabs[4]:
        _render_data_changes_tab(mitarbeiter)
    with tabs[5]:
        _render_zeitkonto_tab(mitarbeiter)
