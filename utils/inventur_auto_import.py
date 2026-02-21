"""
Automatischer Import von Inventur-Artikeln beim App-Start
Wird einmalig ausgeführt, falls noch keine Artikel vorhanden sind
"""

import logging
from utils.database import get_supabase_client

logger = logging.getLogger(__name__)


# Inventur-Daten (aus PDF extrahiert)
KATEGORIEN = [
    {"name": "Flaschenbiere", "sortierung": 1},
    {"name": "Fassbiere", "sortierung": 2},
    {"name": "Coke & H2O", "sortierung": 3},
    {"name": "Säfte", "sortierung": 4},
    {"name": "Kaffee & Tee", "sortierung": 5},
    {"name": "Flaschen Weine", "sortierung": 6},
    {"name": "Offene Weine", "sortierung": 7},
    {"name": "Sekt & Champagner", "sortierung": 8},
    {"name": "Spirituosen", "sortierung": 9},
    {"name": "Fisch", "sortierung": 10},
    {"name": "Fleisch", "sortierung": 11},
    {"name": "Milchprodukte", "sortierung": 12},
    {"name": "Trockenwaren", "sortierung": 13},
    {"name": "Gemüse", "sortierung": 14},
]

ARTIKEL = {
    "Flaschenbiere": [
        {"name": "Becks Blue alkoholfrei 0,33l", "einheit": "Fl"},
        {"name": "Hasseröder Schwarzbier 0,5l", "einheit": "Fl"},
        {"name": "Franziskaner Dunkel 0,5l", "einheit": "Fl"},
        {"name": "Franziskaner Kristall 0,5l", "einheit": "Fl"},
        {"name": "Franziskaner alkoholfrei 0,5l", "einheit": "Fl"},
    ],
    "Fassbiere": [
        {"name": "Becks Pils 30l", "einheit": "30L-Fass"},
        {"name": "Franziskaner Hefeweizen 30l", "einheit": "30L-Fass"},
        {"name": "Spaten Hell 30l", "einheit": "30L-Fass"},
        {"name": "San Miguel 30l", "einheit": "30L-Fass"},
    ],
    "Coke & H2O": [
        {"name": "Aqua Panna Fl 0,25l", "einheit": "Fl"},
        {"name": "Aqua Panna Fl 0,75l", "einheit": "Fl"},
        {"name": "San Pellegrino Fl 0,25l", "einheit": "Fl"},
        {"name": "San Pellegrino Fl 0,75l", "einheit": "Fl"},
        {"name": "Coca Cola Zero Fl 0,33l", "einheit": "Fl"},
        {"name": "Fever Tree Tonic Fl 0,2l", "einheit": "Fl"},
        {"name": "Thomas Henry Tonic Fl 0,2l", "einheit": "Fl"},
        {"name": "Schweppes Dry Tonic Fl 0,2l", "einheit": "Fl"},
        {"name": "Schweppes Bitter Lemon Fl 0,2l", "einheit": "Fl"},
        {"name": "Schweppes Ginger Ale Fl 0,2l", "einheit": "Fl"},
        {"name": "Coca Cola Fl 1,25l", "einheit": "Fl"},
        {"name": "Fanta Fl 1,25l", "einheit": "Fl"},
        {"name": "Sprite Fl 1,25l", "einheit": "Fl"},
        {"name": "Tafelwasser Sprudel Fl 1l", "einheit": "Fl"},
        {"name": "Tafelwasser Still Fl 1l", "einheit": "Fl"},
        {"name": "Wildberry Tonic Fl 1l", "einheit": "Fl"},
    ],
    "Säfte": [
        {"name": "Bauer Ananassaft Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Apfelsaft naturtrüb Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Bananensaft Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Traubensaft Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Johannisbeersaft Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Kirschsaft Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Orangensaft Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Mangosaft Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Rhabarbersaft Fl 1l", "einheit": "Fl"},
        {"name": "Birnensaft Fl 1l", "einheit": "Fl"},
        {"name": "Bauer Tomatensaft Fl 0,2l", "einheit": "Fl"},
        {"name": "Rioba Limettensaft", "einheit": "Fl"},
    ],
    "Kaffee & Tee": [
        {"name": "Espressobohnen", "einheit": "kg"},
        {"name": "Kaffeebohnen ganz", "einheit": "kg"},
        {"name": "Schokolade/Keks für Kaffee", "einheit": "st"},
        {"name": "Teebeutel Portion", "einheit": "st"},
        {"name": "Trinkschokoladenpulver", "einheit": "st"},
    ],
    "Flaschen Weine": [
        {"name": "Asio Otus Weiß", "einheit": "Fl"},
        {"name": "Asio Otus Rose", "einheit": "Fl"},
        {"name": "Asio Otus Rot", "einheit": "Fl"},
        {"name": "Barolo", "einheit": "Fl"},
        {"name": "Malbec Baron de Rothschild", "einheit": "Fl"},
        {"name": "Las Morras Rose", "einheit": "Fl"},
        {"name": "Sonsierra Crianza Rioja", "einheit": "Fl"},
        {"name": "Passivento halbtrocken", "einheit": "Fl"},
        {"name": "Riesling Kalkstein", "einheit": "Fl"},
        {"name": "Villa Antinori", "einheit": "Fl"},
        {"name": "Küchenrotwein", "einheit": "Fl"},
    ],
    "Offene Weine": [
        {"name": "Bacchus", "einheit": "l"},
        {"name": "Chardonnay", "einheit": "l"},
        {"name": "Las Morras Rose", "einheit": "l"},
        {"name": "Feuerzangenbowle", "einheit": "l"},
        {"name": "Glühwein", "einheit": "l"},
        {"name": "Hauswein Rot Rioja Pueblo Vio", "einheit": "l"},
        {"name": "Hauswein Rot Toro", "einheit": "l"},
        {"name": "Müller thurgau", "einheit": "l"},
        {"name": "Oromonte", "einheit": "l"},
        {"name": "Primitivo", "einheit": "l"},
        {"name": "Hauswein Weiß Pinot Grigio", "einheit": "l"},
        {"name": "Trapiche Malbec", "einheit": "l"},
        {"name": "Welchriesling", "einheit": "l"},
    ],
    "Sekt & Champagner": [
        {"name": "Moet", "einheit": "Fl"},
        {"name": "Prosecco", "einheit": "l"},
        {"name": "Prosecco Scavi Ray", "einheit": "Fl"},
        {"name": "Rotkäppchen halbtrocken", "einheit": "Fl"},
        {"name": "Rotkäppchen Rieslingtrocken", "einheit": "Fl"},
    ],
    "Spirituosen": [
        {"name": "Absolut Wodka", "einheit": "l"},
        {"name": "Aperol", "einheit": "l"},
        {"name": "Asbach 15 Jahre", "einheit": "l"},
        {"name": "Bacardi Black", "einheit": "l"},
        {"name": "Bacardi White", "einheit": "l"},
        {"name": "Baileys", "einheit": "l"},
        {"name": "Becherbitter", "einheit": "l"},
        {"name": "Buffalo Trace", "einheit": "l"},
        {"name": "Beluga", "einheit": "l"},
        {"name": "Bols Curacao", "einheit": "l"},
        {"name": "Bombay Black Berry", "einheit": "l"},
        {"name": "Bombay Saphir", "einheit": "l"},
        {"name": "Bonollo Grappa", "einheit": "l"},
        {"name": "Bushmills", "einheit": "l"},
        {"name": "Calvados", "einheit": "l"},
        {"name": "Campari", "einheit": "l"},
        {"name": "Chivas Regal", "einheit": "l"},
        {"name": "Courvoisier", "einheit": "l"},
        {"name": "Conte Camillo Negroni", "einheit": "l"},
        {"name": "Dimple", "einheit": "l"},
        {"name": "Don Papa", "einheit": "l"},
        {"name": "Fernet Branca", "einheit": "l"},
        {"name": "Frangellico", "einheit": "l"},
        {"name": "Glennfiddich 15 Jahre", "einheit": "l"},
        {"name": "Grappa Chardonnay", "einheit": "l"},
        {"name": "Grappa Prosecco", "einheit": "l"},
        {"name": "havanna Club 7 Jahre", "einheit": "l"},
        {"name": "Havanna Rum 3 Jahre", "einheit": "l"},
        {"name": "Hennesy XO", "einheit": "l"},
        {"name": "Jack Daniels", "einheit": "l"},
        {"name": "Jack Daniels Single Barrel", "einheit": "l"},
        {"name": "Jägermeister", "einheit": "l"},
        {"name": "Jim Beam", "einheit": "l"},
        {"name": "Leipziger Allasch", "einheit": "l"},
        {"name": "Leipziger Wilhelm", "einheit": "l"},
        {"name": "Limoncella", "einheit": "l"},
        {"name": "Linie", "einheit": "l"},
        {"name": "Long Horn Gin", "einheit": "l"},
        {"name": "Matusalem", "einheit": "l"},
        {"name": "Malteser", "einheit": "l"},
        {"name": "Martini Bianco", "einheit": "l"},
        {"name": "Martini Extra Dry", "einheit": "l"},
        {"name": "Martini Rosso", "einheit": "l"},
        {"name": "Metaxxa", "einheit": "l"},
        {"name": "Montenegro", "einheit": "l"},
        {"name": "Nordhäuser Doppelkorn", "einheit": "l"},
        {"name": "Osborn / Sandemann Sherry", "einheit": "l"},
        {"name": "Ouzo12", "einheit": "l"},
        {"name": "P 31", "einheit": "l"},
        {"name": "Pitu", "einheit": "l"},
        {"name": "Ramazotti", "einheit": "l"},
        {"name": "Remy Martin XO", "einheit": "l"},
        {"name": "Roku Gin", "einheit": "l"},
        {"name": "Sambucca", "einheit": "l"},
        {"name": "Stroh 80", "einheit": "l"},
        {"name": "Tanquerra Gin", "einheit": "l"},
        {"name": "Tequilla Gold", "einheit": "l"},
        {"name": "Tequila Silver", "einheit": "l"},
        {"name": "Underberg", "einheit": "l"},
        {"name": "Unicum", "einheit": "l"},
        {"name": "Williams Birne", "einheit": "l"},
        {"name": "Ziegler No 1 Kirsch", "einheit": "l"},
        {"name": "Ziegler Waldhimbeere", "einheit": "l"},
        {"name": "Ziegler Zwetschge", "einheit": "l"},
        {"name": "Ziegler Williams Birne", "einheit": "l"},
    ],
    "Fisch": [
        {"name": "Garnelen", "einheit": "kg"},
        {"name": "Fjordlachsforelle", "einheit": "kg"},
        {"name": "Flusskrebsschwänze", "einheit": "kg"},
        {"name": "Forelle", "einheit": "kg"},
        {"name": "Heilbutt", "einheit": "kg"},
        {"name": "Lachsfilet", "einheit": "kg"},
        {"name": "Scampis", "einheit": "kg"},
        {"name": "Zanderfilet", "einheit": "kg"},
    ],
    "Fleisch": [
        {"name": "Arg. Hüftsteak", "einheit": "kg"},
        {"name": "Argent. Rinderfilet", "einheit": "kg"},
        {"name": "Argent. Rumpsteak", "einheit": "kg"},
        {"name": "Argent. Rib-Eye", "einheit": "kg"},
        {"name": "Gänsebrust", "einheit": "st"},
        {"name": "gek.Schinken", "einheit": "kg"},
        {"name": "Hackfleisch", "einheit": "kg"},
        {"name": "Bacon geschnitten", "einheit": "kg"},
        {"name": "Lammsteak", "einheit": "kg"},
        {"name": "Putensteak", "einheit": "kg"},
        {"name": "Schweinelachse", "einheit": "kg"},
        {"name": "Schweineschulter", "einheit": "kg"},
        {"name": "Spare Ribs", "einheit": "kg"},
        {"name": "T-Bone-Steak", "einheit": "kg"},
    ],
    "Milchprodukte": [
        {"name": "Balkankäse", "einheit": "kg"},
        {"name": "Büffelmozzarella", "einheit": "st"},
        {"name": "Butter", "einheit": "kg"},
        {"name": "Milch", "einheit": "kg"},
        {"name": "Edamer Käse", "einheit": "kg"},
        {"name": "Gorgonzola", "einheit": "kg"},
        {"name": "Hollandaise", "einheit": "kg"},
        {"name": "Joghurt", "einheit": "kg"},
        {"name": "Küchensahne", "einheit": "kg"},
        {"name": "Margarine", "einheit": "kg"},
        {"name": "Mayonaise", "einheit": "st"},
        {"name": "Parmesan", "einheit": "kg"},
        {"name": "Quark", "einheit": "kg"},
        {"name": "Sauce Bernaise", "einheit": "st"},
    ],
    "Trockenwaren": [
        {"name": "Aro Tomatenketchup", "einheit": "kg"},
        {"name": "Balsamico rot", "einheit": "kg"},
        {"name": "Balsamico Weiß", "einheit": "kg"},
        {"name": "Basmatireis", "einheit": "kg"},
        {"name": "Frittierfett", "einheit": "kg"},
        {"name": "Gewürze", "einheit": "kg"},
        {"name": "Mehl", "einheit": "kg"},
        {"name": "Miss. Barbequesauce", "einheit": "kg"},
        {"name": "Rapsöl", "einheit": "kg"},
        {"name": "Rohrzucker", "einheit": "kg"},
        {"name": "Puderzucker", "einheit": "kg"},
        {"name": "Olivenöl", "einheit": "l"},
        {"name": "Spaghetti", "einheit": "kg"},
        {"name": "Salz", "einheit": "kg"},
        {"name": "Tagliatelle", "einheit": "kg"},
        {"name": "Trüffel", "einheit": "kg"},
        {"name": "Trüffel Öl", "einheit": "l"},
    ],
    "Gemüse": [
        {"name": "Auberginen", "einheit": "st"},
        {"name": "Blattspinat", "einheit": "kg"},
        {"name": "Brokkoli", "einheit": "st"},
        {"name": "Dill", "einheit": "kg"},
        {"name": "Champignons", "einheit": "kg"},
        {"name": "Fenchel", "einheit": "kg"},
        {"name": "Eisberg", "einheit": "kg"},
        {"name": "Feldsalat", "einheit": "kg"},
        {"name": "Gurken", "einheit": "kg"},
        {"name": "ital. Kräuter", "einheit": "st"},
        {"name": "Kartoffeln", "einheit": "kg"},
        {"name": "Maiskolben", "einheit": "kg"},
        {"name": "Minze frisch Box", "einheit": "st"},
        {"name": "Möhren", "einheit": "kg"},
        {"name": "Paprika", "einheit": "kg"},
        {"name": "Pepperoni/Chilli", "einheit": "kg"},
        {"name": "Petersilie", "einheit": "st"},
        {"name": "Porree", "einheit": "kg"},
        {"name": "Ruccola", "einheit": "kg"},
        {"name": "Staudensellerie", "einheit": "kg"},
    ],
}


def auto_import_inventur_artikel():
    """
    Automatischer Import von Inventur-Artikeln beim App-Start
    Wird nur ausgeführt, falls noch keine Artikel vorhanden sind
    """
    try:
        supabase = get_supabase_client()
        
        # Hole Piccolo Betrieb-ID
        betrieb = supabase.table('betriebe').select('id').eq('betriebsnummer', '20262204').execute()
        
        if not betrieb.data or len(betrieb.data) == 0:
            logger.info("Betrieb Piccolo nicht gefunden - kein Auto-Import")
            return False
        
        betrieb_id = betrieb.data[0]['id']
        
        # Prüfe ob bereits Kategorien vorhanden
        kategorien = supabase.table('inventur_kategorien').select('id').eq('betrieb_id', betrieb_id).execute()
        
        if kategorien.data and len(kategorien.data) > 0:
            logger.info(f"Inventur-Artikel bereits vorhanden ({len(kategorien.data)} Kategorien) - kein Import nötig")
            return False
        
        logger.info("Starte automatischen Import von Inventur-Artikeln...")
        
        # Importiere Kategorien
        kategorie_ids = {}
        
        for kat_data in KATEGORIEN:
            result = supabase.table('inventur_kategorien').insert({
                'betrieb_id': betrieb_id,
                'name': kat_data['name'],
                'sortierung': kat_data['sortierung']
            }).execute()
            
            kategorie_ids[kat_data['name']] = result.data[0]['id']
        
        logger.info(f"✅ {len(KATEGORIEN)} Kategorien erstellt")
        
        # Importiere Artikel
        artikel_count = 0
        
        for kategorie_name, artikel_liste in ARTIKEL.items():
            kategorie_id = kategorie_ids[kategorie_name]
            
            for i, artikel_data in enumerate(artikel_liste):
                supabase.table('inventur_artikel').insert({
                    'betrieb_id': betrieb_id,
                    'kategorie_id': kategorie_id,
                    'name': artikel_data['name'],
                    'einheit': artikel_data['einheit'],
                    'sortierung': i + 1
                }).execute()
                
                artikel_count += 1
        
        logger.info(f"✅ {artikel_count} Artikel erstellt")
        logger.info("✅ Automatischer Import abgeschlossen!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Fehler beim automatischen Import: {e}")
        return False
