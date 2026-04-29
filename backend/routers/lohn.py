"""Lohn-Router: Monatsabrechnung berechnen, speichern, PDF generieren."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from deps import get_betrieb_id, require_admin

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class LohnBerechnungRequest(BaseModel):
    mitarbeiter_id: int
    monat: int
    jahr: int


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

@router.post("/berechnen")
def lohn_berechnen(
    body: LohnBerechnungRequest,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Monatsabrechnung berechnen (nicht speichern)."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, body.mitarbeiter_id, betrieb_id)

    from utils.lohnkern import berechneMonatslohn
    return berechneMonatslohn(body.mitarbeiter_id, body.monat, body.jahr)


@router.post("/speichern")
def lohn_speichern(
    body: LohnBerechnungRequest,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Monatsabrechnung berechnen und in DB speichern."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, body.mitarbeiter_id, betrieb_id)

    from utils.lohnkern import speichereMonatslohn
    result = speichereMonatslohn(body.mitarbeiter_id, body.monat, body.jahr)
    if not result.get("ok"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Fehler beim Speichern der Abrechnung."),
        )
    return result


@router.get("/liste/{mitarbeiter_id}")
def lohn_liste(
    mitarbeiter_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Gespeicherte Lohnabrechnungen eines Mitarbeiters."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id, betrieb_id)

    res = (
        supabase.table("lohnabrechnungen")
        .select("id,monat,jahr,brutto,netto,stunden,erstellt_am")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .order("jahr", desc=True)
        .order("monat", desc=True)
        .execute()
    )
    return res.data or []


@router.get("/pdf/{mitarbeiter_id}")
def lohn_pdf(
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Lohnabrechnung als PDF generieren."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id, betrieb_id)

    try:
        from utils.lohnabrechnung import generate_lohnabrechnung_pdf
        pdf_bytes = generate_lohnabrechnung_pdf(mitarbeiter_id, monat, jahr)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF-Generierung fehlgeschlagen: {e}")

    filename = f"lohnabrechnung_{mitarbeiter_id}_{jahr}_{monat:02d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
