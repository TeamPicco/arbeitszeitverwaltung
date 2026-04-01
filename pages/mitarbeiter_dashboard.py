import streamlit as st
from datetime import datetime
from utils.database import get_supabase_client
from utils.calculations import berechne_azk_kumuliert
from utils.styles import apply_custom_css
from utils.branding import BRAND_APP_NAME, BRAND_ICON_IMAGE, BRAND_LOGO_IMAGE

def show_mitarbeiter_dashboard():
    st.set_page_config(page_title=f"{BRAND_APP_NAME} – Mein Bereich", page_icon=BRAND_ICON_IMAGE, layout="wide")
    apply_custom_css()
    supabase = get_supabase_client()
    m_id = st.session_state.get('mitarbeiter_id')

    st.image(BRAND_LOGO_IMAGE, width=140)
    st.title(f"Hallo {st.session_state.get('vorname')}! 👋")
    
    t1, t2, t3 = st.tabs(["🕒 Stempeln", "📅 Zeitkonto", "📄 Dokumente"])

    with t1:
        st.header("Zeiterfassung")
        # Hier deine Stempel-Logik...
        st.info("Nutzen Sie die Kiosk-Stempeluhr oder geben Sie Zeiten manuell ein.")

    with t2:
        st.header("Arbeitszeitkonto")
        heute = datetime.now()
        konto = (
            supabase.table("arbeitszeit_konten")
            .select("*")
            .eq("mitarbeiter_id", m_id)
            .limit(1)
            .execute()
        )
        if konto.data:
            row = konto.data[0]
            saldo = float(row.get('ueberstunden_saldo') or 0)
            soll = float(row.get('soll_stunden') or 0)
            ist = float(row.get('ist_stunden') or 0)
            urlaub_g = float(row.get('urlaubstage_gesamt') or 0)
            urlaub_n = float(row.get('urlaubstage_genommen') or 0)
            krank = float(row.get('krankheitstage_gesamt') or 0)

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Überstunden-Saldo", f"{saldo:.2f} h")
            k2.metric("Soll / Ist", f"{soll:.2f}h / {ist:.2f}h")
            k3.metric("Urlaub", f"{urlaub_n:.1f} / {urlaub_g:.1f} Tg")
            k4.metric("Krankheitstage", f"{krank:.1f} Tg")

            st.progress(min(max((urlaub_n / urlaub_g), 0.0), 1.0) if urlaub_g > 0 else 0.0)
            st.caption("Urlaubsverbrauch im aktuellen Kontostand")
        else:
            saldo = berechne_azk_kumuliert(m_id, heute.month, heute.year, supabase)
            st.metric("Dein Kontostand", f"{saldo} Std.", delta=saldo)

    with t3:
        render_my_documents(m_id, supabase)

def render_my_documents(m_id, supabase):
    # Wichtig: Die Einrückung hier löst den IndentationError!
    st.header("📄 Meine Dokumente")
    docs = supabase.table("mitarbeiter_dokumente").select("*").eq("mitarbeiter_id", m_id).execute()
    if not docs.data:
        st.write("Keine Dokumente gefunden.")
    for d in docs.data:
        col1, col2 = st.columns([3,1])
        col1.write(f"**{d['name']}** ({d['typ']})")
        col2.link_button("Öffnen", d['file_url'])
