#!/usr/bin/env python3
"""Atomically re-encrypt InboxPilot OAuth tokens and processing state."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


def read_key(path: Path) -> bytes:
    if not path.is_file():
        raise RuntimeError(f"Key file does not exist: {path}")
    if os.name != "nt" and path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise RuntimeError(f"Key file permissions are too broad: {path}")
    value = path.read_bytes().strip()
    Fernet(value)
    return value


def encrypted_files(data_dir: Path) -> list[Path]:
    files = list((data_dir / "tokens").glob("**/*.enc"))
    files.extend((data_dir / "state").glob("**/*.enc"))
    return sorted({path.resolve() for path in files if path.is_file()})


def rotate(data_dir: Path, old_key: bytes, new_key: bytes, backup_dir: Path, apply: bool) -> int:
    old = Fernet(old_key)
    new = Fernet(new_key)
    files = encrypted_files(data_dir)
    plaintexts: dict[Path, bytes] = {}

    for path in files:
        try:
            plaintext = old.decrypt(path.read_bytes())
            json.loads(plaintext)
        except (InvalidToken, json.JSONDecodeError) as exc:
            raise RuntimeError("At least one encrypted runtime file cannot be validated with the old key.") from exc
        plaintexts[path] = plaintext

    if not apply:
        print(f"Dry run successful: {len(files)} encrypted files can be rotated.")
        return len(files)
    if backup_dir.exists():
        raise RuntimeError("Backup directory already exists; refusing to overwrite it.")

    lock_path = data_dir / ".token-key-rotation.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    replaced: list[Path] = []
    try:
        backup_dir.mkdir(parents=True, mode=0o700)
        prepared: dict[Path, Path] = {}
        for path, plaintext in plaintexts.items():
            relative = path.relative_to(data_dir.resolve())
            backup = backup_dir / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)

            temporary = path.with_suffix(path.suffix + ".rotate")
            temporary.write_bytes(new.encrypt(plaintext))
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            if new.decrypt(temporary.read_bytes()) != plaintext:
                raise RuntimeError("Verification of a re-encrypted file failed.")
            prepared[path] = temporary

        for path, temporary in prepared.items():
            os.replace(temporary, path)
            replaced.append(path)
    except Exception:
        for path in replaced:
            backup = backup_dir / path.relative_to(data_dir.resolve())
            if backup.exists():
                shutil.copy2(backup, path)
        for temporary in data_dir.glob("**/*.rotate"):
            temporary.unlink(missing_ok=True)
        raise
    finally:
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)

    print(f"Rotation successful: {len(files)} encrypted files updated and verified.")
    print(f"Encrypted rollback copy retained in: {backup_dir}")
    return len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--old-key-file", required=True, type=Path)
    parser.add_argument("--new-key-file", required=True, type=Path)
    parser.add_argument("--backup-dir", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Apply the rotation; otherwise only validate.")
    args = parser.parse_args()

    try:
        old_key = read_key(args.old_key_file)
        new_key = read_key(args.new_key_file)
        if old_key == new_key:
            raise RuntimeError("Old and new encryption keys are identical.")
        rotate(args.data_dir.resolve(), old_key, new_key, args.backup_dir.resolve(), args.apply)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Rotation aborted: {exc}", file=sys.stderr)
        return 1
    finally:
        if "old_key" in locals():
            old_key = b""
        if "new_key" in locals():
            new_key = b""
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
