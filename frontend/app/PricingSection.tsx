"use client";

import { useState } from "react";

import type { BillingCycle, PaidPlan } from "@/lib/stripeCore";

const PLANS = [
  {
    name: "Free",
    plan: null as PaidPlan | null,
    monthlyPrice: 0,
    subtitle: "Pour découvrir InboxPilot",
    cta: "Commencer gratuitement",
    features: ["1 boîte connectée", "Emails illimités", "Classement intelligent", "Brouillons manuels"],
  },
  {
    name: "Pro",
    plan: "pro" as PaidPlan | null,
    monthlyPrice: 19,
    subtitle: "Pour les professionnels",
    cta: "Démarrer mon abonnement",
    popular: true,
    features: ["3 boîtes connectées", "Emails illimités", "Actions automatiques", "Brouillons & réponses auto", "Support prioritaire"],
  },
  {
    name: "Business",
    plan: "business" as PaidPlan | null,
    monthlyPrice: 99,
    subtitle: "Pour les gros volumes",
    cta: "Démarrer mon abonnement",
    features: ["Jusqu'à 10 boîtes connectées", "Emails illimités", "Règles avancées & IA", "Statistiques avancées", "Support dédié"],
  },
];

export function PricingSection({ signupHref, checkoutEnabled }: { signupHref: string; checkoutEnabled: boolean }) {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const isYearly = billingCycle === "yearly";

  return (
    <section id="tarifs" className="pricing-section">
      <div className="section-title">
        <h2>Des tarifs simples et transparents</h2>
        <p>Choisissez l&apos;offre qui correspond à vos besoins.</p>
        <div className="billing-toggle" role="group" aria-label="Choisir la période de facturation">
          <button
            type="button"
            className={!isYearly ? "active" : ""}
            aria-pressed={!isYearly}
            onClick={() => setBillingCycle("monthly")}
          >
            Mensuel
          </button>
          <button
            type="button"
            className={isYearly ? "active" : ""}
            aria-pressed={isYearly}
            onClick={() => setBillingCycle("yearly")}
          >
            Annuel
          </button>
          <em>2 mois offerts</em>
        </div>
      </div>
      <div className="pricing-grid">
        {PLANS.map((plan) => (
          <PricingCard
            key={plan.name}
            plan={plan}
            billingCycle={billingCycle}
            signupHref={signupHref}
            checkoutEnabled={checkoutEnabled}
          />
        ))}
      </div>
    </section>
  );
}

function PricingCard({
  plan,
  billingCycle,
  signupHref,
  checkoutEnabled,
}: {
  plan: (typeof PLANS)[number];
  billingCycle: BillingCycle;
  signupHref: string;
  checkoutEnabled: boolean;
}) {
  const isYearly = billingCycle === "yearly";
  const yearlyPrice = plan.monthlyPrice * 10;
  const savings = plan.monthlyPrice * 2;
  const displayedPrice = isYearly ? yearlyPrice : plan.monthlyPrice;
  const period = isYearly ? "/ an" : "/ mois";

  return (
    <article className={plan.popular ? "popular" : ""}>
      {plan.popular && <em>Le plus populaire</em>}
      <h3>{plan.name}</h3>
      <p>{plan.subtitle}</p>
      <div className="pricing-price">
        <strong>{displayedPrice}€</strong>
        <span>{period}</span>
      </div>
      {isYearly && plan.monthlyPrice > 0 && (
        <p className="pricing-saving">
          Soit {Math.round(yearlyPrice / 12)}€/mois · Économisez {savings}€/an (2 mois offerts)
        </p>
      )}
      <ul>
        {plan.features.map((feature) => <li key={feature}>✓ {feature}</li>)}
      </ul>
      {plan.plan && checkoutEnabled ? (
        <form action="/api/checkout" method="post">
          <input type="hidden" name="plan" value={plan.plan} />
          <input type="hidden" name="cycle" value={billingCycle} />
          <button type="submit">{plan.cta}</button>
        </form>
      ) : (
        <a href={signupHref}>{plan.cta}</a>
      )}
    </article>
  );
}
