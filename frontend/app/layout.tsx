import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "InboxPilot",
  description: "Connectez Gmail et Outlook à votre agent mail.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const turnstileEnabled = Boolean(process.env.TURNSTILE_SITE_KEY);

  return (
    <html lang="fr">
      <body>
        {children}
        {turnstileEnabled && (
          <Script
            src="https://challenges.cloudflare.com/turnstile/v0/api.js"
            strategy="afterInteractive"
          />
        )}
      </body>
    </html>
  );
}
