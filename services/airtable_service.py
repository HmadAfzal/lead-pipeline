import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Leads")

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

def log_lead(name: str, email: str, company: str, message: str, score: int,
             qualification: str, reasoning: str, status: str = "New") -> dict:
    payload = {
        "fields": {
            "Name": name,
            "Email": email,
            "Company": company,
            "Message": message,
            "Score": score,
            "Qualification": qualification,
            "Reasoning": reasoning,
            "Status": status
        }
    }

    retries = 3
    for attempt in range(retries):
        try:
            response = httpx.post(BASE_URL, headers=HEADERS, json=payload, timeout=10)
            response.raise_for_status()
            print("[AIRTABLE] Lead logged successfully")
            return response.json()
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Airtable logging failed after {retries} attempts: {e}")
            wait = 2 ** attempt 
            print(f"[AIRTABLE] Attempt {attempt + 1} failed: {e} — retrying in {wait}s...")
            time.sleep(wait)
