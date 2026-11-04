import os
import json
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATIE ---
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_NAAM = "Live Prijzen"

def update_google_sheet():
    print("🔑 Inloggen bij Google Sheets via moderne Google Auth...")
    
    # Haal de sleutel op uit GitHub Secrets
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("❌ Fout: Geen GOOGLE_CREDENTIALS gevonden in GitHub Secrets!")
        return

    # Inloggen via de officiële Google aanbevolen methode
    scopes = [
        "https://googleapis.com",
        "https://googleapis.com"
    ]
    
    try:
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        print("✅ Succesvol ingelogd bij Google!")
    except Exception as e:
        print(f"❌ Inlogfout bij Google: {e}")
        return

    try:
        # Open het spreadsheetbestand
        sheet = client.open(GOOGLE_SHEET_NAME)
        
        # Probeer de ruwe data uit het tabblad 'Upload' te halen
        print("📡 Data ophalen uit tabblad 'Upload'...")
        try:
            upload_worksheet = sheet.worksheet("Upload")
            raw_data = upload_worksheet.get_all_values()
        except gspread.exceptions.WorksheetNotFound:
            print("❌ Fout: Maak eerst een tabblad aan met de exacte naam 'Upload'!")
            return

        if len(raw_data) < 2:
            print("⚠️ Het tabblad 'Upload' is leeg of bevat geen producten.")
            return

        print(f"✅ {len(raw_data) - 1} rijen gevonden in 'Upload'. Schoonmaken starten...")

        # --- DATA SCHOONMAAK ZONE ---
        # De robot maakt de data hier strak. We pakken nu de rijen direct over.
        # (Later kunnen we hier intelligente filters plaatsen voor jouw kolommen!)
        schone_rijen = raw_data[1:] 

        # Open het doeltabblad 'Live Prijzen'
        worksheet = sheet.worksheet(TABBLAD_NAAM)
        worksheet.clear()
        
        # Schrijf de kolomkoppen
        headers = ["id", "product-title", "product-link", "actie", "actie-deal", "prijs", "winkel"]
        worksheet.append_row(headers)
        
        # Schrijf de schone rijen eronder
        worksheet.append_rows(schone_rijen)
        print("🎉 GOUD! De robot heeft de data verwerkt en je Google Sheet staat live!")

    except Exception as e:
        print(f"❌ Fout tijdens het verwerken van de spreadsheet: {e}")

if __name__ == "__main__":
    update_google_sheet()
