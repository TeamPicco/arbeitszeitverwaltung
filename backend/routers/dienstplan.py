"""Dienstplan-Router: Wöchentliche Schichtplanung."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from deps import get_betrieb_id, get_current_user, require_admin

router = APIRouter()


def _sb():
    from utils.database import get_service_role_client
    return get_service_role_client()


class EintragBody(BaseModel):
    mitarbeiter_id: int
    datum: date
    schichttyp: str = "arbeit"
    start_zeit: Optional[str] = None
    end_zeit: Optional[str] = None
    pause_minuten: Optional[int] = None


@router.get("/woche")
def woche(
    datum_von: date,
    betrieb_id: int = Depends(get_betrieb_id),
) -> List[Dict[str, Any]]:
    """Alle Dienstplan-Einträge für eine Woche (Mo–So)."""
    supabase = _sb()
    datum_bis = datum_von + timedelta(days=6)
    try:
        res = (
            supabase.table("dienstplaene")
            .select("id, mitarbeiter_id, datum, schichttyp, start_zeit, end_zeit, pause_minuten")
            .eq("betrieb_id", betrieb_id)
            .gte("datum", str(datum_von))
            .lte("datum", str(datum_bis))
            .execute()
        )
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden: {exc}")


@router.post("/eintrag", status_code=200)
def eintrag_setzen(
    body: EintragBody,
    betrieb_id: int = Depends(get_betrieb_id),
    _user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Erstellt oder aktualisiert einen Dienstplan-Eintrag (Upsert)."""
    supabase = _sb()
    data: Dict[str, Any] = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": body.mitarbeiter_id,
        "datum": str(body.datum),
        "schichttyp": body.schichttyp,
    }
    if body.start_zeit is not None:
        data["start_zeit"] = body.start_zeit
    if body.end_zeit is not None:
        data["end_zeit"] = body.end_zeit
    if body.pause_minuten is not None:
        data["pause_minuten"] = body.pause_minuten
    try:
        res = (
            supabase.table("dienstplaene")
            .upsert(data, on_conflict="mitarbeiter_id,datum")
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=500, detail="Eintrag konnte nicht gespeichert werden.")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Speichern: {exc}")


@router.delete("/{eintrag_id}")
def eintrag_loeschen(
    eintrag_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    _user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Löscht einen Dienstplan-Eintrag."""
    supabase = _sb()
    try:
        supabase.table("dienstplaene").delete().eq("id", eintrag_id).eq("betrieb_id", betrieb_id).execute()
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Löschen: {exc}")


@router.get("/monat")
def monat(
    jahr: int,
    monat_nr: int,
    betrieb_id: int = Depends(get_betrieb_id),
) -> List[Dict[str, Any]]:
    """Alle Einträge eines Monats für alle Mitarbeiter des Betriebs."""
    supabase = _sb()
    datum_von = date(jahr, monat_nr, 1)
    # last day of month
    if monat_nr == 12:
        datum_bis = date(jahr + 1, 1, 1) - timedelta(days=1)
    else:
        datum_bis = date(jahr, monat_nr + 1, 1) - timedelta(days=1)
    try:
        res = (
            supabase.table("dienstplaene")
            .select("id, mitarbeiter_id, datum, schichttyp, start_zeit, end_zeit, pause_minuten")
            .eq("betrieb_id", betrieb_id)
            .gte("datum", str(datum_von))
            .lte("datum", str(datum_bis))
            .execute()
        )
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden: {exc}")
