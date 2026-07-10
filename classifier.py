from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path

from groq import Groq
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import yaml

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
    def __init__(self, api_key: str, model: str = "qwen/qwen3-32b", client=None, label_definitions_file: str = "config/label_definitions.yaml"):
        if not api_key and client is None:
            raise ValueError("GROQ_API_KEY is required")
        self.client = client or Groq(api_key=api_key)
        self.model = model
        self.label_definitions = load_label_definitions(label_definitions_file)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
        retry=retry_if_exception_type(Exception),
    )
    def classify(self, subject: str, sender: str, body: str, label_settings: list[dict] | None = None) -> dict:
        allowed_labels = allowed_label_keys(label_settings)
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

Allowed labels: {", ".join(allowed_labels)}.
Allowed actions: {", ".join(ACTIONS)}.
Allowed priorities: {", ".join(PRIORITIES)}.
Confidence must be a number from 0 to 1.

Label definitions:
{format_label_definitions(self.label_definitions, label_settings)}

Important:
- Return the internal label key exactly as written in Allowed labels, not the display name.
- If the subject/body mentions invoice, facture, billing, payment, paiement, receipt, reçu, subscription, abonnement, contract, contrat, or document to review, choose À traiter.
- If the email is promotional, choose Marketing even if it contains friendly wording.
- If the email is a periodic digest/news bulletin, choose Newsletter.
- If the email is an automatic account/security/service alert, choose Notification.
- If the email is a meeting invite/reminder/update, choose Mise à jour de réunion.
- Do not choose Commentaire just because you are uncertain.
- Do not choose À traiter just because you are uncertain.
- Use draft only when a reply is actually needed.
- Use trash for obvious newsletters/marketing.
- If none of the labels clearly fit, choose FYI with action keep.

Subject: {subject}
Sender: {sender}
Body: {body[:4000]}"""
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
        if result.get("label") not in allowed_labels or result.get("action") not in ACTIONS or result.get("priority") not in PRIORITIES:
            raise ValueError(f"Invalid model classification: {result}")
        try:
            result["confidence"] = float(result.get("confidence", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid confidence: {result}") from exc
        result["reason"] = str(result.get("reason", "")).strip() or "No reason provided by model."
        if result["confidence"] < MIN_CONFIDENCE:
            return low_confidence_result(result.get("reason", "Low model confidence."))
        return result

    def safe_classify(self, subject: str, sender: str, body: str, label_settings: list[dict] | None = None) -> dict:
        try:
            return self.classify(subject, sender, body, label_settings=label_settings)
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

    if has_any(text, "demande de reponse", "demande d information", "demande d'informations", "pouvez vous me rappeler", "pouvez-vous me rappeler", "devis", "interesse par vos services", "intéressé par vos services", "can we talk"):
        return decision("À répondre", "draft", "high", 0.98, "Le message demande clairement une réponse.")

    if has_any(text, "a commente", "a commenté", "commentaire", "mentioned you", "vous a mentionne", "vous a mentionné", "tagged you", "a reagi", "a réagi"):
        return decision("Commentaire", "keep", "medium", 0.97, "Le message signale un commentaire, une mention ou une interaction.")

    if has_any(text, "relance", "follow up", "following up", "rappel de suivi"):
        return decision("Relance", "draft", "high", 0.96, "Le message ressemble à une relance ou demande de suivi.")

    if has_any(text, "newsletter", "unsubscribe", "desabonner", "désabonner", "product hunt daily", "daily newsletter", "weekly digest", "digest", "bulletin", "agent hub security", "paper-heavy window", "model-release-heavy window", "practical lessons", "high learning rate", "25 ans aupres", "25 ans auprès", "ce qu'une legende", "ce qu'une légende", "appris", "decouvrez nos nouveautes", "découvrez nos nouveautés", "nouveautes de la semaine", "votre actualite du mois", "votre actualité du mois"):
        return decision("Newsletter", "trash", "low", 0.98, "Le message est clairement une newsletter.")

    if has_any(text, "notification", "welcome to your azure free account", "informations de securite", "informations de sécurité", "code a usage unique", "code à usage unique", "votre compte a ete mis a jour", "votre compte a été mis à jour", "verifiez votre adresse", "vérifiez votre adresse", "code de verification", "nouvelle application autorisee", "nouvelle application autorisée"):
        return decision("Notification", "mark_read", "low", 0.97, "Le message est une notification automatique.")

    if has_any(text, "marketing", "promotion", "promo", "offre", "offres", "offre speciale", "offre spéciale", "economisez", "économisez", "lancement produit", "product launch", "invite a friend", "invitez un proche", "obtenez", "cadeau ideal", "cadeau idéal", "delicieuses offres", "délicieuses offres", "plats favoris", "uber eats", "decouvrez", "découvrez", "essayez", "profitez", "nouveaux profils disponibles", "commence ici", "tournois", "stages", "academy"):
        return decision("Marketing", "trash", "low", 0.94, "Le message ressemble à du contenu marketing.")

    if has_any(text, "reunion", "réunion", "meeting", "calendar", "invitation"):
        return decision("Mise à jour de réunion", "keep", "medium", 0.94, "Le message concerne une réunion ou une invitation.")

    if has_any(text, "facture", "factures", "invoice", "invoicing", "billing", "bill", "paiement", "payment", "payment received", "recu", "reçu", "receipt", "abonnement", "subscription", "contrat", "contract", "devis signe", "document a traiter", "document à traiter", "documents a traiter", "documents à traiter", "document a signer", "document à signer", "documents a signer", "documents à signer", "invite a signer", "invité à signer", "signature de document", "mode de paiement", "numero de facture", "numéro de facture"):
        return decision("À traiter", "keep", "high", 0.99, "Le message concerne une facture, un paiement, un document ou un sujet administratif à traiter.")

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
    return decision("FYI", "keep", "low", 0.0, reason)


def load_label_definitions(path: str) -> dict:
    file = Path(path)
    if not file.exists():
        return {}
    return yaml.safe_load(file.read_text(encoding="utf-8")) or {}


def allowed_label_keys(label_settings: list[dict] | None = None) -> tuple[str, ...]:
    if not label_settings:
        return LABELS
    keys = [str(setting.get("key", "")).strip() for setting in label_settings]
    keys = [key for key in keys if key]
    return tuple(dict.fromkeys(keys)) or LABELS


def format_label_definitions(definitions: dict, label_settings: list[dict] | None = None) -> str:
    if label_settings:
        rows = []
        for setting in label_settings:
            key = str(setting.get("key", "")).strip()
            name = str(setting.get("name", "")).strip()
            description = str(setting.get("description", "")).strip()
            if key:
                rows.append(f"- {key}: display name: {name or key}. Description: {description or 'No custom description.'}")
        if rows:
            return "\n".join(rows)
    if not definitions:
        return "\n".join(f"- {label}" for label in LABELS)
    rows = []
    for label in LABELS:
        if label == "[Imap]/Drafts":
            rows.append("- [Imap]/Drafts: only if the email clearly belongs to imported drafts.")
            continue
        cfg = definitions.get(label, {})
        description = cfg.get("description", "")
        action_hint = cfg.get("action_hint", "")
        examples = cfg.get("examples", []) or []
        example_text = "; ".join(str(item) for item in examples[:4])
        rows.append(f"- {label}: {description} Action hint: {action_hint}. Examples: {example_text}")
    return "\n".join(rows)
