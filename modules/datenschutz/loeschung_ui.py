"""
Datenschutz-Löschroutine – Admin-UI
DSGVO Art. 17: Pseudonymisierung ausgeschiedener Mitarbeiter nach Ablauf der
Aufbewahrungsfrist (§147 AO: 10 Jahre nach Austrittsdatum).
"""
import streamlit as st
from utils.database import get_service_role_client


def _betrieb_id() -> int | None:
    return st.session_state.get("betrieb_id")


def _lade_loeschlog(limit: int = 100):
    betrieb_id = _betrieb_id()
    if not betrieb_id:
        return []
    try:
        supabase = get_service_role_client()
        # Join über mitarbeiter um nur betriebseigene Einträge zu zeigen
        res = (
            supabase.table("datenschutz_loeschlog")
            .select("*, mitarbeiter(betrieb_id)")
            .order("ausgefuehrt_am", desc=True)
            .limit(limit)
            .execute()
        )
        eigene = [
            r for r in (res.data or [])
            if (r.get("mitarbeiter") or {}).get("betrieb_id") == betrieb_id
        ]
        return eigene
    except Exception:
        # Fallback ohne Join wenn mitarbeiter bereits pseudonymisiert
        try:
            supabase = get_service_role_client()
            res = (
                supabase.table("datenschutz_loeschlog")
                .select("*")
                .order("ausgefuehrt_am", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception:
            return []


def _zaehle_faellige() -> int:
    """Zählt Mitarbeiter, deren Pseudonymisierungsfrist abgelaufen ist."""
    betrieb_id = _betrieb_id()
    if not betrieb_id:
        return 0
    try:
        supabase = get_service_role_client()
        res = (
            supabase.table("mitarbeiter")
            .select("id", count="exact")
            .eq("betrieb_id", betrieb_id)
            .not_.is_("austrittsdatum", "null")
            .lt("austrittsdatum", "now() - interval '10 years'")
            .not_.like("vorname", "GELÖSCHT%")
            .execute()
        )
        return res.count or 0
    except Exception:
        return 0


def _fuehre_pseudonymisierung_aus() -> dict:
    try:
        supabase = get_service_role_client()
        res = supabase.rpc("pseudonymisiere_ausgeschiedene_mitarbeiter").execute()
        if res.data:
            row = res.data[0]
            return {
                "ok": True,
                "verarbeitet": row.get("verarbeitet", 0),
                "pseudonymisiert": row.get("pseudonymisiert", 0),
            }
        return {"ok": True, "verarbeitet": 0, "pseudonymisiert": 0}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def show_loeschprotokoll() -> None:
    st.markdown("### Datenschutz-Löschroutine (Art. 17 DSGVO)")
    st.caption(
        "Mitarbeiter, die vor mehr als 10 Jahren ausgeschieden sind (§147 AO), "
        "werden automatisch pseudonymisiert. Persönliche Daten (Name, Adresse, E-Mail) "
        "werden durch neutrale Platzhalter ersetzt. Die Zeiterfassungsdaten bleiben für "
        "steuerliche Prüfungen erhalten."
    )

    st.markdown("---")

    # Status-Karte
    faellig = _zaehle_faellige()
    log_eintraege = _lade_loeschlog()

    col1, col2 = st.columns(2)
    col1.metric(
        "Fällige Pseudonymisierungen",
        faellig,
        delta="Sofort handeln" if faellig > 0 else None,
        delta_color="inverse" if faellig > 0 else "off",
    )
    col2.metric("Bereits pseudonymisiert (gesamt)", len(log_eintraege))

    st.markdown("---")

    # Cron-Info
    st.info(
        "Der automatische Cron-Job läuft jeden 1. des Monats um 03:00 Uhr "
        "(falls pg_cron in Supabase aktiviert ist). "
        "Hier können Sie die Routine auch manuell auslösen."
    )

    if faellig > 0:
        st.warning(
            f"**{faellig} Mitarbeiter** überschreiten die 10-Jahres-Aufbewahrungsfrist "
            "und müssen pseudonymisiert werden."
        )

    if st.button(
        "Pseudonymisierung jetzt ausführen",
        type="primary",
        disabled=faellig == 0,
        help="Führt die DSGVO-Löschroutine manuell aus."
    ):
        with st.spinner("Pseudonymisierung läuft..."):
            result = _fuehre_pseudonymisierung_aus()

        if result.get("ok"):
            p = result.get("pseudonymisiert", 0)
            if p > 0:
                st.success(
                    f"✅ {p} Mitarbeiter erfolgreich pseudonymisiert. "
                    f"Geprüft: {result.get('verarbeitet', 0)}."
                )
            else:
                st.info("Keine fälligen Datensätze gefunden.")
            st.rerun()
        else:
            st.error(f"Fehler: {result.get('error')}")

    st.markdown("---")
    st.markdown("#### Protokoll der letzten Pseudonymisierungen")

    if not log_eintraege:
        st.info("Noch keine Pseudonymisierungen protokolliert.")
        return

    for eintrag in log_eintraege:
        ts = eintrag.get("ausgefuehrt_am", "")[:19].replace("T", " ")
        mit_id = eintrag.get("mitarbeiter_id", "?")
        aktion = eintrag.get("aktion", "pseudonymisiert")
        von = eintrag.get("ausgefuehrt_von", "system")
        grund = eintrag.get("grund", "")
        st.markdown(
            f"- `{ts}` — Mitarbeiter-ID **{mit_id}** | Aktion: {aktion} | Von: {von}"
            + (f" | {grund}" if grund else "")
        )
