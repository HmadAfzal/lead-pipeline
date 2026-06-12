# AI Lead Qualification Pipeline

I didn't have a good automation project I could show, so I built this. It's a lead qualification system that takes the most tedious part of sales, reading, scoring leads and handling them automatically.

Here's what it does: A lead comes through your form. Normally, someone spends 3–5 minutes reading it, scoring it, logging it to your CRM, and notifying the team. This pipeline does all of that in about 5 seconds. Automatically. No human involved.

---
## Quick Navigation
 
**REWORK Eval Questions:**
- [Feature 1: Verifiable Project Review](#proof--evidence)
- [Feature 2: Error Handling Architecture](#failure-recovery-workflow)
- [Feature 3: Asynchronous Documentation](#for-your-team-non-technical-explanation)
- [Feature 4: Timeout Fix](#the-timeout-problem--how-i-fixed-it)
**Other Sections:**
- [How It Works](#how-it-actually-works)
- [The Stack](#the-stack)
- [Getting Started](#getting-started)
- [API Endpoints](#the-endpoints-you-can-use)
- [Evidence & Screenshots](#evidence-checklist)
---

## Proof & Evidence

Before I walk you through the details, here's the proof:

**Screenshots:**
- Airtable records with AI scores
- Real Slack alerts with lead data + AI reasoning
- Processing logs showing Step 1/3 → Step 2/3 → Step 3/3 → DONE
- Shows /stats output with lead count, qualification breakdown, time saved

**[View all screenshots below ↓](#evidence-checklist)**

**The Stack:**
- FastAPI (webhook handler)
- SQLite (persistent database)
- Groq AI (lead scoring)
- Airtable (CRM storage)
- Slack (team notifications)

**Verifiable ROI Metric:**
- Manual lead review: 3–5 minutes per lead
- Automated review: ~5 seconds per lead
- Time saved: 97% faster
- For 100 leads/week: Saves 8+ hours/week (one full workday)
- For 500 leads/week: Saves 40+ hours/week (one full-time employee)
---

## How It Actually Works

A potential customer fills out your form: "Hi, we're a 200-person SaaS company looking to automate our sales process. Budget is $50k, and we want to start this month."
This hits the webhook, saves the lead to a database immediately and response sent back to the form in milliseconds. The user sees "Got it, we're processing your request."
Meanwhile, in the background, completely separate from that HTTP request, the actual pipeline works.

### Step 1: AI Lead Scoring

The system sends the lead details to Groq to check if this is a hot prospect or not?"

The AI reads it, looks at company size, budget, timeline and returns a score (0–100) and a classification (Hot, Warm, or Cold). It also explains its reasoning in a sentence or two.

If Groq is slow, the system waits one second and retries the request. If the second attempt fails, it applies a longer delay before making a third attempt. If all three attempts fail, the request is marked as failed and logged for review.

### Step 2: Log to Your CRM

Now the system puts that scored lead into Airtable (your CRM). The full record appears: name, email, company, what they said, the AI's score, the classification, the reasoning.

### Step 3: Notify the Team

A Slack message fires to your sales channel.

```
🔥 New Lead: Hot (85/100)
Name: John Smith        Email: john@techcorp.com
Company: TechCorp Inc   Score: 85/100

AI Reasoning:
Large company with clear budget and immediate timeline — 
high probability close.
```

The emoji signals urgency. 🔥 for hot, ☀️ for warm, ❄️ for cold.

---

## Failure Recovery Workflow

Here's how the system handles failures and prevents data loss when services become unavailable.

### How the System Handles API Failures

```
Lead arrives & gets saved to SQLite immediately
(Source of truth — lead is safe)
        ↓
Background Worker starts processing
        ↓
        ┌─────────────────────────────────────┐
        │ ATTEMPT 1: Call Groq AI for scoring │
        └──────────────┬──────────────────────┘
                       │
            ┌──────────┴──────────┐
            ↓                     ↓
         SUCCESS            FAILS (timeout, rate limit, error)
            │                     │
            │              Wait 1 second
            │                     │
            │         ┌──────────────────────────┐
            │         │ ATTEMPT 2: Call Groq AI  │
            │         └──────────┬───────────────┘
            │                    │
            │         ┌──────────┴──────────┐
            │         ↓                     ↓
            │      SUCCESS            FAILS AGAIN
            │         │                     │
            │         │              Wait 2 seconds
            │         │                     │
            │         │         ┌──────────────────────────┐
            │         │         │ ATTEMPT 3: Call Groq AI  │
            │         │         └──────────┬───────────────┘
            │         │                    │
            │         │         ┌──────────┴──────────┐
            │         │         ↓                     ↓
            │         │      SUCCESS            FAILS 3 TIMES
            │         │         │                     │
            └─────────┴────┐    │                     │
                           ↓    ↓                     ↓
                      Move to Step 2            Mark as FAILED
                  (Log to Airtable)             in SQLite
                           │                     │
                    ┌──────┴────────┐             │
                    ↓               ↓             │
                 SUCCESS          FAILS      Send Slack Alert:
                    │                │       "Lead John Smith failed"
                    │          Move to       │
                    │          FAILED        Team can click to retry
                    │                │       OR fix the issue
                    │         ┌──────┘
                    │         ↓
                    │      Move to Step 3
                    │  (Send Slack notification)
                    │         │
                    │    ┌────┴────┐
                    │    ↓         ↓
                    │ SUCCESS    FAILS
                    │    │          │
                    │    │    Retry 3x
                    │    │    If all fail:
                    │    │    Mark as failed
                    │    │
                    └────┴──→ Update SQLite
                              Status = DONE
                              
(At any point, if server crashes, unfinished leads
 are automatically recovered on restart)
```

### How This Prevents Data Loss

**Scenario 1: Rate Limit from Groq**
```
You submit 50 leads in a minute.
Groq starts rate-limiting.

With retry and persistence:
- The webhook times out immediately
- Leads may be lost before processing begins

With retry and persistence:
- All 50 leads are already in SQLite ✓
- Worker tries Groq (fails with 429)
- Waits 1 second, tries again (fails)
- Waits 2 seconds, tries again (succeeds, Groq rate limit resolved)
- All 50 leads get processed So Nthing lost. ✓
```

**Scenario 2: Airtable Timeout**
```
You submit a lead.
Airtable is slow that moment (10+ second response).

Without retry and persistence:
- Webhook is still waiting for Airtable
- Browser timeout after 30 seconds
- Lead is lost (no record in your database)

With retry and persistence:
- Lead is already in SQLite immediately ✓
- Groq scoring completes (works fine)
- Airtable call starts but is slow
- Worker retries (1s wait, try again)
- Airtable responds, lead is logged ✓
- Even if Airtable was completely down:
  - Lead is still in SQLite marked as "failed"
  - Slack alerts the team
  - When Airtable comes back, team retries manually
  - Lead is never lost. ✓
```

**Scenario 3: Server Crashes Mid-Process**
```
You submit a lead.
Lead gets scored (done).
Lead is being logged to Airtable (in progress).
SERVER CRASHES.

Without retry and persistence:
- Lead may be lost in transit.

With retry and persistence:
- Lead is in SQLite with status="processing"
- Server restarts
- Recovery logic runs
- Those 3 leads are automatically re-queued
- They continue from where they left off
- All complete successfully ✓
```

### ### Three Rules for Preventing Data Loss

**Rule 1: Persist First**
Every lead goes to SQLite BEFORE any external API calls. No matter what happens, Leads are safe

**Rule 2: Retry Intelligently**
Every external service call has 3 attempts with exponential backoff (wait 1s, then 2s, then 4s). This catches:
- Network hiccups (resolved in <1s)
- Rate limits (resolved in 1–4s)
- Temporary service issues (resolved in a few seconds)

**Rule 3: Alert on Failure**
If all 3 retries fail, the lead is marked as failed and your team gets a Slack alert. You can then:
- Manually retry (click a button)
- Fix the issue (e.g., update your Slack webhook URL if it's wrong)
- Investigate (e.g., is Airtable API broken?)

No leads disappear into a void. Everything is visible.

### Reliability Features in Production

**Dead Letter Queue:**
Leads that fail all retries sit in SQLite with status="failed". Your team can query them anytime:
```
GET /leads/failed

Returns all failed leads with error messages so you know what went wrong.
```

**Manual Retry:**
For a specific failed lead:
```
POST /leads/42/retry

The lead gets re-queued and processing starts again. Once the issue is fixed
(e.g., Airtable is back up), it succeeds.
```

**Crash Recovery:**
On startup, the system checks for stuck leads:
```python
stuck = db.get_stuck_leads()  # Status = pending or processing
# Re-queue all of them automatically
```

**Monitoring:**
```
GET /stats

Shows you:
- Total leads processed
- How many are done
- How many failed
- How many are currently processing
```

---

## Architecture Overview

Let me show you how this all fits together.

### What You See 

```
Lead submitted via form
        ↓
Webhook receives it
        ↓
Save to database (5 milliseconds)
        ↓
Return response to form
        ↓
User sees "Your request is being processed"
        ↓
Process continues asynchronously
```

### Background Processing Flow

```
Worker picks up the lead from the queue
        ↓
Call Groq AI for scoring (usually 2–3 seconds)
   If it fails: retry with backoff
        ↓
Log to Airtable (usually 1 second)
   If it fails: retry with backoff
        ↓
Send Slack notification (usually 0.5 seconds)
   If it fails: retry with backoff
        ↓
Update database with final status
        ↓
Done. Lead is fully processed.
```

Total time in the background: about 4 seconds.

## The Timeout Problem & How I Fixed It

This is the core architectural decision that prevents the 10% failure rate.

### Synchronous (Blocking) Flow

**Scenario:** Webhook → OpenAI Scoring → HubSpot. Fails 10% of the time.

**The Flow:**
```
User submits form
        ↓
Webhook receives request (browser waiting, timeout clock starts)
        ↓
Call OpenAI API for scoring
   (takes 2–8 seconds, sometimes >30s)
        ↓
Wait for OpenAI response (browser still waiting)
        ↓
Call HubSpot API to log lead
   (takes 1–3 seconds, sometimes times out)
        ↓
Wait for HubSpot response
        ↓
Call Slack
        ↓
Return response to user
   (Total time: 10–20+ seconds)

If OpenAI takes >30s or HubSpot times out → entire request fails
If something fails mid-chain → lead data is lost (not in any database)
```

**Why it fails 10% of the time:**
- Most webhooks have a 30-second timeout limit
- OpenAI sometimes takes 6–10 seconds
- HubSpot sometimes takes 3–5 seconds
- Add network latency and it can go upto 15 seconds
- If any service is slow, you can hit 30+ seconds and timeout
- Browser closes connection
- Lead is lost

---

### Asynchronous Queue-Based Approach

**The Key Insight:** Don't make the webhook do all the work. Make it save the data and queue the work.

**Architecture:**
```
User submits form
        ↓
Webhook receives request (browser waiting, timeout clock starts)
        ↓
STEP 1: Save lead to SQLite (5 milliseconds)
        ↓
STEP 2: Queue background task (5 milliseconds)
        ↓
STEP 3: Return response to user (10 milliseconds total)
        ↓
USER GETS RESPONSE INSTANTLY
(Caller is done. No more waiting.)

Meanwhile, completely separate from the webhook:
        ↓
Background worker picks up queued lead
        ↓
Call OpenAI API for scoring (takes 2–8 seconds, no timeout pressure)
        ↓
Call HubSpot API to log lead (takes 1–3 seconds, with auto-retry)
        ↓
Call Slack (with auto-retry)
        ↓
Update SQLite with final status
        ↓
Done.
```

**Total webhook response time: <100 milliseconds (never times out)**

**Total processing time: 4–12 seconds (happens in background)**

---

### Visual Comparison

**Old Approach (Sync - Fails 10%):**
```
Request Timeline:
├─ 0ms: Webhook receives
├─ 500ms: Calling OpenAI...
├─ 6500ms: OpenAI responds
├─ 6500ms: Calling HubSpot...
├─ 9500ms: HubSpot responds
├─ 9500ms: Calling Slack...
├─ 10500ms: Slack responds
└─ 10500ms: Response sent (but browser already timed out at 30s if OpenAI was slow)

Data Loss Risk: HIGH
Timeout Risk: HIGH
```

**New Approach (Async):**
```
Webhook Response Timeline:
├─ 0ms: Webhook receives
├─ 5ms: Save to SQLite
├─ 10ms: Queue task
└─ 10ms: Return response ✓ (caller is done)

Background Processing Timeline (Independent):
├─ 15ms: Worker picks up lead
├─ 100ms: Calling OpenAI...
├─ 6100ms: OpenAI responds
├─ 6100ms: Calling HubSpot...
├─ 9100ms: HubSpot responds
├─ 9100ms: Calling Slack...
├─ 10100ms: Slack responds
├─ 10101ms: Update SQLite
└─ 10101ms: Status = DONE

Data Loss Risk: ZERO (in SQLite first)
Timeout Risk: ZERO (webhook already returned)
```

---

### Step-by-Step Re-Architecture

**What Changed:**

1. **Persistence First**
   - OLD: All work happens synchronously in the webhook
   - NEW: Lead is persisted to SQLite BEFORE any external calls
   - BENEFIT: Lead is safe even if everything downstream fails

2. **Async Processing**
   - OLD: Webhook waits for all API calls to complete
   - NEW: Webhook queues work and returns immediately
   - BENEFIT: Caller never times out

3. **Intelligent Retries**
   - OLD: If OpenAI fails, entire request fails
   - NEW: If OpenAI fails, auto-retry 3 times with exponential backoff
   - BENEFIT: Transient failures are caught and resolved

4. **Dead Letter Queue**
   - OLD: If HubSpot is down, lead is lost
   - NEW: Failed lead sits in SQLite marked "failed", team is alerted
   - BENEFIT: Lead can be retried manually when service is back up

5. **Crash Recovery**
   - OLD: Server crashes mid-process, lead is lost
   - NEW: Server startup automatically re-queues any stuck leads
   - BENEFIT: No data loss from server restarts

---

### Code-Level Implementation (Simplified)

**Old Way (Synchronous):**
```python
@app.post("/webhook/lead")
def receive_lead(lead: Lead):
    # All blocking calls in the request cycle
    score = call_openai(lead)  # Waits (2–8s)
    log_to_hubspot(score)       # Waits (1–3s)
    send_slack_alert(score)     # Waits (0.5s)
    return {"status": "success"}
    
# Total: 10–20+ seconds
# If any call fails, lead is lost
```

**New Way (Asynchronous):**
```python
@app.post("/webhook/lead")
async def receive_lead(lead: Lead, background_tasks: BackgroundTasks):
    # Step 1: Persist (always succeeds)
    lead_id = db.save_lead(lead)
    
    # Step 2: Queue work (returns immediately)
    background_tasks.add_task(process_lead, lead_id)
    
    # Step 3: Return response (caller is done)
    return {"status": "received", "lead_id": lead_id}

# Total webhook time: <100ms
# Lead is safe in database
# Processing happens independently

async def process_lead(lead_id: int):
    # All blocking calls happen here, outside the request cycle
    score = call_openai_with_retry(lead)  # 2–8s, with retries
    log_to_hubspot_with_retry(score)      # 1–3s, with retries
    send_slack_with_retry(score)          # 0.5s, with retries
    db.update_status(lead_id, "done")
    
# Takes 4–12 seconds total, but webhook caller doesn't wait
```

---

### Why This Architecture Never Fails on Timeouts

Webhook returns before making any external API calls and caller always gets response <100ms, never hits timeout.

---

### Production Deployment Upgrade Path

This implementation uses FastAPI's `BackgroundTasks`. For even higher reliability at scale, replace with:

**Redis Queue + Celery Workers:**
```
Webhook → Save to SQLite → Push to Redis Queue → Return instantly
                                    ↓
                    Celery Workers (scalable)
                         ↓
                   Process lead from queue
                   (same logic, but distributed)
```

Same pattern, but with:
- Persistent queue (survives server restarts)
- Multiple workers (process in parallel)
- Built-in monitoring (Flower dashboard)
- Better at handling high volume

But the core principle remains the same.

---

## The Stack

I kept it simple and cheap:

- **API Layer:** FastAPI (handles the webhook, super fast)
- **Database:** SQLite (stores leads, deduplication, recovery state)
- **AI Scoring:** Groq (free tier, same models as expensive providers)
- **CRM:** Airtable (free tier, visual, easy to share with your team)
- **Notifications:** Slack webhooks (free, instant alerts)

Everything runs on a single server and It has no complicated infrastructure.

---

## For Your Team (Non-Technical Explanation)

Here's how to explain this to your sales manager, CEO, or anyone who doesn't care about code:

### The Simple Version

**What it does:** When a customer fills out your form, an AI reads their message and decides if they're a good fit for you (Hot/Warm/Cold). Then it puts them in your CRM and alerts your sales team. All automatic. All in a few seconds.

**What you used to do:** Someone reads the email. Decides if it's worth pursuing. Logs it to Airtable. Sends a Slack message. Takes 3–5 minutes per lead.

**What you do now:** The system does all of that in 5 seconds. Your team jumps on hot leads instantly.

**Why it matters:** If you're getting 100 leads a week, that's one person's full-time job just reading emails. This frees them up to actually talk to customers.

**What if something breaks?** The system automatically retries and alerts you. No leads are ever lost. Even if the server crashes, leads are recovered automatically.

### Why We Built It This Way

- **Fast:** Leads get scored in seconds, not minutes
- **Reliable:** Can't lose a lead even if something fails
- **Simple:** No meetings needed. It just works in the background
- **Visible:** Everything shows up in tools you already use (Airtable, Slack)

---

## Video Walkthrough

For a live demo and explanation, watch this:

**[Insert Loom Video Link Here]**

In this video, you'll see:
1. Submit a test lead via form
2. Watch the system process it in real-time (Airtable updates, Slack fires, logs show steps)
3. Check the stats endpoint to see ROI
4. See what happens when something fails (automatic retry)

Link: `[Your Loom URL]`


Here's what happens when you submit a test lead:

```bash
curl -X POST https://your-public-url/webhook/lead \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sarah Chen",
    "email": "sarah@acmecorp.com",
    "company": "Acme Corp",
    "message": "Interested in your platform for our 150-person team. Budget approved. Can we schedule a demo?"
  }'
```

**The Response (instant):**
```json
{
  "status": "received",
  "lead_id": 42,
  "message": "Lead from Sarah Chen is being processed"
}
```

Then, a few seconds later:
- Airtable shows a new record with a score of 88 (Hot)
- Slack gets a notification: "🔥 New Lead: Hot (88/100)"

---


## Getting Started

**1. Clone the repo**
```bash
git clone <repo-url>
cd ai-lead-pipeline
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Add your API keys**
```bash
cp .env.example .env
# Fill in GROQ_API_KEY, AIRTABLE_API_KEY, AIRTABLE_BASE_ID, SLACK_WEBHOOK_URL
```

**3. Start the server**
```bash
uvicorn main:app --reload
```

**4. Make it public**
```bash
ngrok http 8000
```

**5. Test it**
```bash
curl -X POST https://your-ngrok-url/webhook/lead \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "email": "test@example.com", "company": "Test Co", "message": "Testing this"}'
```

---

## The Endpoints You Can Use

**POST /webhook/lead** — submit a new lead
**GET /stats** — see how many leads you've processed and time saved
**GET /leads/failed** — see any leads that failed processing
**POST /leads/{id}/retry** — manually retry a failed lead
**GET /health** — check if the system is running

---

## Evidence Checklist

All proof is in this repo:

**Visual Proof (Screenshots):**

### Airtable CRM Records
Shows actual leads with scores (85/100 Hot, 42/100 Cold, etc.)

![Airtable Records](screenshots/airtable-records.png)

---

### Slack Notifications
Shows real Slack alerts with formatting and emoji

![Slack Notifications](screenshots/slack-notifications.png)

---

### Terminal Processing Logs
Shows processing flow: [1/3] Scoring → [2/3] Logging → [3/3] Slack → [DONE]

![Terminal Logs](screenshots/terminal-logs.png)

---

### Stats Endpoint Output
Shows /stats output with lead count, qualification breakdown, time saved

![Stats Endpoint](screenshots/stats-endpoint.png)


**Code:**
- `main.py` — FastAPI webhook + background worker
- `db.py` — SQLite persistence + recovery logic
- `services/groq_service.py` — AI scoring with retry logic
- `services/airtable_service.py` — CRM logging with error handling
- `services/slack_service.py` — Notifications with fallback

All code is production-grade, transparent, and ready to run.