import streamlit as st

FEATURES = {
    "HAZARD_ASSESSMENT": {
        "name": "Gefährdungsbeurteilung KI",
        "preis": "39€/Monat",
        "beschreibung": "KI-gestützte Gefährdungsbeurteilung nach §5 ArbSchG"
    },
    "LABOR_LAW_GUARD": {
        "name": "Arbeitszeitgesetz-Wächter",
        "preis": "19€/Monat",
        "beschreibung": "Automatische Erkennung von ArbZG-Verstößen"
    },
    "DATEV_EXPORT": {
        "name": "DATEV-Export",
        "preis": "14€/Monat",
        "beschreibung": "Lohnabrechnung direkt für den Steuerberater"
    }
}

PLAN_FEATURES = {
    "starter":      [],
    "professional": ["LABOR_LAW_GUARD"],
    "compliance":   ["LABOR_LAW_GUARD", "HAZARD_ASSESSMENT"],
    "complete":     ["LABOR_LAW_GUARD", "HAZARD_ASSESSMENT", "DATEV_EXPORT"]
}

def is_feature_enabled(feature_key: str, user_plan: str) -> bool:
    """Gibt True zurück wenn das Feature im aktuellen Plan enthalten ist."""
    return feature_key in PLAN_FEATURES.get(user_plan, [])

@st.cache_data(ttl=120, show_spinner=False)
def get_user_plan(_supabase_client, betrieb_id: str) -> str:
    """Liest den aktuellen Plan des Betriebs aus der Datenbank."""
    if not betrieb_id:
        return "starter"
    try:
        result = _supabase_client.table("user_feature_plans")\
            .select("plan")\
            .eq("betrieb_id", betrieb_id)\
            .single()\
            .execute()
        if result.data:
            return result.data["plan"]
        return "starter"
    except:
        return "starter"
