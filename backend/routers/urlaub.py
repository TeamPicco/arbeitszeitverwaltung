"""Urlaub-Router: Urlaubsanträge stellen, genehmigen, ablehnen, Saldo."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_betrieb_id, get_current_user, require_admin

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class UrlaubsantragCreate(BaseModel):
    mitarbeiter_id: int
    datum_von: str    # ISO date
    datum_bis: str    # ISO date
    anzahl_tage: float
    kommentar: Optional[str] = None


class UrlaubsantragEntscheidung(BaseModel):
    status: str    # "genehmigt" | "abgelehnt"
    kommentar: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_supabase():
    from utils.database import get_service_role_client
    return get_service_role_client()


def _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id: int, betrieb_id: int):
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
def urlaub_liste(
    betrieb_id: int = Depends(get_betrieb_id),
    status: Optional[str] = None,
):
    """Alle Urlaubsanträge des Betriebs (optional nach Status filtern)."""
    supabase = _get_supabase()
    q = (
        supabase.table("urlaubsantraege")
        .select("*, mitarbeiter(vorname, nachname)")
        .eq("betrieb_id", betrieb_id)
        .order("datum_von", desc=True)
    )
    if status:
        q = q.eq("status", status)
    res = q.execute()
    return res.data or []


@router.get("/mitarbeiter/{mitarbeiter_id}")
def urlaub_mitarbeiter(
    mitarbeiter_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
):
    """Urlaubsanträge eines bestimmten Mitarbeiters."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id, betrieb_id)
    res = (
        supabase.table("urlaubsantraege")
        .select("*")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .eq("betrieb_id", betrieb_id)
        .order("datum_von", desc=True)
        .execute()
    )
    return res.data or []


@router.get("/saldo/{mitarbeiter_id}")
def urlaub_saldo(
    mitarbeiter_id: int,
    jahr: int,
    betrieb_id: int = Depends(get_betrieb_id),
):
    """Urlaubssaldo (Anspruch, genommen, Rest) für ein Jahr."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id, betrieb_id)

    from utils.azk import berechne_urlaubskonto
    return berechne_urlaubskonto(mitarbeiter_id, jahr)


@router.post("/")
def urlaub_beantragen(
    body: UrlaubsantragCreate,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Urlaubsantrag stellen."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, body.mitarbeiter_id, betrieb_id)

    payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": body.mitarbeiter_id,
        "datum_von": body.datum_von,
        "datum_bis": body.datum_bis,
        "anzahl_tage": body.anzahl_tage,
        "status": "ausstehend",
        "kommentar": body.kommentar,
    }
    res = supabase.table("urlaubsantraege").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Fehler beim Anlegen des Antrags.")
    return res.data[0]


@router.patch("/{antrag_id}")
def urlaub_entscheiden(
    antrag_id: int,
    body: UrlaubsantragEntscheidung,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Urlaubsantrag genehmigen oder ablehnen (nur Admin)."""
    if body.status not in ("genehmigt", "abgelehnt"):
        raise HTTPException(status_code=400, detail="Ungültiger Status.")

    supabase = _get_supabase()
    chk = (
        supabase.table("urlaubsantraege")
        .select("id")
        .eq("id", antrag_id)
        .eq("betrieb_id", betrieb_id)
        .limit(1)
        .execute()
    )
    if not chk.data:
        raise HTTPException(status_code=404, detail="Antrag nicht gefunden.")

    update = {"status": body.status}
    if body.kommentar is not None:
        update["kommentar"] = body.kommentar

    res = supabase.table("urlaubsantraege").update(update).eq("id", antrag_id).execute()
    return res.data[0] if res.data else {"ok": True}


@router.delete("/{antrag_id}")
def urlaub_loeschen(
    antrag_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Eigenen ausstehenden Urlaubsantrag zurückziehen."""
    supabase = _get_supabase()
    chk = (
        supabase.table("urlaubsantraege")
        .select("id, status, mitarbeiter_id")
        .eq("id", antrag_id)
        .eq("betrieb_id", betrieb_id)
        .limit(1)
        .execute()
    )
    if not chk.data:
        raise HTTPException(status_code=404, detail="Antrag nicht gefunden.")

    antrag = chk.data[0]
    role = user.get("role", "")
    mitarbeiter_id_jwt = user.get("mitarbeiter_id")

    # Non-admins can only delete their own pending requests
    if role not in ("admin", "superadmin"):
        if antrag["status"] != "ausstehend":
            raise HTTPException(status_code=403, detail="Nur ausstehende Anträge können zurückgezogen werden.")
        if str(antrag["mitarbeiter_id"]) != str(mitarbeiter_id_jwt):
            raise HTTPException(status_code=403, detail="Zugriff verweigert.")

    supabase.table("urlaubsantraege").delete().eq("id", antrag_id).execute()
    return {"ok": True}
