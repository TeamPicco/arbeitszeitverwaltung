import os
import secrets
import string
import bcrypt
from typing import Optional, Dict, Any
from utils.database import get_service_role_client


def generiere_betriebsnummer() -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(8))


def generiere_passwort(laenge: int = 12) -> str:
    zeichen = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(zeichen) for _ in range(laenge))


def betriebsnummer_existiert(betriebsnummer: str) -> bool:
    try:
        supabase = get_service_role_client()
        result = supabase.table("betriebe")\
            .select("id")\
            .eq("betriebsnummer", betriebsnummer)\
            .execute()
        return len(result.data) > 0
    except Exception:
        return True


def _sende_willkommensmail(
    email: str,
    betrieb_name: str,
    betriebsnummer: str,
    admin_username: str,
    admin_passwort: str,
) -> None:
    try:
        from utils.email_service import send_email
        subject = f"Willkommen bei Complio – deine Zugangsdaten für {betrieb_name}"
        html = f"""
        <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;color:#111">
          <div style="background:#1a56db;padding:24px 32px;border-radius:12px 12px 0 0">
            <div style="font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.5px">
              Complio<span style="color:#fbbf24">.</span>
            </div>
          </div>
          <div style="border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;padding:32px">
            <h2 style="margin:0 0 8px;font-size:20px">Herzlich willkommen, {admin_username}! 🎉</h2>
            <p style="color:#6b7280;margin:0 0 24px">
              Dein Betrieb <strong>{betrieb_name}</strong> ist jetzt bei Complio registriert.
              Du hast <strong>30 Tage kostenlos</strong> – kein Risiko, keine Kreditkarte.
            </p>

            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:20px;margin-bottom:24px">
              <div style="font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;
                          color:#6b7280;margin-bottom:12px">Deine Zugangsdaten</div>
              <table style="width:100%;border-collapse:collapse">
                <tr>
                  <td style="padding:6px 0;font-size:13px;color:#6b7280;width:140px">Betriebsnummer</td>
                  <td style="padding:6px 0;font-size:13px;font-weight:700;
                              font-family:monospace;color:#1a56db">{betriebsnummer}</td>
                </tr>
                <tr>
                  <td style="padding:6px 0;font-size:13px;color:#6b7280">Benutzername</td>
                  <td style="padding:6px 0;font-size:13px;font-weight:700;
                              font-family:monospace">{admin_username}</td>
                </tr>
                <tr>
                  <td style="padding:6px 0;font-size:13px;color:#6b7280">Passwort</td>
                  <td style="padding:6px 0;font-size:13px;font-weight:700;
                              font-family:monospace">{admin_passwort}</td>
                </tr>
              </table>
            </div>

            <a href="https://app.getcomplio.de"
               style="display:block;text-align:center;background:#1a56db;color:#fff;
                      padding:14px;border-radius:10px;font-weight:700;font-size:15px;
                      text-decoration:none;margin-bottom:24px">
              Jetzt anmelden →
            </a>

            <p style="font-size:12px;color:#9ca3af;text-align:center;margin:0">
              Fragen? Schreib uns: <a href="mailto:hallo@getcomplio.de"
              style="color:#1a56db">hallo@getcomplio.de</a><br>
              Complio · DSGVO-konform · Server in Deutschland 🇩🇪
            </p>
          </div>
        </div>
        """
        plain = (
            f"Willkommen bei Complio!\n\n"
            f"Betrieb: {betrieb_name}\n"
            f"Betriebsnummer: {betriebsnummer}\n"
            f"Benutzername: {admin_username}\n"
            f"Passwort: {admin_passwort}\n\n"
            f"Login: https://app.getcomplio.de\n\n"
            f"Fragen? hallo@getcomplio.de"
        )
        send_email(to_email=email, subject=subject, body=plain, html_body=html)
    except Exception:
        pass  # Mailversand darf Registrierung nicht blockieren


def erstelle_betrieb_und_admin(
    betrieb_name: str,
    admin_username: str,
    admin_passwort: str,
    admin_email: str = "",
) -> Dict[str, Any]:
    try:
        supabase = get_service_role_client()

        betriebsnummer = generiere_betriebsnummer()
        versuche = 0
        while betriebsnummer_existiert(betriebsnummer) and versuche < 10:
            betriebsnummer = generiere_betriebsnummer()
            versuche += 1

        if versuche >= 10:
            return {"ok": False, "betrieb_id": None, "betriebsnummer": None,
                    "error": "Betriebsnummer konnte nicht generiert werden."}

        betrieb_payload = {"betriebsnummer": betriebsnummer, "name": betrieb_name, "aktiv": True}
        if admin_email:
            betrieb_payload["admin_email"] = admin_email.strip().lower()

        betrieb_result = supabase.table("betriebe").insert(betrieb_payload).execute()
        if not betrieb_result.data:
            return {"ok": False, "betrieb_id": None, "betriebsnummer": None,
                    "error": "Betrieb konnte nicht angelegt werden."}

        betrieb_id = betrieb_result.data[0]["id"]

        pw_hash = bcrypt.hashpw(
            admin_passwort.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user_result = supabase.table("users").insert({
            "username": admin_username,
            "password_hash": pw_hash,
            "role": "admin",
            "is_active": True,
            "betrieb_id": betrieb_id,
        }).execute()

        if not user_result.data:
            supabase.table("betriebe").delete().eq("id", betrieb_id).execute()
            return {"ok": False, "betrieb_id": None, "betriebsnummer": None,
                    "error": "Admin-User konnte nicht angelegt werden."}

        from datetime import datetime, timedelta
        # Starter-Plan: 30 Tage Testphase
        supabase.table("user_feature_plans").insert({
            "betrieb_id": betrieb_id,
            "plan": "starter",
            "valid_until": (datetime.now() + timedelta(days=30)).date().isoformat(),
        }).execute()

        # DSE-Einwilligung protokollieren (Art. 7 DSGVO)
        try:
            supabase.table("dse_einwilligungen").insert({
                "betrieb_id": betrieb_id,
                "admin_username": admin_username,
                "dse_version": "1.0",
            }).execute()
        except Exception:
            pass

        # Willkommens-E-Mail senden
        if admin_email:
            _sende_willkommensmail(
                email=admin_email,
                betrieb_name=betrieb_name,
                betriebsnummer=betriebsnummer,
                admin_username=admin_username,
                admin_passwort=admin_passwort,
            )

        return {
            "ok": True,
            "betrieb_id": betrieb_id,
            "betriebsnummer": betriebsnummer,
            "user_id": user_result.data[0]["id"],
            "error": None,
        }

    except Exception as e:
        return {"ok": False, "betrieb_id": None, "betriebsnummer": None, "error": str(e)}


def pruefe_testphase(betrieb_id: int) -> Dict[str, Any]:
    try:
        from datetime import datetime
        supabase = get_service_role_client()
        result = supabase.table("user_feature_plans")\
            .select("plan, valid_until")\
            .eq("betrieb_id", betrieb_id)\
            .limit(1)\
            .execute()

        if not result.data:
            return {"aktiv": True, "tage_verbleibend": 999, "plan": "pro"}

        row = result.data[0]
        plan = row.get("plan", "starter")
        valid_until = row.get("valid_until")

        if not valid_until:
            return {"aktiv": True, "tage_verbleibend": 999, "plan": plan}

        faellig = datetime.fromisoformat(str(valid_until))
        tage = (faellig - datetime.now()).days
        return {"aktiv": tage > 0, "tage_verbleibend": max(0, tage), "plan": plan}
    except Exception:
        return {"aktiv": True, "tage_verbleibend": 999, "plan": "pro"}
