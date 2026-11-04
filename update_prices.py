import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATIE ---
# Plak hier de ID van jouw Google Sheet (te vinden in de URL van je spreadsheet)
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_DOEL = "Live Prijzen"

def haal_live_winkel_data(target_url, winkel_naam, proxy_key):
    print(f"📡 Live data ophalen van {winkel_naam} via ZenRows...")
    
    # De basis-URL is nu volledig hardcoded zonder variabelen, om 'zenrows.com***' errors te voorkomen
    api_url = "https://zenrows.com"
    
    # We instrueren ZenRows om de HTML direct te scrapen en als JSON terug te geven via CSS selectors
    if winkel_naam == "Kruidvat":
        selectors = {
            "products": {
                "list": ".product-tile", 
                "details": {
                    "name": ".product-tile__title",
                    "price": ".text-price",
                    "url": ".product-tile__link @href",
                    "id": ".product-tile @data-product-code"
                }
            }
        }
    else: # Etos
        selectors = {
            "products": {
                "list": ".product-tile", 
                "details": {
                    "name": ".product-title",
                    "price": ".price-format",
                    "url": ".product-link @href",
                    "id": ".product-tile @data-id"
                }
            }
        }

    # Alle parameters worden nu via een POST-request als schone JSON meegestuurd
    # Dit voorkomt dat GitHub Actions de URL-string corrupt maakt met sterretjes
    payload = {
        "url": target_url,
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true",
        "json_response": "true",
        "js_instructions": json.dumps(selectors)
    }
    
    # De apikey sturen we als queryparameter mee, requests handelt de encoding veilig af
    params = {"apikey": proxy_key}
    
    try:
        response = requests.post(api_url, params=params, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            extracted_products = data.get("products", [])
            
            if not extracted_products:
                print(f"⚠️ ZenRows kon de pagina laden, maar vond geen producten via de selectors voor {winkel_naam}.")
                return []
                
            cleaned_items = []
            domain = "kruidvat.nl" if winkel_naam == "Kruidvat" else "etos.nl"
            
            for p in extracted_products:
                p_link = p.get('url', '')
                if p_link and not p_link.startswith('http'):
                    p_link = f"https://www.{domain}{p_link}"
                    
                item = [
                    str(p.get('id') or ''),
                    p.get('name') or 'Onbekend product',
                    p_link,
                    '', 
                    '', 
                    str(p.get('price') or 'Zie site').strip(),
                    winkel_naam
                ]
                cleaned_items.append(item)
                
            print(f"✅ {len(cleaned_items)} live producten gevonden voor {winkel_naam}!")
            return cleaned_items
        else:
            print(f"⚠️ ZenRows gaf een foutmelding (Status {response.status_code}) voor {winkel_naam}.")
            return []
            
    except Exception as e:
        print(f"❌ Critical error tijdens het scrapen van {winkel_naam}: {e}")
        return []

def update_google_sheet():
    print("🔑 Verbinding maken met Google Sheets...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    
    # Haal de proxy key op en strip eventuele verborgen spaties/newlines of aanhalingstekens er direct af
    raw_proxy_key = os.environ.get("PROXY_API_KEY", "")
    proxy_key = raw_proxy_key.strip().replace("'", "").replace('"', '')
    
    if not creds_json or not proxy_key:
        print("❌ Fout: Geheimen ontbreken in GitHub Secrets!")
        return
        
    scopes = [
        "https://googleapis.com",
        "https://googleapis.com"
    ]
    
    try:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
        client = gspread.authorize(creds)
    except Exception as e:
        print(f"❌ Fout bij het laden van Google Credentials: {e}")
        return

    # We roepen de stabiele publieke zoekpagina's aan
    kruidvat_url = "https://kruidvat.nl" 
    etos_url = "https://etos.nl"
    
    kruidvat_data = haal_live_winkel_data(kruidvat_url, "Kruidvat", proxy_key)
    etos_data = haal_live_winkel_data(etos_url, "Etos", proxy_key)
    
    alle_producten = kruidvat_data + etos_data
    print(f"📊 Gecombineerd totaal live opgehaald: {len(alle_producten)} rijen.")
    
    if len(alle_producten) == 0:
        print("❌ Geen live data kunnen ophalen. Script afgebroken.")
        return
        
    try:
        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(TABBLAD_DOEL)
        
        print("🧹 Oude data wissen...")
        worksheet.clear()
        
        headers = ["id", "product-title", "product-link", "actie", "actie-deal", "prijs", "winkel"]
        print("📝 Nieuwe data wegschrijven...")
        worksheet.append_row(headers)
        worksheet.append_rows(alle_producten)
        
        print("🎉 GOUD! De live prijzen staan in je Sheet!")
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven naar de sheet: {e}")

if __name__ == "__main__":
    update_google_sheet()
