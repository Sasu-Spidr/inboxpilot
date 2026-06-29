from __future__ import annotations

import json
import logging

from groq import Groq
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

LOG = logging.getLogger(__name__)

LABELS = (
    "[Imap]/Drafts",
    "À répondre",
    "Commentaire",
    "En attente de réponse",
    "FYI",
    "Marketing",
    "Mise à jour de réunion",
    "Newsletter",
    "Notification",
    "Relance",
    "Traité",
)
ACTIONS = ("keep", "trash", "draft", "archive", "mark_read", "move")
PRIORITIES = ("low", "medium", "high")
MIN_CONFIDENCE = 0.75


class EmailClassifier:
    def __init__(self, api_key: str, model: str = "qwen/qwen3-32b", client=None):
        if not api_key and client is None:
            raise ValueError("GROQ_API_KEY is required")
        self.client = client or Groq(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
        retry=retry_if_exception_type(Exception),
    )
    def classify(self, subject: str, sender: str, body: str) -> dict:
        prompt = f"""Classify this incoming email. Return only strict JSON with keys label, action, priority, confidence and reason.
Allowed labels: {", ".join(LABELS)}. Allowed actions: {", ".join(ACTIONS)}.
Allowed priorities: {", ".join(PRIORITIES)}. Confidence must be a number from 0 to 1.

Label guidance:
- À répondre: the sender expects a direct answer.
- Relance: a follow-up is needed.
- En attente de réponse: we are waiting for the other person.
- FYI: useful information that does not need a reply.
- Marketing: promotional or commercial content.
- Newsletter: newsletter content.
- Notification: automatic service/app notification.
- Mise à jour de réunion: calendar or meeting update.
- Traité: already handled or no further action needed.
- Commentaire: general message, uncertain message, or manual review.
- [Imap]/Drafts: only if the email clearly belongs to imported drafts.

Use draft only when a reply is actually needed. Use trash for obvious newsletters/marketing. Else keep.
Subject: {subject}
Sender: {sender}
Body: {body[:12000]}"""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_completion_tokens=150,
            messages=[
                {"role": "system", "content": "You are a precise email triage assistant. Output JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        if result.get("label") not in LABELS or result.get("action") not in ACTIONS or result.get("priority") not in PRIORITIES:
            raise ValueError(f"Invalid model classification: {result}")
        try:
            result["confidence"] = float(result.get("confidence", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid confidence: {result}") from exc
        result["reason"] = str(result.get("reason", "")).strip() or "No reason provided by model."
        if result["confidence"] < MIN_CONFIDENCE:
            return low_confidence_result(result.get("reason", "Low model confidence."))
        return result

    def safe_classify(self, subject: str, sender: str, body: str) -> dict:
        try:
            return self.classify(subject, sender, body)
        except Exception:
            LOG.exception("Classification failed; preserving email")
            return low_confidence_result("Classification failed; preserved for manual review.")


def low_confidence_result(reason: str) -> dict:
    return {
        "label": "Commentaire",
        "action": "keep",
        "priority": "medium",
        "confidence": 0.0,
        "reason": reason,
    }
