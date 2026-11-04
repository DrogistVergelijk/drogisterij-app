import os
import json
import gspread
from google.oauth2.service_account import Credentials
import google.auth.transport.requests

# --- CONFIGURATIE ---
# PLAK HIER jouw unieke Spreadsheet ID uit de URL!
SPREADSHEET_ID = "1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA"
TABBLAD_NAAM = "Live Prijzen"

def update_google_sheet():
    print("🔑 Inloggen bij Google Sheets met kloksynchronisatie...")
    
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("❌ Fout: Geen GOOGLE_CREDENTIALS gevonden in GitHub Secrets!")
        return

    scopes = [
        "https://googleapis.com",
        "https://googleapis.com"
    ]
    
    try:
        creds_dict = json.loads(creds_json)
        
        # Oplossing voor de klok-fout: we dwingen een tijdsmarge af van 10 seconden
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        # We verversen de token handmatig vóór gspread ermee aan de haal gaat om de fout op te vangen
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        
        client = gspread.authorize(credentials)
        print("✅ Verbinding met Google succesvol gesynchroniseerd!")
    except Exception as e:
        print(f"❌ Inlogfout bij Google Auth (Klok/Token probleem): {e}")
        print("💡 TIP: Als deze fout blijft, is de service-account sleutel in Google Cloud mogelijk gedeactiveerd.")
        return

    try:
        print(f"📂 Openen van spreadsheet ID: {SPREADSHEET_ID}...")
        sheet = client.open_by_key(SPREADSHEET_ID)
        
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
        schone_rijen = raw_data[1:] 

        worksheet = sheet.worksheet(TABBLAD_NAAM)
        worksheet.clear()
        
        headers = ["id", "product-title", "product-link", "actie", "actie-deal", "prijs", "winkel"]
        worksheet.append_row(headers)
        worksheet.append_rows(schone_rijen)
        print("🎉 GOUD! De robot heeft de data verwerkt en je Google Sheet staat live!")

    except Exception as e:
        print(f"❌ Fout tijdens het verwerken van de spreadsheet: {e}")

if __name__ == "__main__":
    update_google_sheet()
