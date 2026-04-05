from __future__ import annotations

from datetime import date

import streamlit as st

from utils.contract_pdf_generator import (
    ContractData,
    as_download_filename,
    generate_contract_pdf,
    preview_pdf_html,
)
from utils.database import get_supabase_client


MITARBEITER_SELECT_COLUMNS = (
    "id, betrieb_id, vorname, nachname, personalnummer, "
    "strasse, plz, ort, geburtsdatum, eintrittsdatum, "
    "monatliche_soll_stunden, monatliche_brutto_verguetung, jahres_urlaubstage"
)


def _safe_text(value: object) -> str:
    return str(value or "").strip()


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


def _to_date(value: object, fallback: date | None = None) -> date:
    if isinstance(value, date):
        return value
    raw = _safe_text(value)
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        try:
            return date.fromisoformat(raw[:10])
        except Exception:
            pass
    if len(raw) >= 10 and raw[2] == "." and raw[5] == ".":
        try:
            d = int(raw[0:2])
            m = int(raw[3:5])
            y = int(raw[6:10])
            return date(y, m, d)
        except Exception:
            pass
    return fallback or date.today()


@st.cache_data(ttl=600, show_spinner=False)
def _load_mitarbeiter_for_contracts(betrieb_id: int | None):
    supabase = get_supabase_client()
    q = supabase.table("mitarbeiter").select(MITARBEITER_SELECT_COLUMNS).order("nachname")
    if betrieb_id is not None:
        q = q.eq("betrieb_id", betrieb_id)
    res = q.execute()
    return res.data or []


def _resolve_logo_path() -> str:
    root = st.session_state.get("_workspace_root", "/workspace")
    candidates = [
        f"{root}/assets/Piccolo Logo.jpeg",
        f"{root}/assets/Piccolo Logo.jpg",
        f"{root}/assets/piccolo_logo.jpeg",
        f"{root}/assets/piccolo_logo.jpg",
    ]
    for path in candidates:
        try:
            with open(path, "rb"):
                return path
        except Exception:
            continue
    return ""


def _build_prefill(ma: dict) -> ContractData:
    first_name = _safe_text(ma.get("vorname"))
    last_name = _safe_text(ma.get("nachname"))
    full_name = f"{first_name} {last_name}".strip()
    street = _safe_text(ma.get("strasse"))
    plz = _safe_text(ma.get("plz"))
    city = _safe_text(ma.get("ort"))
    city_line = f"{plz} {city}".strip()

    today = date.today()
    start_date = _to_date(ma.get("eintrittsdatum"), fallback=today)
    monthly_hours = _safe_float(ma.get("monatliche_soll_stunden"), 130.0)
    monthly_gross = _safe_float(ma.get("monatliche_brutto_verguetung"), 0.0)
    if monthly_gross <= 0:
        monthly_gross = round(monthly_hours * 15.0, 2)
    annual_vacation = _safe_float(ma.get("jahres_urlaubstage"), 20.0)

    return ContractData(
        contract_title="Änderungsvertrag",
        prior_contract_date_text="15. Oktober 2025",
        employer_name="Steakhouse Piccolo",
        employer_represented_by="Silvana Lasinski",
        employer_street="Gustav-Adolf-Straße 17",
        employer_city_line="04105 Leipzig",
        employee_name=full_name,
        employee_birth_date=_to_date(ma.get("geburtsdatum"), fallback=today),
        employee_street=street,
        employee_city_line=city_line,
        employment_start_date=start_date,
        amendment_effective_date=start_date,
        monthly_target_hours=monthly_hours,
        monthly_gross_salary=monthly_gross,
        annual_vacation_days=annual_vacation,
        additional_agreements="",
        logo_path=_resolve_logo_path(),
    )


@st.fragment
def _render_form(prefill: ContractData) -> ContractData:
    st.markdown("### Mitarbeiter-Sync")
    st.caption("Name, Anschrift und Geburtsdatum werden automatisch aus der Datenbank vorgeladen und können angepasst werden.")
    st.markdown("#### Arbeitnehmer-Daten")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        employee_name = st.text_input("Name", value=prefill.employee_name, key="v4_employee_name")
        employee_birth_date = st.date_input(
            "Geburtsdatum",
            value=_to_date(prefill.employee_birth_date),
            format="DD.MM.YYYY",
            key="v4_birth_date",
        )
    with c2:
        employee_street = st.text_input("Straße", value=prefill.employee_street, key="v4_employee_street")
        employee_city_line = st.text_input(
            "PLZ / Ort",
            value=prefill.employee_city_line,
            key="v4_employee_city",
            placeholder="z. B. 04105 Leipzig",
        )
    st.markdown("#### Vertragsdetails")
    d1, d2, d3 = st.columns(3, gap="large")
    with d1:
        prior_contract_date_text = st.text_input(
            "Datum ursprünglicher Arbeitsvertrag",
            value=prefill.prior_contract_date_text,
            key="v4_prior_contract_date_text",
            help="Default: 15. Oktober 2025",
        )
        amendment_effective_date = st.date_input(
            "Inkrafttreten der Änderung",
            value=_to_date(prefill.amendment_effective_date),
            format="DD.MM.YYYY",
            key="v4_effective_date",
        )
    with d2:
        monthly_target_hours = st.number_input(
            "Monatliche Sollarbeitszeit (h)",
            min_value=0.0,
            value=float(prefill.monthly_target_hours),
            step=0.5,
            format="%.2f",
            key="v4_monthly_hours",
        )
        monthly_gross_salary = st.number_input(
            "Monatliche Brutto-Vergütung (€)",
            min_value=0.0,
            value=float(prefill.monthly_gross_salary),
            step=50.0,
            format="%.2f",
            key="v4_monthly_gross",
        )
    with d3:
        annual_vacation_days = st.number_input(
            "Urlaubsanspruch (Tage/Jahr)",
            min_value=0.0,
            value=float(prefill.annual_vacation_days),
            step=0.5,
            format="%.1f",
            key="v4_vacation_days",
        )
        employment_start_date = st.date_input(
            "Eintrittsdatum",
            value=_to_date(prefill.employment_start_date),
            format="DD.MM.YYYY",
            key="v4_start_employment",
        )

    additional_agreements = st.text_area(
        "Sonstige Vereinbarungen (§ 8)",
        value=prefill.additional_agreements,
        key="v4_additional_agreements",
        height=130,
        placeholder="Freitext für individuelle Vereinbarungen...",
    )
    return ContractData(
        contract_title="Änderungsvertrag",
        prior_contract_date_text=prior_contract_date_text,
        employer_name=prefill.employer_name,
        employer_represented_by=prefill.employer_represented_by,
        employer_street=prefill.employer_street,
        employer_city_line=prefill.employer_city_line,
        employee_name=employee_name,
        employee_birth_date=employee_birth_date,
        employee_street=employee_street,
        employee_city_line=employee_city_line,
        employment_start_date=employment_start_date,
        amendment_effective_date=amendment_effective_date,
        monthly_target_hours=float(monthly_target_hours),
        monthly_gross_salary=float(monthly_gross_salary),
        annual_vacation_days=float(annual_vacation_days),
        additional_agreements=additional_agreements,
        employer_signatory="Silvana Lasinski",
        signing_city="Leipzig",
        signing_date=date.today(),
        logo_path=prefill.logo_path,
    )


def _try_embed_pdf(pdf_bytes: bytes) -> None:
    try:
        st.components.v1.html(preview_pdf_html(pdf_bytes), height=980, scrolling=True)
    except Exception:
        st.info("PDF-Vorschau konnte nicht eingebettet werden. Bitte Download verwenden.")


def show_vertraege_page() -> None:
    st.subheader("Verträge")
    st.caption("Rechtssicheres Änderungsvertrags-Modul mit Vorschau und Download.")

    betrieb_id = st.session_state.get("betrieb_id")
    ma_list = _load_mitarbeiter_for_contracts(betrieb_id)
    if not ma_list:
        st.info("Keine Mitarbeiter gefunden.")
        return

    options = {
        f"{_safe_text(m.get('vorname'))} {_safe_text(m.get('nachname'))} ({_safe_text(m.get('personalnummer') or '-')})": m
        for m in ma_list
    }
    selected_label = st.selectbox("Mitarbeiter auswählen", list(options.keys()), key="v4_selected_mitarbeiter")
    selected_employee = options[selected_label]

    prefill = _build_prefill(selected_employee)
    contract_data = _render_form(prefill)

    if st.button("PDF erzeugen", type="primary", use_container_width=True, key="v4_generate_pdf_btn"):
        try:
            pdf_bytes = generate_contract_pdf(contract_data)
            st.session_state["v4_contract_pdf"] = pdf_bytes
            st.success("Vertrag-PDF wurde erzeugt.")
        except Exception as exc:
            st.error(f"PDF-Erzeugung fehlgeschlagen: {exc}")
            return

    pdf_bytes = st.session_state.get("v4_contract_pdf")
    if pdf_bytes:
        st.markdown("### PDF-Vorschau")
        _try_embed_pdf(pdf_bytes)
        st.download_button(
            label="Vertrag herunterladen",
            data=pdf_bytes,
            file_name=as_download_filename(contract_data.employee_name, contract_data.amendment_effective_date),
            mime="application/pdf",
            use_container_width=True,
            key="v4_contract_pdf_download",
        )
