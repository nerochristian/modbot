import React, { useState } from "react";
import { ShieldAlert, RefreshCw, AlertOctagon, Laugh, Ticket, UserCheck, Code, UserMinus, FileClock, BarChart, SlidersHorizontal, Sparkles, Cpu, Lock } from "lucide-react";

interface FeatureCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  category: "defense" | "utility" | "automation";
  badge?: string;
}

function FeatureCard({ title, description, icon, category, badge }: FeatureCardProps) {
  return (
    <div className="glass-panel-hover p-6 rounded-2xl text-left relative group overflow-hidden flex flex-col justify-between">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 via-transparent to-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      
      <div>
        <div className="flex justify-between items-start mb-5">
          <div className="w-11 h-11 rounded-xl bg-[#090D1A] border border-white/10 flex items-center justify-center text-purple-400 group-hover:text-cyan-300 group-hover:border-purple-500/40 group-hover:scale-110 transition-all duration-300 shadow-md">
            {icon}
          </div>
          {badge && (
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/40 text-purple-200 uppercase tracking-wider shadow-[0_0_10px_rgba(168,85,247,0.3)]">
              {badge}
            </span>
          )}
        </div>
        <h4 className="font-heading font-bold text-base sm:text-lg text-white mb-2 group-hover:text-purple-200 transition-colors">
          {title}
        </h4>
        <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
          {description}
        </p>
      </div>

      <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-slate-300">
        <span className="capitalize text-slate-400">{category} Module</span>
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 opacity-60 group-hover:opacity-100 transition-opacity"></span>
      </div>
    </div>
  );
}

export default function FeatureGrid() {
  const [selectedCat, setSelectedCat] = useState<"all" | "defense" | "utility" | "automation">("all");

  const features = [
    {
      title: "Active Raid Protection",
      description: "Detect coordinated join floods and lock down server channels automatically in under 12ms.",
      icon: <ShieldAlert className="w-5 h-5" />,
      category: "defense" as const,
      badge: "CORE SHIELD",
    },
    {
      title: "Anti-Spam Heuristics",
      description: "Halt keyboard spam, duplicate pastes, and mass mentions instantly with adaptive rate limits.",
      icon: <RefreshCw className="w-5 h-5" />,
      category: "defense" as const,
    },
    {
      title: "Crypto Phishing Filter",
      description: "Block deceptive domains, malware, and fraudulent server invitations before users click them.",
      icon: <AlertOctagon className="w-5 h-5" />,
      category: "defense" as const,
      badge: "AI-POWERED",
    },
    {
      title: "Toxicity & Harassment Blocker",
      description: "Natural language scoring classifies and prevents harassment, hate speech, and user hostility.",
      icon: <Laugh className="w-5 h-5" />,
      category: "defense" as const,
    },
    {
      title: "Interactive Support Tickets",
      description: "Create sleek sub-channel rooms where staff can manage private support inquiries and logs.",
      icon: <Ticket className="w-5 h-5" />,
      category: "utility" as const,
    },
    {
      title: "Captcha Joint Gateways",
      description: "Require suspicious new joins to solve brief interactive captchas in-browser before viewing rooms.",
      icon: <UserCheck className="w-5 h-5" />,
      category: "automation" as const,
      badge: "SECURE GATE",
    },
    {
      title: "Custom Command Builder",
      description: "Compose customized automated responses and commands using a simple drag-and-drop rule compiler.",
      icon: <Code className="w-5 h-5" />,
      category: "utility" as const,
    },
    {
      title: "Role Hierarchy Engine",
      description: "Verify, tier, and assign server credentials based on account ages or activity counters.",
      icon: <UserMinus className="w-5 h-5" />,
      category: "automation" as const,
    },
    {
      title: "SaaS Grade Audit Logs",
      description: "Every delete, mute, ban, and warning is logged, indexed, and available for search instantly.",
      icon: <FileClock className="w-5 h-5" />,
      category: "utility" as const,
    },
    {
      title: "Moderator Efficiency Stats",
      description: "Monitor staff response latency, resolved warning ratios, and general community growth trends.",
      icon: <BarChart className="w-5 h-5" />,
      category: "utility" as const,
    },
  ];

  const filteredFeatures = selectedCat === "all"
    ? features
    : features.filter(f => f.category === selectedCat);

  return (
    <section id="features" className="relative py-28 bg-[#05070E] overflow-hidden border-t border-white/10">
      
      {/* Glow Orbs */}
      <div className="absolute top-1/3 left-0 w-[400px] h-[400px] bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[350px] h-[350px] bg-cyan-500/10 rounded-full blur-[130px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Section Headings */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-14 text-left">
          <div className="max-w-xl">
            <div className="inline-flex items-center space-x-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 py-1.5 px-4 rounded-full text-xs font-mono mb-4">
              <Sparkles className="w-4 h-4 text-cyan-300" />
              <span>THE SECURITY MATRIX</span>
            </div>
            <h2 className="font-heading font-extrabold text-3xl sm:text-5xl text-white tracking-tight mb-4">
              All security tools, unified under <span className="bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">one intelligence</span>.
            </h2>
            <p className="font-sans text-slate-300 text-sm sm:text-base leading-relaxed">
              Stop chaining five different bots to manage roles, tickets, and security rules. Docket handles all moderation, automation, and community growth utilities cleanly.
            </p>
          </div>

          {/* Filtering Pill Bar */}
          <div className="flex flex-wrap gap-2 mt-6 md:mt-0 bg-[#090D1A] border border-white/10 p-2 rounded-2xl backdrop-blur-xl">
            {(["all", "defense", "utility", "automation"] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCat(cat)}
                className={`py-2 px-4 text-xs font-semibold rounded-xl transition-all capitalize cursor-pointer ${
                  selectedCat === cat
                    ? "bg-purple-600 text-white shadow-[0_0_15px_rgba(124,58,237,0.5)] font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {cat === "all" ? "All Features" : cat}
              </button>
            ))}
          </div>
        </div>

        {/* Features Bento Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredFeatures.map((feat, idx) => (
            <FeatureCard
              key={idx}
              title={feat.title}
              description={feat.description}
              icon={feat.icon}
              category={feat.category as "defense" | "utility" | "automation"}
              badge={feat.badge}
            />
          ))}
        </div>

      </div>
    </section>
  );
}

