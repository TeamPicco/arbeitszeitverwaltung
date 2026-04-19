import os
import anthropic
from typing import Optional

DGUV_2026_HINWEIS = (
    "NEU ab 2026: DGUV Vorschrift 2 gilt jetzt für Betriebe "
    "bis 20 Mitarbeiter. Psychische Belastungen sind Pflicht."
)

ANZAHL_SCHRITTE = 6


def lade_aktuelle_rechtsinfos(supabase_client=None) -> str:
    """
    Lädt aktuellen Rechtsstand aus DB und gibt ihn als
    String zurück. Wird automatisch in KI-Prompt eingebaut.
    """
    basis = """AKTUELLER RECHTSSTAND (Stand 2026):
- §5 ArbSchG: Gefährdungsbeurteilung Pflicht für jeden Betrieb
- §6 ArbSchG: Dokumentationspflicht ab 10 Mitarbeitern
- DGUV Vorschrift 2 (01.01.2026): Vereinfachte Betreuung
  jetzt bis 20 Mitarbeiter (vorher 10)
- NEU 2026: Psychische Belastungen sind Pflichtbestandteil
- Mindestlohn: 12,82 Euro/Stunde (Stand Januar 2025)
- Max. Arbeitszeit: 8h/Tag, max. 10h mit Ausgleich
- Mindestruhezeit: 11 Stunden zwischen Schichten
- Bußgelder: bis 30.000 Euro bei fehlender Gefährdungsbeurteilung"""

    if supabase_client is None:
        return basis

    try:
        updates = supabase_client.table("legal_update_log")\
            .select("law_name, new_value, valid_from")\
            .order("valid_from", desc=True)\
            .limit(5)\
            .execute()

        if not updates.data:
            return basis

        zusatz = "\nNEUESTE RECHTSÄNDERUNGEN:\n"
        for u in updates.data:
            zusatz += (
                f"- {u.get('law_name')}: "
                f"{u.get('new_value')} "
                f"(ab {u.get('valid_from')})\n"
            )
        return basis + zusatz

    except Exception:
        return basis


def trage_rechtsaenderung_ein(
    supabase_client,
    law_name: str,
    old_value: str,
    new_value: str,
    valid_from: str
) -> bool:
    """
    Trägt neue Rechtsänderung in die Datenbank ein.
    Aufruf durch Admin wenn sich Gesetze ändern.
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
            f"Schreib einen konkreten Vorschlag für diesen Schritt. "
            f"Einfache Sprache – kein Behördendeutsch. "
            f"Kurze Sätze. Konkrete Beispiele aus der Branche. "
            f"Maximal 150 Wörter."
        )

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=400,
            system=(
                "Du hilfst Betriebsinhabern dabei, eine Gefährdungsbeurteilung "
                "zu erstellen – einfach, klar und rechtssicher nach §5 ArbSchG "
                "und DGUV Vorschrift 2 (Stand 2026). "
                "Schreib so, als würdest du einem Restaurantbesitzer persönlich "
                "erklären was zu tun ist. "
                "Kein Behördendeutsch. Keine langen Schachtelsätze. "
                "Konkret und verständlich – wie ein guter Berater. "
                "Kurze Sätze. Bullet Points wo sinnvoll. "
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


def generiere_komplette_beurteilung(antworten: dict, branche: str = "gastronomie") -> Optional[str]:
    """Generiert rechtssichere Gefährdungsbeurteilung nach aktuellem deutschem Recht."""
    try:
        import os
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None

        client = Anthropic(api_key=api_key)

        antworten_text = "\n".join([
            f"- {data['frage']}: {data['antwort']}"
            for key, data in antworten.items()
        ])

        system_prompt = """Du bist Fachkraft für Arbeitssicherheit (Sifa) mit Schwerpunkt Gastronomie und Hotellerie in Deutschland.

Du erstellst rechtssichere Gefährdungsbeurteilungen nach aktuellem Rechtsstand (Stand 2026).

RELEVANTE RECHTSGRUNDLAGEN:
- Arbeitsschutzgesetz (ArbSchG) §§ 3, 5, 6 - Grundpflicht des Arbeitgebers
- Arbeitsstättenverordnung (ArbStättV) - ASR A1.3, A1.5, A2.3, A3.4, A3.5, A3.6, A4.1
- Betriebssicherheitsverordnung (BetrSichV)
- Gefahrstoffverordnung (GefStoffV)
- Biostoffverordnung (BioStoffV)
- Jugendarbeitsschutzgesetz (JArbSchG)
- Mutterschutzgesetz (MuSchG) - Gefährdungsbeurteilung nach § 10 MuSchG
- DGUV Vorschrift 1 - Grundsätze der Prävention
- DGUV Vorschrift 2 (NEUE FASSUNG AB 01.01.2026!) - Betreuung durch Sifa und Betriebsarzt
- DGUV Regel 110-003 - Branchenregel Gastgewerbe (BGN)
- DGUV Information 208-050 - Stand auf dem Fußboden (Rutschgefahr)
- DGUV Information 207-006 - Bodenbeläge für Nassbereiche (Stand 2026)
- LMHV - Lebensmittelhygiene-Verordnung
- VO (EG) Nr. 852/2004 - EU-Hygieneverordnung (HACCP-Konzept Pflicht)
- IfSG § 43 - Erstbelehrung durch Gesundheitsamt

WICHTIG AB 2026:
- DGUV Vorschrift 2 NEU: Bei Betrieben bis 20 Mitarbeiter gilt jetzt das KPZ-Modell (vorher 10)
- Selbsterklärung zur Gefährdungsbeurteilung bei Nutzung alternativer Betreuungsmodelle PFLICHT
- Fortbildungspflicht für Inhaber bei alternativem Betreuungsmodell
- Psychische Belastungen müssen nach § 5 ArbSchG berücksichtigt werden

BUSSGELD-RAHMEN:
- Fehlende Gefährdungsbeurteilung: bis 30.000 € (§ 25 ArbSchG)
- Keine Unterweisungen: bis 5.000 €
- Fehlende Erste-Hilfe-Organisation: bis 5.000 €
- HACCP-Verstöße: bis 50.000 € (LFGB)
- IfSG § 43 Verstöße: bis 25.000 €"""

        user_prompt = f"""Betrieb: Gastronomie
Betriebsanalyse (Wizard-Antworten):

{antworten_text}

Erstelle eine VOLLSTÄNDIGE rechtssichere Gefährdungsbeurteilung.

Format:

# GEFÄHRDUNGSBEURTEILUNG
**Nach § 5 ArbSchG, DGUV Vorschrift 1 und DGUV Regel 110-003**

## 1. BETRIEBSPROFIL
[Kurze Zusammenfassung des Betriebs basierend auf den Antworten]

## 2. RECHTLICHE EINORDNUNG
[Aktueller Rechtsstand speziell für diesen Betrieb, Verweis auf DGUV V2 ab 2026 falls anwendbar]

## 3. SYSTEMATISCHE GEFÄHRDUNGSERMITTLUNG

Nutze diese 10 Gefährdungskategorien (nach DGUV). Für jede zutreffende Kategorie:
- Konkrete Gefährdung benennen
- Risikostufe: NIEDRIG / MITTEL / HOCH / KRITISCH
- Konkrete Schutzmaßnahmen
- Rechtsgrundlage

### 3.1 Mechanische Gefährdungen
(Schnittverletzungen, Stoßen, Quetschen, Sturz)

### 3.2 Elektrische Gefährdungen
(Elektrische Geräte, Feuchträume)

### 3.3 Gefahrstoffe
(Reinigungsmittel, Desinfektionsmittel - GefStoffV, Betriebsanweisungen)

### 3.4 Biologische Arbeitsstoffe
(Lebensmittel, Mikroorganismen - BioStoffV)

### 3.5 Brand- und Explosionsgefahren
(Gas, Fritteusen, offene Flammen - DGUV V 49)

### 3.6 Thermische Gefährdungen
(Verbrennungen, Verbrühungen, Kälte)

### 3.7 Physische Belastungen
(Heben/Tragen - LasthandhabV, Zwangshaltungen, langes Stehen)

### 3.8 Psychische Belastungen
(PFLICHT nach § 5 ArbSchG! Stress, Zeitdruck, Konflikte)

### 3.9 Arbeitsorganisation
(Arbeitszeit, Pausen, Nachtarbeit - ArbZG)

### 3.10 Besondere Personengruppen
(Jugendliche - JArbSchG, Schwangere - MuSchG)

## 4. PRIORISIERTER MASSNAHMENPLAN
Tabelle mit:
| Priorität | Maßnahme | Verantwortlich | Umsetzungsfrist | Status |

Priorität 1 = Sofort (kritische Gefahren)
Priorität 2 = Innerhalb 4 Wochen
Priorität 3 = Innerhalb 3 Monate

## 5. UNTERWEISUNGSPFLICHTEN
Für diesen Betrieb konkret erforderliche Unterweisungen mit Häufigkeit:
- Erstunterweisung (vor Aufnahme der Tätigkeit)
- Jährliche Wiederholungsunterweisung (DGUV V1 § 4)
- Anlassbezogene Unterweisungen

## 6. PFLICHTDOKUMENTE
Checkliste der zu führenden Nachweise:
- [ ] Gefährdungsbeurteilung (dieses Dokument)
- [ ] Unterweisungsnachweise (jährlich)
- [ ] HACCP-Dokumentation
- [ ] IfSG § 43 Belehrungen
- [ ] Erste-Hilfe-Organisation
- [ ] Betriebsanweisungen für Gefahrstoffe
- [ ] Prüfnachweise ortsveränderliche elektrische Geräte (DGUV V3)
- [ ] Mutterschutz-Gefährdungsbeurteilung (falls zutreffend)

## 7. NÄCHSTE SCHRITTE
1. Sofortige Maßnahmen umsetzen
2. Mitarbeiterunterweisung durchführen
3. Betreuung durch Sifa/Betriebsarzt organisieren (DGUV V2 ab 2026)
4. Wiederholungsprüfung in 12 Monaten

## 8. RECHTSHINWEIS
Diese KI-generierte Beurteilung ersetzt nicht die abschließende Prüfung durch eine Fachkraft für Arbeitssicherheit. Bei Unklarheiten wende dich an die BGN (0621 4456-3232) oder einen Sifa-Dienstleister.

---

Sei PRÄZISE, KONKRET und beziehe dich auf die spezifischen Wizard-Antworten. Nenne Bußgeld-Höhen zur Sensibilisierung. Priorisiere Sofortmaßnahmen."""

        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=6000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        return message.content[0].text

    except Exception as e:
        import traceback
        error_msg = f"KI-Fehler: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        import streamlit as st
        st.error(f"KI-Fehler: {str(e)[:200]}")
        return None
