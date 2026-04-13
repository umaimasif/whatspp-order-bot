import os
import uvicorn
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from fastapi import FastAPI, Form, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from twilio.twiml.messaging_response import MessagingResponse
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- 2. GOOGLE SHEETS SETUP ---
sheet = None
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("google_key.json", scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Coffee Orders").sheet1
    print("✅ Google Sheets Connected Successfully!")
except Exception as e:
    print(f"⚠️ Google Sheets Error: {e}")

# --- 3. HOMEPAGE ROUTE ---
@app.get("/")
async def read_root(request: Request):
    orders_data = []
    if sheet:
        try:
            raw_data = sheet.get_all_records()
            for row in raw_data:
                clean_row = {key.strip(): value for key, value in row.items()}
                orders_data.append(clean_row)
        except Exception as e:
            print(f"Error reading sheet: {e}")

    return templates.TemplateResponse("index.html", {"request": request, "orders": orders_data})

# --- 4. AI SETUP ---
GROQ_API_KEY="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"

llm = None
if GROQ_API_KEY:
    try:
        llm = ChatGroq(temperature=0, groq_api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile")
        print("✅ AI Brain Connected!")
    except Exception as e:
        print(f"⚠️ Groq Connection Error: {e}")

# --- 5. HELPER FUNCTIONS ---
def save_order_to_sheet(order_text):
    if not sheet: return "Error: Database not connected."
    try:
        parts = order_text.split("|")
        items = [p.strip() for p in parts]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ADDED "Pending" as the 5th column value automatically
        row_data = [timestamp] + items + ["Pending"]
        
        sheet.append_row(row_data)
        return "✅ Order saved!"
    except Exception as e:
        return f"Error saving: {e}"

def update_order_status(customer_name):
    """Searches for the customer and updates their status to Completed"""
    if not sheet: return "Error: Database not connected."
    try:
        records = sheet.get_all_records()
        # Loop through all rows to find the matching name
        for i, row in enumerate(records):
            sheet_name = str(row.get("Name", "")).strip().lower()
            if sheet_name == customer_name.lower():
                # i + 2 because gspread rows start at 1, and row 1 is the header
                cell_row = i + 2 
                sheet.update_cell(cell_row, 5, "Completed") # Column 5 is 'Status'
                return f"✅ Marked {customer_name}'s order as Completed!"
        return "⚠️ Could not find an order with that name."
    except Exception as e:
        return f"Error updating: {e}"

def get_ai_response(user_text):
    if not llm: return "System Error."
    
    system_instruction = """
    You are a friendly and polite AI assistant for 'Umaima's Coffee Shop'.
    
    HOW TO BEHAVE (CONVERSATIONAL RULES):
    - If the user says "Hi", "Hello", or greets you: Greet them back nicely and ask how you can help. DO NOT ask for their name or address yet.
    - If they ask for the menu or what you offer: Tell them nicely that you have Espresso (400 PKR), Latte (450 PKR), and Cappuccino (500 PKR).
    - ONLY when they explicitly say they want to order a coffee, THEN politely ask for their Name and Address to deliver it.
    
    SYSTEM COMMANDS (USE ONLY WHEN TRIGGERED):
    1. SAVING AN ORDER:
       Once the user has told you what coffee they want, PLUS their Name and Address, you must output EXACTLY:
       SAVE_ORDER: Item Name | Customer Name | Full Address
       
    2. ORDER RECEIVED (UPDATE STATUS):
       If a user says they received their order or it was delivered:
       - Ask for the Name they ordered under (if they haven't provided it).
       - Once you have the Name, output EXACTLY:
       UPDATE_STATUS: Customer Name
    """
    try:
        messages = [SystemMessage(content=system_instruction), HumanMessage(content=user_text)]
        return llm.invoke(messages).content
    except Exception as e:
        return f"AI Error: {e}"

# --- 6. WHATSAPP WEBHOOK ---
@app.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(...)):
    print(f"📩 Received: {Body}")
    ai_reply = get_ai_response(Body)
    final_response = ai_reply
    
    # Check if AI wants to save a new order
    if "SAVE_ORDER:" in ai_reply:
        data = ai_reply.replace("SAVE_ORDER:", "").strip()
        print(save_order_to_sheet(data))
        final_response = "🎉 Thank you! Your order has been placed."
        
    # Check if AI wants to update an existing order
    elif "UPDATE_STATUS:" in ai_reply:
        name = ai_reply.replace("UPDATE_STATUS:", "").strip()
        print(update_order_status(name))
        final_response = "✅ Wonderful! We have marked your order as delivered. Enjoy your coffee! ☕"

    resp = MessagingResponse()
    resp.message(final_response)
    return Response(content=str(resp), media_type="application/xml")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)