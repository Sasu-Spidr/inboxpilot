import LegalPage, { CompanyIdentity } from "../LegalPage";

export const metadata = { title: "Conditions générales de vente — InboxPilot" };

export default function CgvPage() {
  return (
    <LegalPage
      title="Conditions générales de vente"
      description="Les présentes conditions encadrent la souscription et la facturation du service professionnel InboxPilot."
    >
      <section>
        <h2>1. Éditeur et champ d’application</h2>
        <CompanyIdentity />
        <p>
          Les présentes conditions générales de vente (« CGV ») s’appliquent à toute souscription payante à InboxPilot par un client agissant
          dans le cadre de son activité professionnelle. Elles complètent les Conditions générales d’utilisation (« CGU »). En souscrivant,
          le Client reconnaît les avoir lues et acceptées.
        </p>
      </section>

      <section>
        <h2>2. Description du service</h2>
        <p>
          InboxPilot est un service logiciel en ligne permettant de connecter des boîtes Gmail et Microsoft Outlook, de classifier des courriels,
          d’appliquer des libellés ou catégories et, selon l’offre et les paramètres choisis, de préparer des brouillons ou d’exécuter des actions automatisées.
          Les fonctionnalités accessibles dépendent de l’offre Free, Pro ou Business présentée au moment de la commande.
        </p>
        <p>
          Les résultats produits par l’intelligence artificielle sont des aides automatisées susceptibles de contenir des erreurs. Le Client conserve
          la maîtrise de sa configuration et demeure responsable de la vérification des brouillons et des actions sensibles.
        </p>
      </section>

      <section>
        <h2>3. Commande et formation du contrat</h2>
        <p>
          Le contrat est formé lorsque le Client sélectionne une offre, renseigne ses informations de paiement dans l’interface Stripe Checkout et
          reçoit la confirmation de sa souscription. Le récapitulatif Stripe indique l’offre, le prix, la périodicité et les taxes éventuellement applicables.
          SPIDR peut refuser ou suspendre une commande en cas de fraude, d’impayé ou d’informations manifestement erronées.
        </p>
      </section>

      <section>
        <h2>4. Prix, facturation et paiement</h2>
        <p>
          Les prix applicables sont ceux affichés sur InboxPilot et dans Stripe Checkout au jour de la commande. Les éventuelles taxes sont précisées avant
          validation. Les offres payantes sont facturées d’avance à chaque période mensuelle ou annuelle choisie. Le paiement est traité par Stripe ;
          SPIDR ne conserve pas les numéros complets de carte bancaire.
        </p>
        <p>
          En cas d’échec de paiement, le Client est invité à régulariser sa situation depuis le portail de facturation. À défaut, tout ou partie des
          fonctions payantes peut être suspendu et le compte ramené aux droits de l’offre Free.
        </p>
      </section>

      <section>
        <h2>5. Durée, renouvellement et résiliation</h2>
        <p>
          L’abonnement est conclu pour la période sélectionnée et renouvelé automatiquement pour une période identique jusqu’à sa résiliation.
          Le Client peut gérer ou résilier son abonnement à tout moment depuis le portail Stripe accessible dans son espace. Sauf indication contraire
          lors de la commande, la résiliation prend effet à la fin de la période déjà payée et n’entraîne pas le remboursement de celle-ci.
        </p>
      </section>

      <section>
        <h2>6. Disponibilité et assistance</h2>
        <p>
          SPIDR met en œuvre les moyens raisonnables pour assurer la disponibilité et la sécurité du service. Des interruptions peuvent intervenir pour
          maintenance, mise à jour, incident de sécurité ou indisponibilité d’un fournisseur tiers. Sauf engagement écrit distinct, aucune disponibilité
          continue ou absence totale d’erreur n’est garantie.
        </p>
      </section>

      <section>
        <h2>7. Responsabilité</h2>
        <p>
          Chaque partie répond des dommages directs résultant de ses manquements prouvés. SPIDR ne saurait être responsable des décisions prises sur la seule
          base d’un classement ou d’un brouillon automatisé, d’une mauvaise configuration par le Client, ni des défaillances imputables à Google, Microsoft,
          Groq, Stripe ou à un cas de force majeure.
        </p>
        <p>
          Dans les limites admises par la loi, la responsabilité totale de SPIDR au titre d’une période de douze mois est plafonnée aux sommes hors taxes
          effectivement versées par le Client pendant cette période. Cette limitation ne s’applique pas en cas de faute lourde, dol, atteinte corporelle ou
          lorsqu’une disposition impérative l’interdit.
        </p>
      </section>

      <section>
        <h2>8. Propriété intellectuelle</h2>
        <p>
          InboxPilot, son code, son interface, ses marques, textes et éléments graphiques restent la propriété exclusive de SPIDR ou de ses concédants.
          La souscription confère uniquement un droit personnel, non exclusif, non cessible et limité à la durée du contrat. Le Client conserve ses droits
          sur ses données et contenus.
        </p>
      </section>

      <section>
        <h2>9. Données personnelles</h2>
        <p>
          Les traitements de données sont décrits dans la <a href="/legal/privacy">Politique de confidentialité</a>. Les conditions d’accès au service et
          les obligations d’usage figurent dans les <a href="/legal/cgu">CGU</a>.
        </p>
      </section>

      <section>
        <h2>10. Droit applicable et litiges</h2>
        <p>
          Les présentes CGV sont régies par le droit français. Les parties chercheront d’abord une solution amiable. À défaut, et sous réserve des règles
          impératives applicables, les juridictions compétentes du ressort du siège de SPIDR seront seules compétentes.
        </p>
      </section>
    </LegalPage>
  );
}
