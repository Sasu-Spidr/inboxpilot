#!/usr/bin/env python3
"""Verify that an OpenBao instance has at least one enabled audit device."""
from __future__ import annotations

import argparse
import json
import stat
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True)
    parser.add_argument("--token-file", required=True, type=Path)
    args = parser.parse_args()

    if not args.token_file.is_file():
        raise SystemExit("The OpenBao admin token file does not exist.")
    if args.token_file.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise SystemExit("The OpenBao admin token file must not be accessible by group or others.")
    token = args.token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("The OpenBao admin token file is empty.")

    request = urllib.request.Request(
        args.address.rstrip("/") + "/v1/sys/audit",
        headers={"X-Vault-Token": token},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Unable to list OpenBao audit devices: HTTP {exc.code}") from exc
    finally:
        token = ""

    devices = payload.get("data", payload)
    enabled = [name for name, value in devices.items() if isinstance(value, dict)]
    if not enabled:
        raise SystemExit("No OpenBao audit device is enabled.")
    print("Enabled OpenBao audit devices: " + ", ".join(sorted(enabled)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
