"""Encrypted, local-only OAuth token storage."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken


class TokenStore:
    def __init__(self, key: str):
        if not key:
            raise ValueError("TOKEN_ENCRYPTION_KEY is required (generate it with Fernet.generate_key()).")
        try:
            self.fernet = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise ValueError("TOKEN_ENCRYPTION_KEY must be a valid Fernet key.") from exc

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode()

    def load(self, filename: str) -> dict | None:
        path = Path(filename)
        if not path.exists():
            return None
        try:
            return json.loads(self.fernet.decrypt(path.read_bytes()))
        except (InvalidToken, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot decrypt OAuth token file: {path}") from exc

    def save(self, filename: str, token: dict) -> None:
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = self.fernet.encrypt(json.dumps(token).encode())
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(encrypted)
        os.replace(tmp, path)

