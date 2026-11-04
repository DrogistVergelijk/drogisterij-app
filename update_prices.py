import os
import json
import requests
import gspread
import re
import traceback
from google.oauth2.service_account import Credentials

# --- CONFIGURATIE ---
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
        
        prijzen = re.findall(r'(\d+[\.,]\d{2})', html_content)
        
        # Filter om uitschieters te voorkomen
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
        
    # We schrijven de JSON-data tijdelijk naar een fysiek bestand om OIDC-tokenfouten te omzeilen
    temp_creds_path = "creds_temp.json"
    try:
        with open(temp_creds_path, "w") as f:
            f.write(creds_json.strip())
    except Exception as e:
        print(f"❌ Fout bij het aanmaken van het tijdelijke certificaatbestand: {e}")
        return

    # De officiële Google Drive & Sheets scopes die gspread vereist
    scopes = [
        "https://googleapis.com",
        "https://googleapis.com"
    ]
    
    try:
        # Inloggen via het fysieke bestand (dit is de meest robuuste methode)
        creds = Credentials.from_service_account_file(temp_creds_path, scopes=scopes)
        client = gspread.authorize(creds)
        print("🔓 Google API succesvol geauthenticeerd via bestand!")
    except Exception as e:
        print(f"❌ Fout bij de initiële authenticatie: {e}")
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)
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
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)
        return
        
    try:
        print("📁 Stap 1: Google Sheet openen...")
        sheet = client.open_by_key(SPREADSHEET_ID)
        
        print("📄 Stap 2: Juiste tabblad selecteren...")
        worksheet = sheet.worksheet(TABBLAD_DOEL)
        
        print("🧹 Stap 3: Oude data wissen...")
        worksheet.clear()
        
        headers = ["id", "product-title", "product-link", "actie", "actie-deal", "prijs", "winkel"]
        print("📝 Stap 4: Nieuwe headers en data wegschrijven...")
        worksheet.append_row(headers)
        worksheet.append_rows(alle_producten)
        
        print("🎉 GOUD! De live prijzen staan nu écht in je Sheet!")
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven naar de sheet!")
        print(f"🔍 EXACTE FOUTDETAILS:\n{traceback.format_exc()}")
    finally:
        # Altijd het tijdelijke bestand netjes opruimen aan het einde
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)

if __name__ == "__main__":
    update_google_sheet()
