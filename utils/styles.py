"""Globales UI-Framework mit Dark-Mode und maximalem Kontrast."""

import streamlit as st

COLORS = {
    "app_bg": "#000000",
    "surface": "#000000",
    "surface_alt": "#000000",
    "surface_light": "#FFFFFF",
    "border": "#FFFFFF",
    "text_on_light": "#000000",
    "text_on_dark": "#FFFFFF",
    "muted_on_light": "#000000",
    "muted_on_dark": "#FFFFFF",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
}


def apply_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            background: {COLORS["app_bg"]} !important;
            color: {COLORS["text_on_dark"]} !important;
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

        .coreo-topbar {{
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

        .coreo-card {{
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
            color: {COLORS["text_on_dark"]} !important;
        }}

        [style*="background: #000"], [style*="background:#000"], [style*="background-color: #000"],
        [style*="background-color:#000"], [style*="background: rgb(0, 0, 0)"],
        [style*="background-color: rgb(0, 0, 0)"] {{
            color: {COLORS["text_on_dark"]} !important;
        }}
        [style*="background: #000"] *, [style*="background:#000"] *, [style*="background-color: #000"] *,
        [style*="background-color:#000"] *, [style*="background: rgb(0, 0, 0)"] *,
        [style*="background-color: rgb(0, 0, 0)"] * {{
            color: {COLORS["text_on_dark"]} !important;
        }}
        /* Wenn irgendwo weißer Hintergrund auftaucht, erzwinge schwarze Schrift */
        [style*="background:#fff"], [style*="background: #fff"], [style*="background:#ffffff"],
        [style*="background: #ffffff"], [style*="background-color:#fff"], [style*="background-color: #fff"],
        [style*="background-color:#ffffff"], [style*="background-color: #ffffff"] {{
            color: {COLORS["text_on_light"]} !important;
        }}
        [style*="background:#fff"] *, [style*="background: #fff"] *, [style*="background:#ffffff"] *,
        [style*="background: #ffffff"] *, [style*="background-color:#fff"] *, [style*="background-color: #fff"] *,
        [style*="background-color:#ffffff"] *, [style*="background-color: #ffffff"] * {{
            color: {COLORS["text_on_light"]} !important;
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
            color: {COLORS["text_on_dark"]} !important;
        }}

        /* Buttons */
        .stButton > button,
        .stDownloadButton > button {{
            min-height: 42px !important;
            border-radius: 8px !important;
            border: 1px solid {COLORS["primary"]} !important;
            background: {COLORS["primary"]} !important;
            color: {COLORS["text_on_dark"]} !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
        }}
        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            background: {COLORS["primary_hover"]} !important;
            color: {COLORS["text_on_dark"]} !important;
        }}

        /* Inputs: Label + Text strikt kontrastreich */
        .stTextInput label, .stNumberInput label, .stDateInput label, .stTextArea label,
        [data-testid="stWidgetLabel"] {{
            color: {COLORS["text_on_dark"]} !important;
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
            background: {COLORS["surface_alt"]} !important;
            color: {COLORS["text_on_dark"]} !important;
            min-height: 42px !important;
            -webkit-text-fill-color: {COLORS["text_on_dark"]} !important;
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
            background: {COLORS["app_bg"]} !important;
            color: {COLORS["text_on_dark"]} !important;
            -webkit-text-fill-color: {COLORS["text_on_dark"]} !important;
        }}
        .stTextInput input:active,
        .stNumberInput input:active,
        .stDateInput input:active,
        .stTextArea textarea:active {{
            color: {COLORS["text_on_dark"]} !important;
            -webkit-text-fill-color: {COLORS["text_on_dark"]} !important;
        }}
        .stDateInput button,
        .stDateInput svg,
        .stNumberInput button,
        [data-baseweb="select"] svg {{
            color: {COLORS["text_on_dark"]} !important;
            fill: {COLORS["text_on_dark"]} !important;
        }}

        .stTextInput input::placeholder,
        .stNumberInput input::placeholder,
        .stDateInput input::placeholder,
        .stTextArea textarea::placeholder {{
            color: {COLORS["muted_on_dark"]} !important;
            opacity: 1 !important;
        }}
        [role="listbox"] {{
            background: {COLORS["surface_alt"]} !important;
            color: {COLORS["text_on_dark"]} !important;
        }}
        [role="option"] {{
            background: {COLORS["surface_alt"]} !important;
            color: {COLORS["text_on_dark"]} !important;
        }}
        [role="option"]:hover {{
            background: {COLORS["primary"]} !important;
            color: {COLORS["text_on_dark"]} !important;
        }}

        /* DataFrames/Tables mit starkem Kontrast */
        [data-testid="stDataFrame"] *,
        [data-testid="stTable"] *,
        .dataframe * {{
            color: {COLORS["text_on_dark"]} !important;
        }}
        [data-testid="stDataFrame"] [role="grid"],
        [data-testid="stDataFrame"] [role="row"],
        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stDataFrame"] [role="gridcell"] {{
            background: {COLORS["surface_alt"]} !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background: {COLORS["surface"]} !important;
            border-bottom: 1px solid {COLORS["border"]} !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0 !important;
            color: {COLORS["text_on_dark"]} !important;
            background: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            color: {COLORS["text_on_dark"]} !important;
            background: {COLORS["surface_alt"]} !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: {COLORS["primary"]} !important;
            color: {COLORS["text_on_dark"]} !important;
            border: 1px solid {COLORS["primary"]} !important;
        }}

        /* Expander-Abstände straffen */
        [data-testid="stExpander"] {{
            margin-top: 0.35rem !important;
            margin-bottom: 0.35rem !important;
        }}

        .coreo-form-group {{
            background: {COLORS["surface_alt"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            padding: 0.85rem 0.95rem 0.65rem 0.95rem;
            margin: 0.5rem 0 0.9rem 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
            <h4 style="margin:0 0 0.35rem 0; color:{COLORS["text_on_dark"]};">{title}</h4>
            <div style="color:{COLORS["text_on_dark"]};">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
