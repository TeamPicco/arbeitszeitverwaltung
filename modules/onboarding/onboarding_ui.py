import streamlit as st
from modules.onboarding.onboarding_db import (
    erstelle_betrieb_und_admin,
    generiere_passwort,
    pruefe_testphase
)


def show_testphase_banner(betrieb_id: int) -> None:
    """
    Zeigt einen Banner wenn der Betrieb noch in der Testphase ist.
    Wird oben im Admin-Dashboard eingeblendet.
    """
    info = pruefe_testphase(betrieb_id)
    tage = info.get("tage_verbleibend", 0)
    plan = info.get("plan", "starter")

    if plan == "starter" and tage > 0:
        if tage <= 7:
            st.warning(
                f"⚠️ Deine kostenlose Testphase endet in **{tage} Tagen**. "
                f"Jetzt upgraden um alle Funktionen zu behalten."
            )
        else:
            st.info(
                f"🎉 Du bist im kostenlosen Testzeitraum – "
                f"noch **{tage} Tage** verbleibend."
            )
    elif plan == "starter" and tage == 0:
        st.error(
            "🔒 Dein Testzeitraum ist abgelaufen. "
            "Bitte buche einen Plan um weiter arbeiten zu können."
        )


def show_registrierung() -> None:
    """
    Registrierungsformular für neue Betriebe.
    Wird als eigener Tab im Login-Bereich angezeigt.
    """
    st.markdown("## 🏢 Neuen Betrieb registrieren")
    st.markdown(
        "Erstelle jetzt deinen kostenlosen Testzugang. "
        "**30 Tage kostenlos** – keine Kreditkarte erforderlich."
    )
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:

        with st.form("registrierung_form"):
            st.markdown("### Betriebsdaten")
            betrieb_name = st.text_input(
                "Name des Betriebs *",
                placeholder="z.B. Restaurant Muster GmbH"
            )

            st.markdown("### Admin-Zugangsdaten")
            st.caption(
                "Diese Zugangsdaten nutzt du zum Einloggen. "
                "Merke sie dir gut."
            )
            admin_username = st.text_input(
                "Benutzername *",
                placeholder="z.B. admin oder dein Name"
            )

            passwort_vorschlag = generiere_passwort()
            admin_passwort = st.text_input(
                "Passwort *",
                value=passwort_vorschlag,
                help="Automatisch generiert – du kannst es ändern."
            )
            admin_passwort2 = st.text_input(
                "Passwort wiederholen *",
                type="password"
            )

            st.markdown("---")
            agb = st.checkbox(
                "Ich akzeptiere die [Nutzungsbedingungen](https://app.getcomplio.de/agb) "
                "und [Datenschutzerklärung](https://app.getcomplio.de/datenschutz) (DSGVO Art. 13)"
            )

            submitted = st.form_submit_button(
                "🚀 Jetzt kostenlos starten",
                type="primary",
                use_container_width=True
            )

        if submitted:
            # Validierung
            fehler = []
            if not betrieb_name.strip():
                fehler.append("Bitte den Namen des Betriebs eingeben.")
            if not admin_username.strip():
                fehler.append("Bitte einen Benutzernamen eingeben.")
            if len(admin_passwort) < 8:
                fehler.append("Passwort muss mindestens 8 Zeichen haben.")
            if admin_passwort != admin_passwort2:
                fehler.append("Passwörter stimmen nicht überein.")
            if not agb:
                fehler.append("Bitte Nutzungsbedingungen akzeptieren.")

            if fehler:
                for f in fehler:
                    st.error(f)
            else:
                with st.spinner("Betrieb wird angelegt..."):
                    result = erstelle_betrieb_und_admin(
                        betrieb_name=betrieb_name.strip(),
                        admin_username=admin_username.strip(),
                        admin_passwort=admin_passwort,
                    )

                if result.get("ok"):
                    st.success("✅ Betrieb erfolgreich angelegt!")
                    st.markdown("---")
                    st.markdown("### 🔑 Deine Zugangsdaten")
                    st.info(
                        f"**Betriebsnummer:** `{result.get('betriebsnummer')}`\n\n"
                        f"**Benutzername:** `{admin_username}`\n\n"
                        f"**Passwort:** `{admin_passwort}`"
                    )
                    st.warning(
                        "⚠️ Bitte notiere dir diese Zugangsdaten jetzt. "
                        "Das Passwort wird nicht erneut angezeigt."
                    )
                    st.markdown(
                        "👉 Gehe zum **Login-Tab** und melde dich "
                        "mit deiner Betriebsnummer an."
                    )
                else:
                    st.error(
                        f"Fehler beim Anlegen: "
                        f"{result.get('error', 'Unbekannter Fehler')}"
                    )
