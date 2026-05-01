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


@router.get("/datev-export")
def datev_export_herunterladen(
    monat: int,
    jahr: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """DATEV-Lohnexport als CSV (UTF-8 BOM, Semikolon) für den Steuerberater."""
    supabase = _get_supabase()

    ma_res = (
        supabase.table("mitarbeiter")
        .select(
            "id,vorname,nachname,monatliche_soll_stunden,monatliche_brutto_verguetung"
        )
        .eq("betrieb_id", betrieb_id)
        .eq("aktiv", True)
        .execute()
    )
    mitarbeiter = ma_res.data or []

    ma_ids = [m["id"] for m in mitarbeiter]
    if not ma_ids:
        raise HTTPException(status_code=404, detail="Keine aktiven Mitarbeiter gefunden.")

    la_res = (
        supabase.table("lohnabrechnungen")
        .select("*")
        .in_("mitarbeiter_id", ma_ids)
        .eq("monat", monat)
        .eq("jahr", jahr)
        .execute()
    )
    abrechnungen = la_res.data or []

    betrieb_res = (
        supabase.table("betriebe")
        .select("*")
        .eq("id", betrieb_id)
        .limit(1)
        .execute()
    )
    betrieb_info = betrieb_res.data[0] if betrieb_res.data else {}

    from utils.datev_export import erstelle_datev_lohnexport

    try:
        csv_bytes = erstelle_datev_lohnexport(
            mitarbeiter, abrechnungen, monat, jahr, betrieb_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DATEV-Export fehlgeschlagen: {e}")

    filename = f"DATEV_Lohn_{jahr}_{monat:02d}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
