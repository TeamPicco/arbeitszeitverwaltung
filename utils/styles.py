"""
Edles einheitliches Farbschema und Styling für CrewBase
Fokus: Lesbarkeit, Eleganz, Professionalität
"""

import streamlit as st

# Edles Farbschema - Dunkelblau/Gold/Weiß
COLORS = {
    # Primärfarben
    'primary': '#1e3a5f',      # Dunkles elegantes Blau
    'primary_light': '#2c5282', # Helleres Blau
    'primary_dark': '#0f1f3a',  # Sehr dunkles Blau
    
    # Akzentfarben
    'accent': '#d4af37',        # Elegantes Gold
    'accent_light': '#f4d03f',  # Helles Gold
    
    # Statusfarben
    'success': '#2d6a4f',       # Dunkles Grün
    'warning': '#b7791f',       # Dunkles Orange/Gold
    'error': '#9b2c2c',         # Dunkles Rot
    'info': '#2c5282',          # Blau
    
    # Neutrale Farben
    'background': '#ffffff',    # Weiß
    'surface': '#f8f9fa',       # Sehr helles Grau
    'border': '#dee2e6',        # Helles Grau
    
    # Textfarben
    'text_primary': '#212529',  # Fast Schwarz
    'text_secondary': '#6c757d', # Mittelgrau
    'text_light': '#ffffff',    # Weiß
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
    
    /* Selectbox Dropdown */
    .stSelectbox > div > div > div,
    .stSelectbox > div > div > div > div,
    .stSelectbox > div,
    .stSelectbox,
    [data-baseweb="select"],
    [data-baseweb="select"] > div {{
        color: {COLORS['text_primary']} !important;
        background-color: {COLORS['background']} !important;
    }}
    
    /* Selectbox Container */
    .stSelectbox > div {{
        background-color: {COLORS['surface']} !important;
        border-radius: 8px !important;
        padding: 0.5rem !important;
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
        color: {COLORS['text_light']};
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }}
    
    .stButton > button:hover {{
        background-color: {COLORS['primary_light']};
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    
    /* Primary Button */
    .stButton > button[kind="primary"] {{
        background-color: {COLORS['accent']};
        color: {COLORS['text_primary']};
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background-color: {COLORS['accent_light']};
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
        background-color: {COLORS['primary']};
        color: {COLORS['text_light']};
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
    
    [data-testid="stSidebar"] .stMarkdown {{
        color: {COLORS['text_light']};
    }}
    
    [data-testid="stSidebar"] .stButton > button {{
        background-color: {COLORS['accent']};
        color: {COLORS['text_primary']};
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
    'dashboard': '⭐',        # Stern - Übersicht
    'mitarbeiter': '👥',     # Personen - Mitarbeiter
    'urlaub': '🌴',          # Palme - Urlaub
    'zeit': '⏱️',            # Stoppuhr - Zeiterfassung
    'dienstplan': '📅',     # Kalender - Dienstplan
    'lohn': '💰',           # Geldsack - Lohnabrechnung
    'einstellungen': '⚙️',  # Zahnrad - Einstellungen
    'chat': '💬',           # Sprechblase - Plauderecke
    'mastergeraete': '📱', # Handy - Mastergeräte
    
    # Aktionen
    'neu': '➕',              # Plus - Neu erstellen
    'bearbeiten': '✏️',      # Stift - Bearbeiten
    'loeschen': '🗑️',      # Mülleimer - Löschen
    'speichern': '💾',      # Diskette - Speichern
    'abbrechen': '❌',        # X - Abbrechen
    'suchen': '🔍',         # Lupe - Suchen
    'filter': '📊',         # Balkendiagramm - Filter
    'download': '📥',       # Download - Herunterladen
    'upload': '📤',         # Upload - Hochladen
    
    # Status
    'erfolg': '✅',           # Häkchen - Erfolg
    'warnung': '⚠️',        # Warnung - Warnung
    'fehler': '❌',           # X - Fehler
    'info': 'ℹ️',            # i - Information
    'ausstehend': '⏳',       # Sanduhr - Ausstehend
    'genehmigt': '✅',        # Häkchen - Genehmigt
    'abgelehnt': '❌',        # X - Abgelehnt
    
    # Sonstiges
    'benachrichtigung': '🔔', # Glocke - Benachrichtigung
    'statistik': '📊',      # Balkendiagramm - Statistik
    'dokument': '📄',       # Dokument - Dokument
    'email': '✉️',           # Brief - E-Mail
    'telefon': '📞',        # Telefon - Telefon
    'adresse': '🏠',        # Haus - Adresse
    'geburtstag': '🎂',     # Kuchen - Geburtstag
    'vertrag': '📜',        # Scroll - Vertrag
}


def get_icon(name: str) -> str:
    """Gibt das Icon für einen Namen zurück"""
    return ICONS.get(name, '▪️')  # Fallback: Kleines Quadrat
