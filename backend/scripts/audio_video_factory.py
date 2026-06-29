#!/usr/bin/env python
import asyncio
import json
import os
import subprocess
import httpx
from sqlalchemy import text
from app.config import settings
from app.infrastructure.database.engine import get_db

# --- API KEYS ---
GROQ_API_KEY = getattr(settings, "groq_api_key", os.getenv("GROQ_API_KEY"))

# --- PATHS ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
REMOTION_DIR = os.path.join(BASE_DIR, "marketing-video")
OUTPUT_VIDEO_PATH = os.path.join(BASE_DIR, "daily_viral_short.mp4")

LLM_SYSTEM_PROMPT = """
You are a viral TikTok/Reels copywriter for "Cookd AI", an AI dating assistant app.
Look at the chat transcript and the winning response our AI generated.
Write a highly engaging, copy-paste TikTok caption that creates curiosity and asks a question to drive comments. 
You MUST include the promo code COOKD100 in the caption.
Output strictly valid JSON: {"social_caption": "..."}
"""


async def fetch_winning_chat() -> dict | None:
    """Finds a real chat in the `interactions` table where the user copied the AI's line."""
    async for db in get_db():
        # Querying the actual `interactions` table from your models.py
        query = text("""
            SELECT person_name, transcript_json, their_last_message, 
                   reply_0, reply_1, reply_2, reply_3, copied_index
            FROM interactions
            WHERE copied_index IS NOT NULL 
            ORDER BY RANDOM() LIMIT 1
        """)
        res = await db.execute(query)
        row = res.mappings().first()
        return dict(row) if row else None


async def generate_social_caption(transcript: str, winning_line: str) -> dict:
    """Uses Groq (Llama 3) to write the viral caption."""
    prompt = f"Transcript:\n{transcript}\n\nWinning AI Line: {winning_line}"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        )
        return json.loads(r.json()["choices"][0]["message"]["content"])


async def main():
    print("🤖 1. Searching database for a winning chat...")
    win_data = await fetch_winning_chat()
    if not win_data:
        print(
            "❌ No copied lines found in database. You need at least one interaction where a user copied a reply."
        )
        return

    # 1. Parse the chat history (transcript_json from models.py)
    parsed_messages = []
    if win_data.get("transcript_json"):
        try:
            transcript = json.loads(win_data["transcript_json"])
            # The model stores transcript as [{"s":"them"|"user","t":"..."}]
            for m in transcript[-3:]:  # Take last 3 for brevity
                sender = "them" if m.get("s") == "them" else "you"
                parsed_messages.append({"sender": sender, "text": m.get("t", "")[:50]})
        except Exception:
            pass

    # Fallback to their_last_message if transcript_json is empty
    if not parsed_messages and win_data.get("their_last_message"):
        parsed_messages = [
            {"sender": "them", "text": win_data["their_last_message"][:50]}
        ]

    # 2. Extract the specific reply the user copied (reply_0, reply_1, etc.)
    copied_idx = win_data["copied_index"]
    winning_line_raw = win_data.get(f"reply_{copied_idx}", "")

    winning_line = winning_line_raw
    strategy_label = "FRAME CONTROL"  # Default

    # Try to parse the reply as JSON in case you store {"text": "...", "strategy_label": "..."} in the text column
    try:
        reply_obj = json.loads(winning_line_raw)
        if isinstance(reply_obj, dict):
            winning_line = reply_obj.get("text", winning_line_raw)
            strategy_label = reply_obj.get("strategy_label", "FRAME CONTROL")
    except Exception:
        pass  # If it fails, it means the column just contains the raw string, which is perfectly fine.

    transcript_text = "\n".join(
        [f"{m['sender']}: {m['text']}" for m in parsed_messages]
    )
    person_name = win_data.get("person_name") or "Match"

    print("✍️ 2. Writing viral caption with Llama 3...")
    script_data = await generate_social_caption(transcript_text, winning_line)

    # ---------------------------------------------------------
    # 💥 THE PAYLOAD
    # ---------------------------------------------------------
    video_payload = {
        "personName": person_name,
        "messages": parsed_messages,
        "winningLine": winning_line,
        "strategyLabel": strategy_label.upper(),
        "voiceoverAudio": "",
    }

    print("🎬 3. Compiling Video via Remotion Engine...")

    cmd = [
        "npx",
        "remotion",
        "render",
        "src/Root.tsx",
        "CookdChatShort",
        OUTPUT_VIDEO_PATH,
        f"--props={json.dumps(video_payload)}",
    ]

    process = subprocess.Popen(
        cmd, cwd=REMOTION_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        print(f"\n✅ SUCCESS! Viral Video generated at: {OUTPUT_VIDEO_PATH}")
        print("=" * 50)
        print("📱 COPY-PASTE THIS CAPTION TO TIKTOK/REELS:")
        print(f"{script_data.get('social_caption', '')}")
        print("=" * 50)
    else:
        print(f"❌ Video compilation failed:\n{stderr.decode()}")


if __name__ == "__main__":
    asyncio.run(main())
