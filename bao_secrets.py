from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

import requests


class BaoSecretError(RuntimeError):
    """Raised when a required runtime secret cannot be read safely."""


SECRET_LOCATIONS: dict[str, tuple[str, str]] = {
    "GROQ_API_KEY": ("secret/data/inboxpilot/groq", "api_key"),
    "TOKEN_ENCRYPTION_KEY": ("secret/data/inboxpilot/crypto", "token_encryption_key"),
    "MICROSOFT_CLIENT_ID": ("secret/data/inboxpilot/oauth/microsoft", "client_id"),
    "MICROSOFT_CLIENT_SECRET": ("secret/data/inboxpilot/oauth/microsoft", "client_secret"),
    "GMAIL_CLIENT_CONFIG": ("secret/data/inboxpilot/oauth/gmail", "client_config"),
}

_VARIABLE_PATTERN = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")


class BaoSecrets:
    def __init__(
        self,
        agent_addr: str | None = None,
        *,
        timeout_seconds: float = 5.0,
        session: Any | None = None,
    ) -> None:
        self.agent_addr = (agent_addr or os.getenv("BAO_AGENT_ADDR") or "http://bao-agent-worker:8100").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self._path_cache: dict[str, Mapping[str, Any]] = {}
        self._secret_cache: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        if name not in SECRET_LOCATIONS:
            raise BaoSecretError(f"Unknown OpenBao secret name: {name}")
        if name in self._secret_cache:
            return self._secret_cache[name]

        path, field = SECRET_LOCATIONS[name]
        values = self._read_path(path)
        value = values.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise BaoSecretError(f"Required OpenBao secret is missing: {name} ({path} field {field})")
        self._secret_cache[name] = value
        return value

    def load_required(self) -> dict[str, Any]:
        values = {name: self.get(name) for name in SECRET_LOCATIONS}
        values["GMAIL_CLIENT_CONFIG"] = parse_gmail_client_config(values["GMAIL_CLIENT_CONFIG"])
        self._secret_cache["GMAIL_CLIENT_CONFIG"] = values["GMAIL_CLIENT_CONFIG"]
        return values

    def _read_path(self, path: str) -> Mapping[str, Any]:
        if path in self._path_cache:
            return self._path_cache[path]
        url = f"{self.agent_addr}/v1/{path.lstrip('/')}"
        try:
            response = self.session.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise BaoSecretError(f"Unable to read required OpenBao path {path} through {self.agent_addr}: {exc}") from exc
        try:
            payload = response.json()
            values = payload["data"]["data"]
        except (ValueError, KeyError, TypeError) as exc:
            raise BaoSecretError(f"Invalid OpenBao response for required path {path}") from exc
        if not isinstance(values, Mapping):
            raise BaoSecretError(f"Invalid OpenBao secret payload for required path {path}")
        self._path_cache[path] = values
        return values


def parse_gmail_client_config(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        config = dict(value)
    elif isinstance(value, str):
        try:
            config = json.loads(value)
        except json.JSONDecodeError as exc:
            raise BaoSecretError("GMAIL_CLIENT_CONFIG is not valid JSON") from exc
    else:
        raise BaoSecretError("GMAIL_CLIENT_CONFIG must be a JSON object")
    if not isinstance(config, dict) or not ({"web", "installed"} & set(config)):
        raise BaoSecretError("GMAIL_CLIENT_CONFIG must contain a web or installed OAuth client")
    return config


def resolve_settings_text(raw: str, secrets: Mapping[str, Any]) -> str:
    """Resolve secret placeholders from OpenBao and ordinary variables from the environment."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        if name in SECRET_LOCATIONS:
            value = secrets.get(name)
            if value is None or isinstance(value, Mapping):
                raise BaoSecretError(f"Required OpenBao secret is missing or invalid: {name}")
            return str(value)
        return os.environ.get(name, match.group(0))

    return _VARIABLE_PATTERN.sub(replace, raw)


def attach_runtime_secrets(settings: dict[str, Any], resolver: BaoSecrets | Any | None = None) -> dict[str, Any]:
    active_resolver = resolver or BaoSecrets()
    values = active_resolver.load_required()
    settings["_runtime_secrets"] = values
    return settings


def runtime_secret(settings: Mapping[str, Any], name: str) -> Any:
    if name not in SECRET_LOCATIONS:
        return os.getenv(name, "")
    values = settings.get("_runtime_secrets")
    if not isinstance(values, Mapping):
        raise BaoSecretError(f"OpenBao runtime secrets were not loaded before requesting {name}")
    value = values.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise BaoSecretError(f"Required OpenBao secret is missing at runtime: {name}")
    return value


def load_yaml_settings(path: str, resolver: BaoSecrets | Any | None = None) -> dict[str, Any]:
    import yaml

    raw = Path(path).read_text(encoding="utf-8")
    active_resolver = resolver or BaoSecrets()
    values = active_resolver.load_required()
    settings = yaml.safe_load(resolve_settings_text(raw, values)) or {}
    settings["_runtime_secrets"] = values
    return settings
