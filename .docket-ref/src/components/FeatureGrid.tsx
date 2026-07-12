import React, { useState } from "react";
import { ShieldAlert, RefreshCw, AlertOctagon, Laugh, Ticket, UserCheck, Code, UserMinus, FileClock, BarChart, SlidersHorizontal, Sparkles } from "lucide-react";

interface FeatureCardProps {
  key?: any;
  title: string;
  description: string;
  icon: React.ReactNode;
  category: "defense" | "utility" | "automation";
  badge?: string;
}

function FeatureCard({ title, description, icon, category, badge }: FeatureCardProps) {
  return (
    <div className="relative group bg-[#0E111A] border border-slate-800 hover:border-purple-500/40 p-6 rounded-2xl text-left transition-all hover:-translate-y-1 overflow-hidden">
      {/* Subtle hover background light glow */}
      <div className="absolute inset-0 z-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      
      <div className="relative z-10">
        <div className="flex justify-between items-start mb-4">
          <div className="w-10 h-10 rounded-xl bg-[#05060B] border border-slate-800 flex items-center justify-center text-purple-400 group-hover:text-purple-300 group-hover:border-purple-500/30 transition-all">
            {icon}
          </div>
          {badge && (
            <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-purple-950/60 border border-purple-500/30 text-purple-300">
              {badge}
            </span>
          )}
        </div>
        <h4 className="font-display font-bold text-sm sm:text-base text-white mb-2">
          {title}
        </h4>
        <p className="font-sans text-xs sm:text-sm text-slate-400 leading-normal">
          {description}
        </p>
      </div>
    </div>
  );
}

export default function FeatureGrid() {
  const [selectedCat, setSelectedCat] = useState<"all" | "defense" | "utility" | "automation">("all");

  const features = [
    {
      title: "Active Raid Protection",
      description: "Detect coordinated join floods and lock down server channels automatically in less than 150ms.",
      icon: <ShieldAlert className="w-5 h-5" />,
      category: "defense" as const,
      badge: "SHIELD",
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
      badge: "AI-DRIVEN",
    },
    {
      title: "Toxicity & Slur Blocker",
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
      badge: "INTEGRATION",
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
    <section id="features" className="relative py-24 bg-[#05060B] overflow-hidden border-t border-slate-800/80">
      {/* Glow shapes */}
      <div className="absolute top-1/2 left-0 -translate-y-1/2 w-[300px] h-[300px] bg-purple-500/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[250px] h-[250px] bg-cyan-500/5 rounded-full blur-[90px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Section Headings */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 text-left">
          <div className="max-w-xl">
            <div className="inline-flex items-center space-x-2 bg-purple-950/40 border border-purple-500/20 text-purple-400 py-1 px-3 rounded-full text-xs font-mono mb-4">
              <Sparkles className="w-3.5 h-3.5" />
              <span>THE SECURITY MATRIX</span>
            </div>
            <h2 className="font-display font-bold text-3xl sm:text-4xl text-white tracking-tight mb-4">
              All tools, unified under one bot shard.
            </h2>
            <p className="font-sans text-slate-400 text-xs sm:text-sm">
              Stop chaining five different bots to manage roles, tickets, and rules. Docket handles all moderation, automation, and community growth utilities cleanly.
            </p>
          </div>

          {/* Filtering row */}
          <div className="flex flex-wrap gap-2 mt-6 md:mt-0 bg-[#0E111A] border border-slate-800 p-1.5 rounded-xl">
            {(["all", "defense", "utility", "automation"] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCat(cat)}
                className={`py-1.5 px-3.5 text-xs font-sans font-medium rounded-lg transition-all capitalize cursor-pointer ${
                  selectedCat === cat
                    ? "bg-purple-950/60 border border-purple-500/30 text-purple-300 shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {cat === "all" ? "All features" : cat}
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
