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
    "À répondre",
    "À traiter",
    "À lire",
    "Notification",
    "Commercial",
)
ACTIONS = ("keep", "trash", "draft", "archive", "mark_read", "move")
PRIORITIES = ("low", "medium", "high")
MIN_CONFIDENCE = 0.75
DEFAULT_LABEL = "À lire"


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

        prompt = f"""Tu es un moteur de classification de mails entrants. Tu vois UN mail à la fois, sans historique du fil.
Choisis EXACTEMENT UN libellé parmi la liste ci-dessous.

RÈGLE DE DÉCISION
Les libellés sont donnés par priorité DÉCROISSANTE. Parcours-les de haut en bas et choisis le PREMIER dont la définition correspond. Ne redescends jamais.
Si aucun ne correspond clairement, choisis "{default_label(allowed_labels)}".

GARDE-FOUS
- Expéditeur automatique (no-reply, noreply, donotreply, notifications@, mailer@) : ne choisis JAMAIS un libellé de type réponse. Un CTA dans un mail automatique ne rend pas une réponse attendue.
- Pour tout libellé pouvant déclencher une suppression : n'y range un mail que si son caractère de masse/commercial est certain. Dans le doute, choisis un libellé de classement non destructif.
- Le libellé Commercial ne doit être choisi que si le caractère newsletter, promotion, prospection ou envoi de masse est clair.
- Le LLM choisit seulement le libellé, l'urgence, la confiance et une raison. L'action finale est appliquée ensuite par le SaaS selon les paramètres utilisateur.

LIBELLÉS DISPONIBLES
{format_label_definitions(self.label_definitions, label_settings)}

FORMAT DE SORTIE
Réponds UNIQUEMENT par un objet JSON valide, sans texte ni balises autour :
{{
  "libelle": "<nom exact d'un libellé de la liste>",
  "urgence": "<haute|normale>",
  "confiance": <nombre entre 0 et 1>,
  "raison": "<1 phrase max>",
  "expediteur_automatique": <true|false>
}}

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
        result = normalize_model_result(parse_json_object(response.choices[0].message.content), allowed_labels)
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


def normalize_model_result(result: dict, allowed_labels: tuple[str, ...]) -> dict:
    label = str(result.get("libelle") or result.get("label") or "").strip()
    urgency = str(result.get("urgence") or "").strip().lower()
    raw_priority = str(result.get("priority") or "").strip().lower()
    confidence = result.get("confiance", result.get("confidence", 0))
    reason = str(result.get("raison") or result.get("reason") or "").strip()
    if urgency == "haute":
        priority = "high"
    elif raw_priority in PRIORITIES:
        priority = raw_priority
    else:
        priority = "medium"
    if label not in allowed_labels:
        label = default_label(allowed_labels)
        priority = "low"
    return {
        "label": label,
        "action": default_action_for_label(label),
        "priority": priority,
        "urgency": "haute" if priority == "high" else "normale",
        "confidence": confidence,
        "reason": reason,
        "automatic_sender": bool(result.get("expediteur_automatique", False)),
    }


def deterministic_classify(subject: str, sender: str, body: str) -> dict | None:
    """Fast path for obvious mailbox labels."""
    text = normalize_text(f"{subject}\n{sender}\n{body[:2000]}")
    automatic_sender = is_automatic_sender(sender)

    if not automatic_sender and has_any(text, "demande de reponse", "demande d information", "demande d'informations", "pouvez vous me rappeler", "pouvez-vous me rappeler", "devis", "interesse par vos services", "intéressé par vos services", "can we talk"):
        return decision("À répondre", "draft", "high", 0.98, "Le message demande clairement une réponse.")

    if has_any(text, "a commente", "a commenté", "commentaire", "mentioned you", "vous a mentionne", "vous a mentionné", "tagged you", "a reagi", "a réagi"):
        return decision("À lire", "keep", "medium", 0.97, "Le message signale une mention ou une interaction à lire.")

    if not automatic_sender and has_any(text, "relance", "follow up", "following up", "rappel de suivi"):
        return decision("À répondre", "draft", "high", 0.96, "Le message ressemble à une relance ou demande de suivi.")

    if has_any(text, "newsletter", "unsubscribe", "desabonner", "désabonner", "product hunt daily", "daily newsletter", "weekly digest", "digest", "bulletin", "agent hub security", "paper-heavy window", "model-release-heavy window", "practical lessons", "high learning rate", "25 ans aupres", "25 ans auprès", "ce qu'une legende", "ce qu'une légende", "appris", "decouvrez nos nouveautes", "découvrez nos nouveautés", "nouveautes de la semaine", "votre actualite du mois", "votre actualité du mois"):
        return decision("Commercial", "keep", "low", 0.98, "Le message est clairement une newsletter ou un envoi de masse.")

    if has_any(text, "notification", "welcome to your azure free account", "informations de securite", "informations de sécurité", "code a usage unique", "code à usage unique", "votre compte a ete mis a jour", "votre compte a été mis à jour", "verifiez votre adresse", "vérifiez votre adresse", "code de verification", "nouvelle application autorisee", "nouvelle application autorisée"):
        return decision("Notification", "keep", "low", 0.97, "Le message est une notification automatique.")

    if has_any(text, "marketing", "promotion", "promo", "offre", "offres", "offre speciale", "offre spéciale", "economisez", "économisez", "lancement produit", "product launch", "invite a friend", "invitez un proche", "obtenez", "cadeau ideal", "cadeau idéal", "delicieuses offres", "délicieuses offres", "plats favoris", "uber eats", "decouvrez", "découvrez", "essayez", "profitez", "nouveaux profils disponibles", "commence ici", "tournois", "stages", "academy"):
        return decision("Commercial", "keep", "low", 0.94, "Le message ressemble à du contenu commercial.")

    if has_any(text, "reunion", "réunion", "meeting", "calendar", "invitation"):
        return decision("Notification", "keep", "medium", 0.94, "Le message concerne une réunion ou une invitation automatique.")

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
        "urgency": "haute" if priority == "high" else "normale",
        "confidence": confidence,
        "reason": reason,
        "automatic_sender": False,
    }


def low_confidence_result(reason: str) -> dict:
    return decision(DEFAULT_LABEL, "keep", "low", 0.0, reason)


def default_label(allowed_labels: tuple[str, ...]) -> str:
    return DEFAULT_LABEL if DEFAULT_LABEL in allowed_labels else allowed_labels[0]


def default_action_for_label(label: str) -> str:
    return "draft" if label == "À répondre" else "keep"


def is_automatic_sender(sender: str) -> bool:
    text = normalize_text(sender)
    return has_any(text, "no-reply", "noreply", "donotreply", "do-not-reply", "notifications@", "notification@", "mailer@")


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
        for setting in sorted(label_settings, key=lambda item: safe_int(item.get("priority"), 10), reverse=True):
            key = str(setting.get("key", "")).strip()
            name = str(setting.get("name", "")).strip()
            description = str(setting.get("description", "")).strip()
            priority = safe_int(setting.get("priority"), 10)
            if key:
                rows.append(f"[Priorité {priority}] {key}\n  Nom affiché : {name or key}\n  Description : {description or 'Libellé personnalisé.'}")
        if rows:
            return "\n\n".join(rows)
    if not definitions:
        return "\n".join(f"[Priorité {priority_for_label(label)}] {label}" for label in LABELS)
    rows = []
    ordered_labels = sorted(LABELS, key=lambda label: priority_for_label(label, definitions), reverse=True)
    for label in ordered_labels:
        cfg = definitions.get(label, {})
        priority = cfg.get("priority", priority_for_label(label, definitions))
        description = cfg.get("description", "")
        action_hint = cfg.get("action_hint", "")
        examples = cfg.get("examples", []) or []
        example_text = "; ".join(str(item) for item in examples[:4])
        rows.append(f"[Priorité {priority}] {label}\n  {description}\n  Action produit par défaut : {action_hint or default_action_for_label(label)}. Exemples : {example_text}")
    return "\n\n".join(rows)


def priority_for_label(label: str, definitions: dict | None = None) -> int:
    if definitions and label in definitions:
        try:
            return int(definitions[label].get("priority", 10))
        except (TypeError, ValueError):
            pass
    return {"À répondre": 100, "À traiter": 90, "À lire": 60, "Notification": 40, "Commercial": 20}.get(label, 10)


def safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
