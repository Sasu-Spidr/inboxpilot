# SPIDR Mail Agent

Agent mail léger pour Gmail et Hotmail/Outlook.

Il lit les emails non lus, les classe avec l’IA, applique un label/catégorie, déplace si nécessaire, et crée des brouillons de réponse. Il n’envoie jamais d’email automatiquement.

Pas de frontend. Pas de dashboard. Pas de CRM. Pas de FastAPI. Pas de PostgreSQL.

## Fonctionnement

Le worker fait simplement :

```text
Gmail / Hotmail OAuth
↓
Lecture des emails non lus
↓
Classification IA
↓
Application label / catégorie
↓
Action selon rules.yaml
↓
Brouillon si nécessaire
↓
Marquage traité anti-doublon
```

Les tokens OAuth et l’état anti-doublon sont chiffrés avec Fernet.

## Fichiers importants

```text
config/settings.yaml   # clients, boîtes mail, Groq, polling
config/rules.yaml      # actions par label
config/labels.yaml     # labels Gmail / catégories Outlook
.env                   # clés API et variables sensibles
data/tokens/           # tokens OAuth chiffrés
data/state/            # état anti-doublon chiffré
logs/                  # logs
```

## Installation locale

```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory -Force secrets\exuvie, data\tokens, data\state, logs
pip install -r requirements.txt
```

Générer la clé Fernet :

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

À mettre dans `.env` :

```env
GROQ_API_KEY=...
EXUVIE_MICROSOFT_CLIENT_ID=...
TOKEN_ENCRYPTION_KEY=...
```

## Authentification

Lancer l’authentification des boîtes activées dans `config/settings.yaml` :

```powershell
python main.py --authenticate
```

Pour Gmail, placer le fichier OAuth ici :

```text
secrets/exuvie/gmail-client-secret.json
```

Pour Hotmail, mettre le client ID Microsoft dans `.env` :

```env
EXUVIE_MICROSOFT_CLIENT_ID=...
```

## Lancer le worker

Un seul cycle :

```powershell
python main.py --once
```

En continu :

```powershell
python main.py
```

## Docker

Créer les dossiers :

```powershell
New-Item -ItemType Directory -Force secrets\exuvie, data\tokens, data\state, logs
```

Lancer :

```bash
docker compose up -d --build
docker compose logs -f mail-agent
```

Arrêter :

```bash
docker compose down
```

Voir l’état :

```bash
docker compose ps
```

## Déploiement VPS

Copier sur le VPS :

```text
.env
config/
secrets/
data/tokens/
data/state/
docker-compose.yml
Dockerfile
*.py
requirements.txt
```

Puis :

```bash
docker compose up -d --build
docker compose logs -f mail-agent
```

## Tests

```powershell
pip install -r requirements.txt
pytest -q --basetemp .pytest_tmp
```

## Validation rapide

Gmail :

- envoyer un email test
- vérifier le label
- vérifier le brouillon
- vérifier qu’il n’y a pas de doublon au cycle suivant

Hotmail :

- envoyer un email test
- vérifier la catégorie
- vérifier le brouillon
- vérifier qu’il n’y a pas de doublon au cycle suivant

## Notes

- Les règles se changent dans `config/rules.yaml`.
- Les labels se changent dans `config/labels.yaml`.
- Les clients et boîtes se changent dans `config/settings.yaml`.
- Le système fonctionne par polling.
- Les webhooks sont préparés côté architecture mais pas encore activés.
