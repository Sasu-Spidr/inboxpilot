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
