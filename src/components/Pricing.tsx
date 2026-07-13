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
    <section id="pricing" className="relative py-28 bg-[#05070E] overflow-hidden border-t border-white/10">
      
      {/* Background Orbs */}
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        {/* Header Block */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 py-1.5 px-4 rounded-full text-xs font-mono mb-4">
            <ShieldCheck className="w-4 h-4 text-purple-400" />
            <span>COMMUNITY PRICING TIERS</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl text-white tracking-tight mb-4">
            Predictable SaaS plans for <span className="bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">servers of any scale</span>.
          </h2>
          <p className="font-sans text-slate-300 text-base sm:text-lg mb-8 leading-relaxed">
            Start completely free. Upgrade anytime your community scales or as security requirements intensify.
          </p>

          {/* Billing Switcher */}
          <div className="inline-flex items-center space-x-2 bg-[#090D1A] border border-white/10 p-2 rounded-2xl backdrop-blur-xl">
            <button
              onClick={() => setIsYearly(false)}
              className={`py-2 px-5 text-xs font-semibold rounded-xl transition-all cursor-pointer ${
                !isYearly ? "bg-purple-600 text-white shadow-[0_0_15px_rgba(124,58,237,0.5)] font-bold" : "text-slate-400 hover:text-white"
              }`}
            >
              Monthly Billing
            </button>
            <button
              onClick={() => setIsYearly(true)}
              className={`py-2 px-5 text-xs font-semibold rounded-xl transition-all flex items-center space-x-2 cursor-pointer ${
                isYearly ? "bg-purple-600 text-white shadow-[0_0_15px_rgba(124,58,237,0.5)] font-bold" : "text-slate-400 hover:text-white"
              }`}
            >
              <span>Yearly Billing</span>
              <span className="text-[10px] font-mono font-black bg-cyan-400 text-black px-2 py-0.5 rounded-full uppercase tracking-wider">
                Save 20%
              </span>
            </button>
          </div>
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
          {PLANS.map((plan) => {
            const monthlyPrice = isYearly ? plan.priceYearlyTotal / 12 : plan.priceMonthly;
            const finalPrice = monthlyPrice.toFixed(2);

            return (
              <div
                key={plan.name}
                className={`relative rounded-3xl p-8 transition-all flex flex-col justify-between overflow-hidden group ${
                  plan.popular
                    ? "glow-card border-purple-500/80 shadow-[0_0_40px_rgba(124,58,237,0.3)] scale-102 z-10"
                    : "glass-panel-hover border-white/10"
                }`}
              >
                {plan.popular && (
                  <>
                    <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-400" />
                    <div className="absolute top-4 right-6 bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-mono text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider shadow-lg">
                      MOST POPULAR
                    </div>
                  </>
                )}

                <div>
                  <h3 className="font-heading font-extrabold text-2xl text-white mb-2">
                    {plan.name}
                  </h3>
                  <p className="font-sans text-xs text-slate-400 mb-6 leading-relaxed">
                    {plan.description}
                  </p>

                  <div className="flex items-baseline mb-6 border-b border-white/10 pb-6">
                    <span className="font-heading font-extrabold text-3xl text-white">$</span>
                    <span className="font-heading font-extrabold text-5xl text-white tracking-tight">
                      {finalPrice.split(".")[0]}
                    </span>
                    <span className="font-heading font-bold text-2xl text-white">
                      .{finalPrice.split(".")[1]}
                    </span>
                    <span className="font-sans text-xs text-slate-400 ml-2 font-medium">/ month</span>
                  </div>

                  <ul className="space-y-3.5 mb-8">
                    {plan.features.map((feat, idx) => (
                      <li key={idx} className="flex items-start text-xs sm:text-sm text-slate-300 font-sans">
                        <Check className="w-4 h-4 text-cyan-400 mr-3 mt-0.5 shrink-0" />
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <button
                  onClick={() => setCheckoutPlan(plan.name)}
                  className={`w-full py-3.5 px-4 rounded-xl font-heading text-sm font-bold tracking-wide transition-all cursor-pointer uppercase ${
                    plan.popular
                      ? "btn-primary shadow-[0_0_25px_rgba(124,58,237,0.5)]"
                      : "btn-secondary"
                  }`}
                >
                  {plan.cta}
                </button>
              </div>
            );
          })}
        </div>

      </div>

      {/* Checkout Simulation Modal */}
      <AnimatePresence>
        {checkoutPlan && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[#090D1A] border border-white/15 rounded-3xl p-6 sm:p-8 max-w-md w-full relative text-left shadow-2xl"
            >
              <button
                onClick={() => setCheckoutPlan(null)}
                className="absolute top-5 right-5 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500/20 to-cyan-500/20 border border-purple-500/30 flex items-center justify-center text-purple-300 mb-6 shadow-md">
                <Sparkles className="w-6 h-6 text-cyan-300" />
              </div>

              <h4 className="font-heading font-extrabold text-2xl text-white mb-2">
                Checkout Simulation
              </h4>
              <p className="font-sans text-xs sm:text-sm text-slate-300 leading-relaxed">
                You have selected **{checkoutPlan}** ({isYearly ? "Billed Annually" : "Billed Monthly"}). This is a live frontend prototype demo; no credit card charging will occur.
              </p>

              <div className="bg-[#05070E] border border-white/10 rounded-2xl p-4.5 my-6 text-xs font-mono text-slate-300 space-y-2.5">
                <div className="flex justify-between">
                  <span className="text-slate-400">Target Plan:</span>
                  <span className="text-white font-sans font-bold">{checkoutPlan}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Billing Term:</span>
                  <span className="text-white font-sans font-bold">{isYearly ? "Annual Discounted" : "Monthly Recurring"}</span>
                </div>
                <div className="flex justify-between border-t border-white/10 pt-2.5 font-bold">
                  <span className="text-slate-300">Simulated Fee:</span>
                  <span className="text-cyan-300 font-mono">$0.00 Demo</span>
                </div>
              </div>

              <button
                onClick={() => setCheckoutPlan(null)}
                className="btn-primary w-full py-3.5 px-4 rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg text-center"
              >
                Complete Free Setup
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </section>
  );
}

