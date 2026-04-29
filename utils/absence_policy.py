from __future__ import annotations

from typing import Dict, Mapping

from utils.database import get_supabase_client

# Default-Regeln (DE-nah) - können je Betrieb überschrieben werden.
DEFAULT_ABSENCE_PAYMENT_POLICY: Dict[str, bool] = {
    "urlaub": True,
    "krankheit": True,
    "krank": True,  # Legacy-Alias
    "sonderurlaub": True,
    "unbezahlter_urlaub": False,
}


def _normalize_absence_type(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw == "krank":
        return "krankheit"
    return raw


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


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except Exception:
        return float(default)


def _query_betrieb_row(supabase, betrieb_id: int) -> tuple[dict, str]:
    # Instanzen nutzen teils "metadaten", teils "meta".
    for cols, meta_key in (("id,metadaten", "metadaten"), ("id,meta", "meta")):
        try:
            res = (
                supabase.table("betriebe")
                .select(cols)
                .eq("id", int(betrieb_id))
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if rows:
                return rows[0] or {}, meta_key
        except Exception:
            continue
    return {}, "metadaten"


def _canonicalize_policy(raw_policy: Mapping | None) -> Dict[str, bool]:
    out: Dict[str, bool] = {}
    if not isinstance(raw_policy, Mapping):
        return out
    for raw_key, raw_val in raw_policy.items():
        key = _normalize_absence_type(str(raw_key or ""))
        if not key:
            continue
        out[key] = _to_bool(raw_val, DEFAULT_ABSENCE_PAYMENT_POLICY.get(key, False))
    if "krankheit" in out:
        out["krank"] = out["krankheit"]
    return out


def _read_policy_from_betrieb_meta(supabase, betrieb_id: int | None) -> Dict[str, bool]:
    if betrieb_id is None:
        return {}
    row, meta_key = _query_betrieb_row(supabase, int(betrieb_id))
    meta = row.get(meta_key)
    if not isinstance(meta, Mapping):
        return {}

    # Bevorzugt neuer Schlüssel, dann Legacy-Schlüssel.
    for candidate in ("absence_payment_policy", "abwesenheit_bezahlt"):
        policy_raw = meta.get(candidate)
        parsed = _canonicalize_policy(policy_raw if isinstance(policy_raw, Mapping) else None)
        if parsed:
            return parsed
    return {}


def load_absence_compensation_policy(supabase=None, *, betrieb_id: int | None = None) -> Dict[str, bool]:
    """
    Liefert die effektive Bezahl-Policy für Abwesenheitstypen.
    Reihenfolge:
      1) Defaults
      2) optionale betriebe.meta/metadaten overrides (neu+legacy)
    """
    client = supabase or get_supabase_client()
    policy = dict(DEFAULT_ABSENCE_PAYMENT_POLICY)
    policy.update(_read_policy_from_betrieb_meta(client, betrieb_id))
    if "krankheit" in policy:
        policy["krank"] = bool(policy["krankheit"])
    return policy


def get_absence_payment_policy(betrieb_id: int | None = None) -> Dict[str, bool]:
    return load_absence_compensation_policy(betrieb_id=betrieb_id)


def save_absence_compensation_policy(
    supabase,
    *,
    betrieb_id: int | None,
    policy: Mapping[str, bool] | None,
) -> tuple[bool, str]:
    if betrieb_id is None:
        return False, "betrieb_id fehlt"
    try:
        row, meta_key = _query_betrieb_row(supabase, int(betrieb_id))
        meta = row.get(meta_key)
        if not isinstance(meta, dict):
            meta = {}
        canonical = _canonicalize_policy(policy)
        updated = dict(meta)
        # Beide Keys schreiben, damit alte/new code paths konsistent bleiben.
        updated["absence_payment_policy"] = dict(canonical)
        updated["abwesenheit_bezahlt"] = dict(canonical)
        supabase.table("betriebe").update({meta_key: updated}).eq("id", int(betrieb_id)).execute()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def include_paid_absence_in_reports(mode: str | None) -> bool:
    raw = str(mode or "").strip().lower()
    return raw not in {"ohne", "without", "without_paid_absences", "exclude_paid"}


def is_paid_absence(
    absence_type: str,
    policy_map: Mapping[str, bool] | None = None,
    *,
    betrieb_id: int | None = None,
) -> bool:
    typ = _normalize_absence_type(absence_type)
    if not typ:
        return False
    policy = dict(policy_map or {})
    if not policy:
        policy = load_absence_compensation_policy(betrieb_id=betrieb_id)
    if "krankheit" in policy:
        policy["krank"] = bool(policy["krankheit"])
    return bool(policy.get(typ, False))


def evaluate_paid_absence_credit(raw_entry: dict, policy_map: Mapping[str, bool] | None = None) -> float:
    if not isinstance(raw_entry, dict):
        return 0.0
    abs_typ = _normalize_absence_type(
        str(raw_entry.get("abwesenheitstyp") or raw_entry.get("typ") or "")
    )
    if not abs_typ:
        return 0.0
    if not is_paid_absence(abs_typ, policy_map):
        return 0.0
    hours = _as_float(raw_entry.get("arbeitsstunden"), 0.0)
    if hours <= 0:
        hours = _as_float(raw_entry.get("stunden"), 0.0)
    return round(max(0.0, float(hours)), 2)
