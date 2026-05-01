"""Dienstplan-Router: Wöchentliche Schichtplanung."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from deps import get_betrieb_id, get_current_user, require_admin

router = APIRouter()


def _sb():
    from utils.database import get_service_role_client
    return get_service_role_client()


class EintragBody(BaseModel):
    mitarbeiter_id: int
    datum: date
    schichttyp: str = "arbeit"
    start_zeit: Optional[str] = None
    end_zeit: Optional[str] = None
    pause_minuten: Optional[int] = None


@router.get("/woche")
def woche(
    datum_von: date,
    betrieb_id: int = Depends(get_betrieb_id),
) -> List[Dict[str, Any]]:
    """Alle Dienstplan-Einträge für eine Woche (Mo–So)."""
    supabase = _sb()
    datum_bis = datum_von + timedelta(days=6)
    try:
        res = (
            supabase.table("dienstplaene")
            .select("id, mitarbeiter_id, datum, schichttyp, start_zeit, end_zeit, pause_minuten")
            .eq("betrieb_id", betrieb_id)
            .gte("datum", str(datum_von))
            .lte("datum", str(datum_bis))
            .execute()
        )
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden: {exc}")


@router.post("/eintrag", status_code=200)
def eintrag_setzen(
    body: EintragBody,
    betrieb_id: int = Depends(get_betrieb_id),
    _user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Erstellt oder aktualisiert einen Dienstplan-Eintrag (Upsert)."""
    supabase = _sb()
    data: Dict[str, Any] = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": body.mitarbeiter_id,
        "datum": str(body.datum),
        "schichttyp": body.schichttyp,
    }
    if body.start_zeit is not None:
        data["start_zeit"] = body.start_zeit
    if body.end_zeit is not None:
        data["end_zeit"] = body.end_zeit
    if body.pause_minuten is not None:
        data["pause_minuten"] = body.pause_minuten
    try:
        res = (
            supabase.table("dienstplaene")
            .upsert(data, on_conflict="mitarbeiter_id,datum")
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=500, detail="Eintrag konnte nicht gespeichert werden.")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Speichern: {exc}")


@router.delete("/{eintrag_id}")
def eintrag_loeschen(
    eintrag_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    _user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Löscht einen Dienstplan-Eintrag."""
    supabase = _sb()
    try:
        supabase.table("dienstplaene").delete().eq("id", eintrag_id).eq("betrieb_id", betrieb_id).execute()
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Löschen: {exc}")


@router.post("/email-versenden")
def email_versenden(
    monat_nr: int,
    jahr: int,
    betrieb_id: int = Depends(get_betrieb_id),
    _user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Dienstplan per E-Mail an alle Mitarbeiter mit hinterlegter E-Mail versenden."""
    supabase = _sb()
    ma_res = (
        supabase.table("mitarbeiter")
        .select("email,vorname,nachname")
        .eq("betrieb_id", betrieb_id)
        .eq("aktiv", True)
        .execute()
    )
    mitarbeiter = ma_res.data or []

    monate_de = [
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ]
    monat_name = monate_de[monat_nr] if 1 <= monat_nr <= 12 else str(monat_nr)

    from utils.email_service import send_dienstplan_alle_mitarbeiter

    return send_dienstplan_alle_mitarbeiter(mitarbeiter, monat_name, jahr)


@router.get("/wuensche")
def wuensche_liste(
    betrieb_id: int = Depends(get_betrieb_id),
    _user: Dict[str, Any] = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """Alle Dienstplanwünsche für den Betrieb."""
    supabase = _sb()
    try:
        res = (
            supabase.table("dienstplanwuensche")
            .select(
                "id, mitarbeiter_id, von_datum, bis_datum, details, status, "
                "erstellt_am, mitarbeiter(vorname, nachname)"
            )
            .eq("betrieb_id", betrieb_id)
            .order("erstellt_am", desc=True)
            .execute()
        )
        # Normalize column names to API contract (datum_von/datum_bis/wunsch_text)
        rows = []
        for r in res.data or []:
            rows.append({
                **r,
                "datum_von": r.get("von_datum"),
                "datum_bis": r.get("bis_datum"),
                "wunsch_text": r.get("details"),
            })
        return rows
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden: {exc}")


class WunschBody(BaseModel):
    datum_von: date
    datum_bis: date
    wunsch_text: Optional[str] = None


@router.post("/wunsch", status_code=201)
def wunsch_einreichen(
    body: WunschBody,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mitarbeiter reicht Dienstplanwunsch ein."""
    supabase = _sb()
    mitarbeiter_id = user.get("mitarbeiter_id")
    if not mitarbeiter_id:
        raise HTTPException(status_code=403, detail="Kein Mitarbeiter-Konto verknüpft.")
    data = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "von_datum": str(body.datum_von),
        "bis_datum": str(body.datum_bis),
        "details": body.wunsch_text or "",
        "wunsch_typ": "allgemein",
        "monat": body.datum_von.month,
        "jahr": body.datum_von.year,
        "status": "offen",
    }
    try:
        res = supabase.table("dienstplanwuensche").insert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Wunsch konnte nicht gespeichert werden.")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler: {exc}")


class WunschEntscheidBody(BaseModel):
    status: str  # 'genehmigt' | 'abgelehnt'
    ablehnungsgrund: Optional[str] = None


@router.patch("/wunsch/{wunsch_id}")
def wunsch_entscheiden(
    wunsch_id: int,
    body: WunschEntscheidBody,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Admin genehmigt oder lehnt einen Dienstplanwunsch ab."""
    if body.status not in ("genehmigt", "abgelehnt"):
        raise HTTPException(status_code=400, detail="Status muss 'genehmigt' oder 'abgelehnt' sein.")
    supabase = _sb()
    chk = (
        supabase.table("dienstplanwuensche")
        .select("id, mitarbeiter_id, von_datum, bis_datum, details")
        .eq("id", wunsch_id)
        .eq("betrieb_id", betrieb_id)
        .limit(1)
        .execute()
    )
    if not chk.data:
        raise HTTPException(status_code=404, detail="Wunsch nicht gefunden.")

    wunsch = chk.data[0]
    updates: Dict[str, Any] = {"status": body.status, "bearbeitet_am": "now()"}
    if body.ablehnungsgrund:
        updates["admin_kommentar"] = body.ablehnungsgrund

    supabase.table("dienstplanwuensche").update(updates).eq("id", wunsch_id).execute()

    # E-Mail-Benachrichtigung an Mitarbeiter
    try:
        ma_res = (
            supabase.table("mitarbeiter")
            .select("email, vorname, nachname")
            .eq("id", wunsch["mitarbeiter_id"])
            .limit(1)
            .execute()
        )
        if ma_res.data:
            ma = ma_res.data[0]
            if ma.get("email"):
                from utils.email_service import send_dienstplanwunsch_entscheidung
                send_dienstplanwunsch_entscheidung(
                    ma["email"],
                    f"{ma['vorname']} {ma['nachname']}",
                    body.status,
                    str(wunsch.get("von_datum", "")),
                    str(wunsch.get("bis_datum", "")),
                    body.ablehnungsgrund,
                )
    except Exception:
        pass  # E-Mail-Fehler blockieren die API-Antwort nicht

    return {"ok": True, "status": body.status}


@router.get("/monat")
def monat(
    jahr: int,
    monat_nr: int,
    betrieb_id: int = Depends(get_betrieb_id),
) -> List[Dict[str, Any]]:
    """Alle Einträge eines Monats für alle Mitarbeiter des Betriebs."""
    supabase = _sb()
    datum_von = date(jahr, monat_nr, 1)
    # last day of month
    if monat_nr == 12:
        datum_bis = date(jahr + 1, 1, 1) - timedelta(days=1)
    else:
        datum_bis = date(jahr, monat_nr + 1, 1) - timedelta(days=1)
    try:
        res = (
            supabase.table("dienstplaene")
            .select("id, mitarbeiter_id, datum, schichttyp, start_zeit, end_zeit, pause_minuten")
            .eq("betrieb_id", betrieb_id)
            .gte("datum", str(datum_von))
            .lte("datum", str(datum_bis))
            .execute()
        )
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden: {exc}")
