# Registre RGPD InboxPilot

## Statut du document

Ce document décrit les mesures techniques mises en place. Il doit être relu et validé par un avocat spécialisé avant la commercialisation. Cette validation juridique ne peut pas être réalisée par le code ou les tests.

## Responsable et finalités

Le responsable de traitement est SASU SPIDR. InboxPilot traite les données nécessaires pour créer et sécuriser un compte, connecter des boîtes Gmail ou Outlook, classer les nouveaux emails, appliquer les règles choisies et gérer la facturation.

Le contenu d'un email n'est traité par l'agent qu'après un consentement explicite, horodaté et versionné. En l'absence de preuve de consentement, le worker refuse de construire les connecteurs et de traiter un message.

## Données traitées

- identité et adresse de connexion du titulaire du compte ;
- métadonnées des boîtes connectées ;
- contenu, expéditeur, objet et identifiant technique des emails nouveaux à classer ;
- libellés, règles et préférences définis par l'utilisateur ;
- journaux de classement, de sécurité et d'erreur ;
- références Stripe et état de l'abonnement ;
- jetons OAuth chiffrés au repos.

Les mots de passe sont dérivés avec scrypt et un sel aléatoire. Les jetons OAuth sont chiffrés avec `TOKEN_ENCRYPTION_KEY`. Les secrets applicatifs sont lus via les agents OpenBao cloisonnés.

## Bases légales

- exécution du contrat pour le compte, la connexion des boîtes, la configuration et la facturation ;
- consentement explicite pour l'analyse du contenu des emails par IA ;
- intérêt légitime pour la sécurité, la lutte contre les abus et les journaux techniques ;
- obligation légale pour les pièces et traces de facturation conservées après suppression du compte.

## Sous-traitants et destinataires

- Google : OAuth et Gmail ;
- Microsoft : OAuth, Outlook et Microsoft 365 ;
- Groq : exécution du modèle de classification et de génération de brouillons ;
- Stripe : paiement, abonnement, factures et portail client ;
- Hostinger et l'infrastructure SPIDR : hébergement technique ;
- OpenBao : gestion interne des secrets.

La liste doit être comparée périodiquement aux services réellement configurés et aux contrats de sous-traitance en vigueur.

## Accès et portabilité

L'utilisateur authentifié peut télécharger `/account/export-data`. Le fichier JSON contient exclusivement les données liées à son `client_id` : compte, boîtes sans jetons, réglages, classifications et journaux. Les mots de passe, secrets MFA, secrets applicatifs et jetons OAuth sont exclus.

## Effacement

L'utilisateur authentifié doit confirmer son mot de passe et saisir `SUPPRIMER`. Le traitement :

1. résilie l'abonnement Stripe actif ;
2. supprime les jetons OAuth et l'inscription des boîtes ;
3. supprime les réglages et journaux applicatifs du client ;
4. demande au worker de purger l'état chiffré des messages traités ;
5. supprime le compte, les sessions et les événements de sécurité associés ;
6. conserve séparément le minimum de références de facturation requis par la loi.

## Durées et revue

- données du compte et emails classés : jusqu'à la suppression du compte ou la fin du service ;
- journaux de sécurité : durée à fixer et valider juridiquement, puis automatiser ;
- données de facturation : durée légale applicable aux obligations comptables françaises ;
- sauvegardes : durée de rétention de l'infrastructure à documenter et à inclure dans la procédure d'effacement différé.

## Sécurité et traçabilité

Les accès sont authentifiés, les exports sont privés et servis avec `no-store`, les suppressions exigent une confirmation forte, et les lectures de secrets sont auditées par OpenBao. Les incidents et demandes RGPD doivent être consignés avec la date, l'identité du demandeur, les actions réalisées et le délai de réponse.

## Validation juridique restante

Avant mise en production commerciale, un avocat doit valider les bases légales, les durées, les mentions d'information, les contrats de sous-traitance, les transferts éventuels hors UE et le registre ci-dessus.
