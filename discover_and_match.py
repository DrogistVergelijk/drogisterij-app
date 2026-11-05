import os
import json
import re
import requests
from bs4 import BeautifulSoup
import gspread

# --- CONFIGURATIE ---
# ⚠️ VERVANG DIT DOOR JE EIGEN SPREADSHEET ID (VIND JE IN DE URL VAN JE SHEET)
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_BRON = "Producten Database"

PROXY_API_KEY = os.environ.get("PROXY_API_KEY", "")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")

# De lijst met Etos product-links staat nu direct en veilig in het geheugen van de robot
ETOS_URLS = [
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl</loc>",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl",
    "https://etos.nl"
]

def haal_ean_en_naam(url, proxy_key):
    """Bezoekt de Etos productpagina via ZenRows om de EAN-barcode en naam te oogsten."""
    if not url or not proxy_key:
        return None, None
        
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
            print(f" ⚠️ Pagina gaf foutcode {response.status_code}")
            return None, None
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Productnaam zoeken
        title_tag = soup.find('h1') or soup.find('meta', property='og:title')
        title = "Onbekend Product"
        if title_tag:
            title = title_tag.get('content', title_tag.get_text()).strip()

        # EAN zoeken in JSON-LD structuur data
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
                
        # RegEx Fallback
        ean_match = re.search(r'"ean"\s*:\s*"(\d{13})"', html) or re.search(r'"gtin"\s*:\s*"(\d{13})"', html)
        if ean_match:
            return ean_match.group(1), title
            
        return None, title
    except Exception as e:
        print(f" ⚠️ Fout tijdens verwerken pagina: {e}")
        return None, None

def main():
    print("🤖 Robot gestart: Automatische databasevuller...")
    print(f"📊 Succes! Er zijn {len(ETOS_URLS)} productlinks klaargezet in het geheugen.")

    gematchte_database = {}
    
    # VEILIGHEIDSLIMIET: We scannen er nu eerst 5 om de sheet live te testen en je credits te besparen!
    scan_limiet = 5 
    print(f"🔄 De robot gaat nu de eerste {scan_limiet} pagina's controleren op barcodes...")

    for i, url in enumerate(ETOS_URLS[:scan_limiet]):
        product_slug = url.split('/')[-1]
        print(f"📦 [{i+1}/{scan_limiet}] Pagina openen: {product_slug}")
        
        ean, naam = haal_ean_en_naam(url, PROXY_API_KEY)
        if ean:
            print(f" ✅ Barcode gevonden! EAN: {ean} -> Product: {naam}")
            gematchte_database[ean] = [naam, "", url]
        else:
            print(f" ⚠️ Geen barcode (EAN) kunnen extraheren voor: {naam}")

    # Google Sheets Verbinding maken
    if not GOOGLE_CREDENTIALS_JSON:
        print("❌ Fatale fout: GOOGLE_CREDENTIALS ontbreekt in GitHub Secrets!")
        return

    temp_creds_path = "temp_credentials.json"
    try:
        creds_clean = json.loads(GOOGLE_CREDENTIALS_JSON.strip())
        with open(temp_creds_path, "w") as f:
            json.dump(creds_clean, f)
            
        gc = gspread.service_account(filename=temp_creds_path)
        sheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(TABBLAD_BRON)
        print("🔑 Google Sheets kluis succesvol geopend!")
    except Exception as google_error:
        print(f"❌ Google Sheets verbindingsfout: {google_error}")
        if os.path.exists(temp_creds_path): os.remove(temp_creds_path)
        return

    # Pak de verzamelde data uit de database-dictionary en maak er rijen van
    nieuwe_rijen = []
    for ean, data in gematchte_database.items():
        nieuwe_rijen.append([ean, data[0], data[1], data[2]])

    try:
        if nieuwe_rijen:
            worksheet.append_rows(nieuwe_rijen)
            print(f"🎉 GOUD! Er zijn {len(nieuwe_rijen)} Etos-producten succesvol in je spreadsheet gezet!")
        else:
            print("⚠️ Run voltooid, maar er zijn deze keer geen barcodes geoogst.")
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven van de regels naar Google Sheets: {e}")
    except:
        print("❌ Onbekende fout bij wegschrijven.")
    finally:
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)

if __name__ == "__main__":
    main()
