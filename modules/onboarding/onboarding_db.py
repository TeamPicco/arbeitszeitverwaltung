import os
import secrets
import string
import bcrypt
from typing import Optional, Dict, Any
from utils.database import get_service_role_client


def generiere_betriebsnummer() -> str:
    """Generiert eine eindeutige 8-stellige Betriebsnummer."""
    return ''.join(secrets.choice(string.digits) for _ in range(8))


def generiere_passwort(laenge: int = 12) -> str:
    """Generiert ein sicheres zufälliges Passwort."""
    zeichen = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(zeichen) for _ in range(laenge))


def betriebsnummer_existiert(betriebsnummer: str) -> bool:
    """Prüft ob eine Betriebsnummer bereits vergeben ist."""
    try:
        supabase = get_service_role_client()
        result = supabase.table("betriebe")\
            .select("id")\
            .eq("betriebsnummer", betriebsnummer)\
            .execute()
        return len(result.data) > 0
    except Exception:
        return True


def erstelle_betrieb_und_admin(
    betrieb_name: str,
    admin_username: str,
    admin_passwort: str,
) -> Dict[str, Any]:
    """
    Erstellt einen neuen Betrieb + Admin-User in einer Transaktion.
    Gibt zurück: {
        ok: bool,
        betrieb_id: int,
        betriebsnummer: str,
        error: str | None
    }
    """
    try:
        supabase = get_service_role_client()

        # Eindeutige Betriebsnummer generieren
        betriebsnummer = generiere_betriebsnummer()
        versuche = 0
        while betriebsnummer_existiert(betriebsnummer) and versuche < 10:
            betriebsnummer = generiere_betriebsnummer()
            versuche += 1

        if versuche >= 10:
            return {
                "ok": False,
                "betrieb_id": None,
                "betriebsnummer": None,
                "error": "Betriebsnummer konnte nicht generiert werden."
            }

        # Betrieb anlegen
        betrieb_result = supabase.table("betriebe").insert({
            "betriebsnummer": betriebsnummer,
            "name": betrieb_name,
            "aktiv": True,
        }).execute()

        if not betrieb_result.data:
            return {
                "ok": False,
                "betrieb_id": None,
                "betriebsnummer": None,
                "error": "Betrieb konnte nicht angelegt werden."
            }

        betrieb_id = betrieb_result.data[0]["id"]

        # Passwort hashen
        pw_hash = bcrypt.hashpw(
            admin_passwort.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        # Admin-User anlegen
        user_result = supabase.table("users").insert({
            "username": admin_username,
            "password_hash": pw_hash,
            "role": "admin",
            "is_active": True,
            "betrieb_id": betrieb_id,
        }).execute()

        if not user_result.data:
            # Betrieb wieder löschen wenn User-Anlage fehlschlägt
            supabase.table("betriebe")\
                .delete()\
                .eq("id", betrieb_id)\
                .execute()
            return {
                "ok": False,
                "betrieb_id": None,
                "betriebsnummer": None,
                "error": "Admin-User konnte nicht angelegt werden."
            }

        # Starter-Plan zuweisen
        from datetime import datetime, timedelta
        supabase.table("user_feature_plans").insert({
            "user_id": user_result.data[0]["id"],
            "betrieb_id": betrieb_id,
            "plan": "starter",
            "valid_until": (
                datetime.now() + timedelta(days=30)
            ).date().isoformat(),
        }).execute()

        return {
            "ok": True,
            "betrieb_id": betrieb_id,
            "betriebsnummer": betriebsnummer,
            "error": None
        }

    except Exception as e:
        return {
            "ok": False,
            "betrieb_id": None,
            "betriebsnummer": None,
            "error": str(e)
        }


def pruefe_testphase(betrieb_id: int) -> Dict[str, Any]:
    """
    Prüft ob ein Betrieb noch in der kostenlosen Testphase ist.
    Gibt zurück: {
        aktiv: bool,
        tage_verbleibend: int,
        plan: str
    }
    """
    try:
        from datetime import datetime
        supabase = get_service_role_client()
        result = supabase.table("user_feature_plans")\
            .select("plan, valid_until")\
            .eq("betrieb_id", betrieb_id)\
            .single()\
            .execute()

        if not result.data:
            return {"aktiv": False, "tage_verbleibend": 0, "plan": "starter"}

        valid_until = result.data.get("valid_until")
        if not valid_until:
            return {"aktiv": True, "tage_verbleibend": 0, "plan": result.data.get("plan")}

        faellig = datetime.fromisoformat(str(valid_until))
        tage = (faellig - datetime.now()).days

        return {
            "aktiv": tage > 0,
            "tage_verbleibend": max(0, tage),
            "plan": result.data.get("plan", "starter")
        }
    except Exception:
        return {"aktiv": False, "tage_verbleibend": 0, "plan": "starter"}
