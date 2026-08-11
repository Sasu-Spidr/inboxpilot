# Migration OpenBao — export des secrets existants

Ce document décrit comment préparer le fichier de secrets existants pour une migration manuelle vers OpenBao.

Les secrets ne doivent jamais être affichés dans un ticket, un message ou un log. Le script d’export écrit un fichier local avec permissions restrictives et ne imprime pas les valeurs.

## Générer le fichier sur le VPS

Depuis le serveur :

```bash
cd /opt/spidr-mail
python3 scripts/export_openbao_secrets.py --output /root/inboxpilot-openbao-secrets.txt --force
chmod 600 /root/inboxpilot-openbao-secrets.txt
```

Le fichier généré contient :

```ini
# 1. Chiffrement et sécurité
token_encryption_key=<VALEUR>
auth_secret=<VALEUR>
# 2. Base de données
postgres_db=spidr_mail
postgres_user=spidr
postgres_password=<VALEUR>
database_url=<VALEUR>
# 3. Groq
groq_api_key=<VALEUR>
# 4. OAuth Microsoft
microsoft_client_id=<VALEUR>
microsoft_client_secret=<VALEUR>
# 5. OAuth Gmail
gmail_client_config=<JSON_COMPLET>
# 6. URLs Production
oauth_base_url=<VALEUR>
oauth_public_url=<VALEUR>
frontend_base_url=<VALEUR>
```

## Vérifier sans écrire les secrets

```bash
cd /opt/spidr-mail
python3 scripts/export_openbao_secrets.py --check
```

Cette commande indique uniquement les champs manquants. Elle n’affiche pas les secrets.

## Récupération du fichier

Depuis le PC local :

```powershell
scp root@89.116.111.236:/root/inboxpilot-openbao-secrets.txt .\inboxpilot-openbao-secrets.txt
```

Après migration OpenBao, supprimer les copies temporaires :

```bash
shred -u /root/inboxpilot-openbao-secrets.txt 2>/dev/null || rm -f /root/inboxpilot-openbao-secrets.txt
```

Et côté PC, supprimer le fichier local après transmission.

## Important

- Ne pas committer le fichier généré.
- Ne pas coller les valeurs dans Trello, Slack, WhatsApp Web ou un terminal partagé.
- Préférer un transfert chiffré ou un coffre temporaire lorsque c’est possible.
