import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_notification(name: str, email: str, company: str, score: int,
                            qualification: str, reasoning: str) -> bool:
    emoji = "🔥" if qualification == "Hot" else "☀️" if qualification == "Warm" else "❄️"

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} New Lead: {qualification} ({score}/100)"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Name:*\n{name}"},
                    {"type": "mrkdwn", "text": f"*Email:*\n{email}"},
                    {"type": "mrkdwn", "text": f"*Company:*\n{company}"},
                    {"type": "mrkdwn", "text": f"*Score:*\n{score}/100"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Reasoning:*\n{reasoning}"
                }
            }
        ]
    }

    retries = 3
    for attempt in range(retries):
        try:
            response = httpx.post(SLACK_WEBHOOK_URL, json=message, timeout=10)
            response.raise_for_status()
            print("[SLACK] Notification sent")
            return True
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Slack notification failed after {retries} attempts: {e}")
            wait = 2 ** attempt 
            print(f"[SLACK] Attempt {attempt + 1} failed: {e} — retrying in {wait}s...")
            time.sleep(wait)

def send_failure_alert(name: str, email: str, error: str):
    try:
        httpx.post(SLACK_WEBHOOK_URL, json={
            "text": (
                f"⚠️ *Lead processing FAILED* (saved to dead-letter queue)\n"
                f"*Name:* {name} | *Email:* {email}\n"
                f"*Error:* {error}\n"
                f"Retry via `POST /leads/{{id}}/retry`"
            )
        }, timeout=10)
    except Exception:
        pass 
