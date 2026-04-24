"""
Complio Vertragssystem - UI
Formulare zum Erstellen von Arbeitsverträgen.
"""
import streamlit as st
from datetime import datetime, date, timedelta
import re
from modules.vertraege.inhalte import VERTRAGSTYPEN
from utils.database import get_supabase_client
from utils.date_utils import add_months
from utils.session import require_betrieb_id


PROBEZEIT_OPTIONEN = [0, 1, 2, 3, 6]


def _probezeit_label(months: int) -> str:
    return "Keine" if months == 0 else f"{months} Monat{'e' if months > 1 else ''}"


def _render_probezeit_select(label: str = "Probezeit", default_index: int = 4, key_suffix: str = "") -> int:
    return st.selectbox(
        label,
        PROBEZEIT_OPTIONEN,
        index=default_index,
        format_func=_probezeit_label,
        key=f"probezeit_{key_suffix}" if key_suffix else None,
    )


def _render_auszahlung_block(
    default_urlaub: int,
    default_auszahlung_tag: int = 15,
    *,
    with_abschlag: bool = True,
) -> dict:
    """
    Rendert Standardblock Urlaub + Auszahlungstag (+ optional Abschlag).
    Gibt die erfassten Werte als Dict zurück.
    """
    col_a, col_b = st.columns(2)
    with col_a:
        urlaubstage = st.number_input(
            "Urlaubstage/Jahr",
            min_value=20, max_value=30,
            value=int(default_urlaub),
        )
    with col_b:
        auszahlung_tag = st.number_input(
            "Auszahlung zum Tag",
            min_value=1, max_value=28,
            value=int(default_auszahlung_tag),
        )

    abschlag = 0
    abschlag_tag = 3
    if with_abschlag:
        abschlag = st.number_input(
            "Abschlagszahlung netto (€, 0 = keine)",
            min_value=0, value=0,
        )
        if abschlag > 0:
            abschlag_tag = st.number_input(
                "Abschlag-Auszahlung zum Werktag",
                min_value=1, max_value=5, value=3,
            )

    return {
        "urlaubstage": int(urlaubstage),
        "auszahlung_tag": int(auszahlung_tag),
        "abschlag": int(abschlag),
        "abschlag_tag": int(abschlag_tag),
    }


def _build_arbeitnehmer_filename(arbeitnehmer: dict, vertragstyp: str) -> str:
    name_safe = f"{arbeitnehmer.get('nachname', '')}_{arbeitnehmer.get('vorname', '')}".strip("_").replace(" ", "_")
    datum_str = datetime.now().strftime("%Y%m%d")
    titel = VERTRAGSTYPEN[vertragstyp]["name"].replace(" ", "_")
    return f"{titel}_{name_safe or 'Mitarbeiter'}_{datum_str}.pdf"


PROBEZEIT_OPTIONEN = [0, 1, 2, 3, 6]


def _add_months(d: date, months: int) -> date:
    """Addiert 'months' Monate kalendergenau (inklusive Monatslängen)."""
    if not months:
        return d
    total_month = (d.month - 1) + int(months)
    year = d.year + total_month // 12
    month = total_month % 12 + 1
    import calendar
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _probezeit_label(months: int) -> str:
    return "Keine" if months == 0 else f"{months} Monat{'e' if months > 1 else ''}"


def _render_probezeit_select(label: str = "Probezeit", default_index: int = 4, key_suffix: str = "") -> int:
    return st.selectbox(
        label,
        PROBEZEIT_OPTIONEN,
        index=default_index,
        format_func=_probezeit_label,
        key=f"probezeit_{key_suffix}" if key_suffix else None,
    )


def _render_auszahlung_block(
    default_urlaub: int,
    default_auszahlung_tag: int = 15,
    *,
    with_abschlag: bool = True,
) -> dict:
    """
    Rendert Standardblock Urlaub + Auszahlungstag (+ optional Abschlag).
    Gibt die erfassten Werte als Dict zurück.
    """
    col_a, col_b = st.columns(2)
    with col_a:
        urlaubstage = st.number_input(
            "Urlaubstage/Jahr",
            min_value=20, max_value=30,
            value=int(default_urlaub),
        )
    with col_b:
        auszahlung_tag = st.number_input(
            "Auszahlung zum Tag",
            min_value=1, max_value=28,
            value=int(default_auszahlung_tag),
        )

    abschlag = 0
    abschlag_tag = 3
    if with_abschlag:
        abschlag = st.number_input(
            "Abschlagszahlung netto (€, 0 = keine)",
            min_value=0, value=0,
        )
        if abschlag > 0:
            abschlag_tag = st.number_input(
                "Abschlag-Auszahlung zum Werktag",
                min_value=1, max_value=5, value=3,
            )

    return {
        "urlaubstage": int(urlaubstage),
        "auszahlung_tag": int(auszahlung_tag),
        "abschlag": int(abschlag),
        "abschlag_tag": int(abschlag_tag),
    }


def _build_arbeitnehmer_filename(arbeitnehmer: dict, vertragstyp: str) -> str:
    name_safe = f"{arbeitnehmer.get('nachname', '')}_{arbeitnehmer.get('vorname', '')}".strip("_").replace(" ", "_")
    datum_str = datetime.now().strftime("%Y%m%d")
    titel = VERTRAGSTYPEN[vertragstyp]["name"].replace(" ", "_")
    return f"{titel}_{name_safe or 'Mitarbeiter'}_{datum_str}.pdf"


def _get_supabase():
    """Liefert einen gültigen Supabase-Client (Session oder Fallback)."""
    supabase = st.session_state.get("supabase")
    if supabase is not None:
        return supabase
    try:
        supabase = get_supabase_client()
        st.session_state["supabase"] = supabase
        return supabase
    except Exception:
        return None


def _extract_missing_column(exc: Exception) -> str:
    """Extrahiert fehlenden Spaltennamen aus PostgREST-Fehlermeldungen."""
    msg = str(exc or "")
    m = re.search(r'column\s+([a-zA-Z0-9_\."]+)\s+does not exist', msg, flags=re.IGNORECASE)
    if not m:
        return ""
    col = str(m.group(1) or "").strip().strip('"')
    return col.split(".")[-1] if col else ""


def _load_archiv_rows_robust(supabase, betrieb_id: int) -> list[dict]:
    """
    Lädt Vertragsarchiv robust über unterschiedliche DB-Schemas.
    Entfernt unbekannte Spalten automatisch aus SELECT und sortiert über
    das beste verfügbare Datumsfeld.
    """
    select_columns = [
        "id",
        "vertragstyp",
        "vertragsdaten",
        "erstellt_am",
        "created_at",
        "gueltig_ab",
        "gueltig_bis",
        "wochenstunden",
        "soll_stunden_monat",
        "urlaubstage_jahr",
        "monatsbrutto_verguetung",
        "mitarbeiter_id",
    ]
    # Mehrere Versuche: bei "column ... does not exist" Spalte entfernen.
    for _ in range(len(select_columns) + 2):
        try:
            select_expr = ", ".join(select_columns) if select_columns else "id"
            q = supabase.table("vertraege").select(select_expr).eq("betrieb_id", int(betrieb_id))
            if "erstellt_am" in select_columns:
                q = q.order("erstellt_am", desc=True)
            elif "created_at" in select_columns:
                q = q.order("created_at", desc=True)
            elif "gueltig_ab" in select_columns:
                q = q.order("gueltig_ab", desc=True)
            return q.execute().data or []
        except Exception as exc:
            missing_col = _extract_missing_column(exc)
            if missing_col and missing_col in select_columns:
                select_columns = [c for c in select_columns if c != missing_col]
                continue
            raise
    return []


def show_vertraege():
    """Hauptansicht: Verträge-Modul."""
    st.markdown("## 📝 Verträge")
    st.caption(
        "Erstelle rechtssichere Arbeitsverträge nach aktuellem Rechtsstand 2026. "
        "Alle Verträge entsprechen BGB, NachwG, MiLoG und BUrlG."
    )

    # Tabs: Neuer Vertrag / Betriebsdaten / Archiv
    tab1, tab2, tab3 = st.tabs([
        "➕ Neuer Vertrag",
        "⚙️ Betriebsdaten & Logo",
        "📚 Vertragsarchiv"
    ])

    with tab1:
        _show_neuer_vertrag()

    with tab2:
        _show_betriebsdaten()

    with tab3:
        _show_archiv()


def _show_neuer_vertrag():
    """Erstellen eines neuen Vertrags."""
    supabase = _get_supabase()
    betrieb_id = require_betrieb_id()
    if supabase is None:
        st.error("Datenbankverbindung konnte nicht hergestellt werden.")
        return

    # Schritt 1: Vertragstyp wählen
    st.markdown("### 1. Vertragstyp wählen")

    cols = st.columns(len(VERTRAGSTYPEN))
    for i, (key, data) in enumerate(VERTRAGSTYPEN.items()):
        with cols[i]:
            is_active = st.session_state.get("vertrag_typ") == key
            btn_type = "primary" if is_active else "secondary"
            if st.button(
                data["name"],
                key=f"typ_{key}",
                use_container_width=True,
                type=btn_type
            ):
                st.session_state["vertrag_typ"] = key
                st.rerun()
            st.caption(data["beschreibung"])

    vertrag_typ = st.session_state.get("vertrag_typ")
    if not vertrag_typ:
        st.info("Wähle einen Vertragstyp um zu beginnen.")
        return

    st.markdown("---")
    st.markdown(f"### 2. Daten für **{VERTRAGSTYPEN[vertrag_typ]['name']}**")

    # Betriebsdaten laden
    betriebsdaten = _load_betriebsdaten(supabase, betrieb_id)
    logo_bytes = _load_logo(supabase, betrieb_id)

    if not betriebsdaten.get("firmenname"):
        st.warning(
            "⚠️ Deine Betriebsdaten sind noch nicht vollständig. "
            "Gehe zum Tab **'Betriebsdaten & Logo'** und ergänze sie zuerst."
        )
        return

    # Formular je nach Vertragstyp
    if vertrag_typ == "vollzeit":
        _form_vollzeit(supabase, betrieb_id, betriebsdaten, logo_bytes)
    elif vertrag_typ == "teilzeit":
        _form_teilzeit(supabase, betrieb_id, betriebsdaten, logo_bytes)
    elif vertrag_typ == "minijob":
        _form_minijob(supabase, betrieb_id, betriebsdaten, logo_bytes)
    elif vertrag_typ == "aenderungsvertrag":
        _form_aenderungsvertrag(supabase, betrieb_id, betriebsdaten, logo_bytes)


def _mitarbeiter_block():
    """Gemeinsamer Block: Mitarbeiter-Auswahl oder manuelle Eingabe."""
    with st.expander("👤 Arbeitnehmer-Daten", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            vorname = st.text_input("Vorname *", key="an_vorname")
        with col2:
            nachname = st.text_input("Nachname *", key="an_nachname")

        strasse = st.text_input("Straße + Hausnummer *", key="an_strasse")

        col3, col4 = st.columns([1, 2])
        with col3:
            plz = st.text_input("PLZ *", key="an_plz")
        with col4:
            ort = st.text_input("Ort *", key="an_ort")

        iban = st.text_input("IBAN (optional)", key="an_iban")

    return {
        "vorname": vorname,
        "nachname": nachname,
        "strasse": strasse,
        "plz": plz,
        "ort": ort,
        "iban": iban,
    }


def _form_vollzeit(supabase, betrieb_id, betrieb, logo_bytes):
    """Formular: Vollzeit-Arbeitsvertrag."""
    arbeitnehmer = _mitarbeiter_block()

    with st.expander("📅 Vertragsbeginn & Probezeit", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            beginn = st.date_input("Vertragsbeginn *", value=date.today())
        with col2:
            probezeit_monate = _render_probezeit_select(key_suffix="vollzeit")

        probezeit_ende = add_months(beginn, probezeit_monate) if probezeit_monate else None
        if probezeit_ende:
            st.caption(f"Probezeit endet: {probezeit_ende.strftime('%d.%m.%Y')}")

        befristung = st.checkbox("Befristeter Vertrag")
        befristung_bis = None
        if befristung:
            befristung_bis = st.date_input("Befristet bis", value=date.today() + timedelta(days=365))

    with st.expander("⏰ Arbeitszeit & Vergütung", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            wochenstunden = st.number_input("Wochenstunden", min_value=20, max_value=48, value=40)
        with col2:
            stundenlohn = st.text_input("Stundenlohn brutto (€)", value="14,20")

        pay = _render_auszahlung_block(default_urlaub=24)

    with st.expander("💼 Tätigkeit", expanded=True):
        taetigkeit = st.text_area(
            "Tätigkeiten (eine pro Zeile)",
            value="Service und Bar\nKüchenhilfe\nReinigungstätigkeiten",
            height=120
        )
        arbeitsort = st.text_input("Arbeitsort", value=betrieb.get("anschrift_ort", ""))

    _submit_button(
        supabase, betrieb_id, "vollzeit", betrieb, arbeitnehmer, logo_bytes,
        daten={
            "beginn": beginn.isoformat(),
            "probezeit_monate": probezeit_monate,
            "probezeit_ende": probezeit_ende.isoformat() if probezeit_ende else None,
            "befristung": befristung,
            "befristung_bis": befristung_bis.isoformat() if befristung_bis else None,
            "wochenstunden": int(wochenstunden),
            "stundenlohn": stundenlohn,
            "taetigkeit": taetigkeit,
            "arbeitsort": arbeitsort,
            **pay,
        }
    )


def _form_teilzeit(supabase, betrieb_id, betrieb, logo_bytes):
    """Formular: Teilzeit-Arbeitsvertrag."""
    arbeitnehmer = _mitarbeiter_block()

    with st.expander("📅 Vertragsbeginn & Probezeit", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            beginn = st.date_input("Vertragsbeginn *", value=date.today())
        with col2:
            probezeit_monate = _render_probezeit_select(key_suffix="teilzeit")
        probezeit_ende = add_months(beginn, probezeit_monate) if probezeit_monate else None

    with st.expander("⏰ Arbeitszeit & Vergütung", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            monatsstunden = st.number_input("Monatliche Sollstunden", min_value=20, max_value=173, value=130)
        with col2:
            stundenlohn = st.text_input("Stundenlohn brutto (€)", value="14,20")

        pay = _render_auszahlung_block(default_urlaub=22)

    with st.expander("💼 Tätigkeit", expanded=True):
        taetigkeit = st.text_area(
            "Tätigkeiten (eine pro Zeile)",
            value="Service und Bar\nReinigungstätigkeiten",
            height=120
        )
        arbeitsort = st.text_input("Arbeitsort", value=betrieb.get("anschrift_ort", ""))

    _submit_button(
        supabase, betrieb_id, "teilzeit", betrieb, arbeitnehmer, logo_bytes,
        daten={
            "beginn": beginn.isoformat(),
            "probezeit_monate": probezeit_monate,
            "probezeit_ende": probezeit_ende.isoformat() if probezeit_ende else None,
            "monatsstunden": int(monatsstunden),
            "stundenlohn": stundenlohn,
            "taetigkeit": taetigkeit,
            "arbeitsort": arbeitsort,
            **pay,
        }
    )


def _form_minijob(supabase, betrieb_id, betrieb, logo_bytes):
    """Formular: Minijob-Vertrag."""
    arbeitnehmer = _mitarbeiter_block()

    with st.expander("📅 Vertragsbeginn", expanded=True):
        beginn = st.date_input("Vertragsbeginn *", value=date.today())

    with st.expander("⏰ Arbeitszeit & Vergütung", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            wochenstunden = st.text_input("Wochenstunden", value="nach Absprache (max. 10 Std.)")
        with col2:
            stundenlohn = st.text_input("Stundenlohn brutto (€)", value="14,20")

        pay = _render_auszahlung_block(default_urlaub=20, with_abschlag=False)

        st.info("💡 Minijob-Grenze 2026: **556 € / Monat**. Überschreitung nur unvorhergesehen in max. 2 Monaten/Jahr zulässig.")

    with st.expander("💼 Tätigkeit", expanded=True):
        taetigkeit = st.text_area("Tätigkeiten (eine pro Zeile)", value="Aushilfe Service", height=100)
        arbeitsort = st.text_input("Arbeitsort", value=betrieb.get("anschrift_ort", ""))

    _submit_button(
        supabase, betrieb_id, "minijob", betrieb, arbeitnehmer, logo_bytes,
        daten={
            "beginn": beginn.isoformat(),
            "wochenstunden": wochenstunden,
            "stundenlohn": stundenlohn,
            "taetigkeit": taetigkeit,
            "arbeitsort": arbeitsort,
            "urlaubstage": pay["urlaubstage"],
            "auszahlung_tag": pay["auszahlung_tag"],
        }
    )


def _form_aenderungsvertrag(supabase, betrieb_id, betrieb, logo_bytes):
    """Formular: Änderungsvertrag."""
    arbeitnehmer = _mitarbeiter_block()

    with st.expander("📅 Bezug auf Ursprungsvertrag", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            urspr_datum = st.date_input("Datum des ursprünglichen Vertrages *", value=date.today() - timedelta(days=365))
        with col2:
            inkrafttreten = st.date_input("Änderung tritt in Kraft ab *", value=date.today())

    st.markdown("#### Was soll geändert werden?")
    st.caption("Nur ausgewählte Paragraphen werden in den Änderungsvertrag aufgenommen.")

    aendere_arbeitszeit = st.checkbox("⏰ Arbeitszeit ändern")
    neue_wochenstunden = None
    neue_monatsstunden = None
    if aendere_arbeitszeit:
        col_a, col_b = st.columns(2)
        with col_a:
            art = st.radio("Art", ["Wochenstunden", "Monatsstunden"], horizontal=True)
        with col_b:
            if art == "Wochenstunden":
                neue_wochenstunden = st.number_input("Neue Wochenstunden", min_value=5, max_value=48, value=40)
            else:
                neue_monatsstunden = st.number_input("Neue Monatsstunden", min_value=20, max_value=173, value=130)

    aendere_verguetung = st.checkbox("💶 Vergütung ändern")
    neuer_stundenlohn = None
    neuer_abschlag = None
    if aendere_verguetung:
        col_a, col_b = st.columns(2)
        with col_a:
            neuer_stundenlohn = st.text_input("Neuer Stundenlohn (€)", value="15,00")
        with col_b:
            neuer_abschlag = st.number_input("Neue Abschlagszahlung (€, 0 = keine)", min_value=0, value=0)

    aendere_urlaub = st.checkbox("🏖 Urlaub ändern")
    neue_urlaubstage = None
    if aendere_urlaub:
        neue_urlaubstage = st.number_input("Neue Urlaubstage/Jahr", min_value=20, max_value=30, value=24)

    aendere_taetigkeit = st.checkbox("💼 Tätigkeit ändern")
    neue_taetigkeit = ""
    if aendere_taetigkeit:
        neue_taetigkeit = st.text_area("Neue Tätigkeiten (eine pro Zeile)", height=100)

    aendere_probezeit = st.checkbox("⏳ Probezeit beenden")
    probezeit_aenderung = ""
    if aendere_probezeit:
        probezeit_aenderung = st.text_input(
            "Regelung",
            value="vorzeitig beendet"
        )

    if not any([aendere_arbeitszeit, aendere_verguetung, aendere_urlaub, aendere_taetigkeit, aendere_probezeit]):
        st.info("Wähle mindestens eine Änderung aus.")
        return

    _submit_button(
        supabase, betrieb_id, "aenderungsvertrag", betrieb, arbeitnehmer, logo_bytes,
        daten={
            "urspruenglicher_vertrag_datum": urspr_datum.isoformat(),
            "inkrafttreten": inkrafttreten.isoformat(),
            "aendere_arbeitszeit": aendere_arbeitszeit,
            "neue_wochenstunden": neue_wochenstunden,
            "neue_monatsstunden": neue_monatsstunden,
            "aendere_verguetung": aendere_verguetung,
            "neuer_stundenlohn": neuer_stundenlohn,
            "neuer_abschlag": neuer_abschlag,
            "aendere_urlaub": aendere_urlaub,
            "neue_urlaubstage": neue_urlaubstage,
            "aendere_taetigkeit": aendere_taetigkeit,
            "neue_taetigkeit": neue_taetigkeit,
            "aendere_probezeit": aendere_probezeit,
            "probezeit_aenderung": probezeit_aenderung,
            "auszahlung_tag": 15,
            "abschlag_tag": 3,
        }
    )


def _submit_button(supabase, betrieb_id, vertragstyp, betrieb, arbeitnehmer, logo_bytes, daten):
    """Generiert PDF und zeigt Download-Button."""
    st.markdown("---")

    if not arbeitnehmer.get("vorname") or not arbeitnehmer.get("nachname"):
        st.warning("⚠️ Bitte Vorname und Nachname des Arbeitnehmers ausfüllen.")
        return

    # Kopie, um Eingaben des Aufrufers nicht zu mutieren
    betrieb_effective = dict(betrieb or {})
    betrieb_effective.setdefault("verschwiegenheit", True)

    col1, col2 = st.columns([3, 1])
    with col1:
        generator = VERTRAGSTYPEN[vertragstyp]["generator"]
        try:
            pdf_bytes = generator(betrieb_effective, arbeitnehmer, daten, logo_bytes)
            filename = _build_arbeitnehmer_filename(arbeitnehmer, vertragstyp)

            st.download_button(
                label=f"📥 **{VERTRAGSTYPEN[vertragstyp]['name']}** als PDF herunterladen",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Fehler beim Erstellen: {str(e)[:200]}")

    with col2:
        if st.button("💾 Im Archiv speichern", use_container_width=True):
            try:
                supabase.table("vertraege").insert({
                    "betrieb_id": int(betrieb_id),
                    "vertragstyp": vertragstyp,
                    "vertragsdaten": {
                        "betrieb": betrieb_effective,
                        "arbeitnehmer": arbeitnehmer,
                        "daten": daten,
                    },
                    "gueltig_ab": daten.get("beginn") or daten.get("inkrafttreten"),
                }).execute()
                st.success("✅ Im Archiv gespeichert")
            except Exception as e:
                st.error(f"Speichern fehlgeschlagen: {str(e)[:100]}")


def _show_betriebsdaten():
    """Betriebsdaten & Logo verwalten."""
    st.markdown("### ⚙️ Betriebsdaten")
    st.caption("Diese Daten werden automatisch in allen Verträgen verwendet.")

    supabase = _get_supabase()
    betrieb_id = require_betrieb_id()
    if supabase is None:
        st.error("Datenbankverbindung konnte nicht hergestellt werden.")
        return

    daten = _load_betriebsdaten(supabase, betrieb_id)

    with st.form("betriebsdaten"):
        firmenname = st.text_input("Firmenname *", value=daten.get("firmenname", ""))
        vertreten_durch = st.text_input("Vertreten durch", value=daten.get("vertreten_durch", ""))

        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            strasse = st.text_input("Straße + Nr.", value=daten.get("anschrift_strasse", ""))
        with col2:
            plz = st.text_input("PLZ", value=daten.get("anschrift_plz", ""))
        with col3:
            ort = st.text_input("Ort", value=daten.get("anschrift_ort", ""))

        st.markdown("**Standard-Vertragsdaten**")
        col_a, col_b = st.columns(2)
        with col_a:
            standard_urlaub = st.number_input(
                "Standard Urlaubstage",
                min_value=20, max_value=30,
                value=int(daten.get("standard_urlaubstage") or 24)
            )
        with col_b:
            standard_lohn = st.text_input(
                "Standard Stundenlohn (€)",
                value=str(daten.get("standard_stundenlohn") or "14,20")
            )

        verschwiegenheit = st.checkbox(
            "Verschwiegenheitsklausel in Verträgen",
            value=daten.get("verschwiegenheit", True)
        )

        if st.form_submit_button("💾 Speichern", type="primary"):
            try:
                lohn_num = float(standard_lohn.replace(",", "."))
                supabase.table("betrieb_vertragsdaten").upsert({
                    "betrieb_id": int(betrieb_id),
                    "firmenname": firmenname,
                    "vertreten_durch": vertreten_durch,
                    "anschrift_strasse": strasse,
                    "anschrift_plz": plz,
                    "anschrift_ort": ort,
                    "standard_urlaubstage": standard_urlaub,
                    "standard_stundenlohn": lohn_num,
                    "verschwiegenheit": verschwiegenheit,
                }).execute()
                st.success("✅ Betriebsdaten gespeichert")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {str(e)[:200]}")

    # Logo-Upload
    st.markdown("---")
    st.markdown("### 🖼️ Betriebslogo")
    st.caption("Das Logo erscheint oben rechts auf allen erstellten Verträgen.")

    logo_bytes = _load_logo(supabase, betrieb_id)
    if logo_bytes:
        st.image(logo_bytes, width=200)

    uploaded = st.file_uploader(
        "Logo hochladen (PNG, JPG, max 10 MB)",
        type=["png", "jpg", "jpeg"],
        help="Das Logo wird automatisch auf 800x400 px komprimiert für optimale Performance."
    )
    if uploaded:
        _handle_logo_upload(supabase, int(betrieb_id), uploaded)


def _show_archiv():
    """Vertragsarchiv."""
    st.markdown("### 📚 Vertragsarchiv")

    supabase = _get_supabase()
    betrieb_id = require_betrieb_id()
    if supabase is None:
        st.error("Datenbankverbindung konnte nicht hergestellt werden.")
        return

    try:
        vertraege = _load_archiv_rows_robust(supabase, int(betrieb_id))

        if not vertraege:
            st.info("Noch keine Verträge archiviert.")
            return

        for v in vertraege:
            daten_json = v.get("vertragsdaten") or {}
            if not isinstance(daten_json, dict):
                daten_json = {}
            arbeitnehmer = daten_json.get("arbeitnehmer") or {}
            an_name = f"{arbeitnehmer.get('vorname', '')} {arbeitnehmer.get('nachname', '')}".strip()
            vtyp = str(v.get("vertragstyp") or "").strip()
            vtyp_name = VERTRAGSTYPEN.get(vtyp, {}).get("name")
            if not vtyp_name:
                vtyp_name = vtyp.replace("_", " ").title() if vtyp else "Arbeitsvertrag (Bestand)"
            created_value = str(v.get("erstellt_am") or v.get("created_at") or "")

            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{vtyp_name}**")
                    if an_name:
                        st.caption(f"Mitarbeiter: {an_name}")
                    else:
                        ma_id = v.get("mitarbeiter_id")
                        st.caption(f"Mitarbeiter: ID {ma_id}" if ma_id else "Mitarbeiter: Unbekannt")
                with col2:
                    if created_value:
                        st.caption(f"Erstellt: {created_value[:10]}")
                    if v.get("gueltig_ab"):
                        st.caption(f"Gültig ab: {v['gueltig_ab']}")
                with col3:
                    # PDF neu generieren
                    if st.button("🔄 PDF", key=f"regen_{v['id']}", use_container_width=True):
                        try:
                            if vtyp in VERTRAGSTYPEN:
                                logo_bytes = _load_logo(supabase, betrieb_id)
                                pdf = VERTRAGSTYPEN[vtyp]["generator"](
                                    daten_json.get("betrieb") or {},
                                    arbeitnehmer,
                                    daten_json.get("daten") or {},
                                    logo_bytes
                                )
                                st.session_state[f"pdf_{v['id']}"] = pdf
                                st.rerun()
                            else:
                                st.info("PDF-Regeneration für diesen Legacy-Vertragstyp nicht verfügbar.")
                        except Exception as e:
                            st.error(f"{str(e)[:100]}")

                if f"pdf_{v['id']}" in st.session_state:
                    st.download_button(
                        label="📥 PDF herunterladen",
                        data=st.session_state[f"pdf_{v['id']}"],
                        file_name=f"vertrag_{v['id']}.pdf",
                        mime="application/pdf",
                        key=f"dl_{v['id']}",
                        use_container_width=True,
                    )
    except Exception as e:
        st.error(f"Fehler beim Laden: {str(e)[:200]}")


def _compress_logo(file_bytes: bytes) -> tuple[bytes, float, float]:
    """
    Komprimiert ein Logo-Bild für die Speicherung in Supabase.
    Gibt (jpeg_bytes, original_kb, compressed_kb) zurück.
    Löst Exceptions bei ungültigen Bildern aus.
    """
    import io as _io
    from PIL import Image, ImageOps

    original_size_kb = len(file_bytes) / 1024
    img = Image.open(_io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)

    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode in ("P", "LA"):
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
    img.thumbnail((800, 400), resampling)

    buf = _io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    compressed_bytes = buf.getvalue()
    return compressed_bytes, original_size_kb, len(compressed_bytes) / 1024


def _upsert_logo_row(supabase, betrieb_id: int, compressed_bytes: bytes) -> None:
    """
    Speichert das Logo idempotent: erst Update per betrieb_id, sonst Insert.
    """
    import base64

    payload = {
        "logo_bytes": base64.b64encode(compressed_bytes).decode("utf-8"),
        "logo_mime": "image/jpeg",
    }
    updated_rows: list = []
    try:
        update_res = (
            supabase.table("betrieb_logos")
            .update(payload)
            .eq("betrieb_id", int(betrieb_id))
            .execute()
        )
        updated_rows = update_res.data or []
    except Exception:
        updated_rows = []
    if not updated_rows:
        supabase.table("betrieb_logos").insert({
            "betrieb_id": int(betrieb_id),
            **payload,
        }).execute()


def _handle_logo_upload(supabase, betrieb_id: int, uploaded) -> None:
    """UI-Handler: komprimiert und speichert das hochgeladene Logo."""
    try:
        file_bytes = uploaded.read()
        compressed_bytes, original_kb, compressed_kb = _compress_logo(file_bytes)
        _upsert_logo_row(supabase, betrieb_id, compressed_bytes)
        st.success(
            f"✅ Logo hochgeladen (von {original_kb:.0f} KB auf {compressed_kb:.0f} KB komprimiert)"
        )
        st.rerun()
    except Exception as e:
        st.error(f"Upload-Fehler: {str(e)[:200]}")


def _load_betriebsdaten(supabase, betrieb_id):
    """Lädt Betriebsdaten aus Supabase."""
    if supabase is None:
        return {}
    try:
        result = supabase.table("betrieb_vertragsdaten").select("*").eq(
            "betrieb_id", int(betrieb_id)
        ).maybe_single().execute()
        return result.data or {}
    except Exception:
        return {}


def _load_logo(supabase, betrieb_id):
    """Lädt das Betriebslogo als Bytes."""
    if supabase is None:
        return None
    try:
        import base64
        rows = []
        for order_col in ("id", "updated_at", "created_at"):
            try:
                result = (
                    supabase.table("betrieb_logos")
                    .select("logo_bytes")
                    .eq("betrieb_id", int(betrieb_id))
                    .order(order_col, desc=True)
                    .limit(1)
                    .execute()
                )
                rows = result.data or []
                if rows:
                    break
            except Exception:
                continue
        if not rows:
            fallback = (
                supabase.table("betrieb_logos")
                .select("logo_bytes")
                .eq("betrieb_id", int(betrieb_id))
                .limit(1)
                .execute()
            )
            rows = fallback.data or []
        if rows and rows[0].get("logo_bytes"):
            raw = rows[0]["logo_bytes"]
            if isinstance(raw, (bytes, bytearray)):
                return bytes(raw)
            raw_str = str(raw)
            if raw_str.startswith("data:") and "," in raw_str:
                raw_str = raw_str.split(",", 1)[1]
            return base64.b64decode(raw_str)
    except Exception:
        pass
    return None
