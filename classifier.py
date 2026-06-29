from __future__ import annotations
import json
import logging
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

LOG = logging.getLogger(__name__)
LABELS = ("Client", "Prospect", "Facture", "Administratif", "Newsletter", "Spam", "À vérifier")
ACTIONS = ("keep", "trash", "draft", "archive", "mark_read", "move")
PRIORITIES = ("low", "medium", "high")
MIN_CONFIDENCE = 0.75


class EmailClassifier:
    def __init__(self, api_key: str, model: str = "qwen/qwen3-32b", client=None):
        if not api_key and client is None:
            raise ValueError("GROQ_API_KEY is required")
        self.client = client or Groq(api_key=api_key)
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True,
           retry=retry_if_exception_type(Exception))
    def classify(self, subject: str, sender: str, body: str) -> dict:
        prompt = f'''Classify this incoming email. Return only strict JSON with keys label, action, priority, confidence and reason.
Allowed labels: {", ".join(LABELS)}. Allowed actions: {", ".join(ACTIONS)}.
Allowed priorities: {", ".join(PRIORITIES)}. Confidence must be a number from 0 to 1.
Use trash for obvious spam/newsletters, draft for client/prospect messages needing a response, else keep.
Use archive when the email is useful but does not need to stay in the inbox. Use mark_read for low-value informational messages.
Subject: {subject}\nSender: {sender}\nBody: {body[:12000]}'''
        response = self.client.chat.completions.create(
            model=self.model, temperature=0, max_completion_tokens=100,
            messages=[{"role": "system", "content": "You are a precise email triage assistant. Output JSON only."},
                      {"role": "user", "content": prompt}],
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
        "label": "À vérifier",
        "action": "keep",
        "priority": "medium",
        "confidence": 0.0,
        "reason": reason,
    }
