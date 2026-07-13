import React from "react";
import { Quote, Star, Users, MessageSquare } from "lucide-react";
import { TestimonialItem } from "../types";

const TESTIMONIALS: TestimonialItem[] = [
  {
    id: "t-1",
    quote: "Docket's anti-raid system saved our server from a coordinated bot flood of 4,000 joins. The captcha gate kicked in instantly and isolated the threat without disrupting our active chat rooms.",
    author: "Sarah Jenkins",
    role: "Lead Administrator",
    serverName: "Apex Legends Hub Official",
    memberCount: "240k members",
  },
  {
    id: "t-2",
    quote: "We were tired of updating clumsy regex word filters. Docket's NLP context moderation reads actual intent—allowing friendly banter while instantly blocking genuine toxicity and malicious scams.",
    author: "Marcus Vance",
    role: "Community Director",
    serverName: "Dev_HQ Workspace",
    memberCount: "82k members",
  },
  {
    id: "t-3",
    quote: "Switching from older moderation bots to Docket reduced our support ticket queues by 65%. The automated appeal flows handle false-alarm queries cleanly, saving our staff hundreds of hours.",
    author: "Kevin Patel",
    role: "Server Owner",
    serverName: "Crypto Horizon Hub",
    memberCount: "115k members",
  },
];

export default function Testimonials() {
  return (
    <section id="testimonials" className="relative py-28 bg-[#05070E] overflow-hidden border-t border-white/10">
      
      {/* Glow Orbs */}
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[350px] h-[350px] bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 py-1.5 px-4 rounded-full text-xs font-mono mb-4">
            <Quote className="w-4 h-4 text-purple-400" />
            <span>COMMUNITY ENDORSEMENTS</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl text-white tracking-tight mb-4">
            Trusted by the web's <span className="bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">most active hubs</span>.
          </h2>
          <p className="font-sans text-slate-300 text-base sm:text-lg leading-relaxed">
            See how major Discord servers and moderation teams are utilizing Docket to shield their channels and optimize staff workloads.
          </p>
        </div>

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {TESTIMONIALS.map((t) => (
            <div
              key={t.id}
              className="glass-panel-hover p-8 rounded-2xl flex flex-col justify-between relative group overflow-hidden"
            >
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="flex space-x-1">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="w-4 h-4 fill-amber-400 text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.6)]" />
                    ))}
                  </div>
                  <Quote className="w-8 h-8 text-purple-400/20 group-hover:text-purple-400/40 transition-colors" />
                </div>

                <p className="font-sans text-xs sm:text-sm text-slate-300 leading-relaxed italic">
                  "{t.quote}"
                </p>
              </div>

              <div className="pt-6 mt-6 border-t border-white/10 flex items-center space-x-3.5">
                <div className="w-10 h-10 rounded-xl bg-[#090D1A] border border-white/10 flex items-center justify-center font-heading font-bold text-xs text-purple-300 shadow-md">
                  {t.serverName.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <span className="font-heading font-bold text-sm text-white block">
                    {t.author}
                  </span>
                  <span className="text-[11px] font-sans text-slate-400 block leading-none mt-1">
                    {t.role}
                  </span>
                  <div className="flex items-center space-x-2 mt-2">
                    <span className="text-[10px] font-mono text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded-md border border-cyan-500/20 font-semibold">
                      {t.serverName}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400 flex items-center space-x-1">
                      <Users className="w-3 h-3 text-slate-400" />
                      <span>{t.memberCount}</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}

