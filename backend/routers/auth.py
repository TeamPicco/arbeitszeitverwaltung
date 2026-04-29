"""Auth-Router: Login, Passwort-Änderung, eigenes Profil."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from deps import JWT_EXPIRE_MINUTES, create_access_token, get_current_user, verify_password

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    betriebsnummer: str
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    betrieb_id: int
    betrieb_name: str
    user_id: int
    mitarbeiter_id: Optional[int] = None
    expires_in_minutes: int = JWT_EXPIRE_MINUTES


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_supabase():
    from utils.database import get_service_role_client
    return get_service_role_client()


def _load_mitarbeiter_id(supabase, betrieb_id: int, user_id: int) -> Optional[int]:
    try:
        res = (
            supabase.table("mitarbeiter")
            .select("id")
            .eq("betrieb_id", betrieb_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return int(res.data[0]["id"])
    except Exception:
        pass
    return None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    supabase = _get_supabase()

    # 1. Betrieb prüfen
    betrieb_res = (
        supabase.table("betriebe")
        .select("id, name")
        .eq("betriebsnummer", body.betriebsnummer)
        .eq("aktiv", True)
        .execute()
    )
    if not betrieb_res.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login fehlgeschlagen. Betriebsnummer nicht gefunden oder Betrieb inaktiv.",
        )
    betrieb = betrieb_res.data[0]

    # 2. User prüfen
    user_res = (
        supabase.table("users")
        .select("id, username, password_hash, role, is_active")
        .eq("username", body.username)
        .eq("betrieb_id", betrieb["id"])
        .eq("is_active", True)
        .execute()
    )
    if not user_res.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login fehlgeschlagen. Benutzername oder Passwort falsch.",
        )
    user = user_res.data[0]

    # 3. Passwort prüfen
    pw_hash = user.get("password_hash", "")
    if not pw_hash or not bcrypt.checkpw(body.password.encode(), pw_hash.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login fehlgeschlagen. Benutzername oder Passwort falsch.",
        )

    # 4. Mitarbeiter-ID laden (optional, nur für Mitarbeiter-Rolle)
    mitarbeiter_id = _load_mitarbeiter_id(supabase, betrieb["id"], user["id"])

    # 5. Last-Login aktualisieren (best-effort)
    try:
        from datetime import datetime, timezone
        supabase.table("users").update(
            {"last_login": datetime.now(timezone.utc).isoformat()}
        ).eq("id", user["id"]).execute()
    except Exception:
        pass

    # 6. JWT ausstellen
    token = create_access_token({
        "sub": str(user["id"]),
        "role": user["role"],
        "betrieb_id": betrieb["id"],
        "betrieb_name": betrieb.get("name", ""),
        "mitarbeiter_id": mitarbeiter_id,
    })

    return LoginResponse(
        access_token=token,
        role=user["role"],
        betrieb_id=betrieb["id"],
        betrieb_name=betrieb.get("name", ""),
        user_id=user["id"],
        mitarbeiter_id=mitarbeiter_id,
    )


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    supabase = _get_supabase()
    user_res = (
        supabase.table("users")
        .select("password_hash")
        .eq("id", int(user["sub"]))
        .single()
        .execute()
    )
    if not user_res.data:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")

    if not verify_password(body.old_password, user_res.data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Altes Passwort ist falsch.",
        )

    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    supabase.table("users").update({"password_hash": new_hash}).eq("id", int(user["sub"])).execute()
    return {"ok": True, "message": "Passwort erfolgreich geändert."}


@router.get("/me")
def me(user: Dict[str, Any] = Depends(get_current_user)):
    supabase = _get_supabase()
    user_res = (
        supabase.table("users")
        .select("id, username, role, betrieb_id, last_login")
        .eq("id", int(user["sub"]))
        .single()
        .execute()
    )
    if not user_res.data:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")
    return user_res.data
