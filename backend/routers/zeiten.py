"""Zeiten-Router: Zeiterfassungen lesen, manuell anlegen, AZK."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_betrieb_id, get_current_user, require_admin

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ZeiterfassungCreate(BaseModel):
    mitarbeiter_id: int
    datum: str           # ISO date "YYYY-MM-DD"
    start_zeit: str      # "HH:MM"
    ende_zeit: str       # "HH:MM"
    pause_minuten: int = 0
    quelle: str = "manuell"
    manuell_kommentar: Optional[str] = None


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

@router.get("/monat/{mitarbeiter_id}")
def zeiten_monat(
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
    betrieb_id: int = Depends(get_betrieb_id),
):
    """Alle Zeiterfassungen eines Mitarbeiters für einen Monat."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id, betrieb_id)

    erster = date(jahr, monat, 1).isoformat()
    letzter = date(jahr, monat, monthrange(jahr, monat)[1]).isoformat()

    select_variants = [
        (
            "id,datum,start_zeit,ende_zeit,pause_minuten,arbeitsstunden,stunden,"
            "quelle,ist_krank,abwesenheitstyp,created_at,updated_at,manuell_kommentar,korrektur_grund"
        ),
        "id,datum,start_zeit,ende_zeit,pause_minuten,arbeitsstunden,stunden,quelle,ist_krank,abwesenheitstyp,created_at,updated_at",
        "id,datum,start_zeit,ende_zeit,pause_minuten,arbeitsstunden,stunden,quelle,ist_krank,created_at,updated_at",
        "id,datum,start_zeit,ende_zeit,pause_minuten,quelle,ist_krank,created_at,updated_at",
    ]
    for cols in select_variants:
        try:
            r = (
                supabase.table("zeiterfassung")
                .select(cols)
                .eq("mitarbeiter_id", mitarbeiter_id)
                .gte("datum", erster)
                .lte("datum", letzter)
                .order("datum")
                .execute()
            )
            return r.data or []
        except Exception:
            continue

    return []


@router.post("/manuell")
def zeiten_manuell_anlegen(
    body: ZeiterfassungCreate,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Manuellen Zeiteintrag anlegen (Admin/eigene Zeiten)."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, body.mitarbeiter_id, betrieb_id)

    payload = {
        "mitarbeiter_id": body.mitarbeiter_id,
        "datum": body.datum,
        "start_zeit": body.start_zeit,
        "ende_zeit": body.ende_zeit,
        "pause_minuten": body.pause_minuten,
        "quelle": body.quelle,
        "manuell_kommentar": body.manuell_kommentar,
    }
    res = supabase.table("zeiterfassung").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Fehler beim Anlegen des Eintrags.")
    return res.data[0]


@router.delete("/{eintrag_id}")
def zeiten_loeschen(
    eintrag_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Zeiteintrag löschen (nur Admin)."""
    supabase = _get_supabase()
    supabase.table("zeiterfassung").delete().eq("id", eintrag_id).execute()
    return {"ok": True}


@router.get("/azk/{mitarbeiter_id}")
def azk_monat(
    mitarbeiter_id: int,
    monat: int,
    jahr: int,
    betrieb_id: int = Depends(get_betrieb_id),
):
    """Arbeitszeitkonto eines Mitarbeiters für einen Monat."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id, betrieb_id)

    from utils.azk import berechne_azk_monat
    return berechne_azk_monat(mitarbeiter_id, monat, jahr)
