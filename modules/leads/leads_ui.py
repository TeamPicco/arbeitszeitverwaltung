"""
Complio Leads-Dashboard
Zeigt alle Outreach-Leads, Status und Statistiken im Admin-Bereich.
Nur sichtbar für den Piccolo-Admin (betrieb_id == eigener Betrieb).
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.database import get_service_role_client


STATUS_FARBEN = {
    "neu":          "#6b7280",
    "kontaktiert":  "#1a56db",
    "antwort":      "#f59e0b",
    "interessiert": "#059669",
    "abschluss":    "#7c3aed",
    "abgelehnt":    "#dc2626",
    "abgemeldet":   "#9ca3af",
}

STATUS_LABELS = {
    "neu":          "🔵 Neu",
    "kontaktiert":  "📧 Kontaktiert",
    "antwort":      "💬 Antwort",
    "interessiert": "⭐ Interessiert",
    "abschluss":    "🎉 Abschluss",
    "abgelehnt":    "❌ Abgelehnt",
    "abgemeldet":   "🚫 Abgemeldet",
}


def show_leads_dashboard():
    st.markdown("## 📊 Outreach & Leads")

    supabase = get_service_role_client()

    # ── STATS ────────────────────────────────────────────────
    try:
        alle = supabase.table("leads").select("status, emails_gesendet").execute().data
    except Exception:
        st.error("Leads-Tabelle nicht gefunden. Bitte zuerst die Migration `20260426_leads.sql` in Supabase ausführen.")
        return

    df_all = pd.DataFrame(alle) if alle else pd.DataFrame(columns=["status", "emails_gesendet"])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Gesamt", len(df_all))
    col2.metric("Kontaktiert", int((df_all["status"] == "kontaktiert").sum()))
    col3.metric("Interessiert", int((df_all["status"] == "interessiert").sum()))
    col4.metric("Abschlüsse", int((df_all["status"] == "abschluss").sum()))
    col5.metric("E-Mails gesendet", int(df_all["emails_gesendet"].sum()) if "emails_gesendet" in df_all else 0)

    st.markdown("---")

    # ── FILTER & TABELLE ─────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        status_filter = st.selectbox(
            "Status filtern",
            ["Alle"] + list(STATUS_LABELS.values()),
        )
    with col_f2:
        suche = st.text_input("🔍 Suche", placeholder="Firmenname oder Ort ...")
    with col_f3:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Aktualisieren", use_container_width=True):
            st.rerun()

    # Leads laden
    query = supabase.table("leads").select(
        "id, firmenname, ort, email, telefon, status, sequenz_schritt, "
        "emails_gesendet, naechste_email, letzter_kontakt, notizen"
    ).order("created_at", desc=True).limit(500)

    # Status-Filter
    status_map_rev = {v: k for k, v in STATUS_LABELS.items()}
    if status_filter != "Alle":
        raw_status = status_map_rev.get(status_filter, status_filter)
        query = query.eq("status", raw_status)

    try:
        leads = query.execute().data
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return

    df = pd.DataFrame(leads) if leads else pd.DataFrame()

    if df.empty:
        st.info("Noch keine Leads vorhanden. Starte den Lead-Scraper:\n```\npython scripts/lead_scraper.py --stadt Hamburg --max 200\n```")
        return

    # Suche
    if suche:
        mask = (
            df["firmenname"].str.contains(suche, case=False, na=False) |
            df["ort"].str.contains(suche, case=False, na=False)
        )
        df = df[mask]

    # Status-Labels
    df["Status"] = df["status"].map(STATUS_LABELS).fillna(df["status"])
    df["Schritt"] = df["sequenz_schritt"].apply(lambda x: f"{x}/4")
    df["Nächste Mail"] = df["naechste_email"].fillna("—")

    anzeige = df[["firmenname", "ort", "email", "Status", "Schritt", "Nächste Mail", "emails_gesendet"]].copy()
    anzeige.columns = ["Betrieb", "Ort", "E-Mail", "Status", "Sequenz", "Nächste Mail", "Mails"]

    st.dataframe(anzeige, use_container_width=True, height=420, hide_index=True)
    st.caption(f"{len(df)} Leads angezeigt")

    # ── LEAD BEARBEITEN ──────────────────────────────────────
    st.markdown("---")
    st.markdown("### Lead bearbeiten")

    lead_namen = ["— auswählen —"] + [f"{r['firmenname']} ({r['ort']})" for _, r in df.iterrows()]
    auswahl = st.selectbox("Lead auswählen", lead_namen)

    if auswahl != "— auswählen —":
        idx = lead_namen.index(auswahl) - 1
        lead = df.iloc[idx]

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            neuer_status = st.selectbox(
                "Status ändern",
                list(STATUS_LABELS.keys()),
                index=list(STATUS_LABELS.keys()).index(lead["status"]) if lead["status"] in STATUS_LABELS else 0,
                format_func=lambda x: STATUS_LABELS[x],
            )
        with col_b:
            notiz = st.text_input("Notiz hinzufügen", value=lead.get("notizen") or "")
        with col_c:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("💾 Speichern", use_container_width=True):
                supabase.table("leads").update({
                    "status": neuer_status,
                    "notizen": notiz,
                }).eq("id", int(lead["id"])).execute()
                st.success("Gespeichert.")
                st.rerun()

    # ── IMPORT / EXPORT ──────────────────────────────────────
    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**📥 CSV importieren**")
        uploaded = st.file_uploader("CSV-Datei hochladen", type="csv", key="lead_csv")
        if uploaded and st.button("Import starten"):
            import io, csv as _csv
            content = uploaded.read().decode("utf-8-sig")
            reader = _csv.DictReader(io.StringIO(content))
            neu = 0
            for row in reader:
                name = row.get("firmenname") or row.get("name") or row.get("Firma") or ""
                if not name.strip():
                    continue
                try:
                    supabase.table("leads").insert({
                        "firmenname": name.strip(),
                        "email":   (row.get("email") or "").strip() or None,
                        "telefon": (row.get("telefon") or "").strip() or None,
                        "ort":     (row.get("ort") or row.get("Stadt") or "").strip() or None,
                        "quelle":  "csv_import",
                        "status":  "neu",
                        "sequenz_schritt": 0,
                    }).execute()
                    neu += 1
                except Exception:
                    pass
            st.success(f"{neu} Leads importiert.")
            st.rerun()

    with c2:
        st.markdown("**📤 CSV exportieren**")
        if st.button("Alle Leads exportieren"):
            alle_leads = supabase.table("leads").select("*").execute().data
            if alle_leads:
                export_df = pd.DataFrame(alle_leads)
                csv_data = export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇ Download CSV",
                    data=csv_data,
                    file_name=f"complio_leads_{date.today()}.csv",
                    mime="text/csv",
                )
