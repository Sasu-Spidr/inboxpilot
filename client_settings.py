from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

DEFAULT_LABELS: list[dict[str, Any]] = [
    {"key": "À répondre", "name": "À répondre", "description": "Un humain identifiable attend une réponse écrite.", "color": "#0d9488", "priority": 100, "prepareDraft": True, "autoReply": False, "autoDelete": False},
    {"key": "À traiter", "name": "À traiter", "description": "Action manuelle non limitée à une réponse.", "color": "#8b8b7a", "priority": 90, "prepareDraft": False, "autoReply": False, "autoDelete": False},
    {"key": "À lire", "name": "À lire", "description": "Information destinée à un humain, à lire ou conserver.", "color": "#3b82f6", "priority": 60, "prepareDraft": False, "autoReply": False, "autoDelete": False},
    {"key": "Notification", "name": "Notification", "description": "Message généré par une machine, sans action manuelle.", "color": "#22c55e", "priority": 40, "prepareDraft": False, "autoReply": False, "autoDelete": False},
    {"key": "Commercial", "name": "Commercial", "description": "Newsletter, promotion, prospection ou offre commerciale.", "color": "#fb7185", "priority": 20, "prepareDraft": False, "autoReply": False, "autoDelete": False},
]

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
    if setting.get("autoDelete"):
        return "trash"
    if setting.get("autoReply") or setting.get("prepareDraft"):
        return "draft"
    return default_action


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
    return labels


def _int_setting(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
