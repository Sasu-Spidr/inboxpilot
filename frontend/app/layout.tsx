import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SPIDR Mail Agent",
  description: "Connectez Gmail et Outlook à votre agent mail.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
