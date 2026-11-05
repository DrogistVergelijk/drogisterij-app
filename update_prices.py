import os
import json
import requests
import gspread
import re
import traceback
import datetime

# --- CONFIGURATIE ---
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_BRON = "Producten Database"
TABBLAD_DOEL = "Live Prijzen"

def haal_live_prijs(target_url, winkel_naam, proxy_key):
    # Verbeterde controle op ongeldige of te korte (home)pagina URL's
    if not target_url or len(target_url.strip()) < 25 or "Niet leverbaar" in target_url:
        return "Niet leverbaar"

    # CORRECTIE 1: Officieel ZenRows API v1 endpoint
    api_url = "https://zenrows.com"
    payload = {
        "apikey": proxy_key.strip(),
        "url": target_url.strip(),
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

        # Winkel-specifieke HTML extractie via meta-tags
        if winkel_naam == "Kruidvat":
            meta_price = re.search(r'itemprop="price"\s+content="([^"]+)"', html_content)
            if meta_price:
                schone_prijs = f"€ {meta_price.group(1).replace('.', ',')}"
        else: # Etos
            meta_price = re.search(r'data-price="([^"]+)"', html_content)
            if meta_price:
                schone_prijs = f"€ {meta_price.group(1).replace('.', ',')}"

        # Algemene tekst-fallback als de specifieke meta-tags missen
        if schone_prijs == "Zie site":
            alle_prijzen = re.findall(r'(\d+[\.,]\d{2})', html_content)
            logische_prijzen = [p for p in alle_prijzen if not p.startswith("0") and float(p.replace(',', '.')) < 50.00]
            if logische_prijzen:
                # CORRECTIE 2: Pak het eerste element uit de lijst om de crash te voorkomen
                schone_prijs = f"€ {logische_prijzen[0].replace('.', ',')}"

        return schone_prijs
    except Exception as e:
        print(f"⚠️ Fout tijdens scrapemogelijkheid van {winkel_naam}: {e}")
        return "Fout"

def update_google_sheet():
    print("🔑 Verbinding maken met Google Sheets...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    proxy_key = os.environ.get("PROXY_API_KEY", "")

    if not creds_json or not proxy_key:
        print("❌ Geheimen (GOOGLE_CREDENTIALS of PROXY_API_KEY) ontbreken!")
        return

    temp_creds_path = "credentials.json"
    try:
        json_data = json.loads(creds_json.strip())
        if json_data.get("type") != "service_account":
            json_data["type"] = "service_account"
        with open(temp_creds_path, "w") as f:
            json.dump(json_data, f)
    except Exception as e:
        print(f"❌ Fout bij certificaat: {e}")
        return

    try:
        client = gspread.service_account(filename=temp_creds_path)
        sheet = client.open_by_key(SPREADSHEET_ID)

        # Inlezen van de bron-database
        try:
            bron_worksheet = sheet.worksheet(TABBLAD_BRON)
            bron_data = bron_worksheet.get_all_records()
            print(f"📂 Succesvol {len(bron_data)} producten ingeladen uit '{TABBLAD_BRON}'!")
        except Exception:
            print(f"⚠️ Tabblad '{TABBLAD_BRON}' niet gevonden. We maken een test-tabblad aan...")
            bron_worksheet = sheet.add_worksheet(title=TABBLAD_BRON, rows="100", cols="10")
            # CORRECTIE 3: Match deze headers exact met de .get() keys onderin
            bron_worksheet.append_row(["Product ID", "Product Naam", "Link Kruidvat", "Link Etos"])
            bron_worksheet.append_row(["paracetamol-50st", "Paracetamol 500mg (50st)", "https://kruidvat.nl", "https://etos.nl"])
            bron_data = bron_worksheet.get_all_records()

        doel_worksheet = sheet.worksheet(TABBLAD_DOEL)
    except Exception as e:
        print(f"❌ Google Sheets verbindingsfout: {e}")
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)
        return

    alle_rijen = []
    nu = datetime.datetime.now().strftime("%d-%m %H:%M")
    limiet = 30 # Veiligheidslimiet voor testen
    
    for i, p in enumerate(bron_data[:limiet]):
        # Zorg dat deze sleutels exact overeenkomen met de kolomnamen in je sheet!
        naam = p.get("Product Naam") or "Onbekend"
        id_prod = p.get("Product ID") or f"prod-{i}"
        url_kv = p.get("Link Kruidvat") or ""
        url_et = p.get("Link Etos") or ""

        print(f"\n📦 [{i+1}/{min(len(bron_data), limiet)}] Prijs checken voor: {naam}")
        prijs_kv = haal_live_prijs(url_kv, "Kruidvat", proxy_key)
        prijs_et = haal_live_prijs(url_et, "Etos", proxy_key)

        alle_rijen.append([id_prod, naam, url_kv, prijs_kv, url_et, prijs_et, nu])

    try:
        print("\n🧹 Live tabblad updaten...")
        doel_worksheet.clear()
        headers = ["Product ID", "Product Naam", "Link Kruidvat", "Prijs Kruidvat", "Link Etos", "Prijs Etos", "Laatste Update"]
        
        # Geoptimaliseerde schrijfbewerking om data-mismatch te voorkomen
        doel_worksheet.update('A1', [headers] + alle_rijen)
        print("🎉 GOUD! De live prijzen zijn succesvol bijgewerkt!")
    except Exception as e:
        print(f"❌ Fout bij schrijven: {e}")
        traceback.print_exc()
    finally:
        if os.path.exists(temp_creds_path):
            os.remove(temp_creds_path)

if __name__ == "__main__":
    update_google_sheet()
