import os
import json
import requests
import xml.etree.ElementTree as ET
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATIE ---
GOOGLE_SHEET_NAME = "https://docs.google.com/spreadsheets/d/1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA/edit?gid=0#gid=0"
TABBLAD_NAAM = "Live Prijzen"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_data_via_sitemap(store_name, url):
    """Haalt product-links en basisinformatie op via de openbare Google-sitemaps."""
    print(f"📡 Producten ophalen uit de sitemap van {store_name}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code == 200:
            # We ontleden de XML sitemap die voor Google bedoeld is
            root = ET.fromstring(response.content)
            
            # XML sitemaps gebruiken vaak een namespace, die vangen we hier op
            namespace = {'ns': 'http://sitemaps.org'}
            
            cleaned_items = []
            count = 0
            
            # Loop door alle links in de sitemap (we pakken er max 150 als test)
            for url_tag in root.findall('ns:url', namespace):
                loc_tag = url_tag.find('ns:loc', namespace)
                if loc_tag is not None:
                    link = loc_tag.text
                    
                    # We filteren alleen echte productpagina's eruit
                    if "/p/" in link or "/product/" in link:
                        # We proberen de productnaam logisch uit de link te vissen
                        slug = link.split('/')[-1]
                        title = slug.replace('-', ' ').title()
                        
                        # We bootsen een strakke database-rij na
                        item = [
                            f"ID_{count}", # Tijdelijk ID op basis van sitemap volgorde
                            title,
                            link,
                            "Zie website", # Actietekst (halen we live uit de link)
                            "", 
                            "Zie website", # Prijs
                            store_name
                        ]
                        cleaned_items.append(item)
                        count += 1
                        
                        if count >= 150: # Limiet om je sheet niet te overbelasten tijdens de test
                            break
            return cleaned_items
        else:
            print(f"⚠️ Sitemap gaf statuscode {response.status_code} terug.")
    except Exception as e:
        print(f"❌ Fout bij sitemap-verwerking van {store_name}: {e}")
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
        print("🎉 Succes! De robot heeft de sitemap-opdracht uitgevoerd en de Google Sheet is gevuld!")
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven naar Google Sheets: {e}")

if __name__ == "__main__":
    print("🚀 De onblokkeerbare Sitemap-robot start nu...")
    
    # We gebruiken de officiële sitemaps die openbaar toegankelijk zijn
    kruidvat_data = get_data_via_sitemap("Kruidvat", "https://kruidvat.nl")
    trekpleister_data = get_data_via_sitemap("Trekpleister", "https://trekpleister.nl")
    
    alle_producten = kruidvat_data + trekpleister_data
    print(f"📊 Totaal gevonden in sitemaps: {len(alle_producten)} producten.")
    
    if len(alle_producten) > 0:
        update_google_sheet(alle_producten)
    else:
        print("❌ Geen data gevonden om te schrijven")
