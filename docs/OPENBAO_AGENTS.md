# Agents OpenBao InboxPilot

InboxPilot utilise deux agents OpenBao distincts par environnement. Ils ne
publient aucun port sur l'hôte et ne partagent aucun réseau Docker.

| Agent | Réseau | Consommateurs | Périmètre attendu |
|---|---|---|---|
| `bao-agent-frontend` | `bao_frontend` | `frontend` | `frontend`, `database` |
| `bao-agent-worker` | `bao_worker` | `mail-agent`, `oauth-onboarding` | `crypto`, `groq`, `oauth/*` |

Les fichiers d'amorçage sont les seuls bind mounts autorisés :

```text
/etc/inboxpilot/<env>/frontend/{role_id,secret_id}
/etc/inboxpilot/<env>/worker/{role_id,secret_id}
```

Ils restent en `0600`, en dehors du dépôt et des répertoires de déploiement.
La configuration `agent.hcl` est embarquée dans l'image GHCR. Les applications
accèdent aux agents par `http://bao-agent-frontend:8100` ou
`http://bao-agent-worker:8100`, sans recevoir de token OpenBao.

La dev et la prod utilisent des AppRoles et des adresses OpenBao différents.
La stack Exuvie est hors périmètre.

## Vérifications après déploiement

1. Vérifier que les deux agents et les trois applications sont `healthy`.
2. Vérifier qu'aucun port des agents n'est publié.
3. Depuis le frontend, lire le secret frontend sans fournir de token et vérifier
   que `bao-agent-worker` est injoignable.
4. Depuis le mail-agent, lire un secret worker et vérifier que
   `bao-agent-frontend` est injoignable.
5. Vérifier qu'une lecture hors policy renvoie `403`.
6. Redémarrer la stack et confirmer que les fichiers `secret_id` existent
   toujours et que les agents se réauthentifient.

Le reboot complet du VPS ne doit être réalisé qu'après validation de ces tests
sur la dev et dans une fenêtre de maintenance approuvée.
