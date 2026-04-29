"""Dokumente-Router: Mitarbeiter-Dokumente hochladen, abrufen, löschen."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from deps import get_betrieb_id, get_current_user, require_admin

router = APIRouter()


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

@router.get("/mitarbeiter/{mitarbeiter_id}")
def dokumente_liste(
    mitarbeiter_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Alle Dokumente eines Mitarbeiters auflisten."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id, betrieb_id)

    res = (
        supabase.table("mitarbeiter_dokumente")
        .select("id, name, typ, status, gueltig_bis, file_path, file_url, created_at")
        .eq("mitarbeiter_id", mitarbeiter_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    docs = res.data or []

    # Signed URLs für Dokumente ohne direkten file_url generieren
    from utils.database import get_signed_url
    for doc in docs:
        if not doc.get("file_url") and doc.get("file_path"):
            doc["file_url"] = get_signed_url("dokumente", doc["file_path"])

    return docs


@router.post("/mitarbeiter/{mitarbeiter_id}")
async def dokument_hochladen(
    mitarbeiter_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
    file: UploadFile = File(...),
    name: str = Form(...),
    typ: str = Form("sonstig"),
    gueltig_bis: Optional[str] = Form(None),
):
    """Dokument für einen Mitarbeiter hochladen (nur Admin)."""
    supabase = _get_supabase()
    _assert_mitarbeiter_belongs_to_betrieb(supabase, mitarbeiter_id, betrieb_id)

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 10 MB).")

    from utils.database import upload_file_to_storage_result
    import uuid

    safe_filename = file.filename or "dokument"
    file_path = f"{betrieb_id}/{mitarbeiter_id}/{uuid.uuid4()}_{safe_filename}"

    upload_result = upload_file_to_storage_result(
        "dokumente",
        file_path,
        file_bytes,
    )
    if not upload_result.get("ok"):
        raise HTTPException(status_code=500, detail="Upload fehlgeschlagen.")

    payload = {
        "betrieb_id": betrieb_id,
        "mitarbeiter_id": mitarbeiter_id,
        "name": name,
        "typ": typ,
        "status": "aktiv",
        "file_path": file_path,
        "gueltig_bis": gueltig_bis,
    }
    res = supabase.table("mitarbeiter_dokumente").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Fehler beim Speichern des Dokuments.")
    return res.data[0]


@router.delete("/{dokument_id}")
def dokument_loeschen(
    dokument_id: int,
    betrieb_id: int = Depends(get_betrieb_id),
    user: Dict[str, Any] = Depends(require_admin),
):
    """Dokument löschen (nur Admin)."""
    supabase = _get_supabase()
    chk = (
        supabase.table("mitarbeiter_dokumente")
        .select("id, file_path")
        .eq("id", dokument_id)
        .eq("betrieb_id", betrieb_id)
        .limit(1)
        .execute()
    )
    if not chk.data:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

    supabase.table("mitarbeiter_dokumente").delete().eq("id", dokument_id).execute()
    return {"ok": True}
