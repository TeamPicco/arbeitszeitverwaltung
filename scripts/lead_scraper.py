#!/usr/bin/env python3
"""
Complio Lead-Scraper
Findet Restaurants und Gastronomie-Betriebe via Google Places API
und speichert sie als Leads in Supabase.

Verwendung:
    python scripts/lead_scraper.py --stadt "Hamburg" --radius 5000 --max 200
    python scripts/lead_scraper.py --staedte "Berlin,Hamburg,München" --max 500
    python scripts/lead_scraper.py --csv leads_import.csv

Umgebungsvariablen:
    GOOGLE_PLACES_API_KEY  — Google Cloud API Key (Places API aktivieren)
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""

import argparse
import csv
import os
import sys
import time
import httpx
from typing import Optional

# Supabase-Pfad ergänzen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BRANCHEN = [
    "restaurant",
    "cafe",
    "bar",
    "gaststaette",
    "imbiss",
    "pizza",
    "bäckerei",
]

DEUTSCHE_GROSSSTAEDTE = [
    "Berlin", "Hamburg", "München", "Köln", "Frankfurt am Main",
    "Stuttgart", "Düsseldorf", "Leipzig", "Dortmund", "Essen",
    "Bremen", "Dresden", "Hannover", "Nürnberg", "Duisburg",
]


def _get_supabase():
    from utils.database import get_service_role_client
    return get_service_role_client()


def _place_exists(place_id: str, supabase) -> bool:
    try:
        r = supabase.table("leads").select("id").eq("google_place_id", place_id).execute()
        return len(r.data) > 0
    except Exception:
        return False


def _save_lead(lead: dict, supabase) -> bool:
    try:
        supabase.table("leads").insert(lead).execute()
        return True
    except Exception:
        return False


def scrape_google_places(
    stadt: str,
    api_key: str,
    radius: int = 5000,
    max_results: int = 200,
    supabase=None,
) -> int:
    """Ruft Google Places Nearby Search auf und speichert Ergebnisse."""
    base_url = "https://maps.googleapis.com/maps/api/place"
    gespeichert = 0
    gesamt = 0

    # Koordinaten der Stadt über Geocoding ermitteln
    geo_r = httpx.get(
        f"{base_url}s/json",
        params={"query": stadt + " Zentrum", "key": api_key},
        timeout=10,
    )
    geo_data = geo_r.json()
    if not geo_data.get("results"):
        print(f"  ⚠  Keine Koordinaten für {stadt} gefunden.")
        return 0

    loc = geo_data["results"][0]["geometry"]["location"]
    location = f"{loc['lat']},{loc['lng']}"

    for typ in ["restaurant", "cafe", "bar", "meal_takeaway", "bakery"]:
        page_token = None
        runde = 0
        while gesamt < max_results:
            params = {
                "location": location,
                "radius": radius,
                "type": typ,
                "language": "de",
                "key": api_key,
            }
            if page_token:
                params["pagetoken"] = page_token
                time.sleep(2)  # Google verlangt kurze Pause vor pagetoken-Request

            try:
                r = httpx.get(f"{base_url}/nearbysearch/json", params=params, timeout=10)
                data = r.json()
            except Exception as e:
                print(f"  ⚠  API-Fehler: {e}")
                break

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                print(f"  ⚠  API Status: {data.get('status')} — {data.get('error_message','')}")
                break

            for place in data.get("results", []):
                gesamt += 1
                if gesamt > max_results:
                    break

                place_id = place.get("place_id")
                if not place_id or (supabase and _place_exists(place_id, supabase)):
                    continue

                # Detail-Request für E-Mail + Website
                email = None
                website = None
                telefon = None
                try:
                    det_r = httpx.get(
                        f"{base_url}/details/json",
                        params={
                            "place_id": place_id,
                            "fields": "website,formatted_phone_number,international_phone_number",
                            "language": "de",
                            "key": api_key,
                        },
                        timeout=8,
                    )
                    det = det_r.json().get("result", {})
                    website = det.get("website")
                    telefon = det.get("international_phone_number") or det.get("formatted_phone_number")
                except Exception:
                    pass

                adresse = place.get("vicinity", "")
                teile = adresse.rsplit(",", 1)
                strasse = teile[0].strip() if len(teile) > 1 else adresse
                ort_teil = teile[-1].strip() if len(teile) > 1 else ""

                lead = {
                    "firmenname":     place.get("name", ""),
                    "branche":        "Gastronomie",
                    "strasse":        strasse,
                    "ort":            ort_teil or stadt,
                    "website":        website,
                    "telefon":        telefon,
                    "quelle":         "google_maps",
                    "google_place_id": place_id,
                    "status":         "neu",
                    "sequenz_schritt": 0,
                }

                if supabase and _save_lead(lead, supabase):
                    gespeichert += 1

                if gesamt % 20 == 0:
                    print(f"  → {gesamt} geprüft, {gespeichert} gespeichert ...")

            page_token = data.get("next_page_token")
            if not page_token:
                break
            runde += 1
            if runde >= 3:  # max 3 Seiten pro Typ = ~60 Ergebnisse
                break

    print(f"  ✅ {stadt}: {gespeichert} neue Leads gespeichert ({gesamt} geprüft)")
    return gespeichert


def import_csv(filepath: str, supabase) -> int:
    """
    Importiert Leads aus einer CSV-Datei.
    Erwartete Spalten (flexibel): firmenname, email, telefon, strasse, plz, ort, website
    """
    gespeichert = 0
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("firmenname") or row.get("name") or row.get("Firma") or ""
            if not name.strip():
                continue
            lead = {
                "firmenname": name.strip(),
                "branche":    row.get("branche", "Gastronomie"),
                "email":      (row.get("email") or row.get("Email") or "").strip() or None,
                "telefon":    (row.get("telefon") or row.get("Telefon") or "").strip() or None,
                "strasse":    (row.get("strasse") or row.get("Straße") or "").strip() or None,
                "plz":        (row.get("plz") or row.get("PLZ") or "").strip() or None,
                "ort":        (row.get("ort") or row.get("Ort") or row.get("Stadt") or "").strip() or None,
                "website":    (row.get("website") or row.get("Website") or "").strip() or None,
                "quelle":     "csv_import",
                "status":     "neu",
                "sequenz_schritt": 0,
            }
            if _save_lead(lead, supabase):
                gespeichert += 1
    print(f"✅ CSV-Import: {gespeichert} Leads gespeichert")
    return gespeichert


def main():
    parser = argparse.ArgumentParser(description="Complio Lead-Scraper")
    parser.add_argument("--stadt",   help="Eine Stadt scrapen (z.B. Hamburg)")
    parser.add_argument("--staedte", help="Kommagetrennte Städte (z.B. Berlin,Hamburg)")
    parser.add_argument("--alle-grossstaedte", action="store_true",
                        help="Alle 15 deutschen Großstädte scrapen")
    parser.add_argument("--radius",  type=int, default=5000, help="Suchradius in Metern")
    parser.add_argument("--max",     type=int, default=200,  help="Max. Leads pro Stadt")
    parser.add_argument("--csv",     help="CSV-Datei importieren statt scrapen")
    args = parser.parse_args()

    supabase = _get_supabase()

    if args.csv:
        import_csv(args.csv, supabase)
        return

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("❌ GOOGLE_PLACES_API_KEY nicht gesetzt.")
        print("   Google Cloud Console → APIs & Services → Places API aktivieren")
        sys.exit(1)

    if args.alle_grossstaedte:
        staedte = DEUTSCHE_GROSSSTAEDTE
    elif args.staedte:
        staedte = [s.strip() for s in args.staedte.split(",")]
    elif args.stadt:
        staedte = [args.stadt]
    else:
        print("Bitte --stadt, --staedte, --alle-grossstaedte oder --csv angeben.")
        parser.print_help()
        sys.exit(1)

    gesamt = 0
    for stadt in staedte:
        print(f"\n📍 Scrape {stadt} ...")
        n = scrape_google_places(
            stadt=stadt,
            api_key=api_key,
            radius=args.radius,
            max_results=args.max,
            supabase=supabase,
        )
        gesamt += n
        time.sleep(1)

    print(f"\n🎯 Fertig: {gesamt} neue Leads insgesamt gespeichert.")


if __name__ == "__main__":
    main()
