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
    {"key": "À traiter", "name": "À traiter", "description": "Élément important à gérer manuellement : facture, contrat, document, paiement, accès ou problème de compte.", "color": "#8b8b7a", "priority": 110, "prepareDraft": True, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "À répondre", "name": "À répondre", "description": "Message qui demande clairement une réponse humaine ou une action de réponse commerciale.", "color": "#0d9488", "priority": 100, "prepareDraft": True, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Relance", "name": "Relance", "description": "Suivi ou rappel demandant explicitement de revenir vers une personne ou de confirmer une action.", "color": "#f97316", "priority": 95, "prepareDraft": True, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Commentaire", "name": "Commentaire", "description": "Avis, remarque, mention ou retour collaboratif à lire, sans demande d'action immédiate.", "color": "#eab308", "priority": 80, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "FYI", "name": "FYI", "description": "Information utile à conserver ou lire rapidement, sans urgence, réponse attendue ni caractère commercial évident.", "color": "#64748b", "priority": 70, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Notification", "name": "Notification", "description": "Alerte automatique liée à un compte, une application, un code, la sécurité ou un service.", "color": "#22c55e", "priority": 60, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Mise à jour de réunion", "name": "Mise à jour de réunion", "description": "Invitation, rappel, acceptation, annulation ou modification de réunion, calendrier ou visioconférence.", "color": "#93c5fd", "priority": 50, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Newsletter", "name": "Newsletter", "description": "Contenu éditorial récurrent : actualités, digest, bulletin, résumé hebdomadaire ou mensuel.", "color": "#fed7aa", "priority": 40, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Marketing", "name": "Marketing", "description": "Prospection, publicité, promotion, offre commerciale, invitation à acheter ou message d'acquisition.", "color": "#fb7185", "priority": 30, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "Traité", "name": "Traité", "description": "Message déjà résolu, confirmé, terminé ou ne nécessitant plus aucune action particulière.", "color": "#a78bfa", "priority": 20, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
    {"key": "En attente de réponse", "name": "En attente de réponse", "description": "Conversation où une réponse, une confirmation ou un retour externe est encore attendu.", "color": "#44403c", "priority": 10, "prepareDraft": False, "autoReply": False, "autoDelete": False, "markAsRead": False, "autoDeleteUnreadAfterDays": None},
]

OLD_DEFAULT_DESCRIPTIONS = {
    "Un humain identifiable attend une réponse écrite.",
    "Action manuelle non limitée à une réponse.",
    "Information destinée à un humain, à lire ou conserver.",
    "Message généré par une machine, sans action manuelle.",
    "Newsletter, promotion, prospection ou offre commerciale.",
    "Un humain identifiable attend une réponse écrite : question directe, demande d'info/de devis, rappel ou relance demandant un retour.",
    "Action manuelle non limitée à une réponse : payer, signer, valider un document, gérer un accès, un compte ou une opération.",
    "Information destinée à un humain, à lire ou conserver, sans action attendue : FYI, mise au courant, commentaire ou mention collaborative.",
    "Message généré par une machine : alerte, code, reçu, confirmation transactionnelle, rappel ou événement calendaire sans action manuelle.",
    "Newsletter, promotion, prospection, publicité, offre commerciale ou envoi de masse. Ne supprime jamais par défaut.",
}

LEGACY_DEFAULT_KEYS = {
    "À traiter",
    "À répondre",
    "Relance",
    "Commentaire",
    "FYI",
    "Notification",
    "Mise à jour de réunion",
    "Newsletter",
    "Marketing",
    "Traité",
    "En attente de réponse",
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
    keys: list[str] = []
    for setting in normalized_labels_for_client(client_id):
        key = str(setting.get("key", "")).strip()
        if key and key not in keys:
            keys.append(key)
    return keys


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
    if str(setting.get("key", "")).strip() in {"Marketing", "Newsletter"}:
        return "draft" if setting.get("autoReply") or setting.get("prepareDraft") else default_action
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
    if str(setting.get("key", "")).strip() in {"Marketing", "Newsletter"}:
        return None
    days = _int_setting(setting.get("autoDeleteUnreadAfterDays"), 0)
    return days if days > 0 else None


def _label_setting(client_id: str, label: str) -> dict[str, Any] | None:
    for setting in normalized_labels_for_client(client_id):
        if setting.get("key") == label or setting.get("name") == label:
            return setting
    return None


def normalized_labels_for_client(client_id: str) -> list[dict[str, Any]]:
    labels = load_client_settings(client_id).get("labels", [])
    if not labels:
        return DEFAULT_LABELS
    keys = [str(setting.get("key", "")).strip() for setting in labels if str(setting.get("key", "")).strip()]
    if len(keys) >= 8 and all(key in LEGACY_DEFAULT_KEYS for key in keys):
        return DEFAULT_LABELS
    return _with_missing_default_labels([_normalize_default_description(setting) for setting in labels])


def _with_missing_default_labels(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(labels)
    present = {
        value
        for setting in merged
        for value in (str(setting.get("key", "")).strip(), str(setting.get("name", "")).strip())
        if value
    }
    for default_label in DEFAULT_LABELS:
        key = str(default_label.get("key", "")).strip()
        name = str(default_label.get("name", "")).strip()
        if key in present or name in present:
            continue
        merged.append(dict(default_label))
        present.add(key)
        present.add(name)
    return merged


def _normalize_default_description(setting: dict[str, Any]) -> dict[str, Any]:
    key = str(setting.get("key", "")).strip()
    description = str(setting.get("description", "")).strip()
    if key not in CEO_LABEL_DESCRIPTIONS or description not in OLD_DEFAULT_DESCRIPTIONS:
        return setting
    return {**setting, "description": CEO_LABEL_DESCRIPTIONS[key]}


def _int_setting(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
