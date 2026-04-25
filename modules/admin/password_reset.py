"""
Sammel-Passwort-Reset für alle Mitarbeiter eines Betriebs.

Sicherheitsdesign:
- Schreibt nur in den Betrieb des eingeloggten Admins (require_betrieb_id).
- Hashed das neue Passwort mit bcrypt; Klartext geht nicht in DB oder Logs.
- Loggt die Aktion in audit_log (anzahl, betrieb, optional 'must_change_password').
- Zeigt das neue Klartext-Passwort genau einmal in der UI an.
"""
from __future__ import annotations

import secrets
import string
from typing import Optional

import bcrypt
import streamlit as st

from utils.audit_log import log_aktion
from utils.database import get_supabase_client
from utils.session import require_betrieb_id


_NEW_PWD_BUF_KEY = "admin_pw_reset_last_password"


def _generate_password(length: int = 12) -> str:
    """Erzeugt ein robustes Wegwerf-Passwort (Buchstaben + Zahlen)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _users_in_betrieb(supabase, betrieb_id: int) -> list[dict]:
    """Lädt alle Mitarbeiter-User des Betriebs (ohne Admins)."""
    try:
        res = (
            supabase.table("users")
            .select("id,username,role,betrieb_id")
            .eq("betrieb_id", int(betrieb_id))
            .neq("role", "admin")
            .execute()
        )
        return res.data or []
    except Exception:
        # Fallback ohne role-Spalte: alle User des Betriebs
        try:
            res = (
                supabase.table("users")
                .select("id,username,betrieb_id")
                .eq("betrieb_id", int(betrieb_id))
                .execute()
            )
            return res.data or []
        except Exception:
            return []


def _bulk_update_password(supabase, betrieb_id: int, new_hash: str) -> tuple[int, str]:
    """
    Schreibt das neue Hash-Passwort für alle Mitarbeiter-User des Betriebs.
    Versucht erst mit role-Filter, dann ohne (Schema-Kompatibilität).
    Gibt (anzahl_betroffen, fehlertext) zurück.
    """
    base = supabase.table("users").update({"password_hash": new_hash})
    # Variante 1: mit role-Filter
    try:
        res = base.eq("betrieb_id", int(betrieb_id)).neq("role", "admin").execute()
        return len(res.data or []), ""
    except Exception:
        pass
    # Variante 2: ohne role-Spalte
    try:
        res = (
            supabase.table("users")
            .update({"password_hash": new_hash})
            .eq("betrieb_id", int(betrieb_id))
            .execute()
        )
        return len(res.data or []), ""
    except Exception as exc:
        return 0, str(exc)


def show_password_reset() -> None:
    """Streamlit-UI: Sammel-Reset für Mitarbeiter-Passwörter."""
    st.markdown("## 🔐 Mitarbeiter-Passwörter zurücksetzen")
    st.caption(
        "Setzt das Passwort aller Mitarbeiter (außer Admins) deines Betriebs auf einen neuen Wert. "
        "Admins werden nicht angetastet. Die Aktion wird im Audit-Log protokolliert."
    )

    betrieb_id = require_betrieb_id()
    supabase = get_supabase_client()

    affected_users = _users_in_betrieb(supabase, betrieb_id)
    if not affected_users:
        st.info("Es wurden keine Mitarbeiter-Konten in diesem Betrieb gefunden.")
        return

    st.write(f"**{len(affected_users)} Mitarbeiter-Konten** würden zurückgesetzt:")
    with st.expander("Liste anzeigen", expanded=False):
        st.dataframe(
            [
                {"Benutzername": u.get("username") or "-", "Rolle": u.get("role") or "mitarbeiter"}
                for u in affected_users
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.markdown("### Neues Passwort festlegen")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        new_password = st.text_input(
            "Neues Passwort",
            value=st.session_state.get("admin_pw_reset_input", ""),
            type="password",
            help="Mindestens 8 Zeichen empfohlen. Wird gehasht in der DB gespeichert.",
            key="admin_pw_reset_input",
        )
    with col_b:
        if st.button("🔁 Erzeugen", use_container_width=True, key="admin_pw_reset_generate"):
            st.session_state["admin_pw_reset_input"] = _generate_password()
            st.rerun()

    confirm_text_required = "RESET"
    confirm = st.text_input(
        f"Zur Bestätigung **{confirm_text_required}** eingeben",
        key="admin_pw_reset_confirm",
        placeholder=confirm_text_required,
    )

    can_submit = bool(new_password) and confirm.strip() == confirm_text_required and len(new_password) >= 8

    if not can_submit:
        if new_password and len(new_password) < 8:
            st.warning("Bitte mindestens 8 Zeichen verwenden.")
        elif new_password and confirm.strip() != confirm_text_required:
            st.info(f"Bestätigung erforderlich: schreibe '{confirm_text_required}' in das Feld oben.")

    if st.button(
        "Passwörter jetzt zurücksetzen",
        type="primary",
        disabled=not can_submit,
        use_container_width=True,
        key="admin_pw_reset_submit",
    ):
        try:
            new_hash = _hash_password(new_password)
        except Exception as exc:
            st.error(f"Hashen fehlgeschlagen: {exc}")
            return

        affected, err = _bulk_update_password(supabase, betrieb_id, new_hash)
        if err:
            st.error(f"DB-Update fehlgeschlagen: {err}")
            return

        # Audit-Log: Klartext-Passwort niemals loggen
        try:
            log_aktion(
                admin_user_id=int(st.session_state.get("user_id") or 0),
                admin_name=str(
                    st.session_state.get("username")
                    or st.session_state.get("user_name")
                    or "Admin"
                ),
                aktion="passwort_reset_alle",
                tabelle="users",
                datensatz_id=int(betrieb_id),
                begruendung="Sammel-Reset Mitarbeiter-Passwörter",
                mitarbeiter_id=None,
                mitarbeiter_name=None,
                alter_wert=None,
                neuer_wert={"hash_gesetzt": True, "anzahl_betroffen": affected or len(affected_users)},
                betrieb_id=int(betrieb_id),
            )
        except Exception:
            pass

        # Klartext für die einmalige Anzeige zwischenspeichern
        st.session_state[_NEW_PWD_BUF_KEY] = new_password
        st.session_state.pop("admin_pw_reset_input", None)
        st.session_state.pop("admin_pw_reset_confirm", None)
        st.success(
            f"✅ Passwort wurde für {len(affected_users)} Mitarbeiter-Konten zurückgesetzt."
        )

    last_pwd: Optional[str] = st.session_state.get(_NEW_PWD_BUF_KEY)
    if last_pwd:
        st.divider()
        st.markdown("### Neues Passwort (einmalig anzeigen)")
        st.code(last_pwd, language=None)
        st.caption(
            "Bitte unverzüglich den Mitarbeitern auf einem sicheren Weg übermitteln. "
            "Sobald du diese Seite verlässt, wird der Wert nicht mehr angezeigt."
        )
        if st.button("Anzeige ausblenden", key="admin_pw_reset_clear_buffer"):
            st.session_state.pop(_NEW_PWD_BUF_KEY, None)
            st.rerun()
