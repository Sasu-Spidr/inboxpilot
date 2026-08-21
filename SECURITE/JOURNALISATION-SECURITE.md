# Journalisation sécurité

## Événements enregistrés

Les événements sécurité sont stockés dans la table `security_events`.

Événements ajoutés :

- `signup_blocked_public_disabled`
- `signup_invalid`
- `signup_existing_email`
- `signup_pending_email_verification`
- `email_verification_failed`
- `email_verified`
- `login_failed`
- `login_blocked_account_status`
- `login_mfa_required`
- `login_success`
- `mfa_failed`
- `mfa_success`
- `account_suspended_security`

## Données enregistrées

Les logs peuvent contenir :

- type d’événement ;
- client_id si connu ;
- email si connu ;
- adresse IP ;
- user-agent ;
- métadonnées non sensibles.

## Données interdites dans les logs

Ne jamais écrire :

- mot de passe ;
- hash de mot de passe ;
- secret MFA ;
- token OAuth ;
- clé API ;
- token de vérification email en clair.

