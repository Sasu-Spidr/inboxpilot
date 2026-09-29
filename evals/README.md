# Jeu de référence du classement

Ce dossier contient uniquement des messages synthétiques destinés à évaluer le
classement dans les cinq libellés InboxPilot. Il ne contient ni jeton OAuth, ni
secret, ni copie de boîte mail. `label_settings.yaml` fige les paramètres
utilisés afin que deux exécutions restent comparables.

## Ajouter un cas

Ajouter le cas dans le fichier du libellé attendu sous `dataset/` en conservant
ce format :

```yaml
- id: notification-confirmation-fr-015
  subject: "Opération terminée"
  sender: "no-reply@service.example"
  body: "Votre opération est terminée."
  expected: Notification
  tags: [fr, automatique, facile]
  note: "Pourquoi ce libellé est la référence."
```

- L'identifiant est unique, stable, descriptif et n'est jamais recyclé.
- L'expéditeur utilise un domaine réservé `.example`.
- Le libellé attendu fait partie de : `À répondre`, `À traiter`, `À lire`,
  `Notification`, `Commercial`.
- La note explique le choix, surtout pour un cas limite.
- Un cas modifié ou ajouté doit être relu par une seconde personne avant que le
  jeu soit déclaré validé.

## Données personnelles

Un mail réel ne doit jamais être copié tel quel dans ce dépôt. Les cas
synthétiques sont la règle. Si une tournure réelle est indispensable, elle doit
être entièrement réécrite et toutes les informations identifiantes remplacées :
noms, adresses, sociétés, montants, factures, comptes, identifiants et URL.
Une anonymisation partielle n'est pas acceptable.

## Désaccords de labellisation

Chaque libellé attendu doit être approuvé par deux personnes. En cas de
désaccord, retirer le cas ou clarifier d'abord la définition correspondante dans
`config/label_definitions.yaml`. Le jeu ne doit pas transformer une opinion
ambiguë en vérité de référence.

Les tests vérifient la structure, l'équilibre, l'absence d'expéditeurs réels et
la couverture positive/négative des expressions historiques. Le calcul des
métriques et l'appel au classifieur appartiennent à EVAL-02.

## Validation du jeu initial

Le jeu initial de 70 cas livré dans le commit `b1fb094` a fait l'objet d'une
revue de constitution puis d'une validation métier indépendante par Geoffroy
Detrousselle le 29 septembre 2026. Aucun désaccord nécessitant le retrait d'un
cas ou une modification de `config/label_definitions.yaml` n'a été signalé.

## Lancer l'évaluation

Une évaluation en direct nécessite `GROQ_API_KEY` et écrit deux rapports dans
`evals/reports/` :

```bash
python evals/run_eval.py
```

Pour conserver les réponses brutes du modèle afin de les rejouer ensuite :

```bash
python evals/run_eval.py --record
python evals/run_eval.py --replay evals/recordings
```

On peut changer les emplacements avec `--dataset`, `--label-settings`,
`--output-dir` et fournir un autre dossier à `--record`. Une empreinte lie
chaque enregistrement à son cas ; le rejeu échoue si le mail de référence a été
modifié.

Le rapport Markdown est destiné à la lecture. Le JSON est la référence
structurée pour la détection de régressions d'EVAL-03. Les abstentions et les
erreurs techniques sont exclues de la matrice 5x5 et exposées séparément afin
qu'un repli vers `À lire` ne ressemble jamais à une décision normale.

## Coût d'une exécution en direct

Le jeu initial contient 70 cas sur un maximum prévu de 80. Les règles
déterministes ne consomment aucun appel ; chaque autre cas consomme au plus un
appel réussi au modèle. La configuration du classifieur est fixe :
`max_completion_tokens=180` et `temperature=0`. Même avec 80 cas entièrement
traités par le modèle, une exécution représente donc au maximum 80 appels et
14 400 tokens de complétion, hors éventuelles nouvelles tentatives sur erreur.
