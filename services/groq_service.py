import os
import json
import re
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def score_lead(name: str, email: str, company: str, message: str) -> dict:
    prompt = f"""
You are a B2B lead qualification expert. Analyze this lead and return a JSON response only, no extra text, no markdown, no code blocks.

Lead Info:
- Name: {name}
- Email: {email}
- Company: {company}
- Message: {message}

Return this exact JSON format:
{{
    "score": <number from 0-100>,
    "qualification": "<Hot | Warm | Cold>",
    "reasoning": "<2-3 sentence explanation>"
}}
"""

    retries = 3
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=30,
            )
            raw = response.choices[0].message.content
            print(f"[GROQ RAW RESPONSE]: {raw}")
            cleaned = re.sub(r"```json|```", "", raw).strip()
            return json.loads(cleaned)
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Groq scoring failed after {retries} attempts: {e}")
            wait = 2 ** attempt  
            print(f"[GROQ] Attempt {attempt + 1} failed: {e} — retrying in {wait}s...")
            time.sleep(wait)
