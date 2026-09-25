# Accès Python aux secrets OpenBao

Le backend n'utilise plus `BAO_TOKEN`, `.env` ou `hvac` directement. Les
conteneurs Python interrogent exclusivement `bao-agent-worker` avec
`bao_secrets.py`. L'agent injecte son token sans l'exposer à l'application.

Pour comprendre les chemins et les zones, consulter :

- [OPENBAO_SECRETS.md](OPENBAO_SECRETS.md) ;
- [OPENBAO_AGENTS.md](OPENBAO_AGENTS.md) ;
- [DEPLOYMENT.md](DEPLOYMENT.md).

Un nouveau secret worker doit être ajouté à `SECRET_LOCATIONS` dans
`bao_secrets.py`, après ajout du champ OpenBao et validation de sa policy. Il
ne doit jamais bénéficier d'un repli sur une variable d'environnement.
