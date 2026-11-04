import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATIE ---
GOOGLE_SHEET_NAME = "https://docs.google.com/spreadsheets/d/1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA/edit?gid=0#gid=0"
TABBLAD_NAAM = "Live Prijzen"

# Vernieuwde browser-simulatie headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://kruidvat.nl",
    "Referer": "https://kruidvat.nl/"
}

def get_as_watson_data(store_type):
    """Haalt live actie-producten op via de hoofd-categorieën om blokkades te omzeilen."""
    store_name = "Kruidvat" if store_type == "kvn" else "Trekpleister"
    domain = "kruidvat.nl" if store_type == "kvn" else "trekpleister.nl"
    
    # We zoeken specifiek op de actiepagina-endpoint van hun interne zoekmachine
    url = f"https://www.{domain}/api/v2/{store_type}/products/search?fields=FULL&query=:relevance:allCategories:acties&pageSize=100"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            cleaned_items = []
            for p in products:
                item = [
                    p.get('code', ''),
                    p.get('name', ''),
                    f"https://www.{domain}{p.get('url', '')}",
                    p.get('promoText', ''), 
                    '', 
                    p.get('price', {}).get('value', ''),
                    store_name
                ]
                cleaned_items.append(item)
            return cleaned_items
        else:
            print(f"⚠️ {store_name} gaf statuscode {response.status_code} terug.")
    except Exception as e:
        print(f"❌ Fout bij ophalen van {store_name}: {e}")
    return []

def get_etos_data():
    """Haalt data op van de Etos actie-API via hun openbare zoek-endpoint."""
    # Etos gebruikt een POST-aanvraag voor hun zoekbalk, dat bootsen we hier na
    url = "https://etos.nl"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
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
    """Verbindt met Google Sheets op basis van de naam en overschrijft de data."""
    print("🔑 Inloggen bij Google Sheets via de robot-sleutel...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("❌ Fout: Geen GOOGLE_CREDENTIALS gevonden in de GitHub Secrets!")
        return

    creds_dict = json.loads(creds_json)
    scopes = ["https://google.com", "https://googleapis.com"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open(GOOGLE_SHEET_NAME)
        worksheet = sheet.worksheet(TABBLAD_NAAM)
        worksheet.clear()
        
        headers = ["id", "product-title", "product-link", "actie", "actie-deal", "prijs", "winkel"]
        worksheet.append_row(headers)
        worksheet.append_rows(data_to_write)
        print("🎉 Succes! De robot heeft de opdracht uitgevoerd en de Google Sheet is bijgewerkt!")
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven naar Google Sheets: {e}")

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
        print("❌ Geen data gevonden om te schrijven")
