# Déploiement et exploitation d'InboxPilot

Ce document décrit la chaîne complète sans supposer un accès aux anciens
répertoires de sources du VPS.

## Architecture

```text
push dev ─┐
          ├─ tests ─ images GHCR ─ Docker distant par SSH ─ stack dev
tag v* ───┘                                  │
                                             └─ stack prod après approbation

frontend ─ réseau bao_frontend ─ bao-agent-frontend ─ OpenBao
worker   ─ réseau bao_worker   ─ bao-agent-worker   ─ OpenBao
```

Trois images portent toujours le même SHA :

- `ghcr.io/sasu-spidr/inboxpilot` pour le worker et OAuth ;
- `ghcr.io/sasu-spidr/inboxpilot-frontend` ;
- `ghcr.io/sasu-spidr/inboxpilot-bao-agent`.

Le runner GitHub crée un contexte Docker SSH temporaire. Compose est exécuté
depuis le checkout du runner et pilote le démon du VPS. Aucun code, fichier
Compose ou identifiant GHCR n'est déposé sur le serveur.

## Cloisonnement OpenBao

| Zone | Services | Secrets lisibles |
|---|---|---|
| frontend | `frontend` | `frontend`, `database` |
| worker | `mail-agent`, `oauth-onboarding` | `crypto`, `groq`, `oauth/*` |

Les réseaux ne se croisent pas. Une compromission du frontend ne donne donc
pas accès à `token_encryption_key` ni aux identifiants OAuth.

Les seuls secrets d'amorçage durables du VPS sont :

```text
/etc/inboxpilot/<env>/frontend/{role_id,secret_id}
/etc/inboxpilot/<env>/worker/{role_id,secret_id}
```

Ils sont liés à l'IP du VPS, détenus par `100:1000`, avec les répertoires en
`0700` et les fichiers en `0600`.

## Déployer en dev

Un push sur `dev` lance automatiquement : tests, construction et publication
des trois images, puis déploiement de `spidr-mail-dev`. Toutes les vérifications
de santé doivent réussir.

```bash
git switch dev
git pull --ff-only origin dev
# modifications et tests
git push origin dev
gh run list --workflow CI --branch dev --limit 1
```

L'URL attendue est `https://inboxpilot-dev.mallow-hub.tech`. Une réponse `401`
sans identifiants confirme que la Basic Auth protège l'entrée.

## Déployer en production

Lire d'abord [PRODUCTION_RELEASE.md](PRODUCTION_RELEASE.md). La première
bascule impose une sauvegarde, la migration des volumes et la validation du KV
prod. Ensuite, créer un tag depuis `main` :

```bash
git switch main
git pull --ff-only origin main
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

Le pipeline vérifie que le commit appartient à `main`, construit les images,
puis attend l'approbation de l'environment GitHub `prod`. Un push ordinaire
sur `main` ne déploie jamais la production.

## Rollback

Avant de modifier la stack, le workflow relève le SHA du frontend en service.
Si un agent ou un service ne devient pas sain, il redéploie automatiquement ce
SHA. Le job reste en erreur afin que l'incident soit visible.

Pour un rollback volontaire, créer sur `main` un commit qui annule la version
défectueuse, puis publier un nouveau tag `v*`. En urgence, un opérateur peut
redéployer le SHA immuable précédent depuis un poste possédant ce dépôt et un
accès Docker SSH. Toute action manuelle en production exige une fenêtre
approuvée ; ne jamais réécrire l'historique de `main`.

## Exploiter sans fichier Compose sur le VPS

Sur le VPS :

```bash
docker ps --filter label=com.docker.compose.project=spidr-mail-dev
docker ps --filter label=com.docker.compose.project=spidr-mail
docker logs --tail 200 <nom-du-conteneur>
docker inspect <nom-du-conteneur>
```

Depuis un poste possédant le dépôt et un contexte Docker `vps` :

```bash
IMAGE_TAG=<sha> BAO_ADDR=<adresse> \
docker --context vps compose -p spidr-mail-dev \
  -f docker-compose.yml -f docker-compose.dev.yml ps
```

Ne jamais lancer `docker compose` depuis `/opt/spidr-mail*` après la bascule :
les manifests de référence sont ceux du commit déployé par la CI.

## Ajouter un secret

1. déterminer s'il appartient à la zone frontend ou worker ;
2. choisir un chemin existant de cette zone, ou faire ajouter un chemin précis
   dans la policy déclarative de `spidr-infra` ;
3. ajouter le champ avec `bao kv patch` sur dev, jamais avec `put` sur un secret
   contenant déjà d'autres champs ;
4. ajouter la correspondance dans `frontend/lib/baoSecrets.ts` ou
   `bao_secrets.py` ;
5. tester l'accès autorisé et un accès inter-zone qui doit retourner `403` ;
6. répéter séparément sur prod, avec une valeur différente lorsque cela est
   pertinent ;
7. ne jamais ajouter la valeur dans GitHub, `.env`, Compose ou les logs.

## Rotation du `secret_id` d'amorçage

À réaliser séparément pour chaque environnement et chaque zone :

1. générer un nouveau `secret_id` pour l'AppRole runtime concerné ;
2. noter son accessor dans le coffre opérationnel, sans journaliser la valeur ;
3. écrire la nouvelle valeur dans un fichier temporaire `0600` du même
   répertoire ;
4. remplacer atomiquement `secret_id`, conserver le propriétaire `100:1000` ;
5. redémarrer uniquement l'agent concerné et vérifier son état `healthy` ;
6. vérifier qu'un service de la zone lit son chemin autorisé ;
7. révoquer ensuite l'ancien `secret_id` par son accessor.

L'ordre est essentiel : déposer et tester le nouveau secret avant de révoquer
l'ancien. Sinon le prochain redémarrage coupe la zone.

## Dépannage

- agent `unhealthy` : vérifier `BAO_ADDR`, les permissions du bootstrap et les
  journaux de l'agent ;
- HTTP `403` OpenBao : vérifier la zone, le chemin et la policy ;
- secret manquant : contrôler le nom exact du champ sans afficher sa valeur ;
- application saine mais inaccessible : vérifier Traefik et le réseau
  `chatmallow_edge` ;
- jetons OAuth illisibles : arrêter le worker et suivre immédiatement la
  procédure de retour arrière de la clé de chiffrement ;
- image privée impossible à tirer : vérifier le job GitHub et GHCR, ne pas
  effectuer de `docker login` persistant sur le VPS.

## Suppression des anciens secrets

Après rotation confirmée, supprimer les anciens exports en clair du VPS et les
anciens secrets métier GitHub. La suppression précède toujours une vérification
des nouvelles valeurs, jamais leur rotation. Conserver uniquement
`VPS_SSH_KEY` au niveau du dépôt tant que la CI utilise SSH.
