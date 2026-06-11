# AI Lead Qualification Pipeline

An automated lead scoring system that receives form submissions via webhook, scores them using AI, logs them to a CRM, and notifies the sales team in real time — all without any manual intervention.

---

## What It Does

Businesses receive leads from website contact forms. Manually reading and qualifying each one wastes 3–5 minutes per lead. This pipeline eliminates that entirely:

1. Lead submits a form → hits the webhook
2. Lead is instantly persisted to SQLite (no data loss)
3. AI scores the lead 0–100 and classifies it as Hot / Warm / Cold
4. Lead is logged to Airtable (CRM)
5. Sales team gets a Slack notification with score + reasoning

**ROI:** A team processing 100 leads/week saves ~8 hours of manual review time weekly.

---

## Architecture

```
Form Submission
      │
      ▼
FastAPI Webhook  ──► SQLite (persist immediately)
      │
      ▼
Background Worker
      │
      ├──► Groq AI (lead scoring)
      ├──► Airtable (CRM logging)
      └──► Slack (team notification)
```

**Why this architecture?**

The webhook returns instantly (`202 Accepted`) while all processing happens in the background. This means:
- No timeouts, even if AI or CRM calls take seconds
- Lead data is never lost — SQLite is the source of truth
- Any failed step is retried automatically (3 attempts, exponential backoff)

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| API | FastAPI | Async-native, fast, production-grade |
| Storage | SQLite | Zero-config persistent store + dedup |
| AI Scoring | Groq (llama-3.1-8b-instant) | Fast inference, free tier |
| CRM | Airtable | Visual, shareable, free tier |
| Notifications | Slack Webhooks | Instant team alerts |

---

## Error Handling Architecture

Every external service call (Groq, Airtable, Slack) has:

- **3 retry attempts** with exponential backoff (1s → 2s → 4s)
- **Background processing** so webhook never blocks or times out
- **Dead letter queue** — failed leads stay in SQLite with `status=failed` and trigger a Slack failure alert
- **Crash recovery** — on server restart, any leads stuck in `pending` or `processing` are automatically re-queued

```python
# Retry pattern used across all services
for attempt in range(retries):
    try:
        # call external service
    except Exception as e:
        if attempt == retries - 1:
            raise RuntimeError(f"Failed after {retries} attempts: {e}")
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
```

Failed leads can be manually retried via:
```
POST /leads/{id}/retry
```

---

## Timeout Problem Solution

**Problem:** Webhook → AI → CRM chain can exceed 10s timeout limits.

**Solution:** Decouple receipt from processing.

```python
@app.post("/webhook/lead")
async def receive_lead(lead: Lead, background_tasks: BackgroundTasks):
    lead_id = db.save_lead(...)        # persist first
    background_tasks.add_task(process_lead, lead_id)  # process async
    return {"status": "received"}      # instant response
```

The webhook responds in milliseconds. Processing happens independently in the background. Even if Groq takes 8 seconds or Airtable retries twice, the caller never times out and the lead is never lost.

**Production upgrade path:** Replace `BackgroundTasks` with Redis + Celery for distributed processing at scale.

---

## Project Structure

```
ai-lead-pipeline/
├── main.py                  # FastAPI app, webhook, background worker
├── db.py                    # SQLite layer (init, save, update, recovery)
├── services/
│   ├── groq_service.py      # AI lead scoring with retry logic
│   ├── airtable_service.py  # CRM logging with retry logic
│   └── slack_service.py     # Notifications + failure alerts
├── .env                     # API keys (not committed)
└── requirements.txt
```

---

## Setup

**1. Clone and install dependencies**
```bash
git clone <repo-url>
cd ai-lead-pipeline
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment variables**
```bash
cp .env.example .env
# Fill in your keys:
# GROQ_API_KEY
# AIRTABLE_API_KEY
# AIRTABLE_BASE_ID
# AIRTABLE_TABLE_NAME
# SLACK_WEBHOOK_URL
```

**3. Run the server**
```bash
uvicorn main:app --reload
```

**4. Expose publicly (for testing)**
```bash
ngrok http 8000
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/webhook/lead` | Receive a new lead |
| `GET` | `/stats` | Pipeline stats + ROI estimate |
| `GET` | `/leads/failed` | List all failed leads |
| `POST` | `/leads/{id}/retry` | Retry a failed lead |
| `GET` | `/health` | Health check |

---

## Stats Endpoint Sample Response

```json
{
  "total_leads": 12,
  "hot_leads": 4,
  "by_status": {
    "done": 11,
    "failed": 1
  },
  "manual_time_saved_minutes": 60
}
```

---

## Example Lead Submission

```bash
curl -X POST https://your-ngrok-url/webhook/lead \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "email": "john@techcorp.com",
    "company": "TechCorp Inc",
    "message": "We are a 200-person SaaS company looking to automate our lead pipeline. Budget $50k, want to start ASAP."
  }'
```

**Response:**
```json
{
  "status": "received",
  "lead_id": 1,
  "message": "Lead from John Smith is being processed"
}
```

**Slack notification:**
```
🔥 New Lead: Hot (80/100)
Name: John Smith        Email: john@techcorp.com
Company: TechCorp Inc   Score: 80/100

AI Reasoning:
John represents a high-value opportunity — large company, clear budget,
and immediate intent. Prioritize for same-day outreach.
```