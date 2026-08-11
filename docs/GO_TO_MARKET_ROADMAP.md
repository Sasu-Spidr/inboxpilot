# InboxPilot - Roadmap Go-to-Market

**Document de référence pour la commercialisation du produit**

Date: 2026-08-10
Version: 1.0
Statut: 🔴 Pré-commercialisation

---

## Vue d'ensemble

InboxPilot est techniquement solide avec une architecture Docker fonctionnelle, un agent IA performant (Groq/Qwen), et une landing page moderne. Les gaps principaux se situent sur les aspects **monétisation**, **légal**, et **opérations**.

### État actuel
- ✅ Agent IA de classification fonctionnel
- ✅ OAuth Gmail + Hotmail/Microsoft
- ✅ Frontend Next.js + Dashboard
- ✅ Landing page avec pricing (non fonctionnel)
- ✅ Docker Compose multi-services
- ⚠️ Pas de système de paiement
- ⚠️ Pas de légal (CGV/CGU/Privacy)
- ⚠️ Pas de déploiement automatisé
- ⚠️ Pas de monitoring production

---

## 1. Produit & Monétisation 🔴 CRITIQUE

### 1.1 Système de paiement

**Priorité:** P0 (Bloquant)
**Effort estimé:** 5-7 jours

#### Stripe Integration
- [ ] Setup compte Stripe + webhook endpoint
- [ ] Créer les produits Stripe (Free/Pro/Business)
- [ ] Intégration Stripe Checkout pour souscription
- [ ] Webhooks Stripe pour sync état abonnement
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
- [ ] Stockage `subscription_tier` et `subscription_status` en DB
- [ ] Stripe Customer Portal (gestion abonnement côté user)

#### Schema DB requis
```sql
ALTER TABLE users ADD COLUMN subscription_tier VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'active';
ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255);
ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(255);
ALTER TABLE users ADD COLUMN quota_emails_month INTEGER DEFAULT 200;
ALTER TABLE users ADD COLUMN quota_reset_date TIMESTAMP;
```

#### Enforcement des quotas
- [ ] Middleware de vérification quota avant traitement email
- [ ] Compteur mensuel d'emails traités par client
- [ ] Reset automatique chaque mois
- [ ] UI pour afficher consommation quota
- [ ] Email notification à 80% et 100% du quota

**Fichiers à modifier:**
- `frontend/app/api/checkout/route.ts` (nouveau)
- `frontend/app/api/webhooks/stripe/route.ts` (nouveau)
- `frontend/lib/db.ts` (ajout fonctions subscription)
- `main.py` (check quota avant `process_email()`)
- `frontend/app/dashboard/page.tsx` (affichage quota)

---

### 1.2 UX & Onboarding

**Priorité:** P1 (Important)
**Effort estimé:** 3-4 jours

- [ ] **Onboarding wizard** multi-étapes
  1. Création compte
  2. Sélection du plan (avec trial 14j pour Pro)
  3. Connexion Gmail/Outlook
  4. Configuration des labels (avec templates)
  5. Premier email de test
- [ ] **Tutoriels in-app** (tooltips avec Shepherd.js ou similaire)
- [ ] **Notifications** (quota warnings, classification errors)
- [ ] **Internationalization** (i18n en/fr minimum)

**Fichiers à créer:**
- `frontend/app/onboarding/page.tsx`
- `frontend/components/OnboardingWizard.tsx`
- `frontend/lib/i18n.ts`

---

## 2. Légal & Conformité 🔴 CRITIQUE

### 2.1 Documents légaux

**Priorité:** P0 (Bloquant en Europe)
**Effort estimé:** 2-3 jours (avec templates)

- [ ] **CGV (Conditions Générales de Vente)**
  - Prix et modalités de paiement
  - Durée d'engagement et résiliation
  - Garanties et limitations de responsabilité
  - Propriété intellectuelle
- [ ] **CGU (Conditions Générales d'Utilisation)**
  - Règles d'usage du service
  - Obligations de l'utilisateur
  - Suspension/résiliation de compte
- [ ] **Politique de confidentialité (Privacy Policy)**
  - Données collectées (emails, metadata, logs)
  - Finalités du traitement (classification IA)
  - Sous-traitants (Groq, Google, Microsoft)
  - Durée de conservation
  - Droits RGPD (accès, rectification, suppression)
  - Cookies et tracking
- [ ] **Mentions légales**
  - Raison sociale, SIRET, adresse
  - Hébergeur (nom, adresse)
  - Directeur de publication
  - Contact DPO si applicable

**Ressources:**
- Templates: https://www.cnil.fr/fr/modeles
- Générateur CGV/CGU: https://www.legalplace.fr
- Avocat spécialisé SaaS (recommandé pour validation)

**Fichiers à créer:**
- `frontend/app/legal/cgv/page.tsx`
- `frontend/app/legal/cgu/page.tsx`
- `frontend/app/legal/privacy/page.tsx`
- `frontend/app/legal/mentions/page.tsx`

---

### 2.2 RGPD Compliance

**Priorité:** P0 (Obligatoire EU)
**Effort estimé:** 3-5 jours

- [ ] **Consentement explicite** pour traitement IA des emails
  - Checkbox lors de l'onboarding
  - Stockage du consentement en DB avec timestamp
- [ ] **Droit d'accès**
  - Export de toutes les données user (emails classés, settings, logs)
  - Format: JSON ou ZIP
- [ ] **Droit à l'effacement**
  - Suppression complète du compte et données associées
  - Conservation logs légaux (facturation) selon obligation légale
- [ ] **Droit à la portabilité**
  - Export des données dans un format réutilisable
- [ ] **Registre des traitements**
  - Documentation des flux de données
  - Cartographie des sous-traitants
- [ ] **DPO (Data Protection Officer)**
  - Si > 250 employés ou traitement à grande échelle
  - Sinon, désigner un responsable interne

**Fichiers à créer:**
- `frontend/app/account/export-data/page.tsx`
- `frontend/app/account/delete-account/page.tsx`
- `docs/RGPD_COMPLIANCE.md`

---

### 2.3 OAuth Transparency

**Priorité:** P1 (Confiance utilisateur)
**Effort estimé:** 1 jour

- [ ] Page explicative des **scopes OAuth demandés**
  - Gmail: `gmail.modify` (lecture + labels + suppression)
  - Outlook: `Mail.ReadWrite` (lecture + modification)
- [ ] **Justification claire** de chaque permission
- [ ] **Vidéo démo** du flow de connexion
- [ ] **FAQ sécurité** (chiffrement tokens, pas de revente données, etc.)

**Fichier à créer:**
- `frontend/app/security/page.tsx`

---

## 3. Infrastructure & Opérations 🟠 IMPORTANT

### 3.1 Déploiement automatisé

**Priorité:** P1 (Important)
**Effort estimé:** 2-3 jours

**Actuellement:** CI tests uniquement, pas de déploiement

#### GitHub Actions workflow
- [ ] `.github/workflows/deploy.yml`
  - Trigger: push sur `main` ou tag `v*`
  - Steps:
    1. Run tests
    2. Build Docker images
    3. Push to registry (GHCR ou Docker Hub)
    4. SSH to VPS
    5. Pull images + `docker-compose up -d`
    6. Health check
    7. Rollback si échec
- [ ] **Secrets management**
  - GitHub Secrets pour SSH keys, DB passwords
  - Rotation périodique des credentials
- [ ] **Staging environment**
  - Déploiement auto sur `staging` branch
  - Tests E2E avant prod

#### Infrastructure as Code (optionnel mais recommandé)
- [ ] Terraform ou Pulumi pour provisionner VPS
- [ ] State backend distant (S3 ou Terraform Cloud)

---

### 3.2 Monitoring & Observabilité

**Priorité:** P1 (Important)
**Effort estimé:** 2-3 jours

#### Error tracking
- [ ] **Sentry** (frontend + backend)
  - Capture exceptions non gérées
  - Source maps pour React
  - Breadcrumbs pour debug
  - Alerting Slack/Email sur erreurs critiques

#### Logs centralisés
- [ ] **Loki + Grafana** ou **CloudWatch Logs**
  - Agrégation logs des 4 services Docker
  - Recherche full-text
  - Dashboards par service
- [ ] **Log retention policy** (30 jours minimum)

#### Métriques business
- [ ] Dashboard Grafana avec:
  - Emails classés / jour (par client et global)
  - Latence classification IA (Groq API)
  - Taux d'erreur par type (OAuth, classification, actions)
  - Consommation quota par plan
  - Taux de conversion Free → Pro
  - Churn rate mensuel
- [ ] **Alerting** sur:
  - Spike d'erreurs (> 5% sur 5min)
  - Latence Groq > 10s
  - Quota dépassé (alerte admin)

#### Uptime monitoring
- [ ] **UptimeRobot** ou **Pingdom**
  - Check HTTP sur `https://app.spidr.fr` (1min interval)
  - Check sur `/health` endpoint
  - Alerting SMS/Email si down > 2min

**Fichiers à créer:**
- `docker-compose.monitoring.yml` (Prometheus, Grafana, Loki)
- `main.py` (instrumentation Sentry + métriques Prometheus)
- `frontend/lib/sentry.ts`

---

### 3.3 Sécurité

**Priorité:** P1 (Important)
**Effort estimé:** 3-4 jours

- [ ] **Audit de sécurité externe**
  - Pentest sur flux OAuth
  - Vérification stockage tokens (chiffrement Fernet ✅)
  - Test OWASP Top 10
- [ ] **Rate limiting**
  - API publiques: 100 req/min par IP
  - Login: 5 tentatives/15min
  - Middleware Express ou Nginx
- [ ] **IP whitelist** pour endpoints admin
- [ ] **2FA** (authentification à deux facteurs)
  - TOTP avec Google Authenticator
  - Backup codes
- [ ] **CSP (Content Security Policy)** headers
- [ ] **HTTPS strict** (HSTS headers)
- [ ] **Secrets rotation**
  - TOKEN_ENCRYPTION_KEY
  - DB passwords
  - OAuth client secrets

**Fichiers à modifier:**
- `frontend/middleware.ts` (rate limiting)
- `frontend/lib/auth.ts` (2FA)
- `docker-compose.yml` (variables d'environnement sécurisées)

---

### 3.4 Scalabilité

**Priorité:** P2 (Nice to have, pré-scale)
**Effort estimé:** 5-7 jours

**Problème actuel:** Polling synchrone toutes les 60s dans `main.py`

#### Queue system
- [ ] **Redis + Bull/BullMQ** ou **RabbitMQ**
  - Queue `email_processing` pour découpler polling et traitement
  - Workers parallèles pour scalabilité
  - Retry logic avec backoff exponentiel
- [ ] **Job priorities**
  - Pro users: priorité haute
  - Free users: priorité normale
- [ ] **Dead letter queue** pour emails en échec

#### Database optimization
- [ ] **Indexes** sur colonnes fréquemment requêtées
  ```sql
  CREATE INDEX idx_users_client_id ON users(client_id);
  CREATE INDEX idx_users_email ON users(email);
  CREATE INDEX idx_users_subscription_tier ON users(subscription_tier);
  ```
- [ ] **Partitioning** si > 1M lignes (par date)
- [ ] **Connection pooling** (déjà géré par `pg`)

#### Caching
- [ ] **Redis** pour:
  - Settings YAML (TTL 5min)
  - Labels mappings (TTL 1h)
  - User subscription tier (TTL 10min)
- [ ] **Cache invalidation** sur update settings

#### Load balancing
- [ ] Nginx reverse proxy
- [ ] Round-robin entre N instances du worker
- [ ] Health checks

**Fichiers à créer/modifier:**
- `worker_queue.py` (nouveau worker avec Redis)
- `docker-compose.yml` (ajout service Redis)
- `main.py` (publisher vers queue au lieu de traitement direct)

---

### 3.5 Backup & Disaster Recovery

**Priorité:** P1 (Important)
**Effort estimé:** 1-2 jours

- [ ] **PostgreSQL backups automatisés**
  - Cron job quotidien: `pg_dump` vers S3/Backblaze
  - Retention: 7 daily, 4 weekly, 12 monthly
  - Chiffrement des backups
- [ ] **Test de restauration mensuel**
  - Procédure documentée
  - Validation sur environnement staging
- [ ] **Disaster Recovery Plan**
  - RTO (Recovery Time Objective): < 4h
  - RPO (Recovery Point Objective): < 24h
  - Playbook pour incidents majeurs
- [ ] **Backups de configurations**
  - `config/settings.yaml`
  - `config/labels.yaml`
  - Secrets (chiffrés)

**Fichiers à créer:**
- `scripts/backup.sh`
- `scripts/restore.sh`
- `docs/DISASTER_RECOVERY.md`

---

## 4. Support & Go-to-Market 🟡 NÉCESSAIRE

### 4.1 Support client

**Priorité:** P1 (Important)
**Effort estimé:** 2-3 jours

- [ ] **Helpdesk** (Zendesk, Intercom ou Crisp)
  - Ticketing system
  - SLA: 24h pour Free, 4h pour Pro, 1h pour Business
- [ ] **Live chat** (Crisp ou Intercom)
  - Disponible 10h-18h en semaine
  - Chatbot pour FAQ en dehors des heures
- [ ] **Knowledge base** / FAQ
  - "Comment connecter Gmail ?"
  - "Pourquoi mon email n'a pas été classé ?"
  - "Comment annuler mon abonnement ?"
- [ ] **Email support**
  - `support@inboxpilot.com`
  - Auto-responder avec délai de réponse
- [ ] **Status page** (https://status.inboxpilot.com)
  - Statut des services en temps réel
  - Historique des incidents
  - Abonnement aux notifications

**Coûts estimés:**
- Crisp: Gratuit jusqu'à 2 agents
- Zendesk: ~50€/mois pour 2 agents
- Status page: Instatus (20€/mois) ou Statuspage (100€/mois)

---

### 4.2 Marketing & Acquisition

**Priorité:** P2 (Important après lancement)
**Effort estimé:** Continu

#### SEO
- [ ] **Mots-clés cibles**
  - "assistant email IA"
  - "tri automatique gmail"
  - "classification email intelligence artificielle"
  - "productivité email"
- [ ] **Content marketing**
  - Blog posts: "10 astuces pour gérer ses emails"
  - Guides: "Comment atteindre inbox zero avec l'IA"
- [ ] **Backlinks**
  - Lister sur Product Hunt, BetaList, Hacker News
  - Partenariats avec blogs productivité

#### Analytics & Conversion
- [ ] **Google Analytics 4** ou **Plausible**
  - Tracking conversions (signup, upgrade)
  - Funnels (landing → signup → activation)
  - Attribution des sources (SEO, ads, referral)
- [ ] **Hotjar** ou **Microsoft Clarity**
  - Heatmaps
  - Session recordings
  - Feedback polls

#### Email marketing
- [ ] **Newsletter** (Mailchimp, SendGrid ou Brevo)
  - Drip campaign onboarding
  - Monthly updates
  - Product announcements
- [ ] **Transactional emails**
  - Confirmation d'inscription
  - Reset password
  - Quota warnings
  - Facturation (via Stripe)

#### Referral program
- [ ] **Parrainage** (Rewardful ou custom)
  - Offrir 1 mois gratuit pour chaque filleul
  - 20% de commission récurrente pour affiliés

**Fichiers à créer:**
- `frontend/app/blog/page.tsx`
- `frontend/lib/analytics.ts`
- Scripts email templates

---

### 4.3 Documentation

**Priorité:** P2 (Nice to have)
**Effort estimé:** 2-3 jours

- [ ] **API documentation** (si API publique)
  - OpenAPI/Swagger spec
  - Postman collection
  - SDKs (Python, Node.js)
- [ ] **Changelog**
  - Historique des releases
  - Format: https://keepachangelog.com
- [ ] **Migration guides**
  - Free → Pro
  - Import depuis autre service
- [ ] **Video tutorials**
  - YouTube channel
  - "Comment démarrer en 2 minutes"

**Fichiers à créer:**
- `CHANGELOG.md`
- `docs/API_REFERENCE.md`

---

## 5. Plan d'action recommandé

### Phase 1 - MVP Commercial (2-3 semaines) 🚀

**Objectif:** Pouvoir accepter les premiers paiements légalement

| Tâche | Effort | Priorité |
|-------|--------|----------|
| Stripe checkout + webhooks | 5j | P0 |
| Enforcement quotas | 2j | P0 |
| CGV + CGU + Privacy Policy | 2j | P0 |
| Mentions légales | 0.5j | P0 |
| Consentement RGPD + export données | 2j | P0 |
| Sentry error tracking | 1j | P1 |
| CI/CD deployment | 2j | P1 |
| PostgreSQL backups auto | 1j | P1 |
| Zendesk/Crisp setup | 1j | P1 |
| **Total** | **~16.5 jours** | |

**Livrable:** Version 1.0 commercialisable avec paiement, légal OK, monitoring de base.

---

### Phase 2 - Optimisation & Growth (1-2 mois)

| Tâche | Effort | Priorité |
|-------|--------|----------|
| Onboarding wizard | 3j | P1 |
| Internationalization (en/fr) | 2j | P1 |
| Security audit + fixes | 4j | P1 |
| Rate limiting | 1j | P1 |
| Monitoring avancé (Grafana) | 3j | P1 |
| Status page | 1j | P1 |
| SEO + blog | 5j | P2 |
| Analytics tracking | 2j | P2 |
| **Total** | **~21 jours** | |

**Livrable:** Produit robuste, sécurisé, avec acquisition clients.

---

### Phase 3 - Scale (3-6 mois)

| Tâche | Effort | Priorité |
|-------|--------|----------|
| Queue system (Redis/RabbitMQ) | 5j | P2 |
| Load balancing | 2j | P2 |
| Multi-region deployment | 7j | P2 |
| API publique + docs | 10j | P2 |
| Referral program | 3j | P2 |
| **Total** | **~27 jours** | |

**Livrable:** Infrastructure scalable pour 10k+ utilisateurs.

---

## 6. Budget estimé

### Développement
- Phase 1 (MVP): 16.5j × 500€/j = **8 250€**
- Phase 2 (Growth): 21j × 500€/j = **10 500€**
- Phase 3 (Scale): 27j × 500€/j = **13 500€**

**Total dev:** ~32 250€ (en interne ou freelance)

### Services mensuels (après lancement)
| Service | Plan | Coût/mois |
|---------|------|-----------|
| Stripe | 2.9% + 0.30€ par transaction | Variable |
| VPS (production) | 4vCPU, 8GB RAM | 40€ |
| VPS (staging) | 2vCPU, 4GB RAM | 20€ |
| Sentry | Team (50k events) | 26€ |
| Zendesk | Essential | 50€ |
| Status page (Instatus) | Pro | 20€ |
| Backups (Backblaze B2) | 100GB | 5€ |
| Domain + SSL | - | 2€ |
| Email (SendGrid) | 50k emails | 15€ |
| **Total mensuel** | | **~178€ + Stripe fees** |

**Pour 100 clients Pro (1900€/mois MRR):**
- Fees Stripe: ~60€
- Coûts fixes: 178€
- **Marge brute: ~1662€ (87%)** 🎯

---

## 7. Risques & Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| Ban OAuth API (Gmail/Outlook) | 🔴 Critique | Faible | Respecter scrupuleusement ToS, rate limits, avoir un plan B (IMAP) |
| RGPD non-compliance → amende | 🔴 Critique | Moyenne | Validation avocat, audit CNIL |
| Groq API down/changement pricing | 🟠 Majeur | Moyenne | Fallback vers OpenAI, anthropic |
| Churn élevé (> 10%/mois) | 🟠 Majeur | Moyenne | Onboarding solide, support réactif, amélioration continue |
| Sécurité (fuite tokens OAuth) | 🔴 Critique | Faible | Audit sécurité, chiffrement Fernet ✅, 2FA |
| Scalabilité (> 1000 users) | 🟡 Mineur | Moyenne | Queue system (Phase 3) |

---

## 8. KPIs à suivre

### Produit
- **Activation rate:** % users qui connectent un compte email (cible: > 80%)
- **Time to first value:** Temps avant premier email classé (cible: < 5min)
- **Classification accuracy:** % emails bien classés selon feedback user (cible: > 90%)

### Business
- **MRR (Monthly Recurring Revenue):** Revenu mensuel récurrent
- **Conversion Free → Pro:** % (cible: > 5%)
- **Churn rate:** % clients qui annulent (cible: < 5%/mois)
- **CAC (Customer Acquisition Cost):** Coût acquisition client
- **LTV (Lifetime Value):** Valeur vie client (cible: LTV/CAC > 3)

### Tech
- **Uptime:** Disponibilité du service (cible: > 99.5% soit 3.6h downtime/mois max)
- **API latency (p95):** Groq classification (cible: < 5s)
- **Error rate:** % requêtes en erreur (cible: < 0.5%)

---

## 9. Checklist finale avant lancement

### Produit
- [ ] Stripe en mode production (pas test)
- [ ] Tests de bout en bout (signup → paiement → classification → actions)
- [ ] Multi-browser testing (Chrome, Firefox, Safari)
- [ ] Mobile responsive
- [ ] Performance Lighthouse > 80

### Légal
- [ ] CGV/CGU/Privacy en ligne
- [ ] Consentement RGPD trackable
- [ ] Email de confirmation avec liens légaux

### Infrastructure
- [ ] CI/CD testé sur staging
- [ ] Rollback plan documenté
- [ ] Backups automatiques testés
- [ ] Monitoring alerts configurées

### Marketing
- [ ] Landing page SEO optimisée
- [ ] Google Analytics / Plausible actif
- [ ] Email transactionnel configuré
- [ ] Support email fonctionnel

### Communication
- [ ] Annonce Product Hunt
- [ ] Post LinkedIn/Twitter
- [ ] Email early adopters
- [ ] Status page publique

---

## 10. Ressources utiles

### Légal
- CNIL: https://www.cnil.fr
- Modèles RGPD: https://www.cnil.fr/fr/modeles
- LegalPlace (CGV/CGU): https://www.legalplace.fr

### Paiement
- Stripe docs: https://stripe.com/docs
- Stripe webhooks: https://stripe.com/docs/webhooks

### Monitoring
- Sentry: https://sentry.io
- Grafana: https://grafana.com
- UptimeRobot: https://uptimerobot.com

### Support
- Crisp: https://crisp.chat (gratuit jusqu'à 2 agents)
- Zendesk: https://www.zendesk.fr
- Instatus: https://instatus.com

### Infrastructure
- GitHub Actions: https://docs.github.com/en/actions
- Docker best practices: https://docs.docker.com/develop/dev-best-practices/

---

**Prochaine étape recommandée:** Commencer par la Phase 1 (MVP Commercial) avec focus sur Stripe + Légal.

Contact: Pour questions sur cette roadmap, voir `docs/CLIENT_ONBOARDING.md`
