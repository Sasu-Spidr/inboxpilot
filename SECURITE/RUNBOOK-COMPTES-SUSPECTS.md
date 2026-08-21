# Runbook comptes suspects

## Objectif

Identifier les comptes suspects sans exposer de secrets, puis éventuellement les suspendre sans supprimer les données.

## Dry-run

Depuis le VPS :

```bash
cd /opt/spidr-mail/frontend
npm run security:suspicious-signups -- --domain immenseignite.info --dry-run
```

Le dry-run :

- liste le nombre de comptes concernés ;
- génère un rapport JSON dans `SECURITE/` ;
- pseudonymise les identifiants ;
- n’affiche aucun mot de passe, token OAuth, clé API ou secret.

## Suspension confirmée

À lancer uniquement après validation humaine :

```bash
cd /opt/spidr-mail/frontend
npm run security:suspicious-signups -- --domain immenseignite.info --suspend --confirm
```

La suspension :

- met le statut utilisateur à `SUSPENDED_SECURITY` ;
- invalide les sessions existantes ;
- désactive le client dans le registre `data/clients/clients.yaml` ;
- conserve les données, tokens et traces ;
- écrit un événement sécurité en base.

## Ce qui n’est pas fait volontairement

- Pas de suppression de compte.
- Pas de suppression de tokens.
- Pas de purge de logs.

## Retour arrière manuel

À faire uniquement après vérification :

```sql
update users
set status = 'ACTIVE',
    email_verified = true,
    security_suspended_at = null,
    security_suspended_reason = null,
    session_version = session_version + 1
where client_id = '<CLIENT_ID>';
```

Puis réactiver le client concerné dans `data/clients/clients.yaml`.

