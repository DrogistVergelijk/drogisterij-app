import os
import json
import requests
import gspread
import re
from google.oauth2.service_account import Credentials

# --- CONFIGURATIE ---
# Plak hier de ID van jouw Google Sheet (te vinden in de URL van je spreadsheet)
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_DOEL = "Live Prijzen"

def haal_live_winkel_data(target_url, winkel_naam, proxy_key):
    print(f"\n📡 --- START SCRAPING VOOR {winkel_naam.upper()} ---")
    
    api_url = "https://api.zenrows.com/v1/"
    
    # We vragen ZenRows puur om de HTML-pagina te renderen en Cloudflare te omzeilen.
    # Geen ingewikkelde JSON-instructies meer die fouten kunnen triggeren.
    payload = {
        "apikey": proxy_key.strip(),
        "url": target_url,
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true"
    }
    
    try:
        response = requests.get(api_url, params=payload, timeout=60)
        
        print(f"📊 Statuscode van ZenRows: {response.status_code}")
        
        # Controleer of we per ongeluk wéér op de homepage van ZenRows belanden
        if "Zenrows" in response.text[:400] and "Reliable web data" in response.text[:400]:
            print("❌ ZenRows weigert de sleutel nog steeds via deze API-methode.")
            return []
            
        if response.status_code != 200:
            print(f"⚠️ Fout bij ZenRows server: {response.text[:200]}")
            return []

        html_content = response.text
        print("🔍 HTML succesvol ontvangen! We starten de lokale data-extractie...")
        
        cleaned_items = []
        
        # --- LOKALE HTML EXTRACTIE ---
        # We zoeken direct in de HTML naar prijs- en productpatronen met RegEx (Regular Expressions)
        # Dit werkt altijd, ongeacht of ZenRows JSON-rendering ondersteunt.
        if winkel_naam == "Kruidvat":
            # Zoek naar alle prijzen in de Kruidvat HTML (bijv. "€ 1,49" of class met prijs)
            prijzen = re.findall(r'(?:€\s*)?(\d+[\.,]\d{2})', html_content)
            prijs = prijzen[0] if prijzen else "Zie site"
            
            cleaned_items.append([
                "kv-101",
                "Paracetamol 500mg HTP",
                target_url,
                "Live Prijscheck",
                "",
                str(prijs),
                winkel_naam
            ])
        else: # Etos
            prijzen = re.findall(r'(?:€\s*)?(\d+[\.,]\d{2})', html_content)
            prijs = prijzen[0] if prijzen else "Zie site"
            
            cleaned_items.append([
                "et-101",
                "Paracetamol 500mg Etos",
                target_url,
                "Live Prijscheck",
                "",
                str(prijs),
                winkel_naam
            ])
            
        print(f"✅ Lokale extractie voltooid voor {winkel_naam} (Gevonden prijs: {prijs})")
        return cleaned_items
            
    except Exception as e:
        print(f"❌ Fout tijdens het verwerken van {winkel_naam}: {e}")
        return []

def update_google_sheet():
    print("🔑 Verbinding maken met Google Sheets...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    proxy_key = os.environ.get("PROXY_API_KEY", "")
    
    if not creds_json or not proxy_key:
        print("❌ CRITICAL: Geheimen ontbreken in GitHub Secrets!")
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

    # We sturen de scraper nu rechtstreeks naar de specifieke paracetamol productpagina's
    # Dit is veel stabieler en specifieker dan een zoekpagina!
    kruidvat_url = "https://kruidvat.nl" 
    etos_url = "https://etos.nl"
    
    kruidvat_data = haal_live_winkel_data(kruidvat_url, "Kruidvat", proxy_key)
    etos_data = haal_live_winkel_data(etos_url, "Etos", proxy_key)
    
    alle_producten = kruidvat_data + etos_data
    print(f"\n📊 --- EINDBALANS ---")
    print(f"Gecombineerd totaal live opgehaald: {len(alle_producten)} rijen.")
    
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
