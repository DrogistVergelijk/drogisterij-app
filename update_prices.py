import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATIE ---
# 1. VERVANG DIT door de exacte naam van jouw Google Sheet bestand!
GOOGLE_SHEET_NAME = "Drogisterij Database" 

# 2. VERVANG DIT door de naam van het tabblad waar de live prijzen in moeten komen
TABBLAD_NAAM = "Live Prijzen" 

# Universele headers om te zorgen dat de websites ons niet blokkeren
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def get_as_watson_data(store_type):
    """Haalt data op voor Kruidvat (kvn) of Trekpleister (tpa)."""
    store_name = "Kruidvat" if store_type == "kvn" else "Trekpleister"
    domain = "kruidvat.nl" if store_type == "kvn" else "trekpleister.nl"
    url = f"https://www.{domain}/api/v2/{store_type}/products/search?fields=FULL&query=:relevance&pageSize=100"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            cleaned_items = []
            for p in products:
                # We zetten alles om naar een lijstje (een rij voor Excel)
                # Volgorde: id, product-title, product-link, actie, actie-deal, prijs, winkel
                item = [
                    p.get('code', ''),
                    p.get('name', ''),
                    f"https://www.{domain}{p.get('url', '')}",
                    p.get('promoText', ''), 
                    '', # actie-deal houden we nu even leeg
                    p.get('price', {}).get('value', ''),
                    store_name
                ]
                cleaned_items.append(item)
            return cleaned_items
    except Exception as e:
        print(f"❌ Fout bij ophalen van {store_name}: {e}")
    return []

def get_etos_data():
    """Haalt data op van de Etos product-API."""
    url = "https://etos.nl"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', []) or data.get('results', [])
            cleaned_items = []
            for p in products:
                raw_price = p.get('price', {}).get('value') if isinstance(p.get('price'), dict) else p.get('price')
                item = [
                    p.get('id') or p.get('code', ''),
                    p.get('name') or p.get('title', ''),
                    f"https://etos.nl{p.get('url', '')}" if p.get('url') and not p.get('url').startswith('http') else p.get('url', ''),
                    p.get('activePromotion', {}).get('description') if isinstance(p.get('activePromotion'), dict) else p.get('promotionText', ''),
                    '',
                    raw_price,
                    "Etos"
                ]
                cleaned_items.append(item)
            return cleaned_items
    except Exception as e:
        print(f"❌ Fout bij ophalen van Etos: {e}")
    return []

def update_google_sheet(data_to_write):
    """Verbindt met Google Sheets en overschrijft de data."""
    print("🔑 Inloggen bij Google Sheets...")
    
    # GitHub Actions zet jouw geheime sleutel in de omgevingsvariabele 'GOOGLE_CREDENTIALS'
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    
    if not creds_json:
        print("❌ Fout: Geen GOOGLE_CREDENTIALS gevonden in de instellingen!")
        return

    # De inlogprocedure voor Google
    creds_dict = json.loads(creds_json)
    scopes = ["https://google.com", "https://googleapis.com"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
    client = gspread.authorize(creds)
    
    try:
        # Open de sheet en pak het juiste tabblad
        sheet = client.open(GOOGLE_SHEET_NAME)
        worksheet = sheet.worksheet(TABBLAD_NAAM)
        
        # We maken het tabblad eerst helemaal leeg
        worksheet.clear()
        
        # We voegen de kolomkoppen toe als eerste rij (Rij 1)
        headers = ["id", "product-title", "product-link", "actie", "actie-deal", "prijs", "winkel"]
        worksheet.append_row(headers)
        
        # Schrijf alle opgehaalde rijen in één klap onder de kolomkoppen
        worksheet.append_rows(data_to_write)
        print("🎉 Succes! De Google Sheet is succesvol bijgewerkt met de nieuwste prijzen.")
        
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven naar Google Sheets: {e}")

# --- HOOFDPROGRAMMA ---
if __name__ == "__main__":
    print("🚀 De dagelijkse robot start nu met het verzamelen van data...")
    
    kruidvat = get_as_watson_data("kvn")
    trekpleister = get_as_watson_data("tpa")
    etos = get_etos_data()
    
    alle_producten = kruidvat + trekpleister + etos
    print(f"📊 Totaal gevonden: {len(alle_producten)} rijen.")
    
    if len(alle_producten) > 0:
        update_google_sheet(alle_producten)
    else:
        print("❌ Geen data gevonden om te schrijven.")
