import LegalPage, { CompanyIdentity } from "../LegalPage";

export const metadata = { title: "Conditions générales d’utilisation — InboxPilot" };

export default function CguPage() {
  return (
    <LegalPage
      title="Conditions générales d’utilisation"
      description="Ces règles définissent les conditions d’accès et d’usage du service InboxPilot."
    >
      <section>
        <h2>1. Objet</h2>
        <CompanyIdentity />
        <p>
          Les présentes conditions générales d’utilisation (« CGU ») régissent l’accès à InboxPilot et son utilisation. Toute création de compte implique
          leur acceptation. Les offres payantes sont également soumises aux <a href="/legal/cgv">CGV</a>.
        </p>
      </section>

      <section>
        <h2>2. Compte utilisateur</h2>
        <p>
          L’utilisateur fournit des informations exactes, conserve la confidentialité de ses identifiants et signale sans délai toute utilisation non
          autorisée. Il est responsable des actions réalisées depuis son compte. SPIDR peut imposer des mesures de sécurité, notamment une authentification
          multifacteur, une limitation de tentatives ou une vérification supplémentaire.
        </p>
      </section>

      <section>
        <h2>3. Connexion des boîtes mail</h2>
        <p>
          L’utilisateur connecte uniquement des boîtes qu’il est autorisé à administrer. L’accès à Gmail et Outlook repose sur les mécanismes OAuth de Google
          et Microsoft. L’utilisateur peut révoquer ces autorisations depuis InboxPilot ou depuis son compte fournisseur. La déconnexion peut interrompre
          immédiatement le classement, la création de brouillons et l’harmonisation des disponibilités de calendrier.
        </p>
      </section>

      <section>
        <h2>4. Paramètres et actions automatisées</h2>
        <p>
          L’utilisateur choisit les libellés, règles et actions applicables à chaque adresse connectée. Les suppressions, réponses automatiques et autres
          actions ne sont exécutées que lorsqu’elles sont disponibles dans l’offre et activées dans les paramètres concernés. L’utilisateur doit vérifier
          sa configuration et surveiller les résultats, en particulier après toute modification.
        </p>
      </section>

      <section>
        <h2>5. Intelligence artificielle</h2>
        <p>
          Les classifications et brouillons sont générés automatiquement et peuvent être inexacts, incomplets ou inadaptés. Ils ne constituent ni un conseil
          juridique, financier ou professionnel, ni une décision humaine. L’utilisateur reste seul responsable de la lecture, de la validation et de l’envoi
          des contenus préparés par le service.
        </p>
      </section>

      <section>
        <h2>6. Usages interdits</h2>
        <p>Il est notamment interdit :</p>
        <ul>
          <li>d’utiliser InboxPilot pour accéder sans autorisation à une boîte, à des données ou à un système ;</li>
          <li>de contourner les limites d’offre, contrôles de sécurité ou mesures anti-abus ;</li>
          <li>de transmettre des contenus illicites, malveillants ou portant atteinte aux droits de tiers ;</li>
          <li>d’extraire, revendre, copier ou désassembler le service en dehors des cas autorisés par la loi ;</li>
          <li>d’utiliser les fonctions automatiques à des fins de spam, fraude, harcèlement ou surveillance illicite.</li>
        </ul>
      </section>

      <section>
        <h2>7. Suspension et résiliation</h2>
        <p>
          SPIDR peut suspendre temporairement un compte en cas de risque de sécurité, usage illicite, violation grave des présentes conditions, impayé ou
          nécessité technique urgente. Lorsque la situation le permet, l’utilisateur est informé du motif et peut régulariser. Une violation grave ou répétée
          peut entraîner la résiliation du compte, sans préjudice des droits déjà acquis et des obligations légales de conservation.
        </p>
      </section>

      <section>
        <h2>8. Services tiers et disponibilité</h2>
        <p>
          Certaines fonctions dépendent de Google, Microsoft, Groq, Stripe et Cloudflare. Une modification de leurs API, de leurs autorisations ou de leur
          disponibilité peut limiter temporairement InboxPilot. SPIDR peut faire évoluer le service pour des raisons techniques, réglementaires ou de sécurité,
          en veillant à ne pas altérer sans motif légitime les fonctions essentielles d’une offre payante en cours.
        </p>
      </section>

      <section>
        <h2>9. Propriété et données</h2>
        <p>
          L’utilisateur conserve la propriété de ses contenus. Il accorde à SPIDR les droits strictement nécessaires à leur traitement pour fournir et sécuriser
          le service. Aucun droit sur le logiciel InboxPilot n’est transféré. Les règles relatives aux données personnelles figurent dans la
          <a href="/legal/privacy"> Politique de confidentialité</a>.
        </p>
      </section>

      <section>
        <h2>10. Droit applicable</h2>
        <p>
          Les CGU sont régies par le droit français. Toute contestation doit d’abord faire l’objet d’une tentative de résolution amiable avant la saisine de
          la juridiction compétente.
        </p>
      </section>
    </LegalPage>
  );
}
