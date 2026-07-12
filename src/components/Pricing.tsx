import React, { useState } from "react";
import { Check, ShieldCheck, HelpCircle, Landmark, Sparkles, X } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

interface PricingPlan {
  name: string;
  priceMonthly: number;
  priceYearlyTotal: number;
  description: string;
  features: string[];
  cta: string;
  popular?: boolean;
}

const PLANS: PricingPlan[] = [
  {
    name: "Free Guard",
    priceMonthly: 0,
    priceYearlyTotal: 0,
    description: "Essential moderation commands and automatic filters for developing servers.",
    features: [
      "Standard NLP Moderation Engine",
      "Basic Anti-Spam filters",
      "Up to 2,500 total server members",
      "99.0% Bot uptime SLA",
      "Community forum support",
    ],
    cta: "Invite Free Shard",
  },
  {
    name: "Pro Shield",
    priceMonthly: 9.99,
    priceYearlyTotal: 95.88, // $7.99 / mo
    description: "Complete security, captcha gates, raid shields, and AI sentiment analysis.",
    features: [
      "Everything in Free, plus:",
      "Coordinated Raid Protection Shield",
      "AI Phishing Scam link detection",
      "Captcha Join verification gates",
      "Interactive support ticket system",
      "Custom auto-role hierarchy mapping",
      "Priority API response speeds (<12ms)",
      "Dedicated Discord ticket help Desk",
    ],
    cta: "Unlock Pro Protection",
    popular: true,
  },
  {
    name: "Enterprise Sovereign",
    priceMonthly: 29.99,
    priceYearlyTotal: 287.88, // $23.99 / mo
    description: "Custom bot white-label branding, private sharded hardware, and custom dictionaries.",
    features: [
      "Everything in Pro, plus:",
      "White-Label custom branding (your avatar/name)",
      "Dedicated sharded cluster servers",
      "Custom NLP sentiment rules dictionary",
      "Dedicated account success manager",
      "Enterprise security compliance (SOC2)",
      "Priority feature request backlog access",
    ],
    cta: "Contact Enterprise Sales",
  }
];

export default function Pricing() {
  const [isYearly, setIsYearly] = useState(false);
  const [checkoutPlan, setCheckoutPlan] = useState<string | null>(null);

  return (
    <section id="pricing" className="relative py-24 bg-[#05060B] overflow-hidden border-t border-slate-800/80">
      {/* Visual background lights */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 w-[350px] h-[350px] bg-purple-500/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 w-[350px] h-[350px] bg-cyan-500/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        {/* Header and Toggle */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-purple-950/40 border border-purple-500/20 text-purple-400 py-1 px-3 rounded-full text-xs font-mono mb-4">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>COMMUNITY PLANS</span>
          </div>
          <h2 className="font-display font-bold text-3xl sm:text-4xl text-white tracking-tight mb-4">
            Predictable SaaS tiers for servers of any size.
          </h2>
          <p className="font-sans text-slate-400 text-base sm:text-lg mb-8">
            Start completely free. Upgrade anytime your community scales, or as security requirements intensify.
          </p>

          {/* Toggle Switch */}
          <div className="inline-flex items-center space-x-3 bg-[#0E111A] border border-slate-800 p-1.5 rounded-xl">
            <button
              onClick={() => setIsYearly(false)}
              className={`py-1.5 px-4 text-xs font-sans font-medium rounded-lg transition-all cursor-pointer ${
                !isYearly ? "bg-purple-950/60 border border-purple-500/30 text-purple-300 shadow" : "text-slate-400"
              }`}
            >
              Monthly billing
            </button>
            <button
              onClick={() => setIsYearly(true)}
              className={`py-1.5 px-4 text-xs font-sans font-medium rounded-lg transition-all flex items-center space-x-1 cursor-pointer ${
                isYearly ? "bg-purple-950/60 border border-purple-500/30 text-purple-300 shadow" : "text-slate-400"
              }`}
            >
              <span>Yearly billing</span>
              <span className="text-[9px] font-mono font-bold bg-purple-500 text-white px-1.5 py-0.2 rounded-full uppercase scale-90">
                Save 20%
              </span>
            </button>
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
          {PLANS.map((plan) => {
            // Price calculation
            const monthlyPrice = isYearly ? plan.priceYearlyTotal / 12 : plan.priceMonthly;
            const finalPrice = monthlyPrice.toFixed(2);

            return (
              <div
                key={plan.name}
                className={`relative bg-[#0E111A] border rounded-3xl p-8 transition-all flex flex-col justify-between overflow-hidden group ${
                  plan.popular
                    ? "border-purple-500 shadow-2xl shadow-purple-950/10 scale-102 z-10"
                    : "border-slate-800 hover:border-purple-500/30"
                }`}
              >
                {/* Popular card visual background flash */}
                {plan.popular && (
                  <>
                    <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-pink-500 to-cyan-500" />
                    <div className="absolute top-0 right-8 -translate-y-1/2 bg-purple-500 text-white font-mono text-[9px] font-bold px-3 py-1 rounded-full uppercase tracking-wider shadow">
                      RECOMMENDED
                    </div>
                  </>
                )}

                <div>
                  <h3 className="font-display font-bold text-xl text-white mb-2">
                    {plan.name}
                  </h3>
                  <p className="font-sans text-xs text-slate-500 mb-6">
                    {plan.description}
                  </p>

                  {/* Pricing Number */}
                  <div className="flex items-baseline mb-6 border-b border-slate-800/60 pb-6">
                    <span className="font-display font-bold text-4xl text-white">$</span>
                    <span className="font-display font-bold text-5xl text-white tracking-tight">
                      {finalPrice.split(".")[0]}
                    </span>
                    <span className="font-display font-bold text-3xl text-white">
                      .{finalPrice.split(".")[1]}
                    </span>
                    <span className="font-sans text-xs text-slate-500 ml-2">/ month</span>
                  </div>

                  {/* Feature lists */}
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feat, idx) => (
                      <li key={idx} className="flex items-start text-xs sm:text-sm text-slate-300">
                        <Check className="w-4 h-4 text-purple-400 mr-2.5 mt-0.5 shrink-0" />
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* CTA Button */}
                <button
                  onClick={() => setCheckoutPlan(plan.name)}
                  className={`w-full py-3 px-4 rounded-xl font-sans text-sm font-semibold transition-all cursor-pointer ${
                    plan.popular
                      ? "bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 text-white shadow-lg hover:-translate-y-0.5"
                      : "bg-[#05060B] hover:bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:-translate-y-0.5"
                  }`}
                >
                  {plan.cta}
                </button>
              </div>
            );
          })}
        </div>

      </div>

      {/* Interactive Checkout Modal (SaaS feel) */}
      <AnimatePresence>
        {checkoutPlan && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[#0E111A] border border-slate-800 rounded-3xl p-6 sm:p-8 max-w-md w-full relative text-left shadow-2xl"
            >
              <button
                onClick={() => setCheckoutPlan(null)}
                className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-400 mb-6">
                <Sparkles className="w-6 h-6" />
              </div>

              <h4 className="font-display font-bold text-xl text-white mb-2">
                Checkout Simulation
              </h4>
              <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
                You have initiated the checkout for **{checkoutPlan}** ({isYearly ? "Billed Annually" : "Billed Monthly"}). This is a prototype simulation; no real credit card or payment is required.
              </p>

              <div className="bg-[#05060B] border border-slate-800 rounded-xl p-4 my-6 text-xs font-mono text-slate-400 space-y-2">
                <div className="flex justify-between">
                  <span>Product:</span>
                  <span className="text-white font-sans">{checkoutPlan}</span>
                </div>
                <div className="flex justify-between">
                  <span>Cycle:</span>
                  <span className="text-white font-sans">{isYearly ? "Annual" : "Monthly"}</span>
                </div>
                <div className="flex justify-between border-t border-slate-800 pt-2 font-bold">
                  <span>Simulated Total:</span>
                  <span className="text-purple-400">$0.00</span>
                </div>
              </div>

              <button
                onClick={() => setCheckoutPlan(null)}
                className="w-full bg-gradient-to-r from-purple-600 to-violet-600 text-white font-sans font-semibold py-3 px-4 rounded-xl shadow-lg transition-all cursor-pointer text-center"
              >
                Confirm Setup (Free Demo)
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </section>
  );
}
