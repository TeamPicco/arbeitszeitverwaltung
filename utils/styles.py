"""Globales UI-Framework mit Dark-Mode und maximalem Kontrast."""

import streamlit as st

COLORS = {
    "primary": "#F97316",
    "primary_light": "#FB923C",
    "primary_dark": "#0a0a0a",
    "accent": "#F97316",
    "background": "#0a0a0a",
    "surface": "#111111",
    "border": "#1f1f1f",
    "text_primary": "#ffffff",
    "text_secondary": "#a3a3a3",
    "text_light": "#ffffff",
    # Backward-compatible aliases used throughout existing CSS templates.
    "app_bg": "#0a0a0a",
    "surface_alt": "#111111",
    "surface_light": "#111111",
    "text_on_light": "#ffffff",
    "text_on_dark": "#ffffff",
    "muted_on_light": "#a3a3a3",
    "muted_on_dark": "#a3a3a3",
    "primary_hover": "#FB923C",
}


def apply_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            background: {COLORS['background']} !important;
            color: {COLORS['text_primary']} !important;
        }}

        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"] {{
            display: none !important;
        }}

        .block-container {{
            max-width: 1280px !important;
            padding-top: 1.2rem !important;
            padding-bottom: 1.2rem !important;
        }}

        .complio-topbar {{
            position: sticky;
            top: 0;
            z-index: 40;
            background: {COLORS["surface"]};
            border-bottom: none;
            padding: 0.15rem 0 0.15rem 0;
            margin-bottom: 0.55rem;
        }}

        .st-key-header_logo {{
            margin: 0 !important;
            padding: 0 !important;
        }}

        .st-key-header_logo [data-testid="stElementContainer"] {{
            margin: 0 !important;
            padding: 0 !important;
        }}

        .st-key-header_logo [data-testid="stImage"] {{
            margin: 0 !important;
            padding: 0 !important;
            line-height: 0 !important;
        }}

        .complio-card {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 12px;
            box-shadow: none;
            padding: 1rem;
            margin-bottom: 1rem;
        }}

        .st-key-header_logo img {{
            height: 92px !important;
            width: auto !important;
            object-fit: contain !important;
        }}

        /* Kontrastregel: Auf dunklem Grund weiß */
        h1, h2, h3, h4, h5, h6, p, span, label, div,
        [data-testid="stMarkdownContainer"], [data-testid="stText"], [data-testid="stMetricLabel"] {{
            color: {COLORS['text_primary']} !important;
        }}

        [style*="background: #000"], [style*="background:#000"], [style*="background-color: #000"],
        [style*="background-color:#000"], [style*="background: rgb(0, 0, 0)"],
        [style*="background-color: rgb(0, 0, 0)"] {{
            color: {COLORS['text_primary']} !important;
        }}
        [style*="background: #000"] *, [style*="background:#000"] *, [style*="background-color: #000"] *,
        [style*="background-color:#000"] *, [style*="background: rgb(0, 0, 0)"] *,
        [style*="background-color: rgb(0, 0, 0)"] * {{
            color: {COLORS['text_primary']} !important;
        }}
        /* Wenn irgendwo weißer Hintergrund auftaucht, erzwinge schwarze Schrift */
        [style*="background:#fff"], [style*="background: #fff"], [style*="background:#ffffff"],
        [style*="background: #ffffff"], [style*="background-color:#fff"], [style*="background-color: #fff"],
        [style*="background-color:#ffffff"], [style*="background-color: #ffffff"] {{
            color: {COLORS['text_primary']} !important;
        }}
        [style*="background:#fff"] *, [style*="background: #fff"] *, [style*="background:#ffffff"] *,
        [style*="background: #ffffff"] *, [style*="background-color:#fff"] *, [style*="background-color: #fff"] *,
        [style*="background-color:#ffffff"] *, [style*="background-color: #ffffff"] * {{
            color: {COLORS['text_primary']} !important;
        }}

        /* Card-Surfaces */
        div[data-testid="stMetric"],
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-baseweb="tab-panel"] > div {{
            background: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            color: {COLORS['text_primary']} !important;
        }}

        /* Buttons */
        .stButton > button,
        .stDownloadButton > button {{
            min-height: 42px !important;
            border-radius: 8px !important;
            border: 1px solid {COLORS["primary"]} !important;
            background: {COLORS["primary"]} !important;
            color: {COLORS['text_primary']} !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
        }}
        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            background: {COLORS['primary_light']} !important;
            color: {COLORS['text_primary']} !important;
        }}

        /* Inputs: Label + Text strikt kontrastreich */
        .stTextInput label, .stNumberInput label, .stDateInput label, .stTextArea label,
        [data-testid="stWidgetLabel"] {{
            color: {COLORS['text_primary']} !important;
            font-weight: 600 !important;
        }}

        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        .stTextArea textarea,
        [data-baseweb="select"] > div,
        [data-baseweb="input"] input {{
            border-radius: 10px !important;
            border: 1px solid {COLORS["border"]} !important;
            background: {COLORS['surface']} !important;
            color: {COLORS['text_primary']} !important;
            min-height: 42px !important;
            -webkit-text-fill-color: {COLORS['text_primary']} !important;
            opacity: 1 !important;
        }}
        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus,
        .stTextArea textarea:focus,
        [data-baseweb="input"]:focus-within,
        [data-baseweb="select"] > div:focus-within {{
            border: 1px solid {COLORS["primary"]} !important;
            box-shadow: 0 0 0 1px {COLORS["primary"]} !important;
            background: {COLORS['background']} !important;
            color: {COLORS['text_primary']} !important;
            -webkit-text-fill-color: {COLORS['text_primary']} !important;
        }}
        .stTextInput input:active,
        .stNumberInput input:active,
        .stDateInput input:active,
        .stTextArea textarea:active {{
            color: {COLORS['text_primary']} !important;
            -webkit-text-fill-color: {COLORS['text_primary']} !important;
        }}
        .stDateInput button,
        .stDateInput svg,
        .stNumberInput button,
        [data-baseweb="select"] svg {{
            color: {COLORS['text_primary']} !important;
            fill: {COLORS['text_primary']} !important;
        }}

        .stTextInput input::placeholder,
        .stNumberInput input::placeholder,
        .stDateInput input::placeholder,
        .stTextArea textarea::placeholder {{
            color: {COLORS['text_secondary']} !important;
            opacity: 1 !important;
        }}
        [role="listbox"] {{
            background: {COLORS['surface']} !important;
            color: {COLORS['text_primary']} !important;
        }}
        [role="option"] {{
            background: {COLORS['surface']} !important;
            color: {COLORS['text_primary']} !important;
        }}
        [role="option"]:hover {{
            background: {COLORS["primary"]} !important;
            color: {COLORS['text_primary']} !important;
        }}

        /* DataFrames/Tables mit starkem Kontrast */
        [data-testid="stDataFrame"] *,
        [data-testid="stTable"] *,
        .dataframe * {{
            color: {COLORS['text_primary']} !important;
        }}
        [data-testid="stDataFrame"] [role="grid"],
        [data-testid="stDataFrame"] [role="row"],
        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stDataFrame"] [role="gridcell"] {{
            background: {COLORS['surface']} !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background: {COLORS["surface"]} !important;
            border-bottom: 1px solid {COLORS["border"]} !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0 !important;
            color: {COLORS['text_primary']} !important;
            background: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            color: {COLORS['text_primary']} !important;
            background: {COLORS['surface']} !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: {COLORS["primary"]} !important;
            color: {COLORS['text_primary']} !important;
            border: 1px solid {COLORS["primary"]} !important;
        }}

        /* Expander-Abstände straffen */
        [data-testid="stExpander"] {{
            margin-top: 0.35rem !important;
            margin-bottom: 0.35rem !important;
        }}

        .complio-form-group {{
            background: {COLORS['surface']};
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            padding: 0.85rem 0.95rem 0.65rem 0.95rem;
            margin: 0.5rem 0 0.9rem 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_login_css():
    """Professionelles Login-Styling für Complio."""
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: #0a0a0a !important;
    }
    .login-topbar {
        background: #0a0a0a;
        border-bottom: 1px solid #1f1f1f;
        padding: 16px 32px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0;
    }
    .login-logo {
        font-size: 26px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.5px;
    }
    .login-logo span { color: #F97316; }
    .login-tagline {
        font-size: 11px;
        color: #444;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }
    .login-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        min-height: 75vh;
        border-bottom: 1px solid #1a1a1a;
    }
    .login-left {
        background: #0a0a0a;
        padding: 48px;
        border-right: 1px solid #1a1a1a;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .login-left h1 {
        font-size: 30px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        line-height: 1.3 !important;
        margin-bottom: 12px !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    .login-left h1 em { color: #F97316; font-style: normal; }
    .login-left p {
        font-size: 14px;
        color: #666;
        line-height: 1.7;
        margin-bottom: 36px;
    }
    .login-stat {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 16px;
    }
    .login-stat-icon {
        width: 34px;
        height: 34px;
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 7px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        font-size: 14px;
    }
    .login-stat-text { font-size: 13px; color: #777; }
    .login-stat-text strong { color: #bbb; font-weight: 500; }
    .login-right {
        background: #111111;
        padding: 48px;
    }
    .login-footer {
        background: #0a0a0a;
        border-top: 1px solid #1a1a1a;
        padding: 14px 32px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .login-footer-text { font-size: 11px; color: #333; }
    .login-trust { display: flex; gap: 20px; }
    .login-trust-item { font-size: 11px; color: #444; }
    .login-trust-item span { color: #F97316; margin-right: 4px; }
    .register-hint {
        text-align: center;
        font-size: 13px;
        color: #555;
        margin-top: 16px;
    }
    .register-hint a { color: #F97316 !important; font-weight: 500; }
    @media (max-width: 768px) {
        .login-grid { grid-template-columns: 1fr; }
        .login-left { display: none; }
        .login-right { padding: 24px; }
    }
    </style>
    """, unsafe_allow_html=True)


def create_card(title: str, content: str) -> None:
    st.markdown(
        f"""
        <div style="
            background:{COLORS["surface"]};
            border:1px solid {COLORS["border"]};
            border-radius:12px;
            box-shadow:none;
            padding:1rem 1.1rem;
            margin:0.5rem 0;">
            <h4 style="margin:0 0 0.35rem 0; color:{COLORS['text_primary']};">{title}</h4>
            <div style="color:{COLORS['text_primary']};">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
