"""Globales UI-Framework im SaaS-Stil."""

import streamlit as st

COLORS = {
    "app_bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "border": "#E2E8F0",
    "text": "#0F172A",
    "muted": "#64748B",
    "primary": "#0F172A",
    "primary_hover": "#1E293B",
}


def apply_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, .stApp, [data-testid="stAppViewContainer"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            background: {COLORS["app_bg"]} !important;
            color: {COLORS["text"]} !important;
        }}

        [data-testid="stSidebar"] {{
            display: none !important;
        }}

        .block-container {{
            max-width: 1280px !important;
            padding-top: 1.2rem !important;
            padding-bottom: 1.2rem !important;
        }}

        h1, h2, h3, h4, h5, h6, p, span, label, div {{
            color: {COLORS["text"]};
        }}

        /* Card surfaces for common blocks */
        div[data-testid="stMetric"],
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-baseweb="tab-panel"] > div {{
            background: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04) !important;
        }}

        .stButton > button,
        .stDownloadButton > button {{
            min-height: 42px !important;
            border-radius: 8px !important;
            border: 1px solid {COLORS["border"]} !important;
            background: {COLORS["primary"]} !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            background: {COLORS["primary_hover"]} !important;
        }}

        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        .stTextArea textarea,
        [data-baseweb="select"] > div {{
            border-radius: 10px !important;
            border: 1px solid {COLORS["border"]} !important;
            background: #FFFFFF !important;
            color: {COLORS["text"]} !important;
            min-height: 42px !important;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            background: transparent !important;
            border-bottom: 1px solid {COLORS["border"]} !important;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0 !important;
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
            <h4 style="margin:0 0 0.35rem 0; color:{COLORS["text"]};">{title}</h4>
            <div style="color:{COLORS["muted"]};">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
