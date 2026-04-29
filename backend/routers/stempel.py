"""Stempel-Router: PIN-Lookup (Kiosk), Buchungen, Status."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from deps import get_betrieb_id, get_current_user

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class PinLookupRequest(BaseModel):
    betrieb_id: int
    pin: str


class PinLookupResponse(BaseModel):
    id: int
    vorname: str
    nachname: str


class StempelEventRequest(BaseModel):
    mitarbeiter_id: int
    action: str          # "clock_in" | "clock_out" | "break_start" | "break_end"
    geraet_id: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_supabase():
    from utils.database import get_service_role_client
    return get_service_role_client()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/pin", response_model=PinLookupResponse)
def pin_lookup(body: PinLookupRequest):
    """PIN-Lookup ohne Auth — für Kiosk-Terminal. Unterstützt stempel_pin + pin (Legacy)."""
    supabase = _get_supabase()
    for pin_column in ("stempel_pin", "pin"):
        try:
            res = (
                supabase.table("mitarbeiter")
                .select("id, vorname, nachname, stempel_pin, pin")
                .eq("betrieb_id", body.betrieb_id)
                .eq(pin_column, body.pin)
                .limit(1)
                .execute()
            )
            if res.data:
                row = res.data[0]
                return PinLookupResponse(
                    id=row["id"],
                    vorname=row["vorname"],
                    nachname=row["nachname"],
                )
        except Exception:
            continue
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="PIN nicht gefunden.",
    )


@router.post("/event")
def stempel_event(
    body: StempelEventRequest,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Stempel-Buchung schreiben (clock_in / clock_out / break_start / break_end)."""
    supabase = _get_supabase()

    from utils.zeit_events import register_time_event
    result = register_time_event(
        supabase,
        betrieb_id=betrieb_id,
        mitarbeiter_id=body.mitarbeiter_id,
        action=body.action,
        source="api",
        geraet_id=body.geraet_id,
        created_by=int(user.get("sub", 0)) or None,
    )

    if not result.get("ok", True) and result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    return {"ok": True, "action": body.action, "mitarbeiter_id": body.mitarbeiter_id}


@router.get("/status/{mitarbeiter_id}")
def stempel_status(
    mitarbeiter_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
):
    """Aktueller Schicht-/Pausenstatus für heute."""
    supabase = _get_supabase()

    # Verify mitarbeiter belongs to this betrieb
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

    from utils.zeit_events import get_event_state_for_day
    state = get_event_state_for_day(
        supabase,
        mitarbeiter_id=mitarbeiter_id,
        day=date.today(),
    )
    return state
