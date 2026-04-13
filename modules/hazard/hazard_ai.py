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


def lade_aktuelle_rechtsinfos(supabase_client=None) -> str:
    """
    Lädt aktuelle Rechtsinformationen aus der Datenbank
    und gibt sie als formatierten String zurück.
    Wird automatisch in jeden KI-Aufruf eingebaut.
    """
    basis_rechtsstand = """
AKTUELLER RECHTSSTAND (automatisch geladen):

Gesetze und Vorschriften:
- §5 ArbSchG: Gefährdungsbeurteilung Pflicht für JEDEN Betrieb
- §6 ArbSchG: Dokumentationspflicht ab 10 Mitarbeiter
  (unter 10: empfohlen aber nicht Pflicht)
- DGUV Vorschrift 2 (Stand: 01.01.2026, aktuellste Fassung):
  Vereinfachte Betreuung jetzt für Betriebe bis 20 Mitarbeiter
  (vorher: bis 10 Mitarbeiter)
- NEU 2026: Psychische Belastungen sind PFLICHTBESTANDTEIL
  der Gefährdungsbeurteilung – nicht mehr optional
- Mindestlohn aktuell: 12,82 € (Stand: Januar 2025)
- Maximale Arbeitszeit: 8 Stunden/Tag, max. 10 Stunden
  wenn Ausgleich innerhalb 6 Monate
- Mindestruhezeit: 11 Stunden zwischen zwei Schichten
- Jährliche Überprüfungspflicht der Gefährdungsbeurteilung

Bußgelder bei Verstößen:
- Fehlende Gefährdungsbeurteilung: bis 30.000 €
- Falsche Arbeitszeitdokumentation: bis 15.000 €
- Fehlende Unterweisung der Mitarbeiter: bis 5.000 €
"""

    if supabase_client is None:
        return basis_rechtsstand

    try:
        # Lade die neuesten 5 Rechtsänderungen aus der DB
        updates = supabase_client.table("legal_update_log")\
            .select("law_name, new_value, valid_from")\
            .order("valid_from", desc=True)\
            .limit(5)\
            .execute()

        if not updates.data:
            return basis_rechtsstand

        zusatz = "\nNEUESTE RECHTSÄNDERUNGEN AUS DATENBANK:\n"
        for update in updates.data:
            zusatz += (
                f"- {update.get('law_name')}: "
                f"{update.get('new_value')} "
                f"(gültig ab {update.get('valid_from')})\n"
            )

        return basis_rechtsstand + zusatz

    except Exception:
        return basis_rechtsstand


def trage_rechtsaenderung_ein(
    supabase_client,
    law_name: str,
    old_value: str,
    new_value: str,
    valid_from: str
) -> bool:
    """
    Trägt eine neue Rechtsänderung in die Datenbank ein.
    Wird von Complio-Admin aufgerufen wenn sich Gesetze ändern.
    Beispiel: Mindestlohnerhöhung, neue DGUV-Vorschrift etc.
    """
    try:
        supabase_client.table("legal_update_log").insert({
            "law_name": law_name,
            "old_value": old_value,
            "new_value": new_value,
            "valid_from": valid_from,
        }).execute()
        return True
    except Exception:
        return False


def generiere_ki_vorschlag(
    step_number: int,
    industry: str,
    existing_text: str = "",
    supabase_client=None
) -> str:
    """
    Ruft die Anthropic API auf und gibt einen deutschen
    Vorschlag für den jeweiligen Schritt zurück.
    """
    try:
        rechtsstand = lade_aktuelle_rechtsinfos(supabase_client)
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

        branche = BRANCHEN_KONTEXT.get(industry, BRANCHEN_KONTEXT["sonstiges"])
        schritt_hinweis = SCHRITT_KONTEXT.get(step_number, "")

        bisheriger_text = ""
        if existing_text and existing_text.strip():
            bisheriger_text = f"\n\nBisheriger Eintrag des Nutzers:\n{existing_text}\n\nErgänze oder verbessere diesen Text."

        prompt = (
            f"{rechtsstand}\n\n"
            f"BETRIEB: {branche}\n"
            f"SCHRITT {step_number}: {schritt_hinweis}\n"
            f"{bisheriger_text}\n\n"
            f"Gib einen konkreten, verständlichen Vorschlag für diesen Schritt. "
            f"Einfache Sprache – kein Behördendeutsch. "
            f"Maximal 150 Wörter. Direkt und praxisnah."
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
