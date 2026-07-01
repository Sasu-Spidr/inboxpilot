# Connexion client Gmail / Hotmail

Le client n'a pas besoin de GitHub, de terminal, de fichier `.env`, de token ou de Docker.

Il utilise uniquement l'interface web.

## Parcours client

1. Ouvrir l'URL du front :

```text
https://app.spidr.fr
```

En test local/ngrok :

```text
https://votre-url-ngrok.ngrok-free.dev
```

2. Créer son compte avec :

- prénom et nom ;
- email ;
- mot de passe.

3. Se connecter.

4. Dans l'espace client, cliquer sur :

- `Connecter Gmail`
- ou `Connecter Hotmail / Outlook`

5. Accepter les permissions OAuth.

6. Revenir sur l'espace client : le compte apparaît comme connecté.

## Ce que fait l'agent

Une fois le worker lancé côté serveur, l'agent :

- lit les nouveaux emails non lus ;
- classe les emails ;
- applique les labels/catégories ;
- prépare un brouillon quand une réponse est nécessaire ;
- signe le brouillon avec le prénom et nom du client ;
- marque ou déplace les emails selon les règles ;
- n'envoie jamais automatiquement.

## Sécurité

- L'authentification du front utilise PostgreSQL.
- Les tokens OAuth sont stockés côté serveur.
- Les tokens OAuth sont chiffrés avec Fernet.
- Les secrets restent dans les variables d'environnement ou les secrets GitHub/VPS.
- Le client ne reçoit jamais de secret technique.
