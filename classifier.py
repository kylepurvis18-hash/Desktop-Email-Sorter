"""Asks Claude to read one email and decide which job-application category
(if any) it belongs to."""
import json
import re

from anthropic import Anthropic

import config

_client = None

CATEGORIES = {
    "not_job_related",
    "confirmation",
    "action_needed",
    "rejected",
    "interview",
}

SYSTEM_PROMPT = """You classify a single email for someone who is actively job hunting. \
Read the email and decide which ONE category it belongs to:

- "confirmation": A simple acknowledgment that an application was received/submitted \
("thank you for applying", "we received your application"). No action requested, no \
decision made yet.
- "action_needed": The company is asking the person to DO something next: submit more \
documents, complete a background check or pre-screening questionnaire, take an \
assessment/skills test, verify information, schedule something themselves, etc.
- "rejected": The company says they are not moving forward, declining the application, \
or the position was filled by someone else.
- "interview": The company says the person is moving forward, wants to schedule an \
interview or a call, or is extending an offer.
- "not_job_related": The email is not about one of this person's own job applications \
at all (newsletters, unrelated personal/work email, job board digests/recommended \
listings the person did not apply to, marketing, etc).

Respond with ONLY a compact JSON object, no other text, in exactly this form:
{"category": "<one of the five categories above>", "confidence": "<low|medium|high>"}
"""


def _get_client():
    global _client
    if _client is None:
        _client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def classify_email(subject: str, sender: str, body: str) -> dict:
    """Returns {"category": ..., "confidence": ...}. Falls back to
    not_job_related on any parsing/API problem, so a hiccup never mis-files
    or crashes the whole run."""
    user_content = f"From: {sender}\nSubject: {subject}\n\nBody:\n{body}"

    try:
        response = _get_client().messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=100,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = response.content[0].text.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(match.group(0) if match else raw)

        category = parsed.get("category", "not_job_related")
        if category not in CATEGORIES:
            category = "not_job_related"

        return {"category": category, "confidence": parsed.get("confidence", "low")}

    except Exception as e:
        print(f"  [!] Classification failed, skipping this email safely: {e}")
        return {"category": "not_job_related", "confidence": "low"}
