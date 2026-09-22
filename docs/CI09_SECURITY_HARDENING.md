# CI-09 — Audit OpenBao et durcissement runtime

## État d'implémentation

| Mesure | État | Décision |
|---|---|---|
| Audit OpenBao dev/prod | Prêt côté dépôt, activation infrastructure requise | Configuration déclarative, journal JSON, secrets HMAC |
| Détection d'anomalies | Implémentée | Contrôle toutes les 5 minutes, webhook d'équipe facultatif mais recommandé |
| Conteneurs non-root | Implémenté | UID 1000 pour le frontend, 10001 pour Python, 100:1000 pour les agents |
| Racine en lecture seule | Implémenté | Seuls les volumes métier et les `tmpfs` restent inscriptibles |
| Capacités Linux | Implémenté | Toutes retirées, `no-new-privileges` activé |
| Identifiants PostgreSQL dynamiques | Différé | À faire après la migration de la base vers l'infrastructure SpidR |
| Rotation de `TOKEN_ENCRYPTION_KEY` | Outil et procédure livrés | Rotation atomique avec validation et sauvegarde chiffrée |
| Ports publiés | Conforme | Aucun port de la stack runtime n'est publié sur l'hôte |
| Basic Auth dev | Active, source à migrer | Le hash est actuellement une variable GitHub `dev`, pas encore un secret OpenBao |

## 1. Audit OpenBao

Les serveurs `bao-dev` et `bao-prod` sont externes au VPS InboxPilot. Cette
opération doit donc être réalisée sur chacun des deux serveurs OpenBao par un
administrateur ayant la capacité `sudo` sur `sys/audit`.

OpenBao 2.6 recommande une configuration déclarative plutôt qu'une création
par API. Copier le bloc de `deploy/openbao/audit.hcl.example` dans la
configuration serveur, créer `/var/log/openbao` avec le propriétaire du
processus OpenBao, puis recharger le service. Conserver `log_raw=false`.

Vérification sans afficher le token administrateur :

```bash
install -m 600 /dev/null /run/openbao-admin-token
# Écrire le token dans ce fichier par un canal sûr, sans le passer sur la ligne de commande.
python3 scripts/verify_openbao_audit.py \
  --address https://bao-dev.mallow-hub.tech \
  --token-file /run/openbao-admin-token
```

Répéter pour `https://bao-prod.mallow-hub.tech`, puis supprimer le fichier de
token. La commande doit afficher au moins `inboxpilot-json/`.

Configurer `logrotate` pour le journal. Après rotation, envoyer `SIGHUP` au
processus OpenBao afin qu'il rouvre le fichier. Le répertoire et les archives
doivent rester lisibles uniquement par l'équipe infrastructure.

### Anomalies retenues

- au moins 60 lectures par la même identité et le même chemin en 5 minutes ;
- toute lecture d'un chemin worker par l'identité frontend, ou l'inverse ;
- au moins 5 refus d'autorisation en 5 minutes pour une même identité.

Contrôle manuel :

```bash
OPENBAO_ALERT_WEBHOOK_URL='https://webhook-equipe.example' \
python3 scripts/analyze_openbao_audit.py \
  --environment dev \
  /var/log/openbao/inboxpilot-audit.jsonl
```

Sans webhook, une anomalie est écrite sur stderr et le programme termine avec
le code `2`. Avec le webhook, une notification textuelle est également envoyée
à l'équipe. Exécuter cette commande toutes les 5 minutes avec le mécanisme de
supervision déjà utilisé par l'infrastructure. L'URL du webhook doit être
stockée dans OpenBao ou dans le gestionnaire de secrets de la supervision.

## 2. Durcissement des conteneurs

Les services applicatifs utilisent maintenant des UID non-root fixes :

- `frontend` : `1000:1000` (`node`) ;
- `mail-agent` et `oauth-onboarding` : `10001:10001` (`inboxpilot`) ;
- agents OpenBao : `100:1000` (`openbao`).

Avant le premier déploiement durci, préparer les permissions des fichiers
AppRole sur le VPS :

```bash
sudo scripts/prepare_openbao_bootstrap_permissions.sh /etc/inboxpilot/dev
sudo scripts/prepare_openbao_bootstrap_permissions.sh /etc/inboxpilot/prod
```

Le script ne lit aucune valeur. Il transfère la propriété au compte `openbao`
et conserve les répertoires en `0700` et les fichiers en `0600`. Les services
disposent ensuite de :

- `read_only: true` ;
- `cap_drop: [ALL]` ;
- `security_opt: [no-new-privileges:true]` ;
- un `tmpfs` privé pour `/tmp` ;
- un cache temporaire séparé pour Next.js ;
- les volumes nommés existants pour les jetons, l'état et les logs.

Après déploiement, vérifier :

```bash
docker inspect spidr-mail-dev-frontend-1 \
  --format '{{.Config.User}} {{.HostConfig.ReadonlyRootfs}} {{json .HostConfig.CapDrop}}'
docker inspect spidr-mail-dev-mail-agent-1 \
  --format '{{.Config.User}} {{.HostConfig.ReadonlyRootfs}} {{json .HostConfig.CapDrop}}'
```

## 3. Identifiants PostgreSQL dynamiques

Décision : ne pas brancher le moteur database sur l'instance PostgreSQL
actuelle, car cette base doit être migrée côté infrastructure SpidR. Le faire
maintenant créerait une configuration privilégiée temporaire à reconstruire.

La fonctionnalité est pertinente après migration : OpenBao sait générer des
identifiants PostgreSQL uniques, loués et automatiquement révoqués. Cependant,
le frontend utilise actuellement un pool PostgreSQL créé au démarrage. La
future intégration devra être consciente du bail : obtenir les credentials,
renouveler le bail, recréer proprement le pool avant expiration et révoquer le
bail à l'arrêt. Un simple remplacement de `DATABASE_URL` au démarrage ne suffit
pas.

Décision de mise en œuvre après migration :

1. créer un utilisateur PostgreSQL dédié à OpenBao, jamais le superutilisateur
   applicatif courant ;
2. activer le moteur `database` et un rôle `inboxpilot-frontend` ;
3. limiter les permissions SQL de ce rôle aux tables InboxPilot ;
4. choisir un TTL initial de 1 heure et un maximum de 24 heures ;
5. ajouter au frontend un gestionnaire de bail et de renouvellement du pool ;
6. tester expiration, renouvellement, révocation et indisponibilité OpenBao.

## 4. Surface exposée et Basic Auth

Les fichiers Compose runtime ne contiennent aucun bloc `ports:`. Le frontend
rejoint uniquement le réseau externe `chatmallow_edge`, où Traefik le contacte
sur le port interne 3000. OAuth reste accessible seulement via le frontend sur
le réseau Docker privé. PostgreSQL et les agents OpenBao ne sont pas publiés.

La Basic Auth de dev est active dans `docker-compose.dev.yml`. Son hash est
actuellement injecté par la variable d'environment GitHub
`TRAEFIK_BASIC_AUTH_HASH`. Ce hash ne figure ni dans Git ni sur la ligne de
commande, mais il n'est pas encore fourni par OpenBao. Pour satisfaire
complètement le critère, l'infrastructure doit choisir l'une de ces solutions :

- fournir le hash au déploiement via une identité CI OpenBao à durée courte ;
- ou faire rendre une configuration dynamique Traefik par un agent OpenBao
  dédié à l'infrastructure.

La deuxième option est préférable : elle ne donne pas à la CI le droit de lire
un secret runtime et conserve la protection devant le frontend.
