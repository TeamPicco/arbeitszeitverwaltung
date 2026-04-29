"""Mitarbeiter-Router: Liste, Detail, Anlegen, Aktualisieren."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_betrieb_id, get_current_user, require_admin

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class MitarbeiterCreate(BaseModel):
    vorname: str
    nachname: str
    email: Optional[str] = None
    telefon: Optional[str] = None
    position: Optional[str] = None
    bereich: Optional[str] = None
    beschaeftigungsart: Optional[str] = None
    monatliche_brutto_verguetung: Optional[float] = None
    monatliche_soll_stunden: Optional[float] = None
    jahres_urlaubstage: Optional[int] = None
    eintrittsdatum: Optional[str] = None
    stempel_pin: Optional[str] = None


class MitarbeiterUpdate(BaseModel):
    vorname: Optional[str] = None
    nachname: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    position: Optional[str] = None
    bereich: Optional[str] = None
    beschaeftigungsart: Optional[str] = None
    monatliche_brutto_verguetung: Optional[float] = None
    monatliche_soll_stunden: Optional[float] = None
    jahres_urlaubstage: Optional[int] = None
    eintrittsdatum: Optional[str] = None
    austrittsdatum: Optional[str] = None
    stempel_pin: Optional[str] = None
    aktiv: Optional[bool] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_supabase():
    from utils.database import get_service_role_client
    return get_service_role_client()


_SELECT_COLS = (
    "id,vorname,nachname,email,telefon,position,bereich,"
    "monatliche_brutto_verguetung,monatliche_soll_stunden,"
    "jahres_urlaubstage,eintrittsdatum,austrittsdatum,"
    "aktiv,beschaeftigungsart,created_at"
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
def mitarbeiter_liste(
    betrieb_id: int = Depends(get_betrieb_id),
    aktiv: Optional[bool] = None,
):
    """Alle Mitarbeiter des Betriebs."""
    supabase = _get_supabase()
    q = (
        supabase.table("mitarbeiter")
        .select(_SELECT_COLS)
        .eq("betrieb_id", betrieb_id)
        .order("nachname")
    )
    if aktiv is not None:
        q = q.eq("aktiv", aktiv)
    res = q.execute()
    return res.data or []


@router.get("/{mitarbeiter_id}")
def mitarbeiter_detail(
    mitarbeiter_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
):
    """Einzelnen Mitarbeiter abrufen."""
    supabase = _get_supabase()
    res = (
        supabase.table("mitarbeiter")
        .select(_SELECT_COLS)
        .eq("id", mitarbeiter_id)
        .eq("betrieb_id", betrieb_id)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden.")
    return res.data


@router.post("/")
def mitarbeiter_anlegen(
    body: MitarbeiterCreate,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Neuen Mitarbeiter anlegen (nur Admin)."""
    supabase = _get_supabase()
    payload = body.model_dump(exclude_none=True)
    payload["betrieb_id"] = betrieb_id
    payload.setdefault("aktiv", True)

    res = supabase.table("mitarbeiter").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Fehler beim Anlegen.")
    return res.data[0]


@router.patch("/{mitarbeiter_id}")
def mitarbeiter_aktualisieren(
    mitarbeiter_id: int,
    body: MitarbeiterUpdate,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Mitarbeiter aktualisieren (nur Admin)."""
    supabase = _get_supabase()
    chk = (
        supabase.table("mitarbeiter")
        .select("id")
        .eq("id", mitarbeiter_id)
        .eq("betrieb_id", betrieb_id)
        .limit(1)
        .execute()
    )
    if not chk.data:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden.")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben.")

    res = supabase.table("mitarbeiter").update(updates).eq("id", mitarbeiter_id).execute()
    return res.data[0] if res.data else {"ok": True}


@router.delete("/{mitarbeiter_id}")
def mitarbeiter_deaktivieren(
    mitarbeiter_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Mitarbeiter deaktivieren — kein Hard-Delete (nur Admin)."""
    supabase = _get_supabase()
    chk = (
        supabase.table("mitarbeiter")
        .select("id")
        .eq("id", mitarbeiter_id)
        .eq("betrieb_id", betrieb_id)
        .limit(1)
        .execute()
    )
    if not chk.data:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden.")

    supabase.table("mitarbeiter").update({"aktiv": False}).eq("id", mitarbeiter_id).execute()
    return {"ok": True}
