# InboxPilot - Secrets OpenBao

Liste des secrets **application uniquement** à stocker dans OpenBao/Vault pour InboxPilot.

> **Note importante** : Les tokens OAuth individuels des clients (Gmail/Outlook) sont générés au runtime lors du flux OAuth et stockés chiffrés dans PostgreSQL. Ils ne sont **pas** stockés dans OpenBao.

---

## 1. Chiffrement et sécurité

### `secret/inboxpilot/common`

```bash
# Générer une clé Fernet (44 caractères base64)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Générer un secret JWT (64 caractères)
openssl rand -base64 48

# Stocker dans OpenBao
bao kv put secret/inboxpilot/common \
  token_encryption_key="<FERNET_KEY_44_CHARS>" \
  auth_secret="<RANDOM_64_CHARS>"
```

**Usage** :
- `token_encryption_key` : Chiffre les tokens OAuth des utilisateurs dans PostgreSQL
- `auth_secret` : Signe les sessions JWT du frontend

---

## 2. Base de données

### `secret/inboxpilot/database`

```bash
# Générer un mot de passe fort
openssl rand -base64 32

# Stocker dans OpenBao
bao kv put secret/inboxpilot/database \
  postgres_db="spidr_mail" \
  postgres_user="spidr" \
  postgres_password="<STRONG_PASSWORD>" \
  database_url="postgresql://spidr:<PASSWORD>@postgres:5432/spidr_mail"
```

---

## 3. Services tiers

### `secret/inboxpilot/groq`

```bash
# Obtenir la clé sur https://console.groq.com/keys
bao kv put secret/inboxpilot/groq \
  api_key="gsk_<YOUR_GROQ_API_KEY>"
```

---

## 4. OAuth Applications

### 4.1 Microsoft (Azure AD)

Credentials de **votre application Azure AD**, pas des utilisateurs finaux.

```bash
bao kv put secret/inboxpilot/oauth/microsoft \
  client_id="<MICROSOFT_CLIENT_ID>" \
  client_secret="<MICROSOFT_CLIENT_SECRET>"
```

**Configuration Azure AD** :
1. Aller sur https://portal.azure.com/
2. `Azure Active Directory` → `App registrations` → `New registration`
3. Name: `InboxPilot`
4. Supported account types: `Accounts in any organizational directory and personal Microsoft accounts`
5. Redirect URI:
   - Dev: `http://localhost:8080/oauth/hotmail/callback`
   - Prod: `https://oauth.spidr.fr/oauth/hotmail/callback`
6. `Certificates & secrets` → `New client secret`
7. `API permissions` → `Microsoft Graph` → Delegated:
   - `Mail.ReadWrite`
   - `User.Read`
   - `offline_access`

### 4.2 Gmail (Google Cloud)

Credentials de **votre application Google Cloud**, pas des utilisateurs finaux.

```bash
# Le fichier JSON complet de Google Cloud Console
bao kv put secret/inboxpilot/oauth/gmail \
  client_config='{"web":{"client_id":"...","project_id":"...","auth_uri":"...","token_uri":"...","client_secret":"...","redirect_uris":[...]}}'
```

**Configuration Google Cloud** :
1. Aller sur https://console.cloud.google.com/
2. Créer ou sélectionner un projet
3. Activer l'API Gmail (`APIs & Services` → `Enable APIs`)
4. `Credentials` → `Create Credentials` → `OAuth client ID`
5. Type: `Web application`
6. Authorized redirect URIs:
   - Dev: `http://localhost:8080/oauth/gmail/callback`
   - Prod: `https://oauth.spidr.fr/oauth/gmail/callback`
7. Télécharger le fichier JSON

---

## 5. URLs

```bash
bao kv put secret/inboxpilot/urls \
  oauth_base_url="<BASE_URL>" \
  oauth_public_url="<PUBLIC_URL>" \
  frontend_base_url="<FRONTEND_URL>"
```

**Exemples** :
- Dev local : `http://localhost:8080`, `http://localhost:3000`
- Prod : `https://oauth.spidr.fr`, `https://app.spidr.fr`

---

## Récupération des secrets

### Lire tous les secrets d'un path

```bash
bao kv get secret/inboxpilot/common
bao kv get -field=token_encryption_key secret/inboxpilot/common
```

### Lister les secrets

```bash
bao kv list secret/inboxpilot/
```

### Mettre à jour un champ sans écraser les autres

```bash
bao kv patch secret/inboxpilot/common \
  auth_secret="<NEW_VALUE>"
```

---

## Script d'export vers .env

Le script `scripts/load-secrets.sh` peut charger tous ces secrets dans un fichier `.env` :

```bash
./scripts/load-secrets.sh dev   # Pour development
./scripts/load-secrets.sh prod  # Pour production
```

---

## Checklist d'initialisation

Avant de démarrer le projet :

- [ ] Générer `token_encryption_key` (Fernet)
- [ ] Générer `auth_secret` (64 chars)
- [ ] Générer `postgres_password` (32 chars)
- [ ] Créer l'application OAuth Gmail sur Google Cloud Console
- [ ] Créer l'application OAuth Microsoft sur Azure AD
- [ ] Obtenir la clé API Groq
- [ ] Stocker tous les secrets dans OpenBao
- [ ] Exécuter `scripts/load-secrets.sh dev`
- [ ] Vérifier que `.env` est bien généré
- [ ] Vérifier que `secrets/google-oauth-client.json` existe
- [ ] Démarrer les services: `docker-compose up -d`

---

## Sécurité

- ✅ `.env` et `secrets/` sont dans `.gitignore`
- ✅ Les tokens OAuth des utilisateurs sont chiffrés dans PostgreSQL avec `token_encryption_key`
- ✅ Les secrets sont uniquement dans OpenBao, jamais commités
- ⚠️ Rotation régulière des secrets (tous les 90 jours)
- ⚠️ Backup chiffré des secrets critiques dans un coffre-fort (1Password, LastPass, etc.)
