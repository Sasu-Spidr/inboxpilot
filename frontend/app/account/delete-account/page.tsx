import { redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";

export default async function DeleteAccountPage({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  if (!(await currentUser())) redirect("/connexion");
  const params = await searchParams;
  return (
    <main className="dashboard-shell account-privacy-page">
      <nav className="topbar"><a className="ghost-button" href="/dashboard">Retour au tableau de bord</a></nav>
      <section className="info-panel privacy-card danger-zone">
        <p className="eyebrow">Droit à l'effacement</p>
        <h1>Supprimer mon compte</h1>
        <p>Cette action supprime définitivement le compte, les réglages, les journaux applicatifs et les jetons OAuth Gmail et Outlook. L'abonnement actif sera résilié.</p>
        <p>Les éléments de facturation imposés par la loi restent conservés séparément pendant la durée légale.</p>
        {params?.error && <div className="error-banner">Le mot de passe ou le texte de confirmation est incorrect.</div>}
        <form action="/api/account/delete-account" method="post" className="delete-account-form">
          <label>Mot de passe</label>
          <input name="password" type="password" required />
          <label>Écrivez SUPPRIMER pour confirmer</label>
          <input name="confirmation" required pattern="SUPPRIMER" autoComplete="off" />
          <button className="danger-button" type="submit">Supprimer définitivement mon compte</button>
        </form>
      </section>
    </main>
  );
}
