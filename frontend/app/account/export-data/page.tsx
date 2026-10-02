import { redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";

export default async function ExportDataPage() {
  if (!(await currentUser())) redirect("/connexion");
  return (
    <main className="dashboard-shell account-privacy-page">
      <nav className="topbar"><a className="ghost-button" href="/dashboard">Retour au tableau de bord</a></nav>
      <section className="info-panel privacy-card">
        <p className="eyebrow">Données personnelles</p>
        <h1>Exporter mes données</h1>
        <p>Téléchargez un fichier JSON contenant les informations de votre compte, vos boîtes connectées, vos réglages, les emails classés et vos journaux d'activité.</p>
        <p>Les mots de passe, secrets MFA et jetons OAuth ne sont jamais inclus.</p>
        <a className="primary-link" href="/api/account/export-data">Télécharger mon export JSON</a>
      </section>
    </main>
  );
}
