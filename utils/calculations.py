import pandas as pd
from datetime import timedelta, date

def erstelle_zeitraum_auswertung(mitarbeiter_id, start_datum, end_datum, supabase):
    """Erstellt die detaillierte Tabelle für frei wählbare Zeiträume."""
    # 1. Soll pro Tag berechnen
    ma_res = supabase.table("mitarbeiter").select("soll_stunden_monat").eq("id", mitarbeiter_id).single().execute()
    soll_tag = ma_res.data.get('soll_stunden_monat', 160) / 30
    
    # 2. Daten laden
    ist_res = supabase.table("zeiterfassung").select("datum, stunden").eq("mitarbeiter_id", mitarbeiter_id).gte("datum", start_datum).lte("datum", end_datum).execute()
    plan_res = supabase.table("dienstplan").select("datum, stunden").eq("mitarbeiter_id", mitarbeiter_id).gte("datum", start_datum).lte("datum", end_datum).execute()
    abw_res = supabase.table("urlaubsantraege").select("start_datum, end_datum, typ, status").eq("mitarbeiter_id", mitarbeiter_id).eq("status", "genehmigt").execute()

    ist_map = {r['datum']: r['stunden'] for r in ist_res.data}
    plan_map = {r['datum']: r['stunden'] for r in plan_res.data}
    
    # Abwesenheiten (Krank/Urlaub) als Gutschrift (Abweichung)
    abw_tage = {}
    for a in abw_res.data:
        curr = datetime.strptime(a['start_datum'], '%Y-%m-%d').date()
        ende = datetime.strptime(a['end_datum'], '%Y-%m-%d').date()
        while curr <= ende:
            abw_tage[curr.isoformat()] = 8.0 # Beispiel: 8h pro Tag Gutschrift
            curr += timedelta(days=1)

    # 3. Berechnung
    auswertung = []
    lauf_saldo = 0.0
    aktuell = start_datum
    
    while aktuell <= end_datum:
        d_str = aktuell.isoformat()
        ist = ist_map.get(d_str, 0.0)
        abweichung = abw_tage.get(d_str, 0.0)
        
        # Saldo = Ist - Soll + bezahlte Abwesenheit
        tages_saldo = ist - soll_tag + abweichung
        lauf_saldo += tages_saldo
        
        auswertung.append({
            "Datum": aktuell.strftime("%d.%m.%Y"),
            "Soll Stunden": round(soll_tag, 2),
            "Plan": round(plan_map.get(d_str, 0.0), 2),
            "Ist": round(ist, 2),
            "Abweichung": round(abweichung, 2),
            "Saldo": round(tages_saldo, 2),
            "laufender Saldo": round(lauf__saldo, 2)
        })
        aktuell += timedelta(days=1)
    return pd.DataFrame(auswertung)
