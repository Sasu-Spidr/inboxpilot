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

Les serveurs OpenBao ne sont pas le VPS InboxPilot : ils appartiennent à
l'infrastructure SpidR. L'activation du journal, sa rotation et la surveillance
des événements sensibles sont donc **pilotées par le dépôt `spidr-infra`**, pas
par celui-ci :

- workflow `OpenBao - Enable audit log` (`enable-audit-openbao.yml`), au
  déclenchement manuel, environnement `dev` ou `prod` ;
- playbook `ansible/openbao/enable-audit.yml`, copié sur le VPS et exécuté sur
  place ;
- policy `audit-<env>-readonly`, générée depuis
  `config/openbao/policy-templates/audit-admin.hcl.j2`.

Le runner n'utilise aucun token statique : OIDC GitHub, puis rôle JWT
`audit-jwt-<env>`, puis AppRole `audit-<env>`. Le token vaut une heure, ne porte
que la lecture de `sys/audit`, et est révoqué en fin de job.

Trois propriétés de cette activation méritent d'être connues côté application :

- **Le device est déclaratif.** OpenBao 2.6 refuse la création par API avec
  `400 cannot enable audit device via API; use declarative, config-based audit
  device management instead`. Le bloc est écrit dans `server.hcl` et appliqué au
  `SIGHUP`, jamais par redémarrage : les deux instances sont en sceau Shamir 3/5
  sans descellement automatique, un redémarrage laisserait le serveur scellé.
- **Le journal est commun à toutes les applications** servies par l'instance,
  d'où un nom neutre : device `audit-json`, fichier
  `/opt/openbao-<env>/logs/audit.jsonl`, un par instance pour que l'option
  `--environment` ne mélange pas dev et prod.
- **`log_raw` reste à `false`.** Les chemins et les identités sont en clair, les
  valeurs sont HMAC. Si un device activé ne peut pas écrire, OpenBao refuse
  toutes les requêtes — d'où l'activation de dev avant prod.

Vérification côté application, sans token administrateur :

```bash
ssh spidr-ovh 'sudo tail -1 /opt/openbao-dev/logs/audit.jsonl | head -c 300'
```

`scripts/verify_openbao_audit.py` reste disponible pour une vérification par
l'API, avec un token admin passé par fichier et jamais en ligne de commande.

### Détection d'anomalies applicatives

Le playbook installe déjà une surveillance des événements sensibles à l'échelle
du serveur : refus, suppression de secret, modification de policy ou de device,
usage d'un token `root`. Elle écrit dans journald sous le tag
`openbao-audit-alert`.

`scripts/analyze_openbao_audit.py` couvre l'angle applicatif, que le serveur ne
peut pas juger : volume anormal par identité et par chemin, et surtout lecture
croisée entre les zones `frontend` et `worker`. Les deux sont complémentaires.

### Anomalies retenues

- au moins 60 lectures par la même identité et le même chemin en 5 minutes ;
- toute lecture d'un chemin worker par l'identité frontend, ou l'inverse ;
- au moins 5 refus d'autorisation en 5 minutes pour une même identité.

Le seuil de 60 lectures est le défaut du script. Le trafic dev normal atteint
~57 lectures en 5 minutes sur un même chemin : relever le seuil ou allonger le
`cache_ttl` des agents avant de programmer ce contrôle, sinon il alertera en
continu. Allonger le `cache_ttl` traite la cause.

Contrôle manuel, depuis un poste ayant accès au journal :

```bash
ssh spidr-ovh 'sudo cat /opt/openbao-dev/logs/audit.jsonl' \
  | python3 scripts/analyze_openbao_audit.py --environment dev --read-threshold 150 /dev/stdin
```

Codes de sortie : `0` aucune anomalie, `2` anomalie signalée, `3` anomalie
signalée mais la notification a échoué. Les anomalies sont toujours écrites sur
stderr avant toute tentative de notification, donc une panne de notification ne
perd jamais l'alerte.

**Reste à faire** : ce contrôle n'est pas encore programmé. Sa place est le
playbook `enable-audit.yml` de `spidr-infra`, à côté de la surveillance
serveur — pas un déploiement séparé depuis ce dépôt, qui dupliquerait l'accès
SSH au VPS OpenBao.

Quand une URL d'alerte d'équipe existera, la déposer dans OpenBao à
`secret/data/audit/alerting`, champ `webhook_url`, et passer `--approle-dir` au
script : il lit l'URL à l'exécution avec un AppRole limité à ce seul chemin,
révoque son token aussitôt, et ne la lit **que** lorsqu'une anomalie se
déclenche — donc sans gonfler les compteurs de lecture qu'il surveille. Aucune
copie de l'URL sur l'hôte ni dans GitHub. `--webhook-url` court-circuite
l'AppRole, réservé au débogage : l'URL finit dans l'historique du shell.

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
