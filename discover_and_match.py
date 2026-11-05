import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATIE ---
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_BRON = "Producten Database"

# Officiële product-sitemaps (gecontroleerd en live)
KRUIDVAT_SITEMAP = "https://www.kruidvat.nl/sitemap.xml" # Of specifieke sub-sitemaps indien aanwezig
ETOS_SITEMAP = "https://www.etos.nl/sitemap_0-product.xml"

PROXY_API_KEY = os.environ.get("PROXY_API_KEY")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS")

def haal_urls_uit_sitemap(sitemap_url):
    """Leest gratis de sitemap-XML uit en verzamelt alle product-URL's."""
    print(f"🌐 Sitemap scannen: {sitemap_url}")
    urls = []
    try:
        # Sitemaps blokkeren bot-verzoeken zelden hard, dus we proberen het eerst zonder zware proxy-credits
        response = requests.get(sitemap_url, timeout=30)
        if response.status_code != 200 and PROXY_API_KEY:
            # Fallback via ZenRows als de sitemap toch achter Cloudflare zit
            response = requests.get('https://zenrows.com', params={'apikey': PROXY_API_KEY, 'url': sitemap_url}, timeout=45)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # XML-bestanden gebruiken namespaces (ns), daar moeten we rekening mee houden
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for url_tag in root.findall('ns:url', namespaces):
                loc = url_tag.find('ns:loc', namespaces)
                if loc is not None:
                    urls.append(loc.text)
    except Exception as e:
        print(f"⚠️ Kon sitemap niet volledig uitlezen: {e}")
    return urls

def haal_ean_en_naam(url, winkel_naam):
    """Bezoekt een productpagina en zoekt naar de 13-cijferige barcode (EAN)."""
    if not PROXY_API_KEY:
        return None, None
        
    payload = {
        "apikey": PROXY_API_KEY.strip(),
        "url": url,
        "js_render": "true",
        "antibot": "true"
    }
    
    try:
        response = requests.get("https://zenrows.com", params=payload, timeout=45)
        if response.status_code != 200:
            return None, None
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Productnaam achterhalen
        title_tag = soup.find('h1') or soup.find('meta', property='og:title')
        title = title_tag.get_text().strip() if title_tag else "Onbekend Product"
        if title_tag and title_tag.name == 'meta':
            title = title_tag.get('content', 'Onbekend Product').strip()

        # 2. EAN Barcode achterhalen (Kruidvat & Etos stoppen dit vaak in JSON-LD of data-attributes)
        ean = None
        
        # Methode A: Zoeken in de schema.org metadata blocks
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    for key in ['gtin13', 'gtin', 'sku']:
                        val = item.get(key)
                        if val and isinstance(val, str) and re.match(r'^\d{13}$', val):
                            return val, title
            except:
                continue
                
        # Methode B: RegEx fallback op de complete broncode
        ean_match = re.search(r'"ean"\s*:\s*"(\d{13})"', html) or re.search(r'"gtin"\s*:\s*"(\d{13})"', html)
        if ean_match:
            ean = ean_match.group(1)
            
        return ean, title
    except:
        return None, None

def main():
    print("🚀 Automatische Matchmaker gestart...")
    
    kv_urls = haal_urls_uit_sitemap(KRUIDVAT_SITEMAP)
    et_urls = haal_urls_uit_sitemap(ETOS_SITEMAP)
    
    print(f"Found {len(kv_urls)} Kruidvat links en {len(et_urls)} Etos links.")

    # Dictionary om producten tijdelijk in te bewaren: { EAN: [Naam, Kruidvat_URL, Etos_URL] }
    gematchte_database = {}

    # TEST-LIMIET: We testen er eerst 10 per winkel om je gratis credits te sparen!
    test_limiet = 10

    # Kruidvat verwerken
    for url in kv_urls[:test_limiet]:
        print(f"Scannen van Kruidvat link...")
        ean, naam = haal_ean_en_naam(url, "Kruidvat")
        if ean:
            gematchte_database[ean] = [naam, url, ""] # Nog geen Etos link

    # Etos verwerken en direct matchen
    for url in et_urls[:test_limiet]:
        print(f"Scannen van Etos link...")
        ean, naam = haal_ean_en_naam(url, "Etos")
        if ean:
            if ean in gematchte_database:
                print(f"🔗 MATCH! {naam} gevonden bij beide winkels!")
                gematchte_database[ean][2] = url # Etos link toevoegen aan bestaande rij
            else:
                gematchte_database[ean] = [naam, "", url] # Alleen bij Etos bekend

    # Schrijven naar Google Sheets
    if not GOOGLE_CREDENTIALS_JSON:
        print("❌ Geen Google Credentials gevonden. Resultaat geprint naar terminal:")
        print(gematchte_database)
        return

    # Inloggen bij Google Sheets
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON.strip())
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://googleapis.com"])
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet = sheet.worksheet(TABBLAD_BRON)

    # Zet om naar rijen voor de sheet
    nieuwe_rijen = []
    for ean, data in gematchte_database.items():
        # Kolomindeling: Product ID (EAN), Product Naam, Link Kruidvat, Link Etos
        nieuwe_rijen.append([ean, data[0], data[1], data[2]])

    if neue_rijen:
        worksheet.append_rows(nieuwe_rijen)
        print(f"🎉 Succes! Er zijn {len(nieuwe_rijen)} producten automatisch toegevoegd aan de database!")

if __name__ == "__main__":
    main()
