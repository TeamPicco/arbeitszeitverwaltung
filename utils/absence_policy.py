from __future__ import annotations

from typing import Dict

from utils.database import get_supabase_client

# Default-Regeln (DE-nah) - können je Betrieb überschrieben werden.
DEFAULT_ABSENCE_PAYMENT_POLICY: Dict[str, bool] = {
    "urlaub": True,
    "krankheit": True,
    "krank": True,
    "sonderurlaub": True,
    "unbezahlter_urlaub": False,
}


def _to_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    raw = str(value).strip().lower()
    if raw in {"1", "true", "ja", "yes", "y"}:
        return True
    if raw in {"0", "false", "nein", "no", "n"}:
        return False
    return default


def _read_policy_from_betrieb_meta(betrieb_id: int | None) -> Dict[str, bool]:
    if betrieb_id is None:
        return {}
    try:
        supabase = get_supabase_client()
        res = (
            supabase.table("betriebe")
            .select("meta")
            .eq("id", int(betrieb_id))
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return {}
        meta = rows[0].get("meta") or {}
        policy_raw = (meta or {}).get("absence_payment_policy") or {}
        if not isinstance(policy_raw, dict):
            return {}
        out: Dict[str, bool] = {}
        for k, v in policy_raw.items():
            key = str(k or "").strip().lower()
            if not key:
                continue
            out[key] = _to_bool(v, DEFAULT_ABSENCE_PAYMENT_POLICY.get(key, False))
        return out
    except Exception:
        return {}


def get_absence_payment_policy(betrieb_id: int | None = None) -> Dict[str, bool]:
    """
    Liefert die effektive Bezahl-Policy für Abwesenheitstypen.
    Reihenfolge:
      1) Defaults
      2) optionale betrieb.meta.absence_payment_policy overrides
    """
    policy = dict(DEFAULT_ABSENCE_PAYMENT_POLICY)
    policy.update(_read_policy_from_betrieb_meta(betrieb_id))
    return policy


def is_paid_absence(absence_type: str, *, betrieb_id: int | None = None) -> bool:
    t = str(absence_type or "").strip().lower()
    if not t:
        return False
    policy = get_absence_payment_policy(betrieb_id=betrieb_id)
    return bool(policy.get(t, False))
