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
    <section id="testimonials" className="relative py-24 bg-[#05060B] overflow-hidden border-t border-slate-800/80">
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[250px] h-[250px] bg-purple-500/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        {/* Header Block */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-purple-950/40 border border-purple-500/20 text-purple-400 py-1 px-3 rounded-full text-xs font-mono mb-4">
            <Quote className="w-3.5 h-3.5" />
            <span>COMMUNITY ENDORSEMENTS</span>
          </div>
          <h2 className="font-display font-bold text-3xl sm:text-4xl text-white tracking-tight mb-4">
            Trusted by the web's most active hubs.
          </h2>
          <p className="font-sans text-slate-400 text-base sm:text-lg">
            See how major Discord servers and moderation teams are utilizing Docket to shield their channels and optimize staff workloads.
          </p>
        </div>

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {TESTIMONIALS.map((t) => (
            <div
              key={t.id}
              className="bg-[#0E111A] border border-slate-800 hover:border-purple-500/40 p-6 sm:p-8 rounded-2xl transition-all flex flex-col justify-between relative group overflow-hidden"
            >
              {/* Subtle visual accent */}
              <div className="absolute top-0 right-0 w-16 h-16 bg-purple-500/5 rounded-full blur-xl pointer-events-none" />

              <div className="space-y-4">
                {/* Stars and Quote Icon */}
                <div className="flex justify-between items-center">
                  <div className="flex space-x-1">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="w-4 h-4 fill-purple-400 text-purple-400" />
                    ))}
                  </div>
                  <Quote className="w-8 h-8 text-purple-500/10" />
                </div>

                <p className="font-sans text-xs sm:text-sm text-slate-300 leading-relaxed italic">
                  "{t.quote}"
                </p>
              </div>

              <div className="pt-6 mt-6 border-t border-slate-800/60 flex items-center space-x-3">
                {/* Simulated Server Avatar */}
                <div className="w-10 h-10 rounded-full bg-[#05060B] border border-slate-800 flex items-center justify-center font-display font-bold text-xs text-purple-400 group-hover:bg-purple-950/40 transition-colors">
                  {t.serverName.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <span className="font-sans font-bold text-sm text-white block">
                    {t.author}
                  </span>
                  <span className="text-[11px] text-slate-500 block leading-none mt-1">
                    {t.role}
                  </span>
                  <div className="flex items-center space-x-1.5 mt-2">
                    <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/40 px-1.5 py-0.5 rounded">
                      {t.serverName}
                    </span>
                    <span className="text-[9px] font-mono text-slate-600 flex items-center space-x-0.5">
                      <Users className="w-3 h-3 text-slate-600" />
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
