import pandas as pd
from datetime import datetime, date, timedelta

def get_monatsnamen(monat: int) -> str:
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return monate[monat - 1] if 1 <= monat <= 12 else ""

def berechne_azk_kumuliert(mitarbeiter_id, bis_monat, bis_jahr, supabase_client) -> float:
    """Berechnet den echten Stand des Zeitkontos (Ist minus Soll)."""
    res = supabase_client.table("zeiterfassung").select("stunden").eq("mitarbeiter_id", mitarbeiter_id).execute()
    ist_gesamt = sum(r['stunden'] for r in res.data) if res.data else 0.0
    
    ma_res = supabase_client.table("mitarbeiter").select("soll_stunden_monat").eq("id", mitarbeiter_id).single().execute()
    soll_monat = ma_res.data.get('soll_stunden_monat', 160.0)
    
    # Soll-Stunden bis zum aktuellen Monat aufsummieren
    soll_gesamt = bis_monat * soll_monat
    return round(ist_gesamt - soll_gesamt, 2)

def erstelle_zeitraum_auswertung(mitarbeiter_id, start_datum, end_datum, supabase):
    """Erstellt den detaillierten Bericht für den Admin."""
    ma_res = supabase.table("mitarbeiter").select("soll_stunden_monat").eq("id", mitarbeiter_id).single().execute()
    soll_tag = ma_res.data.get('soll_stunden_monat', 160) / 30.0
    
    ist_res = supabase.table("zeiterfassung").select("datum, stunden").eq("mitarbeiter_id", mitarbeiter_id).gte("datum", start_datum).lte("datum", end_datum).execute()
    ist_map = {r['datum']: r['stunden'] for r in ist_res.data}
    
    auswertung = []
    lauf_saldo = 0.0
    aktuell = start_datum
    while aktuell <= end_datum:
        ist = ist_map.get(aktuell.isoformat(), 0.0)
        tages_saldo = ist - soll_tag
        lauf_saldo += tages_saldo
        auswertung.append({
            "Datum": aktuell.strftime("%d.%m.%Y"),
            "Soll": round(soll_tag, 2),
            "Ist": round(ist, 2),
            "Saldo": round(tages_saldo, 2),
            "laufender Saldo": round(lauf_saldo, 2)
        })
        aktuell += timedelta(days=1)
    return pd.DataFrame(auswertung)            "Datum": aktuell.strftime("%d.%m.%Y"),
            "Soll": round(soll_tag, 2),
            "Ist": round(ist, 2),
            "Saldo": round(tages_saldo, 2),
            "laufender Saldo": round(lauf_saldo, 2)
        })
        aktuell += timedelta(days=1)
    return pd.DataFrame(auswertung)
