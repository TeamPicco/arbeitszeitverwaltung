"""Database utilities — FastAPI/standalone version (kein Streamlit)."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import bcrypt
import requests
from supabase import Client, create_client

logger = logging.getLogger(__name__)

# ── Modul-Level Singletons (thread-safe für FastAPI/uvicorn) ─────────────────
_anon_client: Optional[Client] = None
_service_client: Optional[Client] = None


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Fehlende Umgebungsvariable: {name}")
    return value


def get_supabase_client() -> Client:
    """Anon/regulärer Supabase-Client (Module-Singleton)."""
    global _anon_client
    if _anon_client is None:
        url = _require_env("SUPABASE_URL")
        key = _require_env("SUPABASE_KEY")
        _anon_client = create_client(url, key)
    return _anon_client


def get_service_role_client() -> Client:
    """Service-Role-Client — für serverseitige Admin-Operationen."""
    global _service_client
    if _service_client is None:
        url = _require_env("SUPABASE_URL")
        service_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_KEY")
        )
        if not service_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY / SUPABASE_KEY fehlt")
        _service_client = create_client(url, service_key)
    return _service_client


# Alias für Legacy-Code
def init_supabase_client() -> Client:
    return get_supabase_client()


def set_betrieb_session(supabase_client: Client, betrieb_id: int, user_id: Optional[int] = None) -> None:
    """Setzt PostgreSQL Session-Variablen für RLS-Policies."""
    configs = [
        {"setting_name": "app.current_betrieb_id", "new_value": str(betrieb_id), "is_local": False},
    ]
    if user_id is not None:
        configs.append(
            {"setting_name": "app.current_user_id", "new_value": str(user_id), "is_local": False}
        )
    for cfg in configs:
        try:
            supabase_client.rpc("set_config", cfg).execute()
        except Exception as exc:
            raise RuntimeError(
                f"RLS-Session-Setup fehlgeschlagen für {cfg.get('setting_name')}: {exc}"
            ) from exc


def verify_credentials_with_betrieb(
    betriebsnummer: str, username: str, password: str
) -> Optional[Dict[str, Any]]:
    """Verifiziert die Anmeldung inkl. Betriebsnummer."""
    try:
        supabase = get_supabase_client()
        betrieb_res = (
            supabase.table("betriebe")
            .select("*")
            .eq("betriebsnummer", betriebsnummer)
            .eq("aktiv", True)
            .execute()
        )
        if not betrieb_res.data:
            return None

        betrieb = betrieb_res.data[0]
        user_res = (
            supabase.table("users")
            .select("*")
            .eq("username", username)
            .eq("betrieb_id", betrieb["id"])
            .eq("is_active", True)
            .execute()
        )
        if not user_res.data:
            return None

        user = user_res.data[0]
        pw_hash = user.get("password_hash", "")
        if not pw_hash:
            return None

        if bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8")):
            user["betrieb_name"] = betrieb.get("name", "")
            user["betrieb_id"] = betrieb["id"]
            return user
        return None
    except Exception as exc:
        logger.error("Login-Fehler: %s", exc)
        return None


def update_last_login(user_id: str) -> None:
    """Aktualisiert den Zeitstempel des letzten Logins."""
    try:
        supabase = get_supabase_client()
        (
            supabase.table("users")
            .update({"last_login": datetime.now(timezone.utc).isoformat()})
            .eq("id", user_id)
            .execute()
        )
    except Exception:
        pass


def upload_file_to_storage_result(
    bucket_name: str,
    file_path: str,
    file_data: bytes,
    fallback_buckets: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Datei-Upload über Supabase Storage REST API mit Bucket-Fallback."""
    try:
        url = _require_env("SUPABASE_URL")
        service_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_KEY")
        )
        if not service_key:
            return {"ok": False, "bucket": None, "status_code": None, "error": "Service-Key fehlt"}

        headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "x-upsert": "true",
            "Content-Type": "application/octet-stream",
        }
        buckets = [bucket_name] + [b for b in (fallback_buckets or []) if b and b != bucket_name]

        last_status = None
        last_error = None
        for bucket in buckets:
            encoded_path = quote(file_path, safe="/")
            upload_url = f"{url}/storage/v1/object/{bucket}/{encoded_path}"
            response = requests.post(upload_url, headers=headers, data=file_data, timeout=30)
            if response.status_code in (200, 201):
                return {"ok": True, "bucket": bucket, "status_code": response.status_code, "error": None}
            last_status = response.status_code
            body = (response.text or "").strip()
            last_error = body[:500] if body else "Unbekannter Storage-Fehler"

        return {"ok": False, "bucket": None, "status_code": last_status, "error": last_error}
    except Exception as exc:
        return {"ok": False, "bucket": None, "status_code": None, "error": str(exc)}


def upload_file_to_storage(bucket_name: str, file_path: str, file_data: bytes) -> bool:
    result = upload_file_to_storage_result(bucket_name, file_path, file_data)
    return bool(result.get("ok"))


def get_all_mitarbeiter(betrieb_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Lädt alle Mitarbeiter eines Betriebs."""
    supabase = get_supabase_client()
    query = supabase.table("mitarbeiter").select("*").order("nachname")
    if betrieb_id is not None:
        query = query.eq("betrieb_id", betrieb_id)
    res = query.execute()
    return res.data or []


def update_mitarbeiter(mitarbeiter_id: Any, values: Dict[str, Any], betrieb_id: Optional[int] = None) -> bool:
    """Aktualisiert einen Mitarbeiterdatensatz."""
    try:
        supabase = get_supabase_client()
        query = supabase.table("mitarbeiter").update(values).eq("id", mitarbeiter_id)
        if betrieb_id is not None:
            query = query.eq("betrieb_id", betrieb_id)
        query.execute()
        return True
    except Exception:
        return False


def check_and_save_monats_abschluss(mitarbeiter_id: Any, monat: int, jahr: int) -> float:
    """Speichert den Monatsabschluss in azk_historie."""
    supabase = get_supabase_client()

    ist_res = (
        supabase.table("zeiterfassung")
        .select("arbeitsstunden, stunden")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .eq("monat", monat)
        .eq("jahr", jahr)
        .execute()
    )
    ist = 0.0
    for row in ist_res.data or []:
        ist += float(row.get("arbeitsstunden") or row.get("stunden") or 0.0)

    ma = (
        supabase.table("mitarbeiter")
        .select("monatliche_soll_stunden, soll_stunden_monat")
        .eq("id", mitarbeiter_id)
        .single()
        .execute()
    )
    ma_data = ma.data or {}
    soll = float(ma_data.get("monatliche_soll_stunden") or ma_data.get("soll_stunden_monat") or 160.0)

    diff = round(ist - soll, 2)
    (
        supabase.table("azk_historie")
        .upsert(
            {
                "mitarbeiter_id": mitarbeiter_id,
                "monat": monat,
                "jahr": jahr,
                "ist_stunden": round(ist, 2),
                "soll_stunden": round(soll, 2),
                "differenz": diff,
            },
            on_conflict="mitarbeiter_id,monat,jahr",
        )
        .execute()
    )
    return diff


def get_signed_url(bucket_name: str, file_path: str, expires_in: int = 3600) -> Optional[str]:
    """Erstellt eine signierte URL für eine Datei im Supabase Storage."""
    try:
        url = _require_env("SUPABASE_URL")
        service_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_KEY")
        )
        if not service_key:
            return None
        headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        }
        sign_url = f"{url}/storage/v1/object/sign/{bucket_name}/{file_path}"
        response = requests.post(sign_url, headers=headers, json={"expiresIn": expires_in}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            signed_path = data.get("signedURL") or data.get("signedUrl") or ""
            if signed_path:
                return signed_path if signed_path.startswith("http") else f"{url}{signed_path}"
        return None
    except Exception:
        return None
