# SPIDR Mail Agent

Agent mail léger pour Gmail et Hotmail/Outlook.

Il lit les emails non lus, les classe avec l’IA, applique un label/catégorie, déplace si nécessaire, et crée des brouillons de réponse. Il n’envoie jamais d’email automatiquement.

Pas de dashboard. Pas de CRM. Pas de PostgreSQL. Pas de SaaS lourd.

## Commandes utiles

Installer :

```powershell
pip install -r requirements.txt
```

Tester :

```powershell
pytest -q --basetemp .pytest_tmp
```

Lancer un cycle :

```powershell
python main.py --once
```

Lancer le worker :

```powershell
python main.py
```

Lancer Docker :

```bash
docker compose up -d --build
docker compose logs -f mail-agent
```

Lancer l’onboarding OAuth :

```bash
docker compose up -d --build oauth-onboarding
```

## Onboarding client

Le client ne touche pas au repo, ne voit pas les tokens et ne copie aucun secret.

Il clique juste sur un lien :

```text
https://connect.example.com/connect/gmail?client=collegue&account=main
```

ou :

```text
https://connect.example.com/connect/hotmail?client=collegue&account=main
```

Après autorisation, le token OAuth est chiffré automatiquement dans `data/tokens/`.

## Documentation client

Voir :

```text
docs/CLIENT_ONBOARDING.md
```

## Configuration

- Clients : `config/settings.yaml`
- Labels : `config/labels.yaml`
- Règles : `config/rules.yaml`
- Secrets runtime : `.env`, `secrets/`, `data/`

Ces fichiers sensibles ne doivent jamais être commit.
