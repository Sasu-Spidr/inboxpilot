# Rapport d'évaluation InboxPilot

- Modèle : `openai/gpt-oss-120b`
- Cas : **70**
- Justesse stricte : **68.57%**
- Abstentions : **0** (0.00%)
- Erreurs techniques : **13** (18.57%)

## Résultats par chemin

| Chemin | Cas | Corrects | Justesse | Abstentions | Erreurs techniques |
|---|---:|---:|---:|---:|---:|
| deterministic | 34 | 25 | 73.53% | 0 | 0 |
| model | 36 | 23 | 63.89% | 0 | 13 |

## Scores par libellé

| Libellé | Support | Classés | Précision | Rappel | F1 |
|---|---:|---:|---:|---:|---:|
| À répondre | 14 | 14 | 1.000 | 0.929 | 0.963 |
| À traiter | 13 | 5 | 0.375 | 0.600 | 0.462 |
| À lire | 14 | 12 | 0.923 | 1.000 | 0.960 |
| Notification | 16 | 14 | 0.800 | 0.571 | 0.667 |
| Commercial | 13 | 12 | 0.923 | 1.000 | 0.960 |

## Matrice de confusion

| Attendu \ Obtenu | À répondre | À traiter | À lire | Notification | Commercial |
|---|---:|---:|---:|---:|---:|
| À répondre | 13 | 1 | 0 | 0 | 0 |
| À traiter | 0 | 3 | 0 | 2 | 0 |
| À lire | 0 | 0 | 12 | 0 | 0 |
| Notification | 0 | 4 | 1 | 8 | 1 |
| Commercial | 0 | 0 | 0 | 0 | 12 |

## Échecs détaillés

### `read-comment-fr-002`

- Attendu : **À lire**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: 

### `read-compliment-fr-008`

- Attendu : **À lire**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: {
  "libelle": "À lire",
  "urgence": "normale",
  "confiance": 0.97,
  "raison": "Le message est une simple appréciation sans demande de réponse ni d'action.",
  "expediteur_automatique": false


### `reply-document-question-fr-004`

- Attendu : **À répondre**
- Obtenu : **À traiter**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.990
- Raison : Le message concerne une facture, un paiement, un document ou un sujet administratif à traiter.

### `reply-automatic-question-014`

- Attendu : **Notification**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: {


### `action-security-fr-003`

- Attendu : **À traiter**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: 

### `action-access-fr-004`

- Attendu : **À traiter**
- Obtenu : **Notification**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.970
- Raison : Le message est une notification automatique.

### `action-document-en-006`

- Attendu : **À traiter**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: 

### `action-tax-fr-007`

- Attendu : **À traiter**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: {
  "libelle": "Notification",
  "urgence": "normale",
  "confiance": 0.97,
  "raison

### `action-short-008`

- Attendu : **À traiter**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: 

### `action-empty-subject-009`

- Attendu : **À traiter**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: {
  "libelle":

### `action-bank-fr-010`

- Attendu : **À traiter**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: 

### `action-account-fr-011`

- Attendu : **À traiter**
- Obtenu : **Notification**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.980
- Raison : Le message est une notification automatique ou transactionnelle.

### `action-consent-en-012`

- Attendu : **À traiter**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: {
  "libelle": "À traiter",
  "urgence": "normale",
  "confiance": 0.96,
  "raison": "Le message demande à l'utilisateur d'effectuer une action manuelle (se connecter et renouveler le consent

### `action-receipt-negative-013`

- Attendu : **Notification**
- Obtenu : **À traiter**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.990
- Raison : Le message concerne une facture, un paiement, un document ou un sujet administratif à traiter.

### `commercial-no-subject-004`

- Attendu : **Commercial**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: {
  "libelle": "Commercial",
  "urgence": "normale",
  "confiance": 0.98,
  "raison": "Le message provient d'une adresse marketing et propose une offre promotionnelle, typique d'un

### `notification-receipt-fr-002`

- Attendu : **Notification**
- Obtenu : **À traiter**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.990
- Raison : Le message concerne une facture, un paiement, un document ou un sujet administratif à traiter.

### `notification-receipt-promo-fr-003`

- Attendu : **Notification**
- Obtenu : **Commercial**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.940
- Raison : Le message ressemble à du contenu commercial.

### `notification-short-008`

- Attendu : **Notification**
- Obtenu : **À traiter**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.990
- Raison : Le message concerne une facture, un paiement, un document ou un sujet administratif à traiter.

### `notification-automatic-question-009`

- Attendu : **Notification**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response: 

### `notification-app-mention-010`

- Attendu : **Notification**
- Obtenu : **À lire**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.970
- Raison : Le message signale une mention ou une interaction à lire.

### `notification-renewal-done-en-013`

- Attendu : **Notification**
- Obtenu : **À traiter**
- Statut : `classified`
- Chemin : `deterministic`
- Confiance : 0.990
- Raison : Le message concerne une facture, un paiement, un document ou un sujet administratif à traiter.

### `notification-security-action-negative-014`

- Attendu : **À traiter**
- Obtenu : **—**
- Statut : `technical_error`
- Chemin : `model`
- Confiance : —
- Raison : — Erreur : `invalid_json` — No JSON object found in model response:
