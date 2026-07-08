from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


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
    for setting in load_client_settings(client_id).get("labels", []):
        key = str(setting.get("key", "")).strip()
        name = str(setting.get("name", "")).strip()
        color = str(setting.get("color", "")).strip()
        if key and name and re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            settings.append({"key": key, "name": name, "color": color})
    return settings


def managed_label_names_for_client(client_id: str) -> list[str]:
    names: list[str] = []
    for setting in load_client_settings(client_id).get("labels", []):
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
    for setting in load_client_settings(client_id).get("labels", []):
        if setting.get("key") == label or setting.get("name") == label:
            return setting
    return None
