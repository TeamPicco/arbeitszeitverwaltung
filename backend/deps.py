"""Gemeinsame FastAPI-Dependencies: Auth, DB, Tenant-Schutz."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "480"))

_bearer = HTTPBearer(auto_error=False)


def create_access_token(payload: Dict[str, Any]) -> str:
    from datetime import datetime, timedelta, timezone
    data = dict(payload)
    data["exp"] = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ungültig oder abgelaufen. Bitte erneut anmelden.",
        )


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Dict[str, Any]:
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht authentifiziert. Bitte anmelden.",
        )
    return _decode_token(creds.credentials)


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role") not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zugriff verweigert. Diese Funktion erfordert Admin-Rechte.",
        )
    return user


def get_betrieb_id(user: Dict[str, Any] = Depends(get_current_user)) -> int:
    """Liefert die betrieb_id IMMER aus dem JWT — niemals aus dem Request-Body."""
    betrieb_id = user.get("betrieb_id")
    if not betrieb_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kein Betrieb in der Sitzung. Bitte erneut anmelden.",
        )
    return int(betrieb_id)


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
