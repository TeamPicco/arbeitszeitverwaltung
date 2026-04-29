#!/usr/bin/env python3
"""
Complio Outreach-Runner
Sendet die 4-stufige E-Mail-Sequenz an qualifizierte Leads.

Verwendung (täglich per Cron oder manuell):
    python scripts/outreach_runner.py             # sendet fällige E-Mails
    python scripts/outreach_runner.py --dry-run   # zeigt was gesendet würde
    python scripts/outreach_runner.py --test chef@meinrestaurant.de

Cron-Beispiel (täglich 08:00 Uhr):
    0 8 * * * cd /app && python scripts/outreach_runner.py >> logs/outreach.log 2>&1
"""

import argparse
import os
import sys
from datetime import date, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── E-MAIL-SEQUENZ ──────────────────────────────────────────────────────────
# 4 E-Mails mit steigendem Druck, menschlichem Ton, ohne Spam-Trigger

SEQUENZ = [
    {
        "schritt": 1,
        "versand_nach_tagen": 0,
        "betreff": "{firmenname}: Kommen dir diese Probleme bekannt vor?",
        "html": """
<div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;color:#111;line-height:1.6">
  <p>Hallo,</p>
  <p>
    ich wende mich direkt an dich, weil ich weiß, wie es in der Gastronomie läuft:
    Der Service ist fertig, die Gäste sind weg — und dann fängst du an,
    Stundenlisten zu tippen, WhatsApp-Nachrichten für den Dienstplan zu schreiben
    und zu hoffen, dass die Abrechnung am Monatsende stimmt.
  </p>
  <p>
    Wir haben <strong>Complio</strong> gebaut, weil wir selbst einen
    Gastronomiebetrieb führen und genau das jeden Monat erlebt haben.
  </p>
  <p><strong>Was Complio für dich übernimmt:</strong></p>
  <ul style="padding-left:20px">
    <li>Digitale Zeiterfassung per PIN — kein Papier mehr</li>
    <li>Dienstplan mit automatischer Benachrichtigung</li>
    <li>Lohnabrechnung inkl. Sonntags- und Feiertagszuschläge</li>
    <li>DSGVO-konform, Server in Deutschland</li>
  </ul>
  <p>
    Einrichtung dauert 15 Minuten. Und die ersten 30 Tage kosten gar nichts.
  </p>
  <p style="margin:24px 0">
    <a href="https://app.getcomplio.de"
       style="background:#1a56db;color:#fff;padding:12px 24px;border-radius:8px;
              font-weight:700;text-decoration:none;display:inline-block">
      30 Tage kostenlos testen →
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">
    Falls das gerade kein Thema für dich ist, kein Problem —
    einfach auf diese Mail antworten und ich melde mich nicht mehr.
  </p>
  <p style="color:#6b7280;font-size:13px">
    Viele Grüße<br>
    <strong>Melanie</strong><br>
    Complio · <a href="https://getcomplio.de" style="color:#1a56db">getcomplio.de</a>
  </p>
  <p style="font-size:11px;color:#9ca3af;margin-top:24px;border-top:1px solid #e5e7eb;padding-top:12px">
    Du erhältst diese E-Mail weil {firmenname} ein Gastronomie-Betrieb ist.
    <a href="mailto:hallo@getcomplio.de?subject=Abmelden&body=Bitte+keine+weiteren+Mails+an+{email}"
       style="color:#9ca3af">Abmelden</a>
  </p>
</div>""",
    },
    {
        "schritt": 2,
        "versand_nach_tagen": 3,
        "betreff": "Was kostet ein Fehler bei der Arbeitszeitdokumentation?",
        "html": """
<div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;color:#111;line-height:1.6">
  <p>Hallo,</p>
  <p>
    ich hatte dir vor ein paar Tagen geschrieben — heute kurz zu einem Thema,
    das die meisten Gastronomen unterschätzen: <strong>Bußgelder bei fehlerhafter
    Arbeitszeitdokumentation</strong>.
  </p>
  <p>
    Seit dem Urteil des Europäischen Gerichtshofs (2019) und dem NachwG 2022 gilt:
    <strong>Arbeitszeiten müssen lückenlos dokumentiert werden</strong>.
    Bei einer Betriebsprüfung können Bußgelder von bis zu 30.000 € pro Verstoß
    verhängt werden.
  </p>
  <p>
    Mit Complio ist das automatisch erledigt:
    Jede Ein- und Ausstempelung wird sekundengenau gespeichert,
    unveränderlich protokolliert und ist jederzeit exportierbar.
  </p>
  <p style="margin:24px 0">
    <a href="https://app.getcomplio.de"
       style="background:#1a56db;color:#fff;padding:12px 24px;border-radius:8px;
              font-weight:700;text-decoration:none;display:inline-block">
      Jetzt rechtssicher werden →
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">
    Viele Grüße<br>
    <strong>Melanie</strong><br>
    Complio · <a href="https://getcomplio.de" style="color:#1a56db">getcomplio.de</a>
  </p>
  <p style="font-size:11px;color:#9ca3af;margin-top:24px;border-top:1px solid #e5e7eb;padding-top:12px">
    <a href="mailto:hallo@getcomplio.de?subject=Abmelden&body=Bitte+keine+weiteren+Mails+an+{email}"
       style="color:#9ca3af">Abmelden</a>
  </p>
</div>""",
    },
    {
        "schritt": 3,
        "versand_nach_tagen": 7,
        "betreff": "Wie ein Restaurant 3 Stunden pro Woche zurückgewonnen hat",
        "html": """
<div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;color:#111;line-height:1.6">
  <p>Hallo,</p>
  <p>
    kurze Geschichte: Ein Restaurant-Betreiber aus Hamburg
    hat früher jeden Sonntag 2–3 Stunden damit verbracht,
    die Stunden der Woche zusammenzurechnen, Zuschläge auszurechnen
    und Urlaubstage zu kontrollieren.
  </p>
  <p>
    Seit Complio: <strong>12 Minuten</strong>. Den Rest erledigt das System.
  </p>
  <p>
    Nicht weil er besonders technikaffin ist — sondern weil Complio
    genau für Betriebe wie seines gemacht wurde.
    Der Kiosk am Eingang, die Handy-App für die Mitarbeiter,
    der automatische Lohnzettel am Monatsende.
  </p>
  <p>
    Willst du sehen, wie das bei dir aussehen würde?
    Ich zeige dir das gerne in einem kurzen Video-Call — 20 Minuten,
    komplett unverbindlich.
  </p>
  <p style="margin:24px 0">
    <a href="mailto:hallo@getcomplio.de?subject=Demo-Termin für {firmenname}"
       style="background:#1a56db;color:#fff;padding:12px 24px;border-radius:8px;
              font-weight:700;text-decoration:none;display:inline-block">
      Demo-Termin vereinbaren →
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">Oder direkt testen:</p>
  <p style="margin-top:4px">
    <a href="https://app.getcomplio.de"
       style="background:#f3f4f6;color:#111;padding:10px 20px;border-radius:8px;
              font-weight:600;text-decoration:none;display:inline-block;
              border:1px solid #e5e7eb">
      30 Tage kostenlos →
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px;margin-top:20px">
    Viele Grüße<br>
    <strong>Melanie</strong><br>
    Complio · <a href="https://getcomplio.de" style="color:#1a56db">getcomplio.de</a>
  </p>
  <p style="font-size:11px;color:#9ca3af;margin-top:24px;border-top:1px solid #e5e7eb;padding-top:12px">
    <a href="mailto:hallo@getcomplio.de?subject=Abmelden&body=Bitte+keine+weiteren+Mails+an+{email}"
       style="color:#9ca3af">Abmelden</a>
  </p>
</div>""",
    },
    {
        "schritt": 4,
        "versand_nach_tagen": 14,
        "betreff": "Letzte Frage — dann höre ich auf",
        "html": """
<div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;color:#111;line-height:1.6">
  <p>Hallo,</p>
  <p>
    ich habe dir in den letzten Wochen ein paarmal geschrieben — das war die letzte Mail.
    Versprochen.
  </p>
  <p>
    Nur eine kurze Frage: <strong>Ist Complio gerade kein Thema für dich,
    oder gibt es etwas, das dich zögern lässt?</strong>
  </p>
  <p>
    Falls es ums Geld geht, können wir reden — für kleinere Betriebe
    haben wir flexible Optionen. Falls die Timing nicht stimmt,
    sag einfach Bescheid, wann ich mich wieder melden soll.
  </p>
  <p>
    Und falls du sagst "danke, kein Interesse" — das respektiere ich
    selbstverständlich und melde mich nicht mehr.
  </p>
  <p style="margin:24px 0">
    <a href="mailto:hallo@getcomplio.de?subject=Feedback von {firmenname}"
       style="background:#1a56db;color:#fff;padding:12px 24px;border-radius:8px;
              font-weight:700;text-decoration:none;display:inline-block">
      Kurz antworten →
    </a>
  </p>
  <p style="color:#6b7280;font-size:13px">
    Viele Grüße<br>
    <strong>Melanie</strong><br>
    Complio · <a href="https://getcomplio.de" style="color:#1a56db">getcomplio.de</a>
  </p>
  <p style="font-size:11px;color:#9ca3af;margin-top:24px;border-top:1px solid #e5e7eb;padding-top:12px">
    <a href="mailto:hallo@getcomplio.de?subject=Abmelden&body=Bitte+keine+weiteren+Mails+an+{email}"
       style="color:#9ca3af">Abmelden</a>
  </p>
</div>""",
    },
]


def _render(template: str, lead: dict) -> str:
    return template.format(
        firmenname=lead.get("firmenname", ""),
        email=lead.get("email", ""),
        ort=lead.get("ort", ""),
    )


def _send_sequence_email(lead: dict, schritt_config: dict, dry_run: bool, supabase) -> bool:
    email = lead.get("email")
    if not email:
        return False

    betreff = _render(schritt_config["betreff"], lead)
    html    = _render(schritt_config["html"], lead)
    schritt = schritt_config["schritt"]

    if dry_run:
        print(f"  [DRY] → {email} | Schritt {schritt} | {betreff}")
        return True

    try:
        from utils.email_service import send_email
        ok = send_email(
            to_email=email,
            subject=betreff,
            body=f"Complio — {betreff}\n\nhttps://app.getcomplio.de",
            html_body=html,
        )
        if ok:
            # Nächsten Schritt berechnen
            naechster = schritt + 1
            if naechster <= len(SEQUENZ):
                tage = SEQUENZ[naechster - 1]["versand_nach_tagen"]
                naechste_email = (date.today() + timedelta(days=tage)).isoformat()
                neuer_status = "kontaktiert"
            else:
                naechste_email = None
                neuer_status = "kontaktiert"

            from datetime import datetime, timezone
            supabase.table("leads").update({
                "sequenz_schritt":  schritt,
                "naechste_email":   naechste_email,
                "emails_gesendet":  (lead.get("emails_gesendet") or 0) + 1,
                "letzter_kontakt":  datetime.now(timezone.utc).isoformat(),
                "status":           neuer_status,
            }).eq("id", lead["id"]).execute()

            supabase.table("lead_emails").insert({
                "lead_id": lead["id"],
                "schritt": schritt,
                "betreff": betreff,
            }).execute()

        return ok
    except Exception as e:
        print(f"  ⚠  Fehler bei {email}: {e}")
        return False


def run(dry_run: bool = False, test_email: Optional[str] = None):
    from utils.database import get_service_role_client
    supabase = get_service_role_client()

    if test_email:
        # Test-E-Mail: Schritt 1 an beliebige Adresse
        fake_lead = {
            "id": 0,
            "firmenname": "Test-Restaurant",
            "email": test_email,
            "ort": "Berlin",
            "emails_gesendet": 0,
        }
        print(f"Test-Mail → {test_email}")
        _send_sequence_email(fake_lead, SEQUENZ[0], dry_run=False, supabase=supabase)
        return

    heute = date.today().isoformat()

    # Leads holen die heute fällig sind
    fällige = supabase.table("leads")\
        .select("*")\
        .in_("status", ["neu", "kontaktiert"])\
        .not_.is_("email", "null")\
        .lte("naechste_email", heute)\
        .order("naechste_email")\
        .limit(500)\
        .execute().data

    # Neue Leads die noch nie kontaktiert wurden
    neue = supabase.table("leads")\
        .select("*")\
        .eq("status", "neu")\
        .eq("sequenz_schritt", 0)\
        .is_("naechste_email", "null")\
        .not_.is_("email", "null")\
        .order("created_at")\
        .limit(200)\
        .execute().data

    alle = {l["id"]: l for l in fällige + neue}.values()

    gesendet = 0
    übersprungen = 0

    for lead in alle:
        schritt_nr = (lead.get("sequenz_schritt") or 0) + 1
        if schritt_nr > len(SEQUENZ):
            übersprungen += 1
            continue

        config = next((s for s in SEQUENZ if s["schritt"] == schritt_nr), None)
        if not config:
            continue

        ok = _send_sequence_email(lead, config, dry_run, supabase)
        if ok:
            gesendet += 1
        else:
            übersprungen += 1

    print(f"{'[DRY RUN] ' if dry_run else ''}Outreach: {gesendet} E-Mails gesendet, {übersprungen} übersprungen")


def main():
    parser = argparse.ArgumentParser(description="Complio Outreach-Runner")
    parser.add_argument("--dry-run", action="store_true", help="Nicht senden, nur zeigen")
    parser.add_argument("--test", metavar="EMAIL", help="Test-Mail an diese Adresse")
    args = parser.parse_args()
    run(dry_run=args.dry_run, test_email=args.test)


if __name__ == "__main__":
    main()
