import QRCode from "qrcode";
import { redirect } from "next/navigation";

import { currentUser, generateMfaSecret, mfaOtpAuthUrl } from "@/lib/auth";

export default async function MfaSetupPage({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  const user = await currentUser();
  if (!user) redirect("/connexion");

  const secret = generateMfaSecret();
  const otpAuthUrl = mfaOtpAuthUrl(user, secret);
  const qrCode = await QRCode.toDataURL(otpAuthUrl, { margin: 1, width: 220 });
  const error = (await searchParams)?.error;

  return (
    <main className="mfa-shell">
      <section className="mfa-card setup">
        <p className="eyebrow">Protection avancée</p>
        <h1>Activer la double authentification</h1>
        <p>
          Scanne ce QR code avec Google Authenticator, Microsoft Authenticator ou 1Password, puis confirme avec le code
          généré.
        </p>

        <div className="mfa-setup-grid">
          <div className="mfa-qr">
            <img src={qrCode} alt="QR code de configuration MFA" />
          </div>
          <div className="mfa-manual">
            <span>Clé manuelle</span>
            <code>{secret.match(/.{1,4}/g)?.join(" ")}</code>
          </div>
        </div>

        {error && <div className="error">Le code ne correspond pas. Vérifie l'application puis réessaie.</div>}
        <form action="/api/auth/mfa/enable" method="post" className="mfa-form">
          <input type="hidden" name="secret" value={secret} />
          <label htmlFor="mfa-code">Code à 6 chiffres</label>
          <input
            id="mfa-code"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9 ]{6,8}"
            placeholder="123456"
            required
          />
          <button type="submit">Activer la double authentification</button>
        </form>
      </section>
    </main>
  );
}
