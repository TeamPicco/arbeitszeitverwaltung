"""
Edles einheitliches Farbschema und Styling für CrewBase
Fokus: Lesbarkeit, Eleganz, Professionalität
"""

import streamlit as st

# Edles Farbschema - Dunkelblau/Gold/Weiß
COLORS = {
    # Primärfarben (Complio Schwarz/Orange)
    'primary': '#F97316',
    'primary_light': '#FB923C',
    'primary_dark': '#0a0a0a',

    # Akzentfarben
    'accent': '#F97316',
    'accent_light': '#FDBA74',

    # Statusfarben
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'info': '#F97316',

    # Neutrale Farben
    'background': '#0a0a0a',
    'surface': '#111111',
    'border': '#1f1f1f',

    # Textfarben
    'text_primary': '#ffffff',
    'text_secondary': '#a3a3a3',
    'text_light': '#ffffff',
}


def apply_custom_css():
    """Wendet globales Custom CSS an"""
    
    st.markdown(f"""
    <style>
    /* ===== MOBILE OPTIMIERUNG ===== */
    @media (max-width: 768px) {{
        /* Kleinere Schrift auf Mobile */
        .stMarkdown, .stText {{
            font-size: 14px !important;
        }}
        
        /* Buttons volle Breite auf Mobile */
        .stButton > button {{
            width: 100% !important;
        }}
        
        /* Kleinere Abstände */
        .block-container {{
            padding: 0.5rem !important;
        }}
        
        /* Tabellen scrollbar */
        .dataframe {{
            overflow-x: auto !important;
        }}
        
        /* Titel auf Mobile */
        h1 {{
            font-size: 1.5rem !important;
            word-wrap: break-word !important;
        }}
        
        /* Tabs auf Mobile */
        .stTabs [data-baseweb="tab"] {{
            font-size: 12px !important;
            padding: 0.4rem 0.6rem !important;
        }}
    }}
    
    /* ===== GLOBALE STYLES ===== */
    .stApp {{
        background-color: {COLORS['background']} !important;
    }}
    
    /* Hauptcontainer */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }}
    
    /* ALLE TEXTE DUNKEL */
    .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span,
    .stText, .element-container, label, .stSelectbox label,
    [data-testid="stMarkdownContainer"], [data-testid="stText"] {{
        color: {COLORS['text_primary']} !important;
    }}
    
    /* Selectbox Dropdown - HAUPTBEREICH (heller Hintergrund) */
    .stSelectbox > div > div > div,
    .stSelectbox > div > div > div > div,
    .stSelectbox > div,
    .stSelectbox,
    [data-baseweb="select"],
    [data-baseweb="select"] > div {{
        color: {COLORS['text_primary']} !important;
        background-color: {COLORS['background']} !important;
    }}
    
    /* Selectbox Container - KEIN overflow:hidden, kein Clipping */
    .stSelectbox > div {{
        background-color: {COLORS['surface']} !important;
        border-radius: 8px !important;
        padding: 0 !important;
        overflow: visible !important;
    }}
    
    /* ===== SELECTBOX DROPDOWN - VOLLSTÄNDIGER CLIPPING FIX ===== */
    /* Problem: Text (z.B. "2026", "Februar") wird als kleine Striche oben angezeigt */
    /* Ursache: height/padding-Konflikte zwischen Streamlit-internen Stilen */
    
    /* Äußerster Container */
    div[data-baseweb="select"] {{
        overflow: visible !important;
        background-color: {COLORS['background']} !important;
    }}
    
    /* Zweite Ebene - der eigentliche Klick-Bereich */
    div[data-baseweb="select"] > div {{
        line-height: normal !important;
        height: auto !important;
        min-height: 48px !important;
        max-height: none !important;
        overflow: visible !important;
        padding: 8px 14px !important;
        background-color: {COLORS['background']} !important;
        color: {COLORS['text_primary']} !important;
        display: flex !important;
        align-items: center !important;
    }}
    
    /* Role=button (der sichtbare Selectbox-Bereich) */
    div[data-baseweb="select"] [role="button"] {{
        line-height: normal !important;
        height: auto !important;
        min-height: 48px !important;
        max-height: none !important;
        overflow: visible !important;
        padding: 8px 14px !important;
        color: {COLORS['text_primary']} !important;
        background-color: {COLORS['background']} !important;
        font-weight: 500 !important;
        font-size: 16px !important;
        display: flex !important;
        align-items: center !important;
    }}
    
    /* Alle Kindelemente des role=button */
    div[data-baseweb="select"] [role="button"] > div,
    div[data-baseweb="select"] [role="button"] > div > div,
    div[data-baseweb="select"] [role="button"] span,
    div[data-baseweb="select"] [role="button"] p,
    div[data-baseweb="select"] [role="button"] * {{
        line-height: normal !important;
        overflow: visible !important;
        color: {COLORS['text_primary']} !important;
        font-weight: 500 !important;
        font-size: 16px !important;
        height: auto !important;
        max-height: none !important;
        white-space: nowrap !important;
        display: inline !important;
        vertical-align: middle !important;
    }}
    
    /* Verhindert dass Streamlit intern height:0 oder clip setzt */
    div[data-baseweb="select"] [role="button"] > div:first-child {{
        flex: 1 !important;
        display: flex !important;
        align-items: center !important;
        height: auto !important;
        min-height: 32px !important;
        overflow: visible !important;
        padding: 0 !important;
    }}
    
    /* Dropdown-Liste (geöffnet) */
    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] li,
    div[data-baseweb="menu"] [role="option"] {{
        line-height: normal !important;
        padding: 10px 16px !important;
        color: {COLORS['text_primary']} !important;
        background-color: {COLORS['background']} !important;
        overflow: visible !important;
        font-size: 16px !important;
        height: auto !important;
    }}
    
    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="menu"] [role="option"]:hover {{
        background-color: {COLORS['surface']} !important;
        color: {COLORS['primary']} !important;
    }}
    
    /* Date Input */
    .stDateInput > div > div > div,
    .stDateInput label {{
        color: {COLORS['text_primary']} !important;
    }}
    
    /* ===== CHECKBOXEN ===== */
    .stCheckbox label,
    .stCheckbox > div > div > div > label,
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] span {{
        color: {COLORS['text_primary']} !important;
        font-weight: 500 !important;
    }}
    
    .stCheckbox {{
        background-color: {COLORS['surface']} !important;
        padding: 0.5rem !important;
        border-radius: 6px !important;
    }}
    
    /* ===== BUTTONS ===== */
    .stButton > button {{
        background-color: {COLORS['primary']};
        color: {COLORS['text_light']} !important;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }}
    
    .stButton > button:hover {{
        background-color: {COLORS['primary_light']};
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        color: {COLORS['text_light']} !important;
    }}
    
    /* Primary Button */
    .stButton > button[kind="primary"] {{
        background-color: {COLORS['accent']};
        color: {COLORS['text_light']} !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background-color: {COLORS['accent_light']};
        color: {COLORS['text_light']} !important;
    }}
    
    /* Secondary Button */
    .stButton > button[kind="secondary"] {{
        background-color: {COLORS['surface']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
    }}
    
    /* ===== INPUTS ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stSelectbox > div > div,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input {{
        border: 1px solid {COLORS['border']} !important;
        border-radius: 6px !important;
        padding: 0.5rem !important;
        background-color: {COLORS['background']} !important;
        color: {COLORS['text_primary']} !important;
    }}
    
    /* Selectbox Text */
    .stSelectbox label,
    .stSelectbox > div > div > div {{
        color: {COLORS['text_primary']} !important;
    }}
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {{
        border-color: {COLORS['primary']} !important;
        box-shadow: 0 0 0 2px rgba(30, 58, 95, 0.1) !important;
    }}
    
    /* ===== METRICS ===== */
    .stMetric {{
        background-color: {COLORS['surface']} !important;
        padding: 1rem !important;
        border-radius: 8px !important;
        border-left: 4px solid {COLORS['accent']} !important;
    }}
    
    .stMetric label {{
        color: {COLORS['text_primary']} !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }}
    
    .stMetric [data-testid="stMetricValue"] {{
        color: {COLORS['text_primary']} !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
    }}
    
    .stMetric div {{
        color: {COLORS['text_primary']} !important;
    }}
    
    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {{
        background-color: {COLORS['surface']} !important;
        color: {COLORS['text_primary']} !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }}
    
    .streamlit-expanderHeader:hover {{
        background-color: {COLORS['border']} !important;
    }}
    
    .streamlit-expanderContent {{
        background-color: {COLORS['background']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 0 0 8px 8px !important;
        padding: 1rem !important;
    }}
    
    /* Alter Expander-Code: */
    .streamlit-expanderHeader_OLD {{
        background-color: {COLORS['surface']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-weight: 500 !important;
        color: {COLORS['text_primary']} !important;
    }}
    
    .streamlit-expanderHeader:hover {{
        background-color: {COLORS['primary']} !important;
        color: {COLORS['text_light']} !important;
    }}
    
    /* Expander Content */
    .streamlit-expanderContent {{
        background-color: {COLORS['background']} !important;
        color: {COLORS['text_primary']} !important;
    }}
    
    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {COLORS['surface']};
        padding: 0.5rem;
        border-radius: 8px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent;
        border-radius: 6px;
        color: {COLORS['text_secondary']};
        font-weight: 500;
        padding: 0.5rem 1rem;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: #e3f2fd !important;  /* Hellblau für aktiven Tab */
        color: {COLORS['text_primary']} !important;
    }}
    
    /* WICHTIG: Tabs sind KEINE Buttons - schwarze Schrift auf hellem Hintergrund */
    .stTabs [data-baseweb="tab"],
    .stTabs [data-baseweb="tab"] *,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [aria-selected="true"],
    .stTabs [aria-selected="true"] *,
    .stTabs [aria-selected="true"] span {{
        color: {COLORS['text_primary']} !important;
    }}
    
    /* Inaktive Tabs: Grau */
    .stTabs [aria-selected="false"],
    .stTabs [aria-selected="false"] *,
    .stTabs [aria-selected="false"] span {{
        color: {COLORS['text_secondary']} !important;
    }}
    
    /* ===== DUNKLE HINTERGRÜNDE → WEISSE SCHRIFT ===== */
    /* Date Input mit dunklem Hintergrund */
    .stDateInput input,
    .stDateInput input::placeholder,
    .stDateInput [data-baseweb="input"] input {{
        color: {COLORS['text_light']} !important;
        background-color: #2c3e50 !important;
    }}
    
    /* Selectbox mit dunklem Hintergrund - ENTFERNT (Konflikt mit Hauptbereich) */
    
    /* Number Input mit dunklem Hintergrund */
    .stNumberInput input,
    .stNumberInput [data-baseweb="input"] input {{
        background-color: #2c3e50 !important;
        color: {COLORS['text_light']} !important;
    }}
    
    /* Text Area mit dunklem Hintergrund */
    .stTextArea textarea,
    .stTextArea [data-baseweb="textarea"] textarea {{
        background-color: #2c3e50 !important;
        color: {COLORS['text_light']} !important;
    }}
    
    /* Expander mit dunklem Hintergrund - WEISSE SCHRIFT */
    [data-baseweb="accordion"] [role="button"],
    .streamlit-expanderHeader {{
        background-color: #2c3e50 !important;
        color: {COLORS['text_light']} !important;
    }}
    
    /* Buttons mit dunklem Hintergrund - WEISSE SCHRIFT */
    button[kind="secondary"],
    .stButton > button[kind="secondary"] {{
        background-color: #2c3e50 !important;
        color: {COLORS['text_light']} !important;
    }}
    
    /* ALLE Elemente mit dunklem Hintergrund (#2c3e50, #343a40, etc.) */
    div[style*="background-color: rgb(44, 62, 80)"],
    div[style*="background-color: rgb(52, 58, 64)"],
    div[style*="background-color:#2c3e50"],
    div[style*="background-color:#343a40"] {{
        color: {COLORS['text_light']} !important;
    }}
    
    div[style*="background-color: rgb(44, 62, 80)"] *,
    div[style*="background-color: rgb(52, 58, 64)"] *,
    div[style*="background-color:#2c3e50"] *,
    div[style*="background-color:#343a40"] * {{
        color: {COLORS['text_light']} !important;
    }}
    
    /* ===== DATAFRAME ===== */
    .dataframe {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        overflow: hidden;
        background-color: {COLORS['background']};
    }}
    
    .dataframe thead tr th {{
        background-color: {COLORS['primary']} !important;
        color: {COLORS['text_light']} !important;
        font-weight: 600 !important;
        padding: 0.75rem !important;
        text-align: left !important;
        border-bottom: 2px solid {COLORS['accent']} !important;
    }}
    
    .dataframe tbody tr {{
        background-color: {COLORS['background']} !important;
    }}
    
    .dataframe tbody tr:nth-child(even) {{
        background-color: {COLORS['surface']} !important;
    }}
    
    .dataframe tbody tr:hover {{
        background-color: rgba(212, 175, 55, 0.1) !important;
    }}
    
    .dataframe tbody td {{
        color: {COLORS['text_primary']} !important;
        padding: 0.75rem !important;
        border-bottom: 1px solid {COLORS['border']} !important;
    }}
    
    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {{
        background-color: {COLORS['primary_dark']};
    }}
    
    /* Streamlit-eigenes Sidebar-Header-Feld (weißes Logo-Feld oben) verstecken */
    [data-testid="stSidebarHeader"],
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    [data-testid="stSidebarNavSeparator"],
    .stSidebarHeader,
    section[data-testid="stSidebar"] > div:first-child > div:first-child > div:first-child > div[style*="white"],
    section[data-testid="stSidebar"] [data-testid="stImage"],
    [data-testid="stSidebar"] [data-testid="stLogo"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        overflow: hidden !important;
    }}
    
    /* Streamlit App-Logo in Sidebar verstecken (weißes Feld) */
    [data-testid="stSidebar"] > div > div > div > div > img,
    [data-testid="stSidebar"] img[class*="logo"],
    [data-testid="stSidebar"] > div:first-child > div:first-child {{
        background-color: {COLORS['primary_dark']} !important;
    }}
    
    /* Alle Texte in der Sidebar WEISS */
    [data-testid="stSidebar"] .stMarkdown {{
        color: {COLORS['text_light']} !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown div,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] * {{
        color: {COLORS['text_light']} !important;
        background-color: transparent !important;
    }}
    
    /* Ausnahme: Buttons in Sidebar behalten ihren Hintergrund */
    [data-testid="stSidebar"] .stButton > button {{
        background-color: {COLORS['accent']} !important;
        color: {COLORS['text_light']} !important;
    }}
    
    /* ===== FORCE WHITE TEXT ON ALL DARK BUTTONS ===== */
    /* Alle Buttons mit dunklem Hintergrund MÜSSEN weiße Schrift haben */
    .stButton > button,
    button[kind="primary"],
    button[kind="secondary"],
    button[data-baseweb="button"],
    [data-testid="baseButton-primary"],
    [data-testid="baseButton-secondary"],
    [data-testid="baseButton-minimal"] {{
        color: {COLORS['text_light']} !important;
    }}
    
    /* Spezifisch für dunkle Hintergründe */
    .stButton > button[style*="background"],
    button[style*="background-color: rgb(30, 58, 95)"],
    button[style*="background-color: rgb(44, 82, 130)"],
    button[style*="background-color: rgb(212, 175, 55)"] {{
        color: {COLORS['text_light']} !important;
    }}
    
    /* Alle Buttons in der Hauptseite */
    [data-testid="stApp"] .stButton > button {{
        color: {COLORS['text_light']} !important;
    }}
    
    /* ULTRA-STARKE REGEL: Alle Button-Texte MÜSSEN weiss sein */
    .stButton > button,
    .stButton > button *,
    .stButton > button span,
    .stButton > button p,
    .stButton > button div,
    button,
    button *,
    button span {{
        color: {COLORS['text_light']} !important;
    }}
    
    /* Spezifisch für Buttons mit dunklem Hintergrund */
    .stButton > button[style*="background-color"],
    button[style*="background-color: rgb"] {{
        color: {COLORS['text_light']} !important;
    }}
    
    /* Noch spezifischer: Alle Kindelemente von Buttons */
    .stButton button > *,
    .stButton button span,
    .stButton button p {{
        color: {COLORS['text_light']} !important;
    }}
    
    /* ===== ALERTS ===== */
    .stSuccess {{
        background-color: rgba(45, 106, 79, 0.1);
        border-left: 4px solid {COLORS['success']};
        color: {COLORS['success']};
        padding: 1rem;
        border-radius: 6px;
    }}
    
    .stWarning {{
        background-color: rgba(183, 121, 31, 0.1);
        border-left: 4px solid {COLORS['warning']};
        color: {COLORS['warning']};
        padding: 1rem;
        border-radius: 6px;
    }}
    
    .stError {{
        background-color: rgba(155, 44, 44, 0.1);
        border-left: 4px solid {COLORS['error']};
        color: {COLORS['error']};
        padding: 1rem;
        border-radius: 6px;
    }}
    
    .stInfo {{
        background-color: rgba(44, 82, 130, 0.1);
        border-left: 4px solid {COLORS['info']};
        color: {COLORS['info']};
        padding: 1rem;
        border-radius: 6px;
    }}
    
    /* ===== HEADINGS ===== */
    h1, h2, h3 {{
        color: {COLORS['primary']} !important;
        font-weight: 600 !important;
        background-color: {COLORS['background']} !important;
        padding: 0.5rem !important;
    }}
    
    h1 {{
        border-bottom: 3px solid {COLORS['accent']} !important;
        padding-bottom: 0.5rem !important;
        background-color: {COLORS['surface']} !important;
    }}
    
    /* ===== LINKS ===== */
    a {{
        color: {COLORS['primary']};
        text-decoration: none;
        font-weight: 500;
    }}
    
    a:hover {{
        color: {COLORS['accent']};
        text-decoration: underline;
    }}
    
    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {COLORS['surface']};
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {COLORS['primary']};
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS['primary_light']};
    }}

    /* ===== FINAL DARK OVERRIDE (highest priority) ===== */
    html, body, [data-testid="stAppViewContainer"], .stApp {{
        background: #000000 !important;
        color: #ffffff !important;
    }}

    .block-container {{
        background: transparent !important;
    }}

    [data-testid="stHeader"], [data-testid="stToolbar"] {{
        background: #000000 !important;
    }}

    h1, h2, h3, h4, h5, h6,
    p, span, div, label, small, li,
    [data-testid="stMarkdownContainer"], [data-testid="stText"] {{
        color: #ffffff !important;
    }}

    [data-testid="stSidebar"] {{
        background: #050505 !important;
        border-right: 1px solid #1f2937 !important;
    }}

    /* Inputs */
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTimeInput input,
    .stTextArea textarea,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="select"] > div {{
        background: #111111 !important;
        color: #ffffff !important;
        border: 1px solid #2a2a2a !important;
    }}

    /* Buttons */
    .stButton > button,
    .stDownloadButton > button,
    button[data-baseweb="button"] {{
        background: #111111 !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }}

    .stButton > button:hover,
    .stDownloadButton > button:hover {{
        border-color: #60a5fa !important;
        box-shadow: 0 0 0 1px #60a5fa inset !important;
    }}

    /* Cards / Metrics / Expander / Tables */
    .stMetric,
    [data-testid="stMetric"],
    [data-testid="stExpander"],
    .streamlit-expanderHeader,
    .streamlit-expanderContent,
    [data-testid="stDataFrame"] {{
        background: #0b0b0b !important;
        color: #ffffff !important;
        border: 1px solid #1f2937 !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        background: #0b0b0b !important;
        border: 1px solid #1f2937 !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        color: #cbd5e1 !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: #111827 !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
    }}
    </style>
    """, unsafe_allow_html=True)


def apply_login_css():
    """Professionelles Login-Styling für Complio."""
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: #0a0a0a !important;
    }
    .login-screen {
        background: #0a0a0a;
        min-height: 100vh;
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
    .login-left h1 em {
        color: #F97316;
        font-style: normal;
    }
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
    .login-stat-text {
        font-size: 13px;
        color: #777;
        line-height: 1.4;
    }
    .login-stat-text strong {
        color: #bbb;
        font-weight: 500;
    }
    .login-right {
        background: #111111;
        padding: 48px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .login-footer {
        background: #0a0a0a;
        border-top: 1px solid #1a1a1a;
        padding: 14px 32px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .login-footer-text {
        font-size: 11px;
        color: #333;
    }
    .login-trust {
        display: flex;
        gap: 20px;
    }
    .login-trust-item {
        font-size: 11px;
        color: #444;
    }
    .login-trust-item span {
        color: #F97316;
        margin-right: 4px;
    }
    .register-hint {
        text-align: center;
        font-size: 13px;
        color: #555;
        margin-top: 16px;
    }
    .register-hint a {
        color: #F97316 !important;
        font-weight: 500;
        text-decoration: none;
    }
    @media (max-width: 768px) {
        .login-grid { grid-template-columns: 1fr; }
        .login-left { display: none; }
        .login-right { padding: 24px; }
        .login-topbar { padding: 12px 16px; }
    }
    </style>
    """, unsafe_allow_html=True)


def get_status_color(status: str) -> str:
    """Gibt die Farbe für einen Status zurück"""
    status_lower = status.lower()
    
    if status_lower in ['genehmigt', 'approved', 'aktiv', 'active']:
        return COLORS['success']
    elif status_lower in ['beantragt', 'pending', 'ausstehend']:
        return COLORS['warning']
    elif status_lower in ['abgelehnt', 'rejected', 'inaktiv', 'inactive']:
        return COLORS['error']
    else:
        return COLORS['info']


def create_card(title: str, content: str, color: str = None):
    """Erstellt eine elegante Karte"""
    border_color = color or COLORS['accent']
    
    st.markdown(f"""
    <div style="
        background-color: {COLORS['surface']};
        border-left: 4px solid {border_color};
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    ">
        <h3 style="color: {COLORS['primary']}; margin-top: 0;">{title}</h3>
        <div style="color: {COLORS['text_primary']};">{content}</div>
    </div>
    """, unsafe_allow_html=True)


# Einheitliches Icon-System - Elegant und professionell
ICONS = {
    # Navigation
    'dashboard': '🧭',
    'mitarbeiter': '🧑‍💼',
    'urlaub': '🏝️',
    'zeit': '🕒',
    'dienstplan': '🗓️',
    'lohn': '💶',
    'einstellungen': '🛠️',
    'chat': '🗨️',
    'mastergeraete': '📱',

    # Aktionen
    'neu': '✚',
    'bearbeiten': '✎',
    'loeschen': '🗑',
    'speichern': '⬢',
    'abbrechen': '✕',
    'suchen': '⌕',
    'filter': '⛃',
    'download': '⬇',
    'upload': '⬆',

    # Status
    'erfolg': '✔',
    'warnung': '⚠',
    'fehler': '✖',
    'info': 'ⓘ',
    'ausstehend': '◴',
    'genehmigt': '✔',
    'abgelehnt': '✖',

    # Sonstiges
    'benachrichtigung': '🔔',
    'statistik': '📈',
    'dokument': '🧾',
    'email': '✉',
    'telefon': '☎',
    'adresse': '⌂',
    'geburtstag': '🎂',
    'vertrag': '📜',
}


def get_icon(name: str) -> str:
    """Gibt das Icon für einen Namen zurück"""
    return ICONS.get(name, '▪️')  # Fallback: Kleines Quadrat
