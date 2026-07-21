"use client";

import { useState } from "react";

type BillingCycle = "monthly" | "yearly";

const PLANS = [
  {
    name: "Free",
    monthlyPrice: 0,
    subtitle: "Pour découvrir InboxPilot",
    cta: "Commencer gratuitement",
    features: ["1 boîte connectée", "200 emails / mois", "Classement intelligent", "Brouillons manuels"],
  },
  {
    name: "Pro",
    monthlyPrice: 19,
    subtitle: "Pour les professionnels",
    cta: "Démarrer mon abonnement",
    popular: true,
    features: ["5 boîtes connectées", "5 000 emails / mois", "Actions automatiques", "Brouillons & réponses auto", "Support prioritaire"],
  },
  {
    name: "Business",
    monthlyPrice: 49,
    subtitle: "Pour les équipes",
    cta: "Nous contacter",
    features: ["Boîtes illimitées", "Emails illimités", "Règles avancées & IA", "Statistiques avancées", "Support dédié"],
  },
];

export function PricingSection() {
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
          <em>-20%</em>
        </div>
      </div>
      <div className="pricing-grid">
        {PLANS.map((plan) => (
          <PricingCard key={plan.name} plan={plan} billingCycle={billingCycle} />
        ))}
      </div>
    </section>
  );
}

function PricingCard({ plan, billingCycle }: { plan: (typeof PLANS)[number]; billingCycle: BillingCycle }) {
  const isYearly = billingCycle === "yearly";
  const yearlyPrice = Math.round(plan.monthlyPrice * 12 * 0.8);
  const regularYearlyPrice = plan.monthlyPrice * 12;
  const savings = regularYearlyPrice - yearlyPrice;
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
          Soit {Math.round(yearlyPrice / 12)}€/mois · Économisez {savings}€/an
        </p>
      )}
      <ul>
        {plan.features.map((feature) => <li key={feature}>✓ {feature}</li>)}
      </ul>
      <a href="#tarifs">{plan.cta}</a>
    </article>
  );
}
