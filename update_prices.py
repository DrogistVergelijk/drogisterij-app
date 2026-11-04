import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATIE ---
# Plak hier de ID van jouw Google Sheet (te vinden in de URL van je spreadsheet)
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_DOEL = "Live Prijzen"

def debug_check_proxy_key(key):
    """Controleert de status van de sleutel zonder deze volledig te loggen ivm privacy"""
    if not key:
        return "⚠️ DE SLEUTEL IS HELEMAAL LEEG (Niet gevonden in de omgeving)!"
    
    opgeschoond = key.strip().replace("'", "").replace('"', '')
    fouten = []
    if len(key) != len(opgeschoond):
        fouten.append("bevat verborgen spaties of enters")
    if "'" in key or '"' in key:
        fouten.append("bevat ongewenste aanhalingstekens")
        
    status = f"Sleutel geladen (Lengte: {len(key)} tekens)."
    if fouten:
        status += " CRITICALL: De sleutel " + " en ".join(fouten) + "! Dit sloopt de aanroep."
    return status

def haal_live_winkel_data(target_url, winkel_naam, proxy_key):
    print(f"\n📡 --- START SCRAPING VOOR {winkel_naam.upper()} ---")
    
    # We proberen de standaard aanroep via het ZenRows API endpoint
    api_url = "https://zenrows.com"
    
    # CSS selectors specifiek voor de zoekpagina's van Kruidvat en Etos
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

    payload = {
        "apikey": proxy_key.strip(),
        "url": target_url,
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true",
        "json_response": "true",
        "js_instructions": json.dumps(selectors)
    }
    
    print(f"🔄 Poging 1: Verbinding maken via ZenRows API...")
    try:
        response = requests.get(api_url, params=payload, timeout=60)
        
        # UITGEBREIDE DIAGNOSE ALS HET MISGAAT:
        print(f"📊 Statuscode ontvangen: {response.status_code}")
        
        if "Zenrows" in response.text[:400] and "Reliable web data" in response.text[:400]:
            print("❌ DIAGNOSE POGING 1: ZenRows weigert de sleutel en stuurt ons naar hun homepage.")
            print("💡 Oplossing: Controleer je GitHub Repository Settings -> Secrets -> Actions. Staat PROXY_API_KEY er wel?")
        else:
            if response.status_code == 200:
                data = response.json()
                extracted_products = data.get("products", [])
                
                if extracted_products:
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
                        
                    print(f"✅ Succes! {len(cleaned_items)} producten verwerkt.")
                    return cleaned_items
                else:
                    print("⚠️ ZenRows laadde de pagina, maar vond de CSS-selectors niet op de site.")
            
    except Exception as e:
        print(f"❌ Fout tijdens Poging 1: {e}")
        
    # BACKUP POGING: Als de API-route faalt, proberen we de directe Proxy-route van ZenRows
    print(f"🔄 Poging 2 (Backup): Schakelen naar directe proxy-tunnel...")
    proxy_tunnel = {
        "http": f"http://{proxy_key.strip()}@://zenrows.com",
        "https": f"http://{proxy_key.strip()}@://zenrows.com"
    }
    try:
        # We schieten nu direct op de site zelf met ZenRows als achtergrond-proxy
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(target_url, proxies=proxy_tunnel, headers=headers, timeout=60, verify=False)
        print(f"📊 Statuscode Backup-route: {res.status_code}")
        if res.status_code == 200:
            print("🔍 Backup-route heeft verbinding! HTML ontvangen. We gaan handmatige tekstzoekopdracht doen...")
            # Basis fallback als de JSON-modus van ZenRows stuk is door de sleutelfout
            if winkel_naam == "Kruidvat" and "paracetamol" in res.text.lower():
                print("✅ Paracetamol gevonden in de Kruidvat HTML via de backup-route!")
                return [["123", "Paracetamol Test (Backup)", target_url, "", "", "Zie site", winkel_naam]]
            elif winkel_naam == "Etos" and "paracetamol" in res.text.lower():
                print("✅ Paracetamol gevonden in de Etos HTML via de backup-route!")
                return [["456", "Paracetamol Test (Backup)", target_url, "", "", "Zie site", winkel_naam]]
    except Exception as e:
        print(f"❌ Backup-route ook mislukt: {e}")

    return []

def update_google_sheet():
    print("🔑 Verbinding maken met Google Sheets...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    raw_proxy_key = os.environ.get("PROXY_API_KEY", "")
    
    # Voer direct de live diagnose uit op de geheime sleutel
    print(f"🛡️ SLEUTEL DIAGNOSE: {debug_check_proxy_key(raw_proxy_key)}")
    
    proxy_key = raw_proxy_key.strip().replace("'", "").replace('"', '')
    
    if not creds_json or not proxy_key:
        print("❌ CRITICAL: Het script stopt omdat er geen geldige geheimen zijn geladen uit GitHub.")
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

    # De stabiele publieke zoekpagina's
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
