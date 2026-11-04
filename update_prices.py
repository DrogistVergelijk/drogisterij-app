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
    print(f"📡 Live data ophalen van {winkel_naam} via proxy-omleiding...")
    
    api_url = "https://zenrows.com"
    payload = {
        "apikey": proxy_key,
        "url": target_url,
        "js_render": "true", # Renders JavaScript zoals een echte browser
        "antibot": "true", # Omzeilt expliciet Cloudflare / DataDome blokkades
        "premium_proxy": "true" # Gebruikt hoogwaardige residentiële IP-adressen
    }
    
    try:
        response = requests.get(api_url, params=payload, timeout=60)
        
        if response.status_code == 200:
            # DEBUG: Print een klein deel van de response om te zien wat we terugkrijgen
            inhoud = response.text[:200]
            print(f" debug [{winkel_naam}]: Eerste 200 tekens ontvangen: {inhoud}")
            
            try:
                data = response.json()
            except Exception:
                print(f"⚠️ {winkel_naam} gaf HTML/Tekst terug in plaats van JSON. Beveiliging blokkeert nog.")
                return []
                
            # Zoek naar producten in de JSON-respons
            products = data.get('products', []) or data.get('results', []) or data.get('data', {}).get('products', [])
            cleaned_items = []
            
            for p in products:
                raw_price = p.get('price', {}).get('value') if isinstance(p.get('price'), dict) else p.get('price', 'Zie site')
                
                domain = "kruidvat.nl" if winkel_naam == "Kruidvat" else "etos.nl"
                p_link = p.get('url', '')
                if p_link and not p_link.startswith('http'):
                    p_link = f"https://www.{domain}{p_link}"
                    
                item = [
                    str(p.get('code') or p.get('id', '')),
                    p.get('name') or p.get('title', 'Onbekend product'),
                    p_link,
                    p.get('promoText') or (p.get('activePromotion', {}).get('description') if isinstance(p.get('activePromotion'), dict) else ''),
                    '',  
                    str(raw_price),
                    winkel_naam
                ]
                cleaned_items.append(item)
                
            print(f"✅ {len(cleaned_items)} live producten gevonden voor {winkel_naam}!")
            return cleaned_items
        else:
            print(f"⚠️ Proxy gaf statuscode {response.status_code} voor {winkel_naam}. Mogelijk verkeerde URL of geblokkeerd.")
            return []
    except Exception as e:
        print(f"❌ Fout tijdens het live scrapen van {winkel_naam}: {e}")
        return []

def update_google_sheet():
    print("🔑 Verbinding maken met Google Sheets...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    proxy_key = os.environ.get("PROXY_API_KEY")
    
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

    # Aangepaste URLs: We zoeken nu specifiek naar 'paracetamol' via de interne zoek-endpoints die winkels gebruiken
    # Let op: deze endpoints veranderen regelmatig. 
    kruidvat_url = "https://kruidvat.nl" 
    etos_url = "https://etos.nl"
    
    kruidvat_data = haal_live_winkel_data(kruidvat_url, "Kruidvat", proxy_key)
    etos_data = haal_live_winkel_data(etos_url, "Etos", proxy_key)
    
    alle_producten = kruidvat_data + etos_data
    print(f"📊 Gecombineerd totaal live opgehaald: {len(alle_producten)} rijen.")
    
    if len(alle_producten) == 0:
        print("❌ Geen live data kunnen ophalen. Script afgebroken.")
        print("💡 Tip: Als dit blijft mislukken, moeten we overstappen van JSON-API's naar het scrapen van de normale HTML-zoekpagina's.")
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
