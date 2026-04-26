import streamlit as st
from modules.onboarding.onboarding_db import (
    erstelle_betrieb_und_admin,
    generiere_passwort,
    pruefe_testphase,
)


def show_testphase_banner(betrieb_id: int) -> None:
    info = pruefe_testphase(betrieb_id)
    tage = info.get("tage_verbleibend", 0)
    plan = info.get("plan", "starter")

    if plan != "starter":
        return

    if tage > 7:
        st.info(
            f"🎉 Kostenlose Testphase läuft — noch **{tage} Tage** verbleibend. "
            f"[Jetzt upgraden →](mailto:hallo@getcomplio.de)"
        )
    elif tage > 0:
        st.warning(
            f"⚠️ Testphase endet in **{tage} Tagen**. "
            f"Jetzt upgraden, damit nichts verloren geht. "
            f"[Kontakt aufnehmen →](mailto:hallo@getcomplio.de)"
        )
    else:
        st.error(
            "🔒 Dein Testzeitraum ist abgelaufen. "
            "Bitte schreib uns: **hallo@getcomplio.de**"
        )


def show_registrierung() -> None:
    st.markdown("""
    <div style="margin-bottom:8px">
        <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:4px">
            Jetzt kostenlos starten
        </div>
        <div style="font-size:12px;color:#555">
            30 Tage gratis · Keine Kreditkarte · Jederzeit kündbar
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("registrierung_form", clear_on_submit=False):
        betrieb_name = st.text_input(
            "Name deines Betriebs *",
            placeholder="z.B. Restaurant Muster"
        )
        admin_email = st.text_input(
            "Deine E-Mail-Adresse *",
            placeholder="chef@meinrestaurant.de",
            help="Wir schicken dir deine Zugangsdaten per Mail."
        )
        admin_username = st.text_input(
            "Benutzername *",
            placeholder="z.B. chef oder dein Vorname"
        )
        admin_passwort = st.text_input(
            "Passwort *",
            value=generiere_passwort(),
            help="Automatisch generiert — du kannst es jederzeit ändern."
        )
        agb = st.checkbox(
            "Ich akzeptiere die Nutzungsbedingungen und Datenschutzerklärung (DSGVO Art. 13)"
        )

        submitted = st.form_submit_button(
            "🚀 Jetzt kostenlos starten",
            type="primary",
            use_container_width=True
        )

    if submitted:
        fehler = []
        if not betrieb_name.strip():
            fehler.append("Bitte den Namen des Betriebs eingeben.")
        if not admin_email.strip() or "@" not in admin_email:
            fehler.append("Bitte eine gültige E-Mail-Adresse eingeben.")
        if not admin_username.strip():
            fehler.append("Bitte einen Benutzernamen eingeben.")
        if len(admin_passwort) < 8:
            fehler.append("Passwort muss mindestens 8 Zeichen lang sein.")
        if not agb:
            fehler.append("Bitte die Nutzungsbedingungen akzeptieren.")

        if fehler:
            for f in fehler:
                st.error(f)
            return

        with st.spinner("Betrieb wird angelegt..."):
            result = erstelle_betrieb_und_admin(
                betrieb_name=betrieb_name.strip(),
                admin_username=admin_username.strip(),
                admin_passwort=admin_passwort,
                admin_email=admin_email.strip(),
            )

        if result.get("ok"):
            # Auto-Login nach Registrierung
            from utils.database import set_betrieb_session, init_supabase_client
            try:
                supabase = init_supabase_client()
                set_betrieb_session(supabase, result["betrieb_id"], user_id=result["user_id"])
            except Exception:
                pass

            st.session_state.update({
                "logged_in": True,
                "is_admin": True,
                "role": "admin",
                "user_id": result["user_id"],
                "betrieb_id": result["betrieb_id"],
                "betrieb_name": betrieb_name.strip(),
                "mitarbeiter_id": None,
                "_neu_registriert": True,
                "_betriebsnummer": result["betriebsnummer"],
                "_admin_passwort": admin_passwort,
            })
            st.rerun()
        else:
            st.error(
                f"Registrierung fehlgeschlagen: "
                f"{result.get('error', 'Unbekannter Fehler')}. "
                f"Bitte kontaktiere hallo@getcomplio.de"
            )
