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
    
    api_url = "https://zenrows.com"
    payload = {
        "apikey": proxy_key.strip(),
        "url": target_url,
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true"
    }
    
    try:
        response = requests.get(api_url, params=payload, timeout=60)
        
        if response.status_code != 200:
            print(f"⚠️ Fout bij ZenRows server: {response.text[:200]}")
            return []

        html_content = response.text
        print("🔍 HTML succesvol ontvangen! We starten de lokale data-extractie...")
        
        # We zoeken naar geldige Nederlandse prijsformaten (bijv. 1,49 of 2.25)
        prijzen = re.findall(r'(\d+[\.,]\d{2})', html_content)
        
        # Fallback filter om extreme uitschieters of dummy-data te voorkomen
        geldige_prijzen = [p for p in prijzen if not p.startswith("00") and not p.startswith("100")]
        
        if geldige_prijzen:
            schone_prijs = f"€ {geldige_prijzen[0].replace('.', ',')}"
        else:
            schone_prijs = "Zie site"
            
        cleaned_items = []
        if winkel_naam == "Kruidvat":
            cleaned_items.append([
                "kv-16281",
                "Kruidvat Paracetamol 500mg (50st)",
                target_url,
                "Live Prijs",
                "",
                schone_prijs,
                winkel_naam
            ])
        else: # Etos
            cleaned_items.append([
                "et-12046",
                "Etos Paracetamol 500mg (50st)",
                target_url,
                "Live Prijs",
                "",
                schone_prijs,
                winkel_naam
            ])
            
        print(f"✅ Lokale extractie voltooid voor {winkel_naam} (Gevonden prijs: {schone_prijs})")
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
        
    # Teruggebracht naar de enige échte scope die gspread vereist om authenticatiefouten te voorkomen
    scopes = ["https://googleapis.com"]
    
    try:
        # Zorg dat eventuele vreemde regeleinden uit de GitHub Actions string worden gladgestreken
        info = json.loads(creds_json, strict=False)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        print("🔓 Google API succesvol geauthenticeerd!")
    except Exception as e:
        print(f"❌ Fout bij het laden van Google Credentials: {e}")
        return

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
        
        print("🎉 GOUD! De live prijzen staan nu écht in je Sheet!")
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven naar de sheet: {e}")

if __name__ == "__main__":
    update_google_sheet()
