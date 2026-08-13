# InboxPilot - Récupérer les secrets OpenBao en Python

## Installation

```bash
pip install hvac
```

---

## Connexion

```python
import hvac
import os

client = hvac.Client(
    url=os.getenv("BAO_ADDR", "http://127.0.0.1:8200"),
    token=os.getenv("BAO_TOKEN")
)

assert client.is_authenticated(), "Échec d'authentification OpenBao"
```

---

## Récupérer un secret

**C'est toujours la même méthode, seul le path change** :

```python
secret = client.secrets.kv.v2.read_secret_version(path="inboxpilot/XXX")["data"]["data"]
```

### Exemples

```python
# Chiffrement
common = client.secrets.kv.v2.read_secret_version(path="inboxpilot/common")["data"]["data"]
TOKEN_ENCRYPTION_KEY = common["token_encryption_key"]
AUTH_SECRET = common["auth_secret"]

# Database
db = client.secrets.kv.v2.read_secret_version(path="inboxpilot/database")["data"]["data"]
DATABASE_URL = db["database_url"]

# Groq
groq = client.secrets.kv.v2.read_secret_version(path="inboxpilot/groq")["data"]["data"]
GROQ_API_KEY = groq["api_key"]

# OAuth Microsoft
ms = client.secrets.kv.v2.read_secret_version(path="inboxpilot/oauth/microsoft")["data"]["data"]
MICROSOFT_CLIENT_ID = ms["client_id"]
MICROSOFT_CLIENT_SECRET = ms["client_secret"]

# OAuth Gmail
gmail = client.secrets.kv.v2.read_secret_version(path="inboxpilot/oauth/gmail")["data"]["data"]
GMAIL_CLIENT_CONFIG = gmail["client_config"]  # JSON string

# URLs
urls = client.secrets.kv.v2.read_secret_version(path="inboxpilot/urls")["data"]["data"]
OAUTH_BASE_URL = urls["oauth_base_url"]
FRONTEND_BASE_URL = urls["frontend_base_url"]
```

---

## Fonction utilitaire

```python
import hvac
import os
import json

def load_secrets():
    """Charge tous les secrets OpenBao en une fois"""

    client = hvac.Client(
        url=os.getenv("BAO_ADDR", "http://127.0.0.1:8200"),
        token=os.getenv("BAO_TOKEN")
    )

    if not client.is_authenticated():
        raise RuntimeError("OpenBao authentication failed")

    # Helper
    def get(path):
        return client.secrets.kv.v2.read_secret_version(path=path)["data"]["data"]

    # Récupérer tous les secrets
    common = get("inboxpilot/common")
    db = get("inboxpilot/database")
    groq = get("inboxpilot/groq")
    ms = get("inboxpilot/oauth/microsoft")
    gmail = get("inboxpilot/oauth/gmail")
    urls = get("inboxpilot/urls")

    gmail_config = json.loads(gmail["client_config"])

    return {
        # Chiffrement
        "token_encryption_key": common["token_encryption_key"],
        "auth_secret": common["auth_secret"],

        # Database
        "database_url": db["database_url"],

        # Groq
        "groq_api_key": groq["api_key"],

        # OAuth Microsoft
        "microsoft_client_id": ms["client_id"],
        "microsoft_client_secret": ms["client_secret"],

        # OAuth Gmail
        "gmail_client_id": gmail_config["web"]["client_id"],
        "gmail_client_secret": gmail_config["web"]["client_secret"],
        "gmail_config": gmail_config,

        # URLs
        "oauth_base_url": urls["oauth_base_url"],
        "frontend_base_url": urls["frontend_base_url"],
    }

# Usage
secrets = load_secrets()
```

---

## Variables d'environnement requises

```bash
export BAO_ADDR="http://127.0.0.1:8200"
export BAO_TOKEN="hvs.xxxxx"
```
