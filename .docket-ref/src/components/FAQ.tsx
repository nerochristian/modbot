import React, { useState } from "react";
import { HelpCircle, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { FAQItem } from "../types";

const FAQ_ITEMS: FAQItem[] = [
  {
    id: "f-1",
    category: "security",
    question: "What permissions does Docket require to secure my server?",
    answer: "To enforce rules smoothly, Docket needs standard moderation permissions: Manage Roles (for muting), Moderate Members (for timeouts), Manage Messages (for deleting scam links/spam), and View Channels. You can invite Docket with limited rights, but automated actions like muting or link purging will be restricted to rooms where the bot is permitted.",
  },
  {
    id: "f-2",
    category: "security",
    question: "Is user privacy protected? Does Docket store chat logs?",
    answer: "Yes, privacy is a core architectural priority. Docket evaluates incoming chat messages transiently in memory to perform safety scoring, and does not build permanent conversational profiles. Flagged evidence logs for moderation cases are kept in a secure, encrypted ledger, and general message audits are auto-deleted after 48 hours. Docket is fully GDPR and SOC2 compliant.",
  },
  {
    id: "f-3",
    category: "ai",
    question: "How does the AI make decisions without false positives?",
    answer: "Docket uses highly tuned NLP models trained specifically on community guidelines and common online threats. Every message is scored on a confidence scale (0% to 100%). If an infraction score is borderline, or if a user has a stellar account standing with zero past warnings, Docket defers to human staff or logs a warning instead of taking immediate ban actions.",
  },
  {
    id: "f-4",
    category: "setup",
    question: "How do member appeals work for automated punishments?",
    answer: "When Docket bans or mutes a member, it logs the infraction and provides an appeal link. Mistakenly punished members can click this link to access a sandbox appeal portal. Here, they can present their context, and Docket automatically routes the review to your staff channel, where administrators can approve or reject the appeal in a single click.",
  },
  {
    id: "f-5",
    category: "setup",
    question: "Can I customize the bot's commands and triggers?",
    answer: "Absolutely! Docket features an intuitive rule builder in the cloud dashboard. You can create custom triggers (e.g., if a user sends more than 3 capital-letter messages in 5 seconds, warn them), whitelist specific safe domains (like your official website), and configure custom automated reactions for different roles.",
  },
  {
    id: "f-6",
    category: "billing",
    question: "Can I cancel or upgrade my Pro subscription at any time?",
    answer: "Yes. All subscriptions are managed directly through our web portal. You can switch between monthly and yearly cycles or cancel your plan at any time. When you cancel, your server will gracefully transition back to the Free Guard plan at the end of your billing cycle without losing any of your configuration profiles.",
  },
];

export default function FAQ() {
  const [expandedId, setExpandedId] = useState<string | null>(FAQ_ITEMS[0].id);

  const toggleExpand = (id: string) => {
    setExpandedId(prev => (prev === id ? null : id));
  };

  return (
    <section id="faq" className="relative py-24 bg-[#05060B] overflow-hidden border-t border-slate-800/80">
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[300px] h-[300px] bg-cyan-500/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        {/* Header Block */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-purple-950/40 border border-purple-500/20 text-purple-400 py-1 px-3 rounded-full text-xs font-mono mb-4">
            <HelpCircle className="w-3.5 h-3.5" />
            <span>KNOWLEDGE HUB</span>
          </div>
          <h2 className="font-display font-bold text-3xl sm:text-4xl text-white tracking-tight mb-4">
            Frequently Asked Questions
          </h2>
          <p className="font-sans text-slate-400 text-base sm:text-lg">
            Have questions about permissions, artificial intelligence decisions, or security setups? Find answers below.
          </p>
        </div>

        {/* Accordion Container */}
        <div className="space-y-4">
          {FAQ_ITEMS.map((item) => {
            const isOpen = expandedId === item.id;

            return (
              <div
                key={item.id}
                className="bg-[#0E111A] border border-slate-800 rounded-2xl overflow-hidden transition-all hover:border-purple-500/30"
              >
                {/* Accordion Header */}
                <button
                  onClick={() => toggleExpand(item.id)}
                  className="w-full flex justify-between items-center p-5 text-left font-display font-semibold text-white hover:text-purple-300 transition-colors cursor-pointer"
                >
                  <span>{item.question}</span>
                  <span className={`p-1.5 rounded-lg bg-[#05060B]/60 border border-slate-800 text-slate-500 transition-transform ${
                    isOpen ? "rotate-180 text-purple-400 border-purple-500/20" : ""
                  }`}>
                    <ChevronDown className="w-4 h-4" />
                  </span>
                </button>

                {/* Accordion Content */}
                <div
                  className={`transition-all duration-300 ease-in-out ${
                    isOpen ? "max-h-60 border-t border-slate-800/60 py-4 px-5 opacity-100" : "max-h-0 opacity-0 overflow-hidden"
                  }`}
                >
                  <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
                    {item.answer}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
