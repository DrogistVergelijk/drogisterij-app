import os
import json
import requests
import gspread
import re
import traceback
import datetime

# --- CONFIGURATIE ---
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_BRON = "Producten Database" # Het nieuwe tabblad met je product-URL's
TABBLAD_DOEL = "Live Prijzen"

def haal_live_prijs(target_url, winkel_naam, proxy_key):
    if not target_url or target_url.strip() == "" or "Niet leverbaar" in target_url:
        return "Niet leverbaar"
        
    api_url = "https://zenrows.com"
    payload = {
        "apikey": proxy_key.strip(),
        "url": target_url,
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true"
    }
    
    try:
        response = requests.get(api_url, params=payload, timeout=45)
        if response.status_code != 200:
            return "Zie site"

        html_content = response.text
        schone_prijs = "Zie site"
        
        if winkel_naam == "Kruidvat":
            meta_price = re.search(r'itemprop="price"\s+content="([^"]+)"', html_content)
            if meta_price:
                schone_prijs = f"€ {meta_price.group(1).replace('.', ',')}"
        else: # Etos
            meta_price = re.search(r'data-price="([^"]+)"', html_content)
            if meta_price:
                schone_prijs = f"€ {meta_price.group(1).replace('.', ',')}"
                
        if schone_prijs == "Zie site":
            alle_prijzen = re.findall(r'(\d+[\.,]\d{2})', html_content)
            logische_prijzen = [p for p in alle_prijzen if not p.startswith("0") and float(p.replace(',', '.')) < 50.00]
            if logische_prijzen:
                schone_prijs = f"€ {logische_prijzen[0].replace('.', ',')}"
                
        return schone_prijs
    except:
        return "Fout"

def update_google_sheet():
    print("🔑 Verbinding maken met Google Sheets...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    proxy_key = os.environ.get("PROXY_API_KEY", "")
    
    if not creds_json or not proxy_key:
        print("❌ Geheimen ontbreken!")
        return
        
    temp_creds_path = "credentials.json"
    try:
        json_data = json.loads(creds_json.strip())
        with open(temp_creds_path, "w") as f:
            json.dump(json_data, f)
    except Exception as e:
        print(f"❌ Fout bij certificaat: {e}")
        return

    try:
        client = gspread.service_account(filename=temp_creds_path)
        sheet = client.open_by_key(SPREADSHEET_ID)
        
        # 1. LEES DE AUTOMATISCHE DATABASE UIT HET BRONTABBLAD
        try:
            bron_worksheet = sheet.worksheet(TABBLAD_BRON)
            bron_data = bron_worksheet.get_all_records() # Haalt alle rijen netjes als objecten op
            print(f"📂 Succesvol {len(bron_data)} producten ingeladen uit tabblad '{TABBLAD_BRON}'!")
        except Exception:
            print(f"⚠️ Tabblad '{TABBLAD_BRON}' niet gevonden. We maken een test-tabblad aan...")
            # Fallback als het tabblad nog niet bestaat, zodat het script niet crasht
            bron_worksheet = sheet.add_worksheet(title=TABBLAD_BRON, rows="100", cols="10")
            bron_worksheet.append_row(["Product ID", "Product Naam", "Link Kruidvat", "Link Etos"])
            bron_worksheet.append_row(["paracetamol-50st", "Paracetamol 500mg (50st)", "https://kruidvat.nl", "https://etos.nl"])
            bron_data = bron_worksheet.get_all_records()

        doel_worksheet = sheet.worksheet(TABBLAD_DOEL)
    except Exception as e:
        print(f"❌ Google Sheets verbindingsfout: {e}")
        if os.path.exists(temp_creds_path): os.remove(temp_creds_path)
        return

    alle_rijen = []
    nu = datetime.datetime.now().strftime("%d-%m %H:%M")

    # Loop door de dynamische spreadsheet-rijen heen (maximaal 30 per nacht om credits te sparen!)
    limiet = 30
    for i, p in enumerate(bron_data[:limiet]):
        # Flexibele kolomnamen afvangen
        naam = p.get("Product Naam") or p.get("product-title") or "Onbekend"
        id_prod = p.get("Product ID") or p.get("id") or f"prod-{i}"
        url_kv = p.get("Link Kruidvat") or p.get("link-kruidvat") or ""
        url_et = p.get("Link Etos") or p.get("link-etos") or ""
        
        print(f"\n📦 [{i+1}/{min(len(bron_data), limiet)}] Live prijs checken voor: {naam}")
        
        prijs_kv = haal_live_price(url_kv, "Kruidvat", proxy_key)
        prijs_et = haal_live_price(url_et, "Etos", proxy_key)
        
        alle_rijen.append([id_prod, naam, url_kv, prijs_kv, url_et, prijs_et, nu])

    try:
        print("\n🧹 Live tabblad updaten...")
        doel_worksheet.clear()
        headers = ["Product ID", "Product Naam", "Link Kruidvat", "Prijs Kruidvat", "Link Etos", "Prijs Etos", "Laatste Update"]
        doel_worksheet.append_row(headers)
        doel_worksheet.append_rows(alle_rijen)
        print("🎉 GOUD! De live prijzen zijn succesvol bijgewerkt vanuit de Sheet database!")
    except Exception as e:
        print(f"❌ Fout bij schrijven: {e}")
    finally:
        if os.path.exists(temp_creds_path): os.remove(temp_creds_path)

if __name__ == "__main__":
    update_google_sheet()
