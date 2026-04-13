from datetime import datetime, timedelta
from typing import Optional

def get_alle_beurteilungen(supabase, betrieb_id: str) -> list:
    """Lädt alle Gefährdungsbeurteilungen eines Betriebs."""
    try:
        result = supabase.table("hazard_assessments")\
            .select("*")\
            .eq("betrieb_id", betrieb_id)\
            .order("created_at", desc=True)\
            .execute()
        return result.data or []
    except:
        return []

def get_beurteilung_mit_schritten(supabase, assessment_id: str) -> dict:
    """Lädt eine einzelne Beurteilung inklusive aller 5 Schritte."""
    try:
        beurteilung = supabase.table("hazard_assessments")\
            .select("*")\
            .eq("id", assessment_id)\
            .single()\
            .execute()
        schritte = supabase.table("hazard_assessment_steps")\
            .select("*")\
            .eq("assessment_id", assessment_id)\
            .order("step_number")\
            .execute()
        return {
            "beurteilung": beurteilung.data,
            "schritte": schritte.data or []
        }
    except:
        return {"beurteilung": None, "schritte": []}

def erstelle_beurteilung(supabase, betrieb_id: str, 
                          title: str, industry: str, 
                          erstellt_von: str) -> Optional[str]:
    """Erstellt eine neue Gefährdungsbeurteilung mit 5 leeren Schritten."""
    try:
        heute = datetime.now().isoformat()
        naechste_pruefung = (datetime.now() + timedelta(days=365)).isoformat()
        
        result = supabase.table("hazard_assessments").insert({
            "betrieb_id": betrieb_id,
            "title": title,
            "industry": industry,
            "status": "entwurf",
            "last_reviewed_at": heute,
            "next_review_due": naechste_pruefung,
            "created_by": erstellt_von
        }).execute()
        
        assessment_id = result.data[0]["id"]
        
        schritt_namen = [
            "Gefährdungen ermitteln",
            "Gefährdungen beurteilen",
            "Maßnahmen festlegen",
            "Maßnahmen durchführen",
            "Wirksamkeit überprüfen"
        ]
        
        for i, name in enumerate(schritt_namen, 1):
            supabase.table("hazard_assessment_steps").insert({
                "assessment_id": assessment_id,
                "step_number": i,
                "step_name": name,
                "content": "",
                "completed": False
            }).execute()
        
        return assessment_id
    except:
        return None

def speichere_schritt(supabase, assessment_id: str, 
                       step_number: int, content: str) -> bool:
    """Speichert den Inhalt eines einzelnen Schritts."""
    try:
        completed = len(content.strip()) > 20
        supabase.table("hazard_assessment_steps")\
            .update({
                "content": content,
                "completed": completed,
                "updated_at": datetime.now().isoformat()
            })\
            .eq("assessment_id", assessment_id)\
            .eq("step_number", step_number)\
            .execute()
        
        alle = supabase.table("hazard_assessment_steps")\
            .select("completed")\
            .eq("assessment_id", assessment_id)\
            .execute()
        
        alle_fertig = all(s["completed"] for s in alle.data)
        neuer_status = "aktiv" if alle_fertig else "entwurf"
        
        supabase.table("hazard_assessments")\
            .update({"status": neuer_status})\
            .eq("id", assessment_id)\
            .execute()
        
        return True
    except:
        return False

def get_status_farbe(status: str, next_review_due: str) -> tuple:
    """
    Gibt Status-Text und Farbe zurück.
    Rückgabe: (emoji_status, farbe_hex)
    """
    try:
        faellig = datetime.fromisoformat(next_review_due.replace("Z",""))
        heute = datetime.now()
        tage_bis_faellig = (faellig - heute).days
    except:
        tage_bis_faellig = 999

    if status == "entwurf":
        return ("✏️ Entwurf", "#888888")
    elif tage_bis_faellig < 0:
        return ("⚠️ Überfällig", "#e53935")
    elif tage_bis_faellig < 30:
        return ("🔔 Bald fällig", "#fb8c00")
    else:
        return ("✅ Aktuell", "#43a047")
