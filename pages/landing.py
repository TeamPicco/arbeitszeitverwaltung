import streamlit as st


def show_landing():
    """Complio Landing Page als Streamlit-Seite."""

    st.markdown("""
    <style>
    .complio-hero {
        background: #111111;
        padding: 4rem 2rem;
        text-align: center;
        border-radius: 12px;
        margin-bottom: 2rem;
    }
    .complio-logo {
        font-size: 32px;
        font-weight: 700;
        color: white;
        margin-bottom: 1.5rem;
    }
    .complio-logo span { color: #F97316; }
    .complio-h1 {
        font-size: 1.8rem;
        color: white;
        font-weight: 600;
        margin-bottom: 1rem;
        line-height: 1.3;
    }
    .complio-h1 em { color: #F97316; font-style: normal; }
    .complio-sub {
        color: #aaaaaa;
        font-size: 1rem;
        margin-bottom: 0;
    }
    .fear-banner {
        background: #F97316;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 1rem;
        text-align: center;
    }
    .fear-item strong {
        display: block;
        font-size: 1.5rem;
        color: white;
        font-weight: 700;
    }
    .fear-item p { color: #fff3e0; font-size: 0.85rem; margin: 0; }
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .feature-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1.25rem;
    }
    .feature-card h3 {
        color: #111;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .feature-card p { color: #666; font-size: 0.85rem; line-height: 1.5; }
    .pricing-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .price-card {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        background: white;
    }
    .price-card.featured { border: 2px solid #F97316; }
    .price-card h3 { font-size: 1rem; font-weight: 600; color: #111; }
    .price-card .amount {
        font-size: 2rem;
        font-weight: 700;
        color: #F97316;
        margin: 0.5rem 0;
    }
    .price-card p { font-size: 0.85rem; color: #666; }
    .cta-block {
        background: #111111;
        border-radius: 12px;
        padding: 3rem 2rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    .cta-block h2 { color: white; font-size: 1.5rem; margin-bottom: 0.5rem; }
    .cta-block p { color: #aaa; font-size: 0.95rem; margin-bottom: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)

    # Hero
    st.markdown("""
    <div class="complio-hero">
        <div class="complio-logo">Complio<span>.</span></div>
        <div class="complio-h1">
            Nie wieder Bußgelder wegen<br>
            <em>fehlender Dokumentation.</em>
        </div>
        <div class="complio-sub">
            Dienstplanung · Personalakte · Arbeitssicherheit · Rechtssicher
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Bußgeld-Banner
    st.markdown("""
    <div class="fear-banner">
        <div class="fear-item">
            <strong>bis 30.000 €</strong>
            <p>fehlende Gefährdungsbeurteilung</p>
        </div>
        <div class="fear-item">
            <strong>bis 15.000 €</strong>
            <p>falsche Arbeitszeitdokumentation</p>
        </div>
        <div class="fear-item">
            <strong>ab 5.000 €</strong>
            <p>fehlende Arbeitsverträge</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Features
    st.markdown("## Was Complio für dich erledigt")
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <h3>📅 Dienstplanung</h3>
            <p>Schichten planen mit automatischer Kostenberechnung</p>
        </div>
        <div class="feature-card">
            <h3>👥 Personalakte</h3>
            <p>Alle Mitarbeiterdaten DSGVO-konform verwalten</p>
        </div>
        <div class="feature-card">
            <h3>🛡️ Gefährdungsbeurteilung KI</h3>
            <p>§5 ArbSchG in 10 Minuten – rechtssicher</p>
        </div>
        <div class="feature-card">
            <h3>⏰ ArbZG-Wächter</h3>
            <p>Verstöße erkennen bevor sie teuer werden</p>
        </div>
        <div class="feature-card">
            <h3>📤 DATEV-Export</h3>
            <p>Lohnabrechnung für den Steuerberater</p>
        </div>
        <div class="feature-card">
            <h3>⏱️ Arbeitszeitkonto</h3>
            <p>Überstunden automatisch und rechtssicher</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Preise
    st.markdown("## Einfache Preise")
    st.markdown("""
    <div class="pricing-grid">
        <div class="price-card">
            <h3>Starter</h3>
            <div class="amount">29 €<small style="font-size:1rem">/Monat</small></div>
            <p>Dienstplanung + Personalakte + Arbeitszeitkonto</p>
        </div>
        <div class="price-card featured">
            <div style="color:#F97316;font-size:0.75rem;font-weight:700;
            letter-spacing:1px">BELIEBTESTER PLAN</div>
            <h3>Compliance</h3>
            <div class="amount">79 €<small style="font-size:1rem">/Monat</small></div>
            <p>+ Gefährdungsbeurteilung KI + ArbZG-Wächter</p>
        </div>
        <div class="price-card">
            <h3>Complete</h3>
            <div class="amount">99 €<small style="font-size:1rem">/Monat</small></div>
            <p>+ DATEV-Export + Prioritäts-Support</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # CTA
    st.markdown("""
    <div class="cta-block">
        <h2>Bereit deinen Betrieb zu schützen?</h2>
        <p>30 Tage kostenlos – keine Kreditkarte erforderlich</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.link_button(
            "Jetzt kostenlos starten",
            url="https://getcomplio.de/?locale=de",
            use_container_width=True,
            type="primary"
        )
        st.markdown(
            "<p style='text-align:center;font-size:12px;color:gray'>"
            "Keine Kreditkarte · 30 Tage kostenlos · Kündigung jederzeit</p>",
            unsafe_allow_html=True
        )
