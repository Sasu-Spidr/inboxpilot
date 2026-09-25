# Mise en production InboxPilot

La production utilise les images immuables publiées sur GHCR et le workflow
réutilisable `.github/workflows/deploy.yml`. La première bascule reste une
opération supervisée : créer un tag ne doit pas servir à migrer les données ou
à initialiser OpenBao.

## Garde-fous GitHub

L'environment `prod` doit avoir :

- `SasuSpidR` comme approbateur obligatoire ;
- le contournement administrateur désactivé ;
- uniquement la branche `main` et les tags `v*` autorisés ;
- les variables `BAO_ADDR`, `FRONTEND_BASE_URL`, `OAUTH_BASE_URL` et
  `OAUTH_PUBLIC_URL` sans espace final.

Le workflow vérifie également que le commit visé par un tag `v*` appartient à
l'historique de `main`. Un tag créé depuis une autre branche échoue avant le
job protégé par l'approbation.

## Préparation obligatoire avant le premier tag

Ne pas lancer la production tant que tous les contrôles suivants ne sont pas
validés :

1. annoncer une fenêtre de maintenance ;
2. confirmer la présence de `/etc/inboxpilot/prod/frontend/` et
   `/etc/inboxpilot/prod/worker/`, avec des fichiers détenus par `100:1000`,
   des répertoires `0700` et des fichiers `0600` ;
3. peupler **l'instance OpenBao prod** depuis le `.env` de la production
   actuelle, sans prendre une valeur depuis la dev et sans écrire les valeurs
   dans Git ou dans un journal ;
4. contrôler tous les chemins définis par `docs/OPENBAO_SECRETS.md` :
   `frontend`, `database`, `crypto`, `groq`, `oauth/gmail`,
   `oauth/microsoft` et `urls` ;
5. confirmer que `token_encryption_key` est strictement celle de la production
   existante, sinon les jetons OAuth deviendraient illisibles ;
6. confirmer que la dev et la prod ne partagent ni `token_encryption_key` ni
   `database_url` ;
7. sauvegarder les volumes et la base avant la migration ;
8. copier `/opt/spidr-mail/data` et `/opt/spidr-mail/logs` dans les volumes
   nommés avec `scripts/migrate_compose_state_to_volumes.sh spidr-mail
   /opt/spidr-mail`, puis vérifier la copie avant tout déploiement.

Le script de migration arrête seulement les anciens conteneurs applicatifs,
refuse d'écraser un volume non vide et compare la source avec la destination.
Il est relançable sans recopier des données déjà migrées.

## Livraison normale

Depuis un clone à jour sur `main` :

```bash
git switch main
git pull --ff-only origin main
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

La chaîne effectue les tests, publie les trois images avec le même SHA, vérifie
que le commit vient de `main`, puis attend l'approbation de l'environment
`prod`. Après approbation, elle déploie `spidr-mail` avec
`docker-compose.prod.yml` et attend que les agents OpenBao et les services
applicatifs soient sains.

Le lancement manuel est réservé aux cas exceptionnels : ouvrir le workflow
`CI`, sélectionner la branche `main`, cocher `deploy_prod`, lancer puis faire
approuver le job `prod`.

## Vérifications après bascule

- les six conteneurs `spidr-mail-*` sont `healthy` ;
- les images applicatives portent toutes le SHA attendu ;
- `https://inboxpilot.mallow-hub.tech` répond ;
- `docker inspect` ne montre aucun secret applicatif dans l'environnement ;
- une boîte Gmail et une boîte Outlook déjà connectées continuent de traiter
  les nouveaux messages sans perdre leurs paramètres ;
- aucun jeton OAuth ne produit d'erreur de déchiffrement.

## Rollback supervisé

Le workflow mémorise le tag du frontend présent avant la modification. Si un
service échoue, il redéploie automatiquement ce tag et termine en erreur.

Après une première bascule réussie, faire un exercice planifié : déployer un
tag de test volontairement non sain, constater le retour automatique au SHA
précédent, puis vérifier l'application et une boîte de test. Ne jamais réaliser
cet exercice sans fenêtre de maintenance et sauvegarde vérifiée.
