# InboxPilot

livrable Exuvie d'InboxPilot.

Cette branche contient uniquement le nécessaire pour lancer l'application :

- page de connexion et création de compte ;
- dashboard client ;
- configuration des libellés par boîte mail ;
- connexion Gmail et Outlook/Hotmail ;
- agent de tri, labellisation et brouillons ;
- Docker Compose avec PostgreSQL, frontend, agent et serveur OAuth.


## Installation locale

Depuis la racine du projet :

```bash
cp .env.example .env
mkdir -p secrets data logs
```

Remplissez ensuite `.env` avec vos valeurs.

Placez le fichier OAuth Gmail ici :

```text
secrets/google-oauth-client.json
```

Puis lancez :

```bash
docker compose up -d --build
```

URLs locales :

- Frontend : `http://localhost:3000`
- OAuth : `http://localhost:8080`

## Callbacks OAuth

En local :

- Gmail : `http://localhost:8080/oauth/gmail/callback`
- Outlook / Hotmail : `http://localhost:8080/oauth/hotmail/callback`

En production Exuvie, adaptez selon le domaine utilisé, par exemple :

- Gmail : `https://inboxpilot-exuvie.mallow-hub.tech/oauth/gmail/callback`
- Outlook / Hotmail : `https://inboxpilot-exuvie.mallow-hub.tech/oauth/hotmail/callback`

## Variables importantes

- `TOKEN_ENCRYPTION_KEY` chiffre les tokens OAuth stockés dans `data/tokens`.
- `AUTH_SECRET` signe les sessions de connexion.
- `DATABASE_URL` pointe vers PostgreSQL.
- `GROQ_API_KEY` permet à l'agent d'appeler le modèle IA.
- `MICROSOFT_CLIENT_ID` et `MICROSOFT_CLIENT_SECRET` servent à la connexion Outlook/Hotmail.

## Mise à jour

```bash
git pull origin livraison_exuvie
docker compose up -d --build
```
