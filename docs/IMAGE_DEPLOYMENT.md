# Déploiement par images

La composition principale utilise uniquement les images suivantes :

- `ghcr.io/sasu-spidr/inboxpilot:${IMAGE_TAG}` pour `mail-agent` et `oauth-onboarding` ;
- `ghcr.io/sasu-spidr/inboxpilot-frontend:${IMAGE_TAG}` pour le frontend ;
- `ghcr.io/sasu-spidr/inboxpilot-bao-agent:${IMAGE_TAG}` pour l'agent OpenBao ;
- `postgres:16-alpine` pour PostgreSQL.

À chaque push sur `main` ou `dev`, le workflow CI publie les trois images avec
le même tag immuable `sha-<court>` et avec le tag de branche `main` ou `dev`.
Les pull requests exécutent les tests sans publier d'image.

Le même tag immuable doit être utilisé pour les trois images InboxPilot.

## Développement local

Le fichier `docker-compose.build.yml` réintroduit les builds et les ports locaux. Le backend n'est construit qu'une fois : `oauth-onboarding` réutilise exactement l'image de `mail-agent` avec une commande différente.

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.build.yml ps
```

Les images locales sont nommées `inboxpilot:local` et `inboxpilot-frontend:local`. Les données applicatives et les logs utilisent des volumes Docker nommés, comme en déploiement.

## Vérifier l'artefact

```bash
IMAGE_TAG="$(git rev-parse HEAD)"
docker build -t "ghcr.io/sasu-spidr/inboxpilot:${IMAGE_TAG}" .
docker build -t "ghcr.io/sasu-spidr/inboxpilot-frontend:${IMAGE_TAG}" frontend
docker run --rm "ghcr.io/sasu-spidr/inboxpilot:${IMAGE_TAG}" sha256sum /app/config/settings.yaml
sha256sum config/settings.yaml
```

Les deux sommes de contrôle doivent être identiques. Aucun montage de `config/` n'est utilisé à l'exécution.

## Fichiers d'environnement

- `docker-compose.dev.yml` contient les routes et labels Traefik de `inboxpilot-dev.mallow-hub.tech`.
- `docker-compose.prod.yml` contient les routes et labels Traefik de `inboxpilot.mallow-hub.tech`.
- `TRAEFIK_BASIC_AUTH_HASH` est obligatoire en dev et doit être injecté depuis OpenBao. Il ne doit jamais être commité.

Le déploiement doit toujours préciser le fichier d'environnement :

```bash
IMAGE_TAG="<sha>" docker compose -p spidr-mail-dev \
  -f docker-compose.yml -f docker-compose.dev.yml up -d

IMAGE_TAG="<sha>" docker compose -p spidr-mail \
  -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Migration unique des données existantes

Les anciens dossiers `data`, `logs` et `secrets` ne doivent pas être abandonnés lors de la bascule. Ils contiennent notamment les jetons OAuth, l'état chiffré et le fichier client OAuth Gmail. Le fichier OAuth est copié provisoirement dans un volume Docker dédié en lecture seule pour les services applicatifs. L'agent OpenBao remplacera ensuite le contenu de ce volume sans réintroduire de bind mount.

Avant la première bascule par image, vérifier que la configuration n'a pas divergé :

```bash
ssh root@89.116.111.236 'cd /opt/spidr-mail-dev && git status --porcelain config/'
ssh root@89.116.111.236 'cd /opt/spidr-mail && git status --porcelain config/'
```

Les deux commandes doivent rester silencieuses. Ensuite, exécuter une seule fois depuis le runner, avec le démon Docker du VPS comme cible :

```bash
DOCKER_HOST=ssh://root@89.116.111.236 \
  sh scripts/migrate_compose_state_to_volumes.sh spidr-mail-dev /opt/spidr-mail-dev

DOCKER_HOST=ssh://root@89.116.111.236 \
  sh scripts/migrate_compose_state_to_volumes.sh spidr-mail /opt/spidr-mail
```

Le script vérifie les chemins sur l'hôte Docker distant, refuse d'écraser un volume non vide, arrête uniquement les trois services applicatifs pendant la copie et compare intégralement la source et la destination. Les secrets ne sont jamais intégrés à l'image. En cas d'échec, les anciens conteneurs sont redémarrés. PostgreSQL et son volume ne sont pas modifiés. Il faut lancer immédiatement la nouvelle stack après chaque migration.

Après la bascule, vérifier :

```bash
docker compose -p <projet> -f docker-compose.yml -f docker-compose.<env>.yml ps
docker run --rm -v <projet>_inboxpilot_data:/data alpine:3.20 \
  sh -c 'test -d /data/tokens && test -d /data/state'
```

Tous les services doivent être `healthy` et les comptes déjà connectés doivent rester présents.
