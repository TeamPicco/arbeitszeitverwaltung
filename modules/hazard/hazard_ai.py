import os
import anthropic

DGUV_2026_HINWEIS = (
    "NEU ab 2026: Die DGUV Vorschrift 2 gilt jetzt "
    "für Betriebe bis 20 Mitarbeiter (vorher: 10). "
    "Psychische Belastungen sind jetzt Pflichtbestandteil "
    "der Gefährdungsbeurteilung."
)

ANZAHL_SCHRITTE = 6  # War 5, jetzt 6 mit psychischen Belastungen

SCHRITT_KONTEXT = {
    1: (
        "Schau dir jeden Arbeitsbereich genau an: "
        "Küche, Service, Lager, Reinigung, Büro. "
        "Frag dich: Was könnte hier schiefgehen? "
        "Denk an Stolpern, Schneiden, Hitze, Lärm, "
        "schwere Lasten, Chemikalien und Stress. "
        "Schreib auf was du siehst – ganz einfach, "
        "kein Fachchinesisch."
    ),
    2: (
        "Jetzt bewertest du jede Gefahr die du gefunden hast. "
        "Wie wahrscheinlich ist ein Unfall? Wie schlimm wäre er? "
        "Stufe ein: GERING (unwahrscheinlich, harmlos), "
        "MITTEL (möglich, behandelbar), HOCH (wahrscheinlich "
        "oder schwerwiegend). Sei ehrlich – lieber eine "
        "Gefahr zu viel als eine zu wenig."
    ),
    3: (
        "Für jede Gefahr legst du jetzt eine Maßnahme fest. "
        "Reihenfolge: Erst versuchen die Gefahr ganz zu beseitigen. "
        "Dann technisch absichern (z.B. Schutzgitter). "
        "Dann Arbeit anders organisieren (z.B. Pause einlegen). "
        "Zuletzt: Schutzausrüstung tragen (z.B. Handschuhe). "
        "Das nennt sich STOP-Prinzip. Schreib konkret: "
        "WAS wird gemacht, WER macht es, BIS WANN."
    ),
    4: (
        "Trag ein: Wer setzt welche Maßnahme bis wann um? "
        "Zum Beispiel: 'Rutschfeste Matten – Max Müller – bis 01.05.2026'. "
        "Informiere alle Mitarbeiter über die Maßnahmen. "
        "Das muss schriftlich dokumentiert werden."
    ),
    5: (
        "Nach spätestens einem Jahr prüfst du: "
        "Hat die Maßnahme wirklich geholfen? "
        "Gibt es neue Gefahren? "
        "Mach das auch nach Unfällen, Umbauten oder "
        "wenn neue Mitarbeiter eingestellt werden. "
        "Kurze Notiz reicht: Was wurde geprüft, was ist das Ergebnis."
    ),
    6: (
        "NEU ab 2026 – PFLICHT: Psychische Belastungen. "
        "Frag dich und dein Team: Gibt es regelmäßig extremen Zeitdruck? "
        "Fallen Pausen aus? Gibt es Stress durch schwierige Gäste? "
        "Ist die Schichtplanung fair? Fühlen sich Mitarbeiter wertgeschätzt? "
        "Das ist kein Nice-to-have – seit Januar 2026 ist das genauso "
        "Pflicht wie der Rest. Einfach aufschreiben was belastet."
    )
}

BRANCHEN_KONTEXT = {
    "gastronomie": (
        "Gastronomie/Restaurant "
        "(Küche, Service, Lager, Reinigung) – "
        "Hauptrisiken: Schnittverletzungen, Verbrennungen, "
        "Rutschunfälle, Gefahrstoffe, psychische Belastung "
        "durch Zeitdruck und Kundenkontakt"
    ),
    "einzelhandel": (
        "Einzelhandel "
        "(Kassenbereich, Verkaufsfläche, Lager) – "
        "Hauptrisiken: Heben und Tragen, Bildschirmarbeit, "
        "Kundenumgang, Einbruch/Gewalt, monotone Tätigkeiten"
    ),
    "handwerk": (
        "Handwerksbetrieb "
        "(Werkstatt, Baustelle, Fahrzeuge) – "
        "Hauptrisiken: Maschinen, Absturzgefahr, "
        "Lärm, Staub, Gefahrstoffe, körperliche Belastung"
    ),
    "buero": (
        "Büro "
        "(Bildschirmarbeit, Sitzarbeitsplätze) – "
        "Hauptrisiken: Rückenprobleme, Augenbelastung, "
        "psychische Belastung, mangelnde Bewegung"
    ),
    "pflege": (
        "Pflegeeinrichtung "
        "(Pflege, Küche, Verwaltung) – "
        "Hauptrisiken: körperliche Belastung beim Heben, "
        "Infektionsrisiko, Schichtarbeit, psychische Belastung"
    ),
    "einzelhandel_lebensmittel": (
        "Lebensmitteleinzelhandel "
        "(Kasse, Frischetheke, Lager, Kühlung) – "
        "Hauptrisiken: Kältearbeit, Heben, Schnittgefahr, "
        "Kundenumgang, Zeitdruck"
    ),
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
                "Du hilfst Betriebsinhabern dabei, eine Gefährdungsbeurteilung "
                "zu erstellen – einfach, klar und rechtssicher nach §5 ArbSchG "
                "und DGUV Vorschrift 2 (Stand 2026). "
                "Schreib immer so, als würdest du einem Restaurantbesitzer "
                "persönlich erklären was zu tun ist. "
                "Kein Behördendeutsch. Keine langen Schachtelsätze. "
                "Konkret und verständlich – wie ein guter Berater der neben "
                "dir steht. "
                "Nutze kurze Sätze. Bullet Points wo sinnvoll. "
                "Immer mit konkreten Beispielen aus der genannten Branche. "
                "Antworte ausschließlich auf Deutsch. "
                "Maximal 150 Wörter pro Antwort."
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
