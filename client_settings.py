from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

CEO_LABEL_DESCRIPTIONS = {
    "À répondre": """Définition. Un humain identifiable attend une réponse écrite de ma part.
Une réponse textuelle réglerait le mail. Inclut les relances (quelqu'un réclame un retour promis). Signaux. Question directe, demande d'info ou de devis, sollicitation commerciale d'un prospect réel, message personnel appelant un retour, rappel dirigé vers moi (« avez-vous eu le temps de… »). Ne pas confondre :
• Facture/contrat/accès où répondre par texte ne suffit pas → À traiter.
• Expéditeur automatique (no-reply) même avec un « confirmez » → Notification.
• Compliment ou mise au courant sans réponse réellement attendue → À lire.
Métadonnée urgence : mets haute si le mail est une relance, mentionne une échéance proche, ou emploie un ton pressant ; sinon normale.""",
    "À traiter": """Définition. Le mail exige une action manuelle qui n'est pas une simple réponse : payer, signer, valider un document, gérer un accès ou un compte, effectuer une opération. Signaux. Facture à régler, contrat à signer, document à valider, demande d'accès légitime, alerte de sécurité exigeant une action réelle. Ne pas confondre :
• Simple question sur un document (« quel est le montant ? ») → À répondre.
• Reçu / confirmation d'une opération déjà faite → Notification.
• Promo urgente déguisée (« dernière chance -50 % ») → Commercial.""",
    "À lire": """Définition. Information destinée à un humain, à lire ou conserver, sans action attendue. Regroupe FYI, mises au courant, commentaires et mentions collaboratifs. Signaux. Transfert « pour info », note interne, mention dans un fil, commentaire sur un document, retour d'un collègue, document partagé sans demande. Ne pas confondre :
• Le message attend un retour de ma part → À répondre.
• Message généré par un système/application → Notification.
• Contenu éditorial d'abonnement ou promotion → Commercial.""",
    "Notification": """Définition. Message généré par une machine : alerte, code, confirmation transactionnelle, événement calendaire. Aucune action manuelle requise. Signaux. Expéditeur no-reply / notifications@, code de connexion, alerte système, reçu, invitation ou modification de réunion (fichier .ics), rappel automatique d'événement. Ne pas confondre :
• L'alerte exige une action manuelle réelle (« connexion suspecte, sécurisez votre compte ») → À traiter.
• Message écrit par un humain pour être lu → À lire.
• Promotion ou prospection → Commercial.""",
    "Commercial": """Définition. Contenu d'abonnement éditorial, promotion, prospection, publicité, offre commerciale, acquisition. Signaux. Newsletter récurrente, cold email, promo/remise, argumentaire de vente, lien de désabonnement, envoi de masse. Ne pas confondre :
• Mail transactionnel légitime d'un service que j'utilise (reçu, confirmation) → Notification.
• Message personnel ou professionnel individuel → À répondre ou À lire.
• ⚠ Ce libellé peut déclencher une suppression (si l'utilisateur l'a activée). Au moindre doute sur le caractère de masse/commercial, ne choisis pas Commercial → Notification ou À lire.""",
}

DEFAULT_LABELS: list[dict[str, Any]] = [
    {"key": "À répondre", "name": "À répondre", "description": CEO_LABEL_DESCRIPTIONS["À répondre"], "color": "#0d9488", "priority": 100, "prepareDraft": True, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "À traiter", "name": "À traiter", "description": CEO_LABEL_DESCRIPTIONS["À traiter"], "color": "#8b8b7a", "priority": 90, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "À lire", "name": "À lire", "description": CEO_LABEL_DESCRIPTIONS["À lire"], "color": "#3b82f6", "priority": 70, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Notification", "name": "Notification", "description": CEO_LABEL_DESCRIPTIONS["Notification"], "color": "#22c55e", "priority": 50, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Commercial", "name": "Commercial", "description": CEO_LABEL_DESCRIPTIONS["Commercial"], "color": "#fb7185", "priority": 30, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
]

CANONICAL_LABEL_KEYS = {label["key"] for label in DEFAULT_LABELS}

LABEL_ALIASES = {
    "A répondre": "À répondre",
    "Relance": "À répondre",
    "A traiter": "À traiter",
    "FYI": "À lire",
    "Commentaire": "À lire",
    "Newsletter": "À lire",
    "Traité": "À lire",
    "Traite": "À lire",
    "En attente de réponse": "À lire",
    "En attente de reponse": "À lire",
    "Mise à jour de réunion": "Notification",
    "Mise a jour de reunion": "Notification",
    "Marketing": "Commercial",
}


def settings_path(client_id: str) -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    safe_client_id = re.sub(r"[^a-zA-Z0-9._-]", "-", client_id)
    return data_dir / "client-settings" / f"{safe_client_id}.json"


def load_client_settings(client_id: str) -> dict[str, Any]:
    try:
        return json.loads(settings_path(client_id).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"labels": []}


def label_name_for_client(client_id: str, label: str, default_name: str) -> str:
    setting = _label_setting(client_id, label)
    name = str(setting.get("name", "")).strip() if setting else ""
    return name or default_name


def label_color_for_client(client_id: str, label: str) -> str | None:
    setting = _label_setting(client_id, label)
    color = str(setting.get("color", "")).strip() if setting else ""
    return color if re.fullmatch(r"#[0-9a-fA-F]{6}", color) else None


def label_color_settings_for_client(client_id: str) -> list[dict[str, str]]:
    settings: list[dict[str, str]] = []
    for setting in normalized_labels_for_client(client_id):
        key = str(setting.get("key", "")).strip()
        name = str(setting.get("name", "")).strip()
        color = str(setting.get("color", "")).strip()
        if key and name and re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            settings.append({"key": key, "name": name, "color": color})
    return settings


def label_settings_for_classifier(client_id: str) -> list[dict[str, str]]:
    labels: list[dict[str, str]] = []
    for setting in normalized_labels_for_client(client_id):
        key = str(setting.get("key", "")).strip()
        name = str(setting.get("name", "")).strip()
        description = str(setting.get("description", "")).strip()
        priority = _int_setting(setting.get("priority"), 10)
        if key and name:
            labels.append({"key": key, "name": name, "description": description, "priority": priority})
    return labels


def active_label_keys_for_client(client_id: str) -> list[str]:
    return [str(setting["key"]) for setting in normalized_labels_for_client(client_id)]


def managed_label_names_for_client(client_id: str) -> list[str]:
    names: list[str] = []
    for setting in normalized_labels_for_client(client_id):
        name = str(setting.get("name", "")).strip()
        if name and name not in names:
            names.append(name)
    return names


def action_for_client(client_id: str, label: str, default_action: str) -> str:
    setting = _label_setting(client_id, label)
    if not setting:
        return default_action
    if setting.get("autoDelete"):
        return "trash"
    if setting.get("autoReply") or setting.get("prepareDraft"):
        return "draft"
    return default_action


def mark_as_read_for_client(client_id: str, label: str) -> bool:
    setting = _label_setting(client_id, label)
    return bool(setting and setting.get("markAsRead"))


def unread_delete_after_days_for_client(client_id: str, label: str) -> int | None:
    setting = _label_setting(client_id, label)
    if not setting:
        return None
    days = _int_setting(setting.get("autoDeleteUnreadAfterDays"), 0)
    return days if days > 0 else None


def canonical_label_key(label: str) -> str:
    label = str(label or "").strip()
    return LABEL_ALIASES.get(label, label)


def _label_setting(client_id: str, label: str) -> dict[str, Any] | None:
    canonical = canonical_label_key(label)
    for setting in normalized_labels_for_client(client_id):
        if setting.get("key") == canonical or setting.get("name") == canonical:
            return setting
    return None


def normalized_labels_for_client(client_id: str) -> list[dict[str, Any]]:
    labels = load_client_settings(client_id).get("labels", [])
    if not labels:
        return [dict(label) for label in DEFAULT_LABELS]
    return _with_canonical_defaults(labels)


def _with_canonical_defaults(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fallback_by_key = {label["key"]: label for label in DEFAULT_LABELS}
    grouped: dict[str, dict[str, Any]] = {}

    for raw in labels:
        key = canonical_label_key(str(raw.get("key") or raw.get("name") or "").strip())
        if key not in CANONICAL_LABEL_KEYS:
            continue
        fallback = fallback_by_key[key]
        if key not in grouped:
            grouped[key] = _sanitize_label(raw, fallback)

    return [grouped.get(label["key"], dict(label)) for label in DEFAULT_LABELS]


def _sanitize_label(label: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    key = fallback["key"]
    name = str(label.get("name", "")).strip() or fallback["name"]
    raw_key = str(label.get("key", "")).strip()
    if raw_key and raw_key != key and canonical_label_key(raw_key) == key:
        name = fallback["name"]
    color = str(label.get("color", "")).strip()
    description = str(label.get("description", "")).strip()
    return {
        "key": key,
        "name": name,
        "description": description if description and len(description) > 80 else fallback["description"],
        "color": color if re.fullmatch(r"#[0-9a-fA-F]{6}", color) else fallback["color"],
        "priority": _int_setting(label.get("priority"), fallback["priority"]),
        "prepareDraft": bool(label.get("prepareDraft")),
        "autoReply": bool(label.get("autoReply")),
        "autoDelete": bool(label.get("autoDelete")),
        "markAsRead": bool(label.get("markAsRead")),
        "autoDeleteUnreadAfterDays": _sanitize_unread_days(label.get("autoDeleteUnreadAfterDays")),
    }


def _sanitize_unread_days(value: Any) -> int | None:
    days = _int_setting(value, 0)
    if days <= 0:
        return None
    return min(365, max(1, days))


def _int_setting(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
