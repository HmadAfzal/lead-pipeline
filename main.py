import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from contextlib import asynccontextmanager

import db
from services.groq_service import score_lead
from services.airtable_service import log_lead
from services.slack_service import send_slack_notification, send_failure_alert

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    stuck = db.get_stuck_leads()
    if stuck:
        print(f"[RECOVERY] Re-processing {len(stuck)} stuck lead(s)")
        import threading
        for lead in stuck:
            threading.Thread(target=process_lead, args=(lead["id"],)).start()
    yield

app = FastAPI(title="AI Lead Qualification Pipeline", lifespan=lifespan)

class Lead(BaseModel):
    name: str
    email: EmailStr
    company: str
    message: str

def process_lead(lead_id: int):
    lead = db.get_lead(lead_id)
    if not lead or lead["status"] == "done":
        return

    db.update_status(lead_id, "processing")

    try:
        print(f"[1/3] Scoring lead #{lead_id}: {lead['name']}")
        result = score_lead(lead["name"], lead["email"], lead["company"], lead["message"])

        score = result["score"]
        qualification = result["qualification"]
        reasoning = result["reasoning"]
        print(f"[1/3] Score: {score} | {qualification}")

        print(f"[2/3] Logging to Airtable...")
        log_lead(
            name=lead["name"], email=lead["email"], company=lead["company"],
            message=lead["message"], score=score, qualification=qualification,
            reasoning=reasoning, status="New",
        )

        print(f"[3/3] Sending Slack notification...")
        send_slack_notification(
            name=lead["name"], email=lead["email"], company=lead["company"],
            score=score, qualification=qualification, reasoning=reasoning,
        )

        db.update_status(lead_id, "done", score=score,
                         qualification=qualification, reasoning=reasoning)
        print(f"[DONE] Lead #{lead_id} processed")

    except Exception as e:
        db.update_status(lead_id, "failed", error=str(e))
        print(f"[FAILED] Lead #{lead_id}: {e}")
        send_failure_alert(lead["name"], lead["email"], str(e))

@app.post("/webhook/lead")
async def receive_lead(lead: Lead, background_tasks: BackgroundTasks):
    lead_id = db.save_lead(lead.name, lead.email, lead.company, lead.message)
    if lead_id is None:
        return {"status": "duplicate", "message": "Lead already received"}

    background_tasks.add_task(process_lead, lead_id)
    return {"status": "received", "lead_id": lead_id,
            "message": f"Lead from {lead.name} is being processed"}

@app.post("/leads/{lead_id}/retry")
def retry_failed_lead(lead_id: int, background_tasks: BackgroundTasks):
    lead = db.get_lead(lead_id)
    if not lead:
        return {"status": "not_found"}
    db.update_status(lead_id, "pending")
    background_tasks.add_task(process_lead, lead_id)
    return {"status": "retrying", "lead_id": lead_id}

@app.get("/leads/failed")
def list_failed_leads():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT id, name, email, error FROM leads WHERE status='failed'").fetchall()
        return [dict(r) for r in rows]

@app.get("/stats")
def stats():
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as count FROM leads GROUP BY status"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        hot = conn.execute("SELECT COUNT(*) FROM leads WHERE qualification='Hot'").fetchone()[0]
    return {
        "total_leads": total,
        "hot_leads": hot,
        "by_status": {r["status"]: r["count"] for r in rows},
        "manual_time_saved_minutes": total * 5,
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {"status": "AI Lead Qualification Pipeline is running 🚀"}
