import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATIE ---
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_DOEL = "Live Prijzen"

def haal_live_winkel_data(url, winkel_naam, proxy_key):
    """Haalt live data op via een roterende proxy om Cloudflare te omzeilen."""
    print(f"📡 Live data ophalen van {winkel_naam} via proxy-omleiding...")
    
    # We sturen de aanvraag door via de gratis proxy-dienst om de 403 blokkade te omzeilen
    proxy_url = f"https://zenrows.com{proxy_key}&url={requests.utils.quote(url)}"
    
    try:
        response = requests.get(proxy_url, timeout=25)
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', []) or data.get('results', [])
            
            cleaned_items = []
            for p in products:
                # Prijs-extractie finetunen
                raw_price = p.get('price', {}).get('value') if isinstance(p.get('price'), dict) else p.get('price', 'Zie site')
                
                # Bepaal de link op basis van de winkel
                domain = "kruidvat.nl" if winkel_naam == "Kruidvat" else "etos.nl"
                p_link = p.get('url', '')
                if p_link and not p_link.startswith('http'):
                    p_link = f"https://www.{domain}{p_link}"

                item = [
                    str(p.get('code') or p.get('id', '')),
                    p.get('name') or p.get('title', 'Onbekend product'),
                    p_link,
                    p.get('promoText') or (p.get('activePromotion', {}).get('description') if isinstance(p.get('activePromotion'), dict) else ''),
                    '', # actie-deal
                    str(raw_price),
                    winkel_naam
                ]
                cleaned_items.append(item)
            
            print(f"✅ {len(cleaned_items)} live producten gevonden voor {winkel_naam}!")
            return cleaned_items
        else:
            print(f"⚠️ Proxy gaf statuscode {response.status_code} voor {winkel_naam}. Mogelijk token-limiet bereikt.")
    except Exception as e:
        print(f"❌ Fout tijdens het live scrapen van {winkel_naam}: {e}")
    return []

def update_google_sheet():
    print("🔑 Verbinding maken met Google Sheets...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    proxy_key = os.environ.get("PROXY_API_KEY")
    
    if not creds_json or not proxy_key:
        print("❌ Fout: GOOGLE_CREDENTIALS of PROXY_API_KEY ontbreekt in GitHub Secrets!")
        return

    scopes = ["https://googleapis.com", "https://googleapis.com"]
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
    client = gspread.authorize(creds)
    
    # De echte live interne endpoints van Kruidvat en Etos
    kruidvat_url = "https://kruidvat.nl"
    etos_url = "https://etos.nl"

    # Haal de data écht live op!
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
        worksheet.clear()
        
        headers = ["id", "product-title", "product-link", "actie", "actie-deal", "prijs", "winkel"]
        worksheet.append_row(headers)
        worksheet.append_rows(alle_producten)
        print("🎉 GOUD! De robot heeft de BEVEILIGING omzeild en de live prijzen staan in je Sheet!")
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven naar de sheet: {e}")

if __name__ == "__main__":
    update_google_sheet()
