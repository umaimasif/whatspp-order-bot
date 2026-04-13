import gspread
from google.oauth2.service_account import Credentials
import os

print("--- STARTING GOOGLE SHEETS TEST ---")

# 1. Check if key file exists
if os.path.exists("google_key.json"):
    print("✅ Found google_key.json file!")
else:
    print("❌ ERROR: google_key.json NOT found. Please move it here.")
    exit()

# 2. Try to connect
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("google_key.json", scopes=scopes)
    client = gspread.authorize(creds)
    print("✅ Authenticated with Google!")
    
    # 3. Print the email to double-check
    print(f"🤖 Bot Email: {creds.service_account_email}")
    print("⚠️ MAKE SURE YOU SHARED THE SHEET WITH THIS EMAIL ABOVE! ⚠️")

    # 4. Try to open the sheet
    sheet = client.open("Coffee Orders").sheet1
    print("✅ SUCCESS! Found the sheet 'Coffee Orders'")
    
    # 5. Write a test line
    sheet.append_row(["TEST", "Connection Successful", "It works!"])
    print("✅ Wrote a test line to your sheet.")

except Exception as e:
    print("\n❌ SOMETHING FAILED:")
    print(f"Error Type: {type(e)}")
    print(f"Error Details: {e}")