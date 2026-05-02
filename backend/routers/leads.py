"""Leads-Router: CRM für Complio-Vertrieb (superadmin only)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_current_user
from utils.database import get_service_role_client

router = APIRouter()


def require_superadmin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Kein Zugriff")
    return current_user


class LeadCreate(BaseModel):
    firmenname: str
    ort: Optional[str] = None
    branche: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    notizen: Optional[str] = None


class LeadUpdate(BaseModel):
    firmenname: Optional[str] = None
    ort: Optional[str] = None
    branche: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    status: Optional[str] = None
    notizen: Optional[str] = None


@router.get("/")
def leads_liste(
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_superadmin),
) -> List[Dict[str, Any]]:
    supabase = get_service_role_client()
    q = supabase.table("leads").select("*").order("erstellt_am", desc=True)
    if status:
        q = q.eq("status", status)
    resp = q.execute()
    rows = resp.data or []
    if search:
        s = search.lower()
        rows = [
            r for r in rows
            if s in (r.get("firmenname") or "").lower()
            or s in (r.get("ort") or "").lower()
            or s in (r.get("branche") or "").lower()
        ]
    return rows


@router.get("/stats")
def leads_stats(
    current_user: Dict[str, Any] = Depends(require_superadmin),
) -> Dict[str, Any]:
    supabase = get_service_role_client()
    resp = supabase.table("leads").select("status").execute()
    rows = resp.data or []
    counts: Dict[str, int] = {"neu": 0, "kontaktiert": 0, "interessiert": 0, "abschluss": 0}
    for r in rows:
        s = r.get("status", "neu")
        counts[s] = counts.get(s, 0) + 1
    counts["gesamt"] = len(rows)
    return counts


@router.post("/")
def lead_anlegen(
    body: LeadCreate,
    current_user: Dict[str, Any] = Depends(require_superadmin),
) -> Dict[str, Any]:
    supabase = get_service_role_client()
    data = {
        **body.model_dump(exclude_none=True),
        "status": "neu",
        "erstellt_am": datetime.utcnow().isoformat(),
    }
    resp = supabase.table("leads").insert(data).execute()
    return resp.data[0] if resp.data else {}


@router.patch("/{lead_id}")
def lead_aktualisieren(
    lead_id: int,
    body: LeadUpdate,
    current_user: Dict[str, Any] = Depends(require_superadmin),
) -> Dict[str, Any]:
    supabase = get_service_role_client()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Keine Änderungen")
    resp = supabase.table("leads").update(updates).eq("id", lead_id).execute()
    return resp.data[0] if resp.data else {}


@router.delete("/{lead_id}")
def lead_loeschen(
    lead_id: int,
    current_user: Dict[str, Any] = Depends(require_superadmin),
) -> Dict[str, Any]:
    supabase = get_service_role_client()
    supabase.table("leads").delete().eq("id", lead_id).execute()
    return {"ok": True}
