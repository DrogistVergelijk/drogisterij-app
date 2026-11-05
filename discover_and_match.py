import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import gspread

# --- CONFIGURATIE ---
# Vul hier je eigen spreadsheet ID in
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_BRON = "Producten Database"

# Gecorrigeerde sitemap URL's die we direct via ZenRows gaan opvragen
KRUIDVAT_SITEMAP = "https://www.kruidvat.nl/sitemap.xml"
# We gebruiken de product sitemap van Etos die je in de bestanden hebt meegeleverd
ETOS_SITEMAP = "https://www.etos.nl/sitemap_0-product.xml"

PROXY_API_KEY = os.environ.get("PROXY_API_KEY", "")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")

def haal_urls_uit_sitemap(sitemap_url, proxy_key):
    """Haalt de sitemap op via de ZenRows API en vist alle product-links eruit."""
    print(f"🌐 Sitemap scannen via ZenRows: {sitemap_url}")
    urls = []
    
    if not proxy_key:
        print("❌ Fout: PROXY_API_KEY is leeg. Kan sitemap niet veilig ophalen.")
        return urls

    # Voor sitemaps hebben we GEEN js_render nodig, dat scheelt je enorm veel gratis credits!
    payload = {
        "apikey": proxy_key.strip(),
        "url": sitemap_url,
        "antibot": "true",
        "premium_proxy": "true"
    }
    
    try:
        response = requests.get("https://zenrows.com", params=payload, timeout=60)
        if response.status_code != 200:
            print(f"⚠️ ZenRows sitemap fout: Statuscode {response.status_code}")
            return urls
            
        # Parse de XML inhoud
        xml_content = response.content
        root = ET.fromstring(xml_content)
        
        # Sitemaps gebruiken bijna altijd deze standaard XML namespace
        namespaces = {'ns': 'http://sitemaps.org'}
        for url_tag in root.findall('ns:url', namespaces):
            loc = url_tag.find('ns:loc', namespaces)
            if loc is not None:
                urls.append(loc.text)
                
    except ET.ParseError as xml_error:
        print(f"❌ XML Verwerkingsfout (Waarschijnlijk gaf de site HTML-blokkade terug): {xml_error}")
    except Exception as e:
        print(f"⚠️ Algemene fout bij uitlezen sitemap: {e}")
        
    return urls

def haal_ean_en_naam(url, winkel_naam, proxy_key):
    """Bezoekt een productpagina en zoekt naar de 13-cijferige barcode (EAN)."""
    if not url or not proxy_key:
        return None, None
        
    # Voor productpagina's hebben we WEL JavaScript rendering nodig om de Cloudflare-beveiliging te kraken
    payload = {
        "apikey": proxy_key.strip(),
        "url": url,
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true"
    }
    
    try:
        response = requests.get("https://zenrows.com", params=payload, timeout=45)
        if response.status_code != 200:
            return None, None
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Productnaam zoeken
        title_tag = soup.find('h1') or soup.find('meta', property='og:title')
        title = "Onbekend Product"
        if title_tag:
            title = title_tag.get('content', title_tag.get_text()).strip()

        # EAN zoeken in JSON-LD scripts
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
                
        # Regex Fallback op complete broncode
        ean_match = re.search(r'"ean"\s*:\s*"(\d{13})"', html) or re.search(r'"gtin"\s*:\s*"(\d{13})"', html)
        if ean_match:
            return ean_match.group(1), title
            
        return None, title
    except:
        return None, None

def main():
    print("🚀 Gecorrigeerde Automatische Matchmaker gestart...")
    
    # 1. Sitemap checken
    kv_urls = haal_urls_uit_sitemap(KRUIDVAT_SITEMAP, PROXY_API_KEY)
    et_urls = haal_urls_uit_sitemap(ETOS_SITEMAP, PROXY_API_KEY)
    
    print(f"📊 Resultaat: {len(kv_urls)} Kruidvat links en {len(et_urls)} Etos links gevonden.")

    if not kv_urls and not et_urls:
        print("❌ Stopzetting: Er konden geen sitemaps worden uitgelezen. Controleer je PROXY_API_KEY.")
        return

    gematchte_database = {}
    test_limiet = 5 # Heel laag houden om eerst je verbinding en sheet te testen!

    # Kruidvat links testen
    for url in kv_urls[:test_limiet]:
        print(f"🔍 Scannen Kruidvat product...")
        ean, naam = haal_ean_en_naam(url, "Kruidvat", PROXY_API_KEY)
        if ean:
            gematchte_database[ean] = [naam, url, ""]

    # Etos links testen en matchen
    for url in et_urls[:test_limiet]:
        print(f"🔍 Scannen Etos product...")
        ean, naam = haal_ean_en_naam(url, "Etos", PROXY_API_KEY)
        if ean:
            if ean in gematchte_database:
                print(f"🔗 MATCH GEPAST! '{naam}' hoort bij elkaar via EAN barcode: {ean}")
                gematchte_database[ean][2] = url
            else:
                gematchte_database[ean] = [naam, "", url]

    # 2. Google Sheets Verbinding (Met Beveiligings-Fix)
    if not GOOGLE_CREDENTIALS_JSON:
        print("❌ Fout: GOOGLE_CREDENTIALS secret ontbreekt op GitHub!")
        return

    temp_creds_path = "temp_credentials.json"
    try:
        # Schrijf de JSON-string naar een echt, tijdelijk bestand (dit lost de RefreshError op)
        creds_clean = json.loads(GOOGLE_CREDENTIALS_JSON.strip())
        if creds_clean.get("type") != "service_account":
            creds_clean["type"] = "service_account"
            
        with open(temp_creds_path, "w") as f:
            json.dump(creds_clean, f)
            
        # Inloggen via het bestand
        gc = gspread.service_account(filename=temp_creds_path)
        sheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(TABBLAD_BRON)
        print("🔑 Google Sheets succesvol gekoppeld!")
        
    except Exception as google_error:
        print(f"❌ Fatale Google Sheets inlogfout: {google_error}")
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)
        return

    # Omzetten naar rijen voor je Sheet
    nieuwe_rijen = []
    for ean, data in gematchte_database.items():
        nieuwe_rijen.append([ean, data[0], data[1], data[2]])

    try:
        if nieuwe_rijen:
            worksheet.append_rows(nieuwe_rijen)
            print(f"🎉 GOUD! Er zijn {len(nieuwe_rijen)} producten toegevoegd aan je database!")
        else:
            print("⚠️ Geen nieuwe barcodes kunnen ontdekken tijdens deze testrun.")
    except Exception as e:
        print(f"❌ Fout bij schrijven naar Google Sheets: {e}")
    finally:
        # Altijd het tijdelijke bestand netjes opruimen voor de veiligheid
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)

if __name__ == "__main__":
    main()
