# Secrets OpenBao InboxPilot

InboxPilot utilise deux instances indépendantes : `bao-dev` et `bao-prod`.
Un secret de production ne doit jamais être copié dans l'instance dev.

## Chemins et zones

| Chemin CLI | Champs | Zone autorisée |
|---|---|---|
| `secret/inboxpilot/frontend` | `auth_secret`, `turnstile_secret_key`, `signup_access_code` | frontend |
| `secret/inboxpilot/database` | `database_url` | frontend |
| `secret/inboxpilot/crypto` | `token_encryption_key` | worker |
| `secret/inboxpilot/groq` | `api_key` | worker |
| `secret/inboxpilot/oauth/gmail` | `client_id`, `client_secret` | worker |
| `secret/inboxpilot/oauth/microsoft` | `client_id`, `client_secret` | worker |

Le champ `smoke_gmail_token_enc_b64` existe uniquement dans
`secret/inboxpilot/oauth/gmail` sur **dev**. Il contient le jeton chiffré de la
boîte technique utilisée par `.github/workflows/mailbox-smoke.yml`. Ce jeton
n'est pas un jeton client de production.

Les URLs, identifiants publics et réglages fonctionnels restent des variables
GitHub d'environment. `TURNSTILE_SITE_KEY` est public ;
`turnstile_secret_key` reste dans OpenBao.

## Mise à jour sûre

Toujours utiliser `bao kv patch` pour ajouter ou modifier un champ sans
effacer les autres :

```bash
bao kv patch secret/inboxpilot/oauth/gmail \
  smoke_gmail_token_enc_b64='<JETON_CHIFFRE_BASE64>'
```

Ne jamais écrire une valeur sur la ligne de commande si l'historique du shell
est conservé. Préférer une saisie protégée, un fichier temporaire `0600` ou le
mécanisme sécurisé de l'infrastructure. Ne jamais utiliser `bao kv put` pour
modifier un seul champ : cette commande remplace l'ensemble du secret.

## Accès runtime

- `bao-agent-frontend` peut lire uniquement `frontend` et `database` ;
- `bao-agent-worker` peut lire uniquement `crypto`, `groq` et `oauth/*` ;
- les applications interrogent leur agent sans recevoir de token OpenBao ;
- les agents s'authentifient avec les fichiers placés dans
  `/etc/inboxpilot/<env>/<zone>/{role_id,secret_id}`.

Les chemins API contiennent `/data/`, par exemple :
`secret/data/inboxpilot/groq`. Les chemins CLI `bao kv` ne le contiennent pas.

## Smoke test CI

Le workflow smoke utilise GitHub OIDC avec l'audience
`https://github.com/Sasu-Spidr/inboxpilot`, puis :

1. obtient un token court via `inboxpilot-jwt-dev` ;
2. demande un `secret_id` response-wrapped pour `inboxpilot-dev` ;
3. consomme une seule fois le wrapping token ;
4. se connecte avec le `role_id` public de la variable
   `INBOXPILOT_ROLE_ID` ;
5. lit les secrets dev avec un token éphémère ;
6. détruit les fichiers temporaires à la fin du job.

Il n'utilise aucun secret métier GitHub.

## Rotation

- `api_key`, secrets OAuth et `auth_secret` : créer la nouvelle valeur chez le
  fournisseur, l'écrire dans le bon coffre, redéployer, vérifier, puis révoquer
  l'ancienne ;
- `auth_secret` invalide toutes les sessions web ;
- `token_encryption_key` ne doit jamais être simplement remplacée : suivre
  [TOKEN_ENCRYPTION_KEY_ROTATION.md](TOKEN_ENCRYPTION_KEY_ROTATION.md) afin de
  rechiffrer les jetons avant la bascule ;
- `database_url` sera remplacée par des identifiants dynamiques après la
  migration PostgreSQL côté infrastructure.
