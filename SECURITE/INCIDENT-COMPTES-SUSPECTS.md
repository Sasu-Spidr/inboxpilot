# Incident comptes suspects InboxPilot

## Situation

Des inscriptions suspectes ont été constatées avec des adresses email aléatoires, notamment sur le domaine `immenseignite.info`.

## Ce qui est confirmé

- Le formulaire d’inscription public permettait de créer directement un compte applicatif.
- À la création du compte, le registre client pouvait être initialisé automatiquement.
- Un compte nouvellement créé pouvait obtenir une session immédiatement après inscription.

## Ce qui est corrigé dans le code

- Les inscriptions publiques sont désactivées par défaut avec `PUBLIC_SIGNUP_ENABLED=false`.
- Les nouveaux comptes créés par l’API passent désormais en statut `PENDING_EMAIL_VERIFICATION`.
- Aucun registre Gmail/Outlook n’est créé avant validation email.
- Aucune session n’est ouverte tant que l’email n’est pas vérifié.
- Les comptes non actifs, non vérifiés ou suspendus sont refusés côté serveur.
- Les sessions contiennent une version interne. Une suspension incrémente cette version et invalide les cookies déjà émis.
- Les pages admin et logs exigent un compte admin actif, email vérifié, et MFA si `ADMIN_MFA_REQUIRED=true`.
- Les accès OAuth refusent les clients, connecteurs ou comptes désactivés.

## Ce qui reste à connecter

- L’envoi réel de l’email de vérification doit être branché à un provider email transactionnel.
- Le endpoint `/api/auth/verify-email?token=...` est prêt côté serveur.

## Variables de sécurité

```env
PUBLIC_SIGNUP_ENABLED=false
ADMIN_MFA_REQUIRED=true
SESSION_MAX_AGE_SECONDS=86400
EMAIL_VERIFICATION_TOKEN_TTL_MINUTES=30
LOGIN_RATE_LIMIT_15M=10
REGISTER_RATE_LIMIT_1H=5
```

## Règle importante

Ne supprimez pas les comptes suspects pendant l’analyse. Il faut préserver les traces.
