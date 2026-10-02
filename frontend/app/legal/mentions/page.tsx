import LegalPage, { COMPANY } from "../LegalPage";

export const metadata = { title: "Mentions légales - InboxPilot" };

export default function MentionsLegalesPage() {
  return (
    <LegalPage
      title="Mentions légales"
      description="Informations relatives à l’éditeur, au directeur de la publication et à l’hébergement du service InboxPilot."
    >
      <section>
        <h2>1. Éditeur du site</h2>
        <p>
          Le site et le service InboxPilot sont édités par <strong>{COMPANY.name}</strong>, {COMPANY.legalForm}.
        </p>
        <ul>
          <li>Siège social : {COMPANY.address}</li>
          <li>SIRET : {COMPANY.siret}</li>
          <li>Immatriculation : {COMPANY.registration}</li>
          <li>Numéro de TVA intracommunautaire : {COMPANY.vat}</li>
        </ul>
      </section>

      <section>
        <h2>2. Directeur de la publication</h2>
        <p>Le directeur de la publication est {COMPANY.representative}.</p>
      </section>

      <section>
        <h2>3. Hébergement</h2>
        <p>
          Le service est hébergé par <strong>Hostinger International Limited</strong>, société privée à responsabilité limitée de droit chypriote.
        </p>
        <ul>
          <li>Adresse : 61 Lordou Vironos Street, Lumiel Building, 4e étage, 6023 Larnaca, Chypre</li>
          <li>Téléphone : +370 645 03378</li>
          <li>Site internet : <a href="https://www.hostinger.fr" target="_blank" rel="noreferrer">www.hostinger.fr</a></li>
        </ul>
      </section>

      <section>
        <h2>4. Propriété intellectuelle</h2>
        <p>
          Les textes, interfaces, éléments graphiques, marques, logiciels et autres contenus composant InboxPilot sont protégés par les règles relatives
          à la propriété intellectuelle. Toute reproduction, représentation, adaptation ou exploitation non autorisée, totale ou partielle, est interdite.
        </p>
      </section>

      <section>
        <h2>5. Responsabilité</h2>
        <p>
          SPIDR met en œuvre des moyens raisonnables pour assurer l’exactitude des informations et la disponibilité du service. SPIDR ne peut toutefois
          garantir l’absence d’erreur ou d’interruption et ne saurait être tenue responsable d’un dommage résultant d’un usage inadapté du service,
          d’une mauvaise configuration ou d’un service tiers.
        </p>
      </section>

      <section>
        <h2>6. Données personnelles</h2>
        <p>
          Les informations relatives aux traitements de données personnelles, aux destinataires, aux durées de conservation et à l’exercice des droits
          sont détaillées dans la <a href="/legal/privacy">politique de confidentialité</a>.
        </p>
      </section>
    </LegalPage>
  );
}
