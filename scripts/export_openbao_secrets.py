from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key] = value
    return values


def env_value(values: dict[str, str], key: str, default: str = "") -> str:
    return os.getenv(key) or values.get(key, default)


def required(value: str, name: str) -> str:
    return value if value else f"<MANQUANT:{name}>"


def gmail_client_config(values: dict[str, str]) -> str:
    raw_path = env_value(values, "GMAIL_OAUTH_CLIENT_FILE", "./secrets/google-oauth-client.json")
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return f"<MANQUANT:{raw_path}>"
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def build_export(values: dict[str, str]) -> str:
    postgres_db = env_value(values, "POSTGRES_DB", "spidr_mail")
    postgres_user = env_value(values, "POSTGRES_USER", "spidr")
    postgres_password = env_value(values, "POSTGRES_PASSWORD", "spidr_dev_password")
    database_url = env_value(values, "DATABASE_URL", f"postgresql://{postgres_user}:{postgres_password}@postgres:5432/{postgres_db}")
    oauth_base_url = env_value(values, "OAUTH_BASE_URL", "")
    oauth_public_url = env_value(values, "OAUTH_PUBLIC_URL", oauth_base_url)
    frontend_base_url = env_value(values, "FRONTEND_BASE_URL", "")

    lines = [
        "# 1. Chiffrement et sécurité",
        f"token_encryption_key={required(env_value(values, 'TOKEN_ENCRYPTION_KEY'), 'TOKEN_ENCRYPTION_KEY')}",
        f"auth_secret={required(env_value(values, 'AUTH_SECRET'), 'AUTH_SECRET')}",
        "# 2. Base de données",
        f"postgres_db={postgres_db}",
        f"postgres_user={postgres_user}",
        f"postgres_password={required(postgres_password, 'POSTGRES_PASSWORD')}",
        f"database_url={required(database_url, 'DATABASE_URL')}",
        "# 3. Groq",
        f"groq_api_key={required(env_value(values, 'GROQ_API_KEY'), 'GROQ_API_KEY')}",
        "# 4. OAuth Microsoft",
        f"microsoft_client_id={required(env_value(values, 'MICROSOFT_CLIENT_ID'), 'MICROSOFT_CLIENT_ID')}",
        f"microsoft_client_secret={required(env_value(values, 'MICROSOFT_CLIENT_SECRET'), 'MICROSOFT_CLIENT_SECRET')}",
        "# 5. OAuth Gmail",
        f"gmail_client_config={gmail_client_config(values)}",
        "# 6. URLs Production",
        f"oauth_base_url={required(oauth_base_url, 'OAUTH_BASE_URL')}",
        f"oauth_public_url={required(oauth_public_url, 'OAUTH_PUBLIC_URL')}",
        f"frontend_base_url={required(frontend_base_url, 'FRONTEND_BASE_URL')}",
        "",
    ]
    return "\n".join(lines)


def missing_fields(export: str) -> list[str]:
    missing: list[str] = []
    for line in export.splitlines():
        if "<MANQUANT:" not in line:
            continue
        missing.append(line.split("<MANQUANT:", 1)[1].split(">", 1)[0])
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Export InboxPilot secrets for manual OpenBao migration.")
    parser.add_argument("--env-file", default=str(ROOT / ".env"), help="Path to the existing .env file.")
    parser.add_argument("--output", default=str(ROOT / "openbao-secrets.txt"), help="Destination file. Never commit it.")
    parser.add_argument("--force", action="store_true", help="Overwrite destination if it already exists.")
    parser.add_argument("--check", action="store_true", help="Only report missing fields. Does not write secrets.")
    args = parser.parse_args()

    values = parse_env_file(Path(args.env_file))
    export = build_export(values)
    missing = missing_fields(export)

    if args.check:
        if missing:
            print("Missing fields:", ", ".join(sorted(set(missing))))
            raise SystemExit(1)
        print("OK: all expected secrets are present.")
        return

    output = Path(args.output)
    if output.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing file: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(export, encoding="utf-8")
    try:
        output.chmod(0o600)
    except OSError:
        pass

    print(f"Export written: {output}")
    print("Secrets were not printed. Transfer this file through a secure channel, then delete it after migration.")
    if missing:
        print("Warning: missing fields:", ", ".join(sorted(set(missing))))


if __name__ == "__main__":
    main()
