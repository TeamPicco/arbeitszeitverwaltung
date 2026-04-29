"""Admin-Router: Betrieb-Einstellungen, User-Verwaltung, Übersichten."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_betrieb_id, require_admin

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "mitarbeiter"
    mitarbeiter_id: Optional[int] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class BetriebUpdate(BaseModel):
    name: Optional[str] = None
    adresse: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_supabase():
    from utils.database import get_service_role_client
    return get_service_role_client()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/betrieb")
def betrieb_info(
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Betrieb-Stammdaten abrufen."""
    supabase = _get_supabase()
    res = (
        supabase.table("betriebe")
        .select("id, name, betriebsnummer, adresse, telefon, email, aktiv, created_at")
        .eq("id", betrieb_id)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Betrieb nicht gefunden.")
    return res.data


@router.patch("/betrieb")
def betrieb_aktualisieren(
    body: BetriebUpdate,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Betrieb-Stammdaten aktualisieren."""
    supabase = _get_supabase()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben.")
    res = supabase.table("betriebe").update(updates).eq("id", betrieb_id).execute()
    return res.data[0] if res.data else {"ok": True}


@router.get("/users")
def users_liste(
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Alle User-Accounts des Betriebs."""
    supabase = _get_supabase()
    res = (
        supabase.table("users")
        .select("id, username, role, is_active, last_login, created_at")
        .eq("betrieb_id", betrieb_id)
        .order("username")
        .execute()
    )
    return res.data or []


@router.post("/users")
def user_anlegen(
    body: UserCreate,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Neuen User-Account anlegen."""
    import bcrypt
    supabase = _get_supabase()

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    payload = {
        "betrieb_id": betrieb_id,
        "username": body.username,
        "password_hash": pw_hash,
        "role": body.role,
        "is_active": True,
    }
    if body.mitarbeiter_id is not None:
        payload["mitarbeiter_id"] = body.mitarbeiter_id

    res = supabase.table("users").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Fehler beim Anlegen des Users.")

    row = res.data[0]
    row.pop("password_hash", None)
    return row


@router.patch("/users/{user_id}")
def user_aktualisieren(
    user_id: int,
    body: UserUpdate,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """User-Account aktualisieren."""
    supabase = _get_supabase()
    chk = (
        supabase.table("users")
        .select("id")
        .eq("id", user_id)
        .eq("betrieb_id", betrieb_id)
        .limit(1)
        .execute()
    )
    if not chk.data:
        raise HTTPException(status_code=404, detail="User nicht gefunden.")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben.")

    res = supabase.table("users").update(updates).eq("id", user_id).execute()
    return res.data[0] if res.data else {"ok": True}


@router.get("/dashboard")
def admin_dashboard_stats(
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Kurz-Statistiken für das Admin-Dashboard."""
    supabase = _get_supabase()
    from datetime import date

    heute = date.today().isoformat()

    ma_res = (
        supabase.table("mitarbeiter")
        .select("id", count="exact")
        .eq("betrieb_id", betrieb_id)
        .eq("aktiv", True)
        .execute()
    )
    anzahl_mitarbeiter = ma_res.count or 0

    offen_res = (
        supabase.table("urlaubsantraege")
        .select("id", count="exact")
        .eq("betrieb_id", betrieb_id)
        .eq("status", "ausstehend")
        .execute()
    )
    offene_urlaube = offen_res.count or 0

    eingestempelt_res = (
        supabase.table("zeit_eintraege")
        .select("mitarbeiter_id")
        .eq("betrieb_id", betrieb_id)
        .eq("aktion", "clock_in")
        .gte("zeitpunkt_utc", f"{heute}T00:00:00+00:00")
        .execute()
    )
    clock_ins = {r["mitarbeiter_id"] for r in (eingestempelt_res.data or [])}

    clock_out_res = (
        supabase.table("zeit_eintraege")
        .select("mitarbeiter_id")
        .eq("betrieb_id", betrieb_id)
        .eq("aktion", "clock_out")
        .gte("zeitpunkt_utc", f"{heute}T00:00:00+00:00")
        .execute()
    )
    clock_outs = {r["mitarbeiter_id"] for r in (clock_out_res.data or [])}
    aktuell_eingestempelt = len(clock_ins - clock_outs)

    return {
        "anzahl_mitarbeiter": anzahl_mitarbeiter,
        "offene_urlaubsantraege": offene_urlaube,
        "aktuell_eingestempelt": aktuell_eingestempelt,
        "datum": heute,
    }
