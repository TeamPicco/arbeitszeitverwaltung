import os
import anthropic

SCHRITT_KONTEXT = {
    1: "Ermittle alle möglichen Gefährdungen am Arbeitsplatz. "
       "Denke an physische, chemische, biologische, psychische "
       "und ergonomische Gefährdungen.",
    2: "Beurteile die ermittelten Gefährdungen nach Eintritts- "
       "wahrscheinlichkeit und Schwere des möglichen Schadens. "
       "Priorisiere nach Risikostufen: gering, mittel, hoch.",
    3: "Lege konkrete Schutzmaßnahmen fest. Beachte die STOP-Hierarchie: "
       "Substitution → Technisch → Organisatorisch → Persönlich.",
    4: "Beschreibe wie die festgelegten Maßnahmen umgesetzt werden. "
       "Wer ist verantwortlich? Bis wann? Mit welchen Ressourcen?",
    5: "Erkläre wie die Wirksamkeit der Maßnahmen überprüft wird. "
       "Welche Kontrollintervalle? Welche Messkriterien?"
}

BRANCHEN_KONTEXT = {
    "gastronomie": "Gastronomie/Restaurant (Küche, Service, Lager)",
    "einzelhandel": "Einzelhandel (Kassenbereich, Lager, Verkaufsfläche)",
    "handwerk": "Handwerksbetrieb (Werkstatt, Baustelle, Fahrzeuge)",
    "buero": "Büro (Bildschirmarbeit, Sitzarbeitsplätze)",
    "sonstiges": "Allgemeiner Betrieb"
}


def generiere_ki_vorschlag(
    step_number: int,
    industry: str,
    existing_text: str = ""
) -> str:
    """
    Ruft die Anthropic API auf und gibt einen deutschen
    Vorschlag für den jeweiligen Schritt zurück.
    """
    try:
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

        branche = BRANCHEN_KONTEXT.get(industry, BRANCHEN_KONTEXT["sonstiges"])
        schritt_hinweis = SCHRITT_KONTEXT.get(step_number, "")

        bisheriger_text = ""
        if existing_text and existing_text.strip():
            bisheriger_text = f"\n\nBisheriger Eintrag des Nutzers:\n{existing_text}\n\nErgänze oder verbessere diesen Text."

        prompt = (
            f"Branche: {branche}\n"
            f"Schritt {step_number} der Gefährdungsbeurteilung nach §5 ArbSchG:\n"
            f"{schritt_hinweis}"
            f"{bisheriger_text}\n\n"
            f"Gib einen konkreten, praxisnahen Vorschlag für diesen Schritt. "
            f"Maximal 150 Wörter. Nur den Vorschlagstext, keine Einleitung."
        )

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=400,
            system=(
                "Du bist ein Experte für deutsche Arbeitssicherheit. "
                "Du kennst §5 ArbSchG, die DGUV-Vorschriften und alle relevanten "
                "deutschen Arbeitsschutzgesetze auswendig. "
                "Gib konkrete, praxisnahe und rechtssichere Vorschläge für "
                "Gefährdungsbeurteilungen. Antworte ausschließlich auf Deutsch."
            ),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        texte = []
        for block in message.content:
            text = getattr(block, "text", None)
            if text:
                texte.append(text.strip())

        if texte:
            return "\n".join(texte).strip()
        return "Kein KI-Vorschlag verfügbar."
    except Exception:
        return "KI-Vorschlag konnte aktuell nicht generiert werden."


def pruefe_api_key() -> bool:
    """Prüft ob ein gültiger Anthropic API-Key vorhanden ist."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return key.startswith("sk-ant-") and len(key) > 20
