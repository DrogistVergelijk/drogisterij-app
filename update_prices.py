import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATIE ---
GOOGLE_SHEET_NAME = "https://docs.google.com/spreadsheets/d/1xbvHQKn_UUwr4mQHixOG0ABD-JMmZi7v7oOrs-C3LbA/edit?gid=0#gid=0"
TABBLAD_NAAM = "Live Prijzen"
RUW_CSV_BESTAND = "ruwe_data.csv" # De naam van de CSV die jij in Drive uploadt

def get_data_from_drive_csv(client):
    """Leest de handmatig/automatisch geüploade CSV uit vanaf Google Drive."""
    print(f"📡 Zoeken naar {RUW_CSV_BESTAND} op Google Drive...")
    try:
        # Zoek het bestand op in Google Drive
        file_list = client.list_spreadsheet_files()
        # We gebruiken de drive API om het ruwe tekstbestand te vinden
        drive_client = client # gspread hergebruikt de credentials
        
        # Omdat we met gspread werken, openen we het bestand als een tijdelijke sheet of importeren het direct.
        # Als beginner is het 't makkelijkst om de ruwe data simpelweg in een extra tabblad genaamd 'Upload' te plakken!
        sheet = client.open(GOOGLE_SHEET_NAME)
        try:
            upload_worksheet = sheet.worksheet("Upload")
            all_records = upload_worksheet.get_all_values()
            
            if len(all_records) < 2:
                print("⚠️ Het tabblad 'Upload' is leeg of bevat geen rijen.")
                return []
                
            print(f"✅ Succesvol {len(all_records) - 1} rijen ingeladen uit tabblad 'Upload'!")
            return all_records[1:] # Retourneer data zonder de kolomkoppen
        except gspread.exceptions.WorksheetNotFound:
            print("❌ Fout: Maak eerst een tabblad aan met de exacte naam 'Upload'!")
            return []
            
    except Exception as e:
        print(f"❌ Fout bij het ophalen van de gegevens: {e}")
    return []

def update_google_sheet(data_to_write):
    """Overschrijft het tabblad Live Prijzen met de schone data."""
    print("🔑 Inloggen bij Google Sheets...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("❌ Fout: Geen GOOGLE_CREDENTIALS gevonden!")
        return

    creds_dict = json.loads(creds_json)
    scopes = ["https://google.com", "https://googleapis.com"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
    client = gspread.authorize(creds)
    
    raw_data = get_data_from_drive_csv(client)
    
    if len(raw_data) == 0:
        print("❌ Geen data gevonden om te verwerken.")
        return

    try:
        sheet = client.open(GOOGLE_SHEET_NAME)
        worksheet = sheet.worksheet(TABBLAD_NAAM)
        worksheet.clear()
        
        headers = ["id", "product-title", "product-link", "actie", "actie-deal", "prijs", "winkel"]
        worksheet.append_row(headers)
        
        # Schrijf de rijen weg
        worksheet.append_rows(data_to_write if 'data_to_write' in locals() else raw_data)
        print("🎉 Succes! De robot heeft de gegevens verwerkt en gekoppeld!")
    except Exception as e:
        print(f"❌ Fout tijdens het schrijven naar Google Sheets: {e}")

if __name__ == "__main__":
    update_google_sheet([])
