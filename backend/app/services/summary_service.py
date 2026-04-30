"""
Summary generation service.

At conversation end, this module calls Gemini to produce a structured JSON
summary, then stores it in-memory keyed by session ID for the frontend to
retrieve via the REST API.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# In-memory summary store: session_id → summary dict
_summaries: dict[str, dict] = {}


def get_summary(session_id: str) -> Optional[dict]:
    return _summaries.get(session_id)


def store_summary(session_id: str, summary: dict):
    _summaries[session_id] = summary


async def generate_summary(
    session_id: str,
    user_name: Optional[str],
    user_phone: Optional[str],
    appointments: list[dict],
) -> dict:
    """
    Use Gemini to generate a structured conversation summary.
    Falls back to a minimal summary if the API call fails.
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    context = (
        f"Patient name: {user_name or 'Unknown'}\n"
        f"Phone: {user_phone or 'Unknown'}\n"
        f"Appointments booked/managed:\n"
        + json.dumps(appointments, indent=2)
    )

    prompt = f"""
You are a hospital receptionist AI. Based on the following session information,
generate a concise structured summary.

Session information:
{context}

Return ONLY valid JSON with this exact schema:
{{
  "summary_text": "A 2-3 sentence natural language summary of the conversation",
  "user_details": {{
    "name": "patient name or null",
    "phone": "phone number or null"
  }},
  "appointments": [
    {{
      "id": 1,
      "doctor": "doctor name",
      "specialization": "specialization",
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "status": "confirmed|cancelled"
    }}
  ],
  "preferences": {{
    "preferred_doctor": "if mentioned",
    "preferred_time": "if mentioned"
  }},
  "timestamp": "ISO 8601 timestamp"
}}
""".strip()

    summary_data = {
        "summary_text": f"Conversation with {user_name or 'patient'} completed.",
        "user_details": {"name": user_name, "phone": user_phone},
        "appointments": appointments,
        "preferences": {},
        "timestamp": datetime.utcnow().isoformat(),
    }

    if gemini_key:
        try:
            from google import genai
            from google.genai import types as genai_types

            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt,
                config=genai_types.GenerateContentConfig(temperature=0.3),
            )
            raw = response.text.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip().rstrip("```").strip()

            parsed = json.loads(raw)
            parsed["timestamp"] = datetime.utcnow().isoformat()
            summary_data = parsed
        except Exception as exc:
            logger.error("Gemini summary generation failed: %s", exc)
            # Use fallback summary_data already set above

    store_summary(session_id, summary_data)
    return summary_data
