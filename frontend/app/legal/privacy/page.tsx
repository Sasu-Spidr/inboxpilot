import LegalPage, { CompanyIdentity } from "../LegalPage";

export const metadata = { title: "Politique de confidentialité — InboxPilot" };

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Politique de confidentialité"
      description="Cette politique explique quelles données InboxPilot traite, pourquoi, pendant combien de temps et quels sont vos droits."
    >
      <section>
        <h2>1. Responsable du traitement</h2>
        <CompanyIdentity />
        <p>
          Pour les données de compte, de sécurité et de facturation, SPIDR agit comme responsable du traitement. Pour le contenu des boîtes professionnelles
          connecté par un client, SPIDR agit généralement comme sous-traitant pour fournir InboxPilot selon les instructions et paramètres de ce client.
        </p>
      </section>

      <section>
        <h2>2. Données traitées</h2>
        <ul>
          <li><strong>Compte :</strong> nom, adresse email, identifiant client, rôle, état du compte et preuve d’acceptation des conditions.</li>
          <li><strong>Authentification :</strong> mot de passe haché et salé, paramètres MFA, cookies de session et événements de sécurité.</li>
          <li><strong>Boîtes connectées :</strong> adresse, fournisseur, jetons OAuth chiffrés, identifiants techniques et autorisations accordées.</li>
          <li><strong>Emails :</strong> identifiant, expéditeur, objet et corps nécessaires au classement ; le corps est limité dans les requêtes IA.</li>
          <li><strong>Résultats :</strong> libellé, action, niveau de confiance, brouillon, état de traitement et journaux d’activité.</li>
          <li><strong>Calendrier :</strong> identifiants et horaires occupés nécessaires à l’harmonisation quotidienne des disponibilités.</li>
          <li><strong>Facturation :</strong> offre, statut, identifiants Stripe et historique utile ; les données complètes de carte restent chez Stripe.</li>
          <li><strong>Données techniques :</strong> adresse IP, navigateur, horodatages, erreurs et journaux de sécurité.</li>
        </ul>
      </section>

      <section>
        <h2>3. Finalités et bases légales</h2>
        <div className="legal-table-wrap">
          <table>
            <thead><tr><th>Finalité</th><th>Base légale</th></tr></thead>
            <tbody>
              <tr><td>Créer le compte, connecter les boîtes et fournir les fonctions souscrites</td><td>Exécution du contrat</td></tr>
              <tr><td>Classer les emails, appliquer les règles et préparer les brouillons</td><td>Exécution du contrat et instructions du client</td></tr>
              <tr><td>Gérer l’abonnement, les paiements et les obligations comptables</td><td>Contrat et obligation légale</td></tr>
              <tr><td>Prévenir la fraude, sécuriser les accès et diagnostiquer les incidents</td><td>Intérêt légitime de SPIDR</td></tr>
              <tr><td>Déposer les cookies strictement nécessaires à la session</td><td>Exécution du service</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>4. Traitement par intelligence artificielle</h2>
        <p>
          Pour classifier un email, InboxPilot transmet à Groq son objet, son expéditeur et un extrait du corps limité à 4 000 caractères. Lorsqu’un brouillon
          est demandé, le contenu transmis est limité à 5 000 caractères. Ces données servent à produire le résultat demandé ; InboxPilot ne prend pas de
          décision produisant à elle seule un effet juridique sur la personne concernée. Les règles du compte déterminent ensuite les actions autorisées.
        </p>
      </section>

      <section>
        <h2>5. Destinataires et sous-traitants</h2>
        <p>Les données sont accessibles aux personnes habilitées de SPIDR et, selon la fonction utilisée, aux prestataires suivants :</p>
        <ul>
          <li><strong>Google :</strong> OAuth, Gmail et Google Calendar ;</li>
          <li><strong>Microsoft :</strong> OAuth, Outlook et Microsoft Calendar via Microsoft Graph ;</li>
          <li><strong>Groq :</strong> exécution du modèle de classification et génération de brouillons ;</li>
          <li><strong>Stripe :</strong> paiement, facturation et portail de gestion des abonnements ;</li>
          <li><strong>Cloudflare :</strong> protection anti-robots Turnstile lors de l’inscription ;</li>
          <li><strong>Hostinger :</strong> infrastructure d’hébergement du service ;</li>
          <li><strong>OpenBao et PostgreSQL :</strong> gestion des secrets et stockage applicatif dans l’infrastructure contrôlée par SPIDR.</li>
        </ul>
        <p>
          Certains fournisseurs peuvent traiter des données hors de l’Espace économique européen. SPIDR s’appuie alors sur les mécanismes contractuels et
          garanties proposés par ces fournisseurs conformément au droit applicable.
        </p>
      </section>

      <section>
        <h2>6. Durées de conservation</h2>
        <ul>
          <li>compte et configuration : pendant la relation contractuelle, puis le temps nécessaire à la clôture et aux obligations légales ;</li>
          <li>jetons OAuth : jusqu’à la déconnexion de la boîte, la révocation de l’autorisation ou la suppression du compte ;</li>
          <li>état de classement et journaux fonctionnels : durée nécessaire au fonctionnement, au support et à la résolution des incidents ;</li>
          <li>journaux de sécurité : durée proportionnée à la détection et à l’analyse des incidents ;</li>
          <li>documents de facturation : durée imposée par la réglementation comptable et fiscale.</li>
        </ul>
        <p>
          Lorsqu’une durée précise ne peut être fixée à l’avance, SPIDR applique les critères de nécessité, de sécurité, de prescription et d’obligation légale.
          Les données peuvent être archivées avec des accès restreints lorsqu’elles ne sont plus nécessaires à l’usage courant.
        </p>
      </section>

      <section>
        <h2>7. Sécurité</h2>
        <p>
          SPIDR met en œuvre des mesures techniques et organisationnelles adaptées : chiffrement des jetons OAuth et des secrets MFA, séparation des secrets,
          contrôle d’accès, journalisation, limitation des tentatives, MFA, isolation des conteneurs et communications HTTPS. Aucun système ne garantissant une
          sécurité absolue, les mesures sont réévaluées selon les risques et l’état de l’art.
        </p>
      </section>

      <section>
        <h2>8. Cookies et traceurs</h2>
        <p>
          InboxPilot utilise des cookies strictement nécessaires à la connexion, à la session et au parcours MFA. Cloudflare Turnstile peut traiter des signaux
          techniques nécessaires à la lutte contre les robots. Aucun outil publicitaire ni outil de mesure d’audience non essentiel n’est activé dans
          l’application à la date de cette version. Toute évolution nécessitant un consentement fera l’objet d’une information et d’un choix préalable.
        </p>
      </section>

      <section>
        <h2>9. Vos droits</h2>
        <p>
          Selon le traitement, vous disposez des droits d’accès, de rectification, d’effacement, de limitation, d’opposition et de portabilité. Vous pouvez
          également retirer un consentement lorsque celui-ci constitue la base du traitement. Pour exercer vos droits, écrivez à SPIDR, 60 rue de l’Aveyron,
          95100 Argenteuil, en précisant votre compte et la demande. Une preuve d’identité peut être demandée uniquement en cas de doute raisonnable.
        </p>
        <p>
          Vous pouvez introduire une réclamation auprès de la Commission nationale de l’informatique et des libertés (CNIL), notamment depuis
          <a href="https://www.cnil.fr" target="_blank" rel="noreferrer"> cnil.fr</a>.
        </p>
      </section>

      <section>
        <h2>10. Évolution de la politique</h2>
        <p>
          Cette politique peut évoluer pour refléter les changements du service, des prestataires ou de la réglementation. La date et la version sont indiquées
          en haut de page. Une modification importante est portée à la connaissance des utilisateurs par un moyen approprié.
        </p>
      </section>
    </LegalPage>
  );
}
