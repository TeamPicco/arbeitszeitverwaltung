from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from datetime import timedelta
from typing import Dict

from utils.time_utils import now_utc


MAX_AUTHORIZED_DEVICES = 2


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def issue_device_verification_code(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    device_fingerprint: str,
    created_by: int | None = None,
    ttl_minutes: int = 15,
) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"
    payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "device_fingerprint": device_fingerprint,
        "code_hash": _hash_code(code),
        "expires_at_utc": (now_utc() + timedelta(minutes=ttl_minutes)).isoformat(),
        "created_by": created_by,
    }
    supabase.table("geraete_verifizierungen").insert(payload).execute()
    return code


def _authorized_device_count(supabase, *, mitarbeiter_id: int) -> int:
    res = (
        supabase.table("mitarbeiter_geraete")
        .select("id", count="exact")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .eq("autorisiert", True)
        .eq("ausnahme_genehmigt", False)
        .limit(1)
        .execute()
    )
    return int(res.count or 0)


def verify_and_authorize_device(
    supabase,
    *,
    betrieb_id: int,
    mitarbeiter_id: int,
    device_fingerprint: str,
    code: str,
    authorized_by: int | None = None,
) -> Dict[str, str | bool]:
    now = now_utc()
    verif_res = (
        supabase.table("geraete_verifizierungen")
        .select("*")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .eq("device_fingerprint", device_fingerprint)
        .is_("consumed_at_utc", "null")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not verif_res.data:
        return {"ok": False, "reason": "Kein gültiger Verifizierungscode vorhanden."}

    verif = verif_res.data[0]
    expires = datetime.fromisoformat(str(verif["expires_at_utc"]).replace("Z", "+00:00"))
    if expires < now:
        return {"ok": False, "reason": "Verifizierungscode abgelaufen."}
    if _hash_code(code) != verif.get("code_hash"):
        return {"ok": False, "reason": "Verifizierungscode ungültig."}

    count = _authorized_device_count(supabase, mitarbeiter_id=mitarbeiter_id)
    if count >= MAX_AUTHORIZED_DEVICES:
        return {
            "ok": False,
            "reason": f"Maximal {MAX_AUTHORIZED_DEVICES} autorisierte Geräte erreicht.",
        }

    upsert_payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "device_fingerprint": device_fingerprint,
        "autorisiert": True,
        "autorisiert_durch": authorized_by,
        "autorisiert_am": now.isoformat(),
        "letzter_kontakt_utc": now.isoformat(),
    }
    supabase.table("mitarbeiter_geraete").upsert(
        upsert_payload, on_conflict="mitarbeiter_id,device_fingerprint"
    ).execute()
    (
        supabase.table("geraete_verifizierungen")
        .update({"consumed_at_utc": now.isoformat()})
        .eq("id", verif["id"])
        .execute()
    )
    return {"ok": True, "reason": "Gerät autorisiert."}

