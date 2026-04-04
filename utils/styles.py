"""Globales UI-Framework mit strengem Kontrastmanagement."""

import streamlit as st

COLORS = {
    "app_bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "surface_dark": "#000000",
    "border": "#E2E8F0",
    "text_on_light": "#000000",
    "text_on_dark": "#FFFFFF",
    "muted_on_light": "#111111",
    "primary": "#000000",
    "primary_hover": "#111111",
}


def apply_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, .stApp, [data-testid="stAppViewContainer"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            background: {COLORS["app_bg"]} !important;
            color: {COLORS["text_on_light"]} !important;
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
            background: {COLORS["app_bg"]};
            border-bottom: 1px solid {COLORS["border"]};
            padding: 0.25rem 0 0.5rem 0;
            margin-bottom: 1rem;
        }}

        .coreo-card {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
            padding: 1rem;
            margin-bottom: 1rem;
        }}

        .st-key-header_logo img {{
            height: 92px !important;
            width: auto !important;
            object-fit: contain !important;
        }}

        /* Kontrastregel: Auf hellem Grund schwarz, auf dunklem Grund weiß */
        h1, h2, h3, h4, h5, h6, p, span, label, div,
        [data-testid="stMarkdownContainer"], [data-testid="stText"], [data-testid="stMetricLabel"] {{
            color: {COLORS["text_on_light"]} !important;
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

        /* Card-Surfaces */
        div[data-testid="stMetric"],
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-baseweb="tab-panel"] > div {{
            background: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04) !important;
            color: {COLORS["text_on_light"]} !important;
        }}

        /* Buttons */
        .stButton > button,
        .stDownloadButton > button {{
            min-height: 42px !important;
            border-radius: 8px !important;
            border: 1px solid {COLORS["border"]} !important;
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
            color: {COLORS["text_on_light"]} !important;
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
            background: {COLORS["surface"]} !important;
            color: {COLORS["text_on_light"]} !important;
            min-height: 42px !important;
            -webkit-text-fill-color: {COLORS["text_on_light"]} !important;
            opacity: 1 !important;
        }}

        .stTextInput input::placeholder,
        .stNumberInput input::placeholder,
        .stDateInput input::placeholder,
        .stTextArea textarea::placeholder {{
            color: {COLORS["muted_on_light"]} !important;
            opacity: 1 !important;
        }}

        /* DataFrames/Tables mit starkem Kontrast */
        [data-testid="stDataFrame"] *,
        [data-testid="stTable"] *,
        .dataframe * {{
            color: {COLORS["text_on_light"]} !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background: transparent !important;
            border-bottom: 1px solid {COLORS["border"]} !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0 !important;
            color: {COLORS["text_on_light"]} !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: {COLORS["surface"]} !important;
            color: {COLORS["text_on_light"]} !important;
            border: 1px solid {COLORS["border"]} !important;
        }}

        /* Expander-Abstände straffen */
        [data-testid="stExpander"] {{
            margin-top: 0.35rem !important;
            margin-bottom: 0.35rem !important;
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
            box-shadow:0 2px 10px rgba(15,23,42,0.04);
            padding:1rem 1.1rem;
            margin:0.5rem 0;">
            <h4 style="margin:0 0 0.35rem 0; color:{COLORS["text_on_light"]};">{title}</h4>
            <div style="color:{COLORS["muted_on_light"]};">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
