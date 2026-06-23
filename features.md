Cookd Data Engine Blueprint: High-Signal Data Collection for Model Distillation
This document outlines the complete architectural setup for capturing, filtering, and structuring Cookd's backend telemetry. Implementing this pipeline now ensures that every interaction on the Android client automatically populates a proprietary, high-wit training corpus for future Small Language Model (SLM) fine-tuning (e.g., Llama 8B, Hermes 3).

1. System Architecture Overview
   The Cookd Data Engine turns our production application into an automated dataset factory. Instead of relying on sterile, corporate synthetic data, we capture a dual-validated signal: AI Agent Optimization (RLAIF) combined with Real-World Human Telemetry (HITL).

[Android User Interface] ────(User Action / Copy)───► [FastAPI Telemetry Route]
│
▼
[Gemini Multi-Agent Loop] ───(Full Vision Payload)──► [PostgreSQL Database (JSONB)]
│
▼
[Training Dataset]
(SFT Instruction / DPO) 2. Database Schema (PostgreSQL & SQLAlchemy)
We use Postgres JSONB data types to preserve the full, raw contextual footprint of the Vision Node. Storing the complete extraction layer prevents our future lightweight models from experiencing context blindness or hallucination bugs.

Python
from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class GenerationLog(Base):
**tablename** = "generation_logs"

    # Transaction Identifiers
    interaction_id = Column(String, primary_key=True, index=True) # Unique run UUID
    conversation_id = Column(String, index=True)                  # Sticky chat thread ID
    user_id = Column(String, index=True)                          # End-user account ID

    # Context Classification Metadata
    direction = Column(String, nullable=False)     # "opener" or "reply"
    person_name = Column(String, nullable=True)     # Target profile name (e.g., "Anvi")
    detected_archetype = Column(String, nullable=True) # e.g., "THE EAGER/DIRECT"
    detected_dialect = Column(String, nullable=False)   # e.g., "HINGLISH"

    # The Full Vision Dump (Essential for training alignment)
    # Stores: raw_ocr_text, visual_hooks, photo_persona, durable_facts
    full_vision_context = Column(JSONB, nullable=False)

    # Multi-Agent Pipeline Auditing
    revision_count = Column(Integer, default=0)         # Number of internal rewrite loops
    initial_auditor_pass = Column(Boolean, default=True) # True if Auditor approved Gen 1
    auditor_issues = Column(String, nullable=True)       # The critique text if a rewrite occurred

    # The Structural Payload Options Generated
    # Array of dicts: [{"index": 0, "text": "...", "strategy": "PUSH-PULL"}]
    generated_replies = Column(JSON, nullable=False)

    # Real-World Human Validation Telemetry
    copied_reply_index = Column(Integer, nullable=True) # 0-3 index of line chosen by user
    was_regenerated = Column(Boolean, default=False)    # True if user discarded all lines

    created_at = Column(DateTime(timezone=True), server_default=func.now())

3. Backend Ingestion Pipeline
   When a user initiates a request, the backend executes the Vision node and passes the structured text to the Generator and Auditor. Immediately before sending the final response to the Android client, the server dumps the entire execution record to the database in a background process.

Code Implementation: Ingesting Data
Python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
import uuid

router = APIRouter()

async def save_pipeline_telemetry(db: Session, raw_log_data: dict):
"""Asynchronously writes generation metadata to the database."""
try:
log_entry = GenerationLog(\*\*raw_log_data)
db.add(log_entry)
db.commit()
except Exception as e:
db.rollback() # Log to structural logger (Sentry/CloudWatch)
print(f"Telemetry logging error: {str(e)}")

@router.post("/api/v2/generate")
async def generate_rizz_lines(
payload: GenerationRequest,
background_tasks: BackgroundTasks,
db: Session = Depends(get_db)
):
interaction_id = str(uuid.uuid4())

    # 1. Run Premium Multimodal Vision Node
    vision_output = await run_vision_agent(payload.screenshots)

    # 2. Run Multi-Agent Orchestration / Rewrite Loop
    generation_pipeline = await run_orchestration_loop(vision_output)

    # Assemble the comprehensive dataset payload
    vision_data_dump = {
        "raw_ocr_text": vision_output.raw_ocr_text,
        "visual_hooks": vision_output.visual_hooks,
        "photo_persona": vision_output.photo_persona,
        "durable_facts": vision_output.durable_facts,
        "intent": vision_output.intent
    }

    raw_log_data = {
        "interaction_id": interaction_id,
        "conversation_id": payload.conversation_id,
        "user_id": payload.user_id,
        "direction": payload.direction,
        "person_name": vision_output.person_name,
        "detected_archetype": vision_output.detected_archetype,
        "detected_dialect": vision_output.detected_dialect,
        "full_vision_context": vision_data_dump,
        "revision_count": generation_pipeline.revision_count,
        "initial_auditor_pass": (generation_pipeline.revision_count == 0),
        "auditor_issues": generation_pipeline.critique,
        "generated_replies": generation_pipeline.final_options_array
    }

    # Enqueue telemetry write to prevent API latency bloating
    background_tasks.add_task(save_pipeline_telemetry, db, raw_log_data)

    return {
        "interaction_id": interaction_id,
        "replies": generation_pipeline.final_options_array
    }

4. Frontend Client Telemetry Protocol
   To capture what lines actually work in the real world, the Android application must send user interactions back to the server using the interaction_id.

Telemetry API Contract
Endpoint: /api/v2/telemetry/action

Method: POST

Payload Structure:

JSON
{
"interaction_id": "ef4fc61e-db01-4432-95f3-a94af2c4f2aa",
"copied_reply_index": 1,
"was_regenerated": false
}
Backend Telemetry Target Endpoint
Python
class TelemetryPayload(BaseModel):
interaction_id: str
copied_reply_index: int | None = None
was_regenerated: bool = False

@router.post("/api/v2/telemetry/action")
async def update_user_action(payload: TelemetryPayload, db: Session = Depends(get_db)):
log_record = db.query(GenerationLog).filter(
GenerationLog.interaction_id == payload.interaction_id
).first()

    if not log_record:
        return {"status": "error", "message": "Interaction log not found"}

    if payload.copied_reply_index is not None:
        log_record.copied_reply_index = payload.copied_reply_index
    if payload.was_regenerated:
        log_record.was_regenerated = True

    db.commit()
    return {"status": "success", "message": "Human telemetry synchronized"}

Frontend Event Mapping Rules
UI Event Triggered Action Telemetry Payload Update Signal Strength
Tap Copy Button User selected a specific line to paste into Hinge. copied_reply_index = index_number High Positive Signal (Gold standard)
Tap Regenerate User disliked all 4 variants and wants a new batch. was_regenerated = true High Negative Signal (DPO reject candidate)
Back/Dismiss User closed the app screen without interacting. No updates sent Neutral (Ignored in training) 5. Dataset Curation Strategy (Filtering for Fine-Tuning)
When preparing to train an open-source model (like Llama 3.1 8B or Qwen 2.5), we extract data from the database using two distinct dataset strategies.

Strategy A: Supervised Fine-Tuning (SFT) Format
SFT teaches the model how to follow instruction-based constraints and adopt Cookd's unique conversational cadence. We only select entries where a human explicitly copied a line that the AI auditor passed on the first run.

SQL
SELECT
JSON_BUILD_OBJECT(
'system', 'You are Cookd AI, a culturally sharp dating strategist. Analyze the vision metrics and output an elite line in ' || detected_dialect || ' language style matching the strategy.',
'instruction', JSON_BUILD_OBJECT(
'archetype', detected_archetype,
'profile_data', full_vision_context,
'strategy_requested', generated_replies->copied_reply_index->>'strategy',
'direction', direction
),
'response', generated_replies->copied_reply_index->>'text'
) AS sft_json_row
FROM generation_logs
WHERE initial_auditor_pass = TRUE
AND copied_reply_index IS NOT NULL
AND was_regenerated = FALSE;
Strategy B: Direct Preference Optimization (DPO) Format
DPO shifts model parameters away from corporate sterilization and aligns it with sharp wit. We construct triplets showing the exact line a human copied versus the lines our system or users rejected.

SQL
SELECT
full_vision_context AS context,
generated_replies->copied_reply_index->>'text' AS chosen, -- The line the human copied
CASE
-- If it required a rewrite, the rejected sample is the initial critique profile
WHEN initial_auditor_pass = FALSE THEN auditor_issues
-- Otherwise, grab an unchosen alternative index row from the generated batch
ELSE generated_replies->0->>'text'
END AS rejected
FROM generation_logs
WHERE copied_reply_index IS NOT NULL; 6. Maintenance & Anti-Overfitting Guards
To keep the training corpus free of data noise, execute the following data hygiene steps prior to launching a model training pass:

Text Deduplication: Users often upload identical profile keywords (e.g., "loves coffee"). Use a Python scrubbing script to remove identical text outputs from the training pool to avoid loop-repetition overfitting.

PII Sanitization: Automatically strip telephone strings, Instagram handles, or location identifiers out of the full_vision_context before exporting to json datasets.

Token Length Capping: Drop any generation samples where the visual context dump exceeds the core token density limits of the targeted small model. Capping the initial vision intake at 4,000 text context tokens ensures efficient computing resource usage.
