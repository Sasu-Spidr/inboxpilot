# Connexion Gmail / Hotmail

Cette page explique comment connecter une boîte mail à l’agent.

Le client n’a pas besoin de GitHub, de terminal, de fichier `.env`, ni de token.

## Gmail

1. Ouvrez le lien reçu, par exemple :

```text
https://connect.example.com/connect/gmail?client=collegue&account=main
```

2. Connectez-vous au compte Gmail à autoriser.
3. Acceptez les permissions Gmail demandées.
4. Quand la page affiche :

```text
Connexion Gmail réussie
```

vous pouvez fermer l’onglet.

## Hotmail / Outlook

1. Ouvrez le lien reçu, par exemple :

```text
https://connect.example.com/connect/hotmail?client=collegue&account=main
```

2. Connectez-vous au compte Microsoft / Outlook / Hotmail.
3. Acceptez les permissions demandées.
4. Quand la page affiche :

```text
Connexion Hotmail / Outlook réussie
```

vous pouvez fermer l’onglet.

## Ce que l’agent fait

- lit les emails non lus ;
- classe les emails ;
- applique des labels ou catégories ;
- crée des brouillons si une réponse est nécessaire ;
- déplace les newsletters/spams selon les règles ;
- n’envoie jamais automatiquement.

## Sécurité

Les tokens OAuth sont chiffrés côté serveur.

Le client ne reçoit jamais de token et ne doit jamais copier de secret.
