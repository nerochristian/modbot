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
    <section id="how-it-works" className="relative py-28 bg-[#05070E] overflow-hidden border-t border-white/10">
      
      {/* Background Orbs */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[450px] h-[450px] bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 py-1.5 px-4 rounded-full text-xs font-mono mb-4">
            <UserCheck className="w-4 h-4 text-purple-400" />
            <span>HOW DOCKET PROTECTS</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl text-white tracking-tight mb-4">
            Secure your server in <span className="bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">three direct steps</span>.
          </h2>
          <p className="font-sans text-slate-300 text-base sm:text-lg leading-relaxed">
            No convoluted coding, no server crashes. Docket simplifies Discord protection so you can focus on building your community.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 relative">
          
          {/* Connecting line */}
          <div className="hidden lg:block absolute top-1/2 left-12 right-12 h-[1px] bg-gradient-to-r from-purple-500/30 via-cyan-500/30 to-emerald-500/30 -translate-y-12 z-0" />

          {steps.map((st, i) => (
            <div
              key={i}
              className="glass-panel-hover p-8 rounded-2xl relative z-10 flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-center mb-6">
                  <div className="w-13 h-13 rounded-2xl bg-[#090D1A] border border-white/10 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                    {st.icon}
                  </div>
                  <span className="font-mono font-extrabold text-3xl text-purple-400/30 tracking-tight group-hover:text-purple-400 transition-colors">
                    {st.step}
                  </span>
                </div>

                <h3 className="font-heading font-bold text-xl text-white mb-3">
                  {st.title}
                </h3>
                <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed mb-6">
                  {st.description}
                </p>
              </div>

              <div>
                {st.link ? (
                  <a
                    href={st.link}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-2 font-mono text-xs font-bold text-purple-300 hover:text-white transition-colors cursor-pointer group/btn"
                  >
                    <span>{st.actionText}</span>
                    <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                  </a>
                ) : (
                  <button
                    onClick={() => {
                      const el = document.getElementById("dashboard");
                      if (el) el.scrollIntoView({ behavior: "smooth" });
                    }}
                    className="inline-flex items-center space-x-2 font-mono text-xs font-bold text-cyan-300 hover:text-white transition-colors cursor-pointer group/btn"
                  >
                    <span>{st.actionText}</span>
                    <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
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

