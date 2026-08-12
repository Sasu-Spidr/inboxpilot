import { redirect } from "next/navigation";

import { currentMfaPendingUser } from "@/lib/auth";
import { mfaFeatureEnabled } from "@/lib/features";

export default async function MfaPage({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  if (!mfaFeatureEnabled()) redirect("/connexion");
  const user = await currentMfaPendingUser();
  if (!user || !user.mfaEnabled) redirect("/connexion");
  const error = (await searchParams)?.error;

  return (
    <main className="mfa-shell">
      <section className="mfa-card">
        <p className="eyebrow">Sécurité du compte</p>
        <h1>Double authentification</h1>
        <p>Entre le code à 6 chiffres généré par ton application d'authentification pour continuer.</p>
        {error && <div className="error">Code invalide ou expiré. Réessaie avec le dernier code affiché.</div>}
        <form action="/api/auth/mfa/verify" method="post" className="mfa-form">
          <label htmlFor="mfa-code">Code de vérification</label>
          <input
            id="mfa-code"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9 ]{6,8}"
            placeholder="123456"
            required
            autoFocus
          />
          <button type="submit">Valider et accéder à mon espace</button>
        </form>
      </section>
    </main>
  );
}
