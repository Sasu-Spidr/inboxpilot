# Procédure de rotation de `TOKEN_ENCRYPTION_KEY`

## Risque couvert

Cette clé Fernet chiffre les jetons OAuth Gmail et Microsoft ainsi que l'état
de traitement. Si elle est compromise, un attaquant qui obtient aussi les
fichiers chiffrés peut récupérer les jetons. Changer seulement la valeur dans
OpenBao rendrait tous les comptes illisibles et interromprait l'agent.

## Rotation planifiée avec rechiffrement

1. Annoncer une courte fenêtre de maintenance OAuth.
2. Générer une nouvelle clé Fernet dans un environnement sûr.
3. Stocker l'ancienne et la nouvelle clé dans deux fichiers temporaires `0600`.
   Ne jamais les passer en arguments, les afficher ou les committer.
4. Arrêter `mail-agent` et `oauth-onboarding`. Le frontend peut rester actif,
   mais aucune connexion de boîte ne doit être lancée pendant la rotation.
5. Faire une validation sans écriture :

```bash
python3 scripts/rotate_token_encryption_key.py \
  --data-dir /app/data \
  --old-key-file /run/keys/old \
  --new-key-file /run/keys/new \
  --backup-dir /app/data/key-rotation-backup-YYYYMMDD
```

6. Exécuter la rotation :

```bash
python3 scripts/rotate_token_encryption_key.py \
  --data-dir /app/data \
  --old-key-file /run/keys/old \
  --new-key-file /run/keys/new \
  --backup-dir /app/data/key-rotation-backup-YYYYMMDD \
  --apply
```

Le script déchiffre et valide tous les fichiers avant toute modification. Il
prépare les nouvelles versions, les vérifie, conserve une sauvegarde encore
chiffrée avec l'ancienne clé, puis utilise des remplacements atomiques. En cas
d'erreur pendant l'écriture, les fichiers déjà remplacés sont restaurés.

7. Remplacer `secret/inboxpilot/crypto.token_encryption_key` dans OpenBao.
8. Redémarrer d'abord `oauth-onboarding`, puis `mail-agent`.
9. Vérifier une connexion Gmail, une connexion Outlook, la lecture de l'état et
   un cycle de classement sans erreur `InvalidToken`.
10. Conserver la sauvegarde le temps de la validation fonctionnelle, puis la
    détruire avec l'ancienne clé selon la politique de rétention sécurisée.

## Retour arrière

Si un service ne peut plus lire les jetons : arrêter les deux services,
restaurer le dossier de sauvegarde, remettre l'ancienne clé dans OpenBao et
redémarrer. Ne jamais mélanger une partie des fichiers avec l'ancienne clé et
une autre avec la nouvelle.

## Compromission avérée

Un rechiffrement protège les données futures mais ne révoque pas les jetons
OAuth que l'attaquant a déjà pu extraire. Si la confidentialité de l'ancienne
clé ou des fichiers chiffrés est réellement perdue :

1. désactiver temporairement le worker ;
2. révoquer les autorisations OAuth côté Google et Microsoft ;
3. générer et installer une nouvelle clé ;
4. supprimer les anciens fichiers de jetons ;
5. demander à chaque client concerné de reconnecter ses boîtes ;
6. informer les clients de la période, des données concernées, des mesures de
   confinement et de l'action demandée ;
7. conserver les journaux d'audit et ouvrir un incident formel.

## Exercice automatisé

`tests/test_security_operations.py` crée des jetons et un état factices,
effectue une validation à blanc, applique la rotation, vérifie le déchiffrement
avec la nouvelle clé et confirme que la sauvegarde reste lisible avec
l'ancienne. Cet exercice ne manipule aucun jeton client.
