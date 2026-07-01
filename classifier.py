from __future__ import annotations

import json
import logging
import re
import unicodedata

from groq import Groq
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

LOG = logging.getLogger(__name__)

LABELS = (
    "[Imap]/Drafts",
    "À répondre",
    "À traiter",
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
        deterministic = deterministic_classify(subject, sender, body)
        if deterministic:
            return deterministic

        prompt = f"""Classify this incoming email.

Return only valid JSON with these keys:
- label
- action
- priority
- confidence
- reason

Allowed labels: {", ".join(LABELS)}.
Allowed actions: {", ".join(ACTIONS)}.
Allowed priorities: {", ".join(PRIORITIES)}.
Confidence must be a number from 0 to 1.

Label guidance:
- À répondre: the sender expects a direct answer.
- À traiter: invoices, payments, billing, documents, contracts, account/payment problems, or anything that needs manual business processing but not necessarily a written reply.
- Relance: a follow-up is needed.
- En attente de réponse: we are waiting for the other person.
- FYI: useful information that does not need a reply.
- Marketing: promotional or commercial content.
- Newsletter: newsletter content.
- Notification: automatic service/app notification.
- Mise à jour de réunion: calendar or meeting update.
- Traité: already handled or no further action needed.
- Commentaire: only explicit comments, mentions, feedback, notes, or messages saying someone commented/mentioned/tagged you.
- [Imap]/Drafts: only if the email clearly belongs to imported drafts.

Important:
- If the subject/body mentions invoice, facture, billing, payment, paiement, receipt, reçu, subscription, abonnement, contract, contrat, or document to review, choose À traiter.
- Do not choose Commentaire just because you are uncertain.
- Use draft only when a reply is actually needed.
- Use trash for obvious newsletters/marketing.
- Else use À traiter for manual review.

Subject: {subject}
Sender: {sender}
Body: {body[:12000]}"""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_completion_tokens=180,
            messages=[
                {"role": "system", "content": "You are a precise email triage assistant. Output JSON only, without markdown."},
                {"role": "user", "content": prompt},
            ],
        )
        result = parse_json_object(response.choices[0].message.content)
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


def parse_json_object(value: str) -> dict:
    cleaned = value.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response: {value[:200]}")
    return json.loads(match.group(0))


def deterministic_classify(subject: str, sender: str, body: str) -> dict | None:
    """Fast path for obvious mailbox labels."""
    text = normalize_text(f"{subject}\n{sender}\n{body[:2000]}")

    if has_any(text, "facture", "factures", "invoice", "invoicing", "billing", "bill", "paiement", "payment", "recu", "reçu", "receipt", "abonnement", "subscription", "contrat", "contract", "devis signe", "document a traiter", "document à traiter", "mode de paiement", "numero de facture", "numéro de facture"):
        return decision("À traiter", "keep", "high", 0.99, "Le message concerne une facture, un paiement, un document ou un sujet administratif à traiter.")

    if has_any(text, "demande de reponse", "demande d information", "demande d'informations", "pouvez vous me rappeler", "pouvez-vous me rappeler", "devis", "interesse par vos services", "intéressé par vos services", "can we talk"):
        return decision("À répondre", "draft", "high", 0.98, "Le message demande clairement une réponse.")

    if has_any(text, "a commente", "a commenté", "commentaire", "mentioned you", "vous a mentionne", "vous a mentionné", "tagged you", "a reagi", "a réagi"):
        return decision("Commentaire", "keep", "medium", 0.97, "Le message signale un commentaire, une mention ou une interaction.")

    if has_any(text, "relance", "follow up", "following up", "rappel de suivi"):
        return decision("Relance", "draft", "high", 0.96, "Le message ressemble à une relance ou demande de suivi.")

    if has_any(text, "newsletter", "unsubscribe", "desabonner", "désabonner", "decouvrez nos nouveautes", "découvrez nos nouveautés", "nouveautes de la semaine", "votre actualite du mois", "votre actualité du mois"):
        return decision("Newsletter", "trash", "low", 0.98, "Le message est clairement une newsletter.")

    if has_any(text, "notification", "votre compte a ete mis a jour", "votre compte a été mis à jour", "verifiez votre adresse", "vérifiez votre adresse", "code de verification", "nouvelle application autorisee", "nouvelle application autorisée"):
        return decision("Notification", "mark_read", "low", 0.97, "Le message est une notification automatique.")

    if has_any(text, "marketing", "promotion", "promo", "offre speciale", "offre spéciale", "lancement produit", "product launch", "decouvrez", "découvrez", "essayez", "profitez", "nouveaux profils disponibles", "commence ici", "tournois", "stages", "academy"):
        return decision("Marketing", "trash", "low", 0.94, "Le message ressemble à du contenu marketing.")

    if has_any(text, "reunion", "réunion", "meeting", "calendar", "invitation"):
        return decision("Mise à jour de réunion", "keep", "medium", 0.94, "Le message concerne une réunion ou une invitation.")

    return None


def normalize_text(value: str) -> str:
    lowered = value.lower()
    return "".join(char for char in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(char))


def has_any(text: str, *needles: str) -> bool:
    normalized_needles = [normalize_text(needle) for needle in needles]
    return any(needle in text for needle in normalized_needles)


def decision(label: str, action: str, priority: str, confidence: float, reason: str) -> dict:
    return {
        "label": label,
        "action": action,
        "priority": priority,
        "confidence": confidence,
        "reason": reason,
    }


def low_confidence_result(reason: str) -> dict:
    return decision("À traiter", "keep", "medium", 0.0, reason)
