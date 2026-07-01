# SPIDR Mail Agent

Agent mail léger pour Gmail et Hotmail/Outlook.

Il lit les emails non lus, les classe avec l'IA, applique un label/catégorie, déplace si nécessaire, et crée des brouillons de réponse. Il n'envoie jamais d'email automatiquement.

Le front client est en Next.js avec authentification et PostgreSQL.

## Commandes utiles

Tester :

```powershell
pytest -q --basetemp .pytest_run_tmp
```

Lancer l'ensemble :

```bash
docker compose up -d --build postgres frontend oauth-onboarding mail-agent
```

Voir les logs :

```bash
docker compose logs -f frontend
docker compose logs -f oauth-onboarding
docker compose logs -f mail-agent
```

## Interface client

En local :

```text
http://localhost:3000
```

Si le port 3000 est déjà pris :

```powershell
$env:FRONTEND_HOST_PORT='3010'; docker compose up -d frontend
```

Puis :

```text
http://localhost:3010
```

Le client peut :

- créer son compte avec nom, email et mot de passe ;
- se connecter avec email et mot de passe ;
- connecter Gmail ;
- connecter Hotmail/Outlook ;
- voir les boîtes déjà connectées.

## Brouillons

Les brouillons sont courts, professionnels et contextuels.

La signature utilise le prénom et nom saisis par le client à l'inscription.

## Configuration

- Front/auth : PostgreSQL
- Registre technique clients : `data/clients/clients.yaml`
- Labels : `config/labels.yaml`
- Règles : `config/rules.yaml`
- Tokens OAuth chiffrés : `data/tokens/`

Les secrets restent dans `.env`, GitHub Secrets ou les variables du VPS. Ils ne doivent jamais être commit.
