# Checklist déploiement sécurité

## Avant déploiement

- Vérifier que `PUBLIC_SIGNUP_ENABLED=false` en production.
- Vérifier que `ADMIN_MFA_REQUIRED=true` en production.
- Vérifier que les comptes admin ont MFA activé.
- Lancer un build frontend.
- Vérifier les migrations automatiques au démarrage via `ensureSchema()`.

## Après déploiement

- Tester une inscription publique : elle doit être refusée ou rester en attente de vérification.
- Tester une connexion client existant : elle doit fonctionner.
- Tester un compte suspendu : il doit être refusé.
- Tester `/73948261502839476150` avec un client non admin : page introuvable.
- Tester `/logs` avec un client non admin : page introuvable.
- Lancer un dry-run sur le domaine suspect.

## Commande dry-run

```bash
cd /opt/spidr-mail/frontend
npm run security:suspicious-signups -- --domain immenseignite.info --dry-run
```

