import React from "react";
import { Link2, Sparkles, Shield, UserCheck, ArrowRight } from "lucide-react";

export default function HowItWorks() {
  const steps = [
    {
      step: "01",
      title: "Connect Your Server",
      description: "Invite Docket to your Discord guild in one click. Secure OAuth scopes grant necessary permissions for channel reading, moderation, and role management.",
      icon: <Link2 className="w-6 h-6 text-purple-400" />,
      actionText: "Invite Bot Shard",
      link: "https://discord.com",
    },
    {
      step: "02",
      title: "Configure Preferences",
      description: "Access our ultra-responsive cloud dashboard. Choose from pre-configured security templates (Strict, Balanced, Lax) or compile granular custom rules.",
      icon: <Sparkles className="w-6 h-6 text-cyan-400" />,
      actionText: "Open Cloud Dashboard",
    },
    {
      step: "03",
      title: "Active Protection Enabled",
      description: "Sit back and let Docket monitor active conversation. Coordinated attacks, phish domains, and hostility vectors are mitigated automatically in real-time.",
      icon: <Shield className="w-6 h-6 text-emerald-400" />,
      actionText: "Monitor Secure Feed",
    },
  ];

  return (
    <section id="how-it-works" className="relative py-24 bg-[#05060B] overflow-hidden border-t border-slate-800/80">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[350px] h-[350px] bg-purple-500/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        {/* Header Block */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-purple-950/40 border border-purple-500/20 text-purple-400 py-1 px-3 rounded-full text-xs font-mono mb-4">
            <UserCheck className="w-3.5 h-3.5" />
            <span>HOW DOCKET PROTECTS</span>
          </div>
          <h2 className="font-display font-bold text-3xl sm:text-4xl text-white tracking-tight mb-4">
            Secure your server in three direct steps.
          </h2>
          <p className="font-sans text-slate-400 text-base sm:text-lg">
            No convoluted coding, no server crashes. Docket simplifies Discord protection so you can focus on building your community.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 relative">
          
          {/* Subtle line connector for large screens */}
          <div className="hidden lg:block absolute top-1/2 left-8 right-8 h-[1px] bg-gradient-to-r from-purple-500/20 via-cyan-500/20 to-emerald-500/20 -translate-y-8 z-0" />

          {steps.map((st, i) => (
            <div
              key={i}
              className="relative z-10 bg-[#0E111A] border border-slate-800 hover:border-purple-500/40 p-6 sm:p-8 rounded-2xl transition-all group flex flex-col justify-between"
            >
              <div>
                {/* Step circle */}
                <div className="flex justify-between items-center mb-6">
                  <div className="w-12 h-12 rounded-xl bg-[#05060B] border border-slate-800 flex items-center justify-center text-purple-400 transition-transform group-hover:scale-105">
                    {st.icon}
                  </div>
                  <span className="font-display font-bold text-2xl text-slate-800 font-mono tracking-tight group-hover:text-purple-500/40 transition-colors">
                    {st.step}
                  </span>
                </div>

                <h3 className="font-display font-bold text-lg sm:text-xl text-white mb-3">
                  {st.title}
                </h3>
                <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed mb-6">
                  {st.description}
                </p>
              </div>

              {/* Action trigger button */}
              <div>
                {st.link ? (
                  <a
                    href={st.link}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-1.5 font-sans text-xs font-semibold text-purple-400 hover:text-purple-300 transition-colors cursor-pointer"
                  >
                    <span>{st.actionText}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </a>
                ) : (
                  <button
                    onClick={() => {
                      const el = document.getElementById("dashboard");
                      if (el) el.scrollIntoView({ behavior: "smooth" });
                    }}
                    className="inline-flex items-center space-x-1.5 font-sans text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
                  >
                    <span>{st.actionText}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          ))}

        </div>

      </div>
    </section>
  );
}
