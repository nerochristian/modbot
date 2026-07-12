import React, { useState } from "react";
import { Shield, Sparkles, Send, Mail, CheckCircle2, ChevronRight, Github, Twitter, MessageSquare, ExternalLink } from "lucide-react";

export default function Footer() {
  const [email, setEmail] = useState("");
  const [isSubscribed, setIsSubscribed] = useState(false);

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim()) {
      setIsSubscribed(true);
      setEmail("");
    }
  };

  const currentYear = new Date().getFullYear();

  return (
    <footer className="relative bg-[#05060B] overflow-hidden pt-24 border-t border-slate-800/80 text-left">
      {/* Decorative background light */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-purple-950/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* FINAL CTA PANEL */}
        <div className="relative bg-gradient-to-br from-[#0E111A] to-[#141824] border border-slate-800 rounded-3xl p-8 sm:p-12 mb-20 overflow-hidden shadow-2xl">
          <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative z-10">
            <div className="lg:col-span-8 space-y-4">
              <div className="inline-flex items-center space-x-2 bg-purple-950/60 border border-purple-500/30 text-purple-300 py-1 px-3 rounded-full text-xs font-mono">
                <Sparkles className="w-3.5 h-3.5" />
                <span>SHIELD YOUR SERVER TODAY</span>
              </div>
              <h3 className="font-display font-bold text-3xl sm:text-4xl text-white tracking-tight">
                Ready to elevate your server security?
              </h3>
              <p className="font-sans text-slate-400 text-sm sm:text-base max-w-xl">
                Set up Docket in under five minutes. Protect your server members, streamline moderator tasks, and enjoy peaceful, structured growth.
              </p>
            </div>

            <div className="lg:col-span-4 flex flex-col sm:flex-row lg:flex-col sm:space-x-4 lg:space-x-0 lg:space-y-3 justify-end w-full">
              <a
                href="https://discord.com"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center space-x-2.5 bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 text-white font-sans font-semibold py-3 px-6 rounded-xl shadow-lg shadow-purple-950/20 transition-all text-center hover:-translate-y-0.5 cursor-pointer"
              >
                <Shield className="w-4 h-4" />
                <span>Add Docket to Discord</span>
              </a>
              <button
                onClick={() => {
                  const el = document.getElementById("dashboard");
                  if (el) el.scrollIntoView({ behavior: "smooth" });
                }}
                className="inline-flex items-center justify-center space-x-2 bg-[#05060B] hover:bg-[#0E111A] border border-slate-800 text-slate-300 hover:text-white font-sans font-semibold py-3 px-6 rounded-xl transition-all text-center hover:-translate-y-0.5 mt-3 sm:mt-0 lg:mt-0 cursor-pointer"
              >
                <span>Explore Live Dashboard</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* SITE MAP LINKS */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-10 mb-16 border-b border-slate-800/60 pb-16">
          
          {/* Column 1: Logo and News */}
          <div className="lg:col-span-4 space-y-6">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-cyan-500 p-[1px]">
                <div className="w-full h-full bg-[#05060B] rounded-[7px] flex items-center justify-center">
                  <Shield className="w-4 h-4 text-purple-400" />
                </div>
              </div>
              <span className="font-display font-bold text-lg text-white">
                Doc<span className="text-purple-400">ket</span>
              </span>
            </div>
            <p className="font-sans text-xs sm:text-sm text-slate-500 leading-relaxed max-w-sm">
               docket is a premium, sharded Discord moderation bot utilizing heuristic security layers and context-aware natural language scoring to shield top-tier server communities.
            </p>
            
            {/* Social handles */}
            <div className="flex space-x-3">
              <a href="https://twitter.com" target="_blank" rel="noreferrer" className="w-8 h-8 rounded-lg bg-[#0E111A] border border-slate-800 flex items-center justify-center text-slate-400 hover:text-white hover:border-purple-500/40 transition-all">
                <Twitter className="w-4 h-4" />
              </a>
              <a href="https://github.com" target="_blank" rel="noreferrer" className="w-8 h-8 rounded-lg bg-[#0E111A] border border-slate-800 flex items-center justify-center text-slate-400 hover:text-white hover:border-purple-500/40 transition-all">
                <Github className="w-4 h-4" />
              </a>
              <a href="https://discord.com" target="_blank" rel="noreferrer" className="w-8 h-8 rounded-lg bg-[#0E111A] border border-slate-800 flex items-center justify-center text-slate-400 hover:text-white hover:border-purple-500/40 transition-all">
                <MessageSquare className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Column 2: Product */}
          <div className="lg:col-span-2 space-y-4">
            <h4 className="font-display font-bold text-xs uppercase tracking-wider text-white">Product</h4>
            <ul className="space-y-2 text-xs font-sans text-slate-400">
              <li><button onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })} className="hover:text-white transition-colors cursor-pointer">Bot Features</button></li>
              <li><button onClick={() => document.getElementById("smart-moderation")?.scrollIntoView({ behavior: "smooth" })} className="hover:text-white transition-colors cursor-pointer">AI Moderation</button></li>
              <li><button onClick={() => document.getElementById("commands")?.scrollIntoView({ behavior: "smooth" })} className="hover:text-white transition-colors cursor-pointer">Bot Commands</button></li>
              <li><button onClick={() => document.getElementById("pricing")?.scrollIntoView({ behavior: "smooth" })} className="hover:text-white transition-colors cursor-pointer">Pricing Plans</button></li>
            </ul>
          </div>

          {/* Column 3: Resources */}
          <div className="lg:col-span-2 space-y-4">
            <h4 className="font-display font-bold text-xs uppercase tracking-wider text-white">Resources</h4>
            <ul className="space-y-2 text-xs font-sans text-slate-400">
              <li><a href="#" className="hover:text-white transition-colors flex items-center space-x-1"><span>Documentation</span> <ExternalLink className="w-3 h-3 text-slate-600" /></a></li>
              <li><a href="#" className="hover:text-white transition-colors flex items-center space-x-1"><span>Appeal Portal</span> <ExternalLink className="w-3 h-3 text-slate-600" /></a></li>
              <li><a href="#" className="hover:text-white transition-colors">Developer API</a></li>
              <li><a href="#" className="hover:text-white transition-colors">System Status</a></li>
            </ul>
          </div>

          {/* Column 4: Newsletter */}
          <div className="lg:col-span-4 space-y-4">
            <h4 className="font-display font-bold text-xs uppercase tracking-wider text-white">Security Dispatch Newsletter</h4>
            <p className="font-sans text-xs text-slate-500 leading-relaxed">
              Stay ahead of the latest phishing vectors, bot storms, and moderation strategies. Bimonthly logs straight to your inbox.
            </p>

            <form onSubmit={handleSubscribe} className="space-y-2">
              <div className="flex bg-[#0E111A] border border-slate-800 p-1.5 rounded-xl focus-within:border-purple-500/50 transition-all items-center">
                <Mail className="w-4 h-4 text-slate-500 ml-2" />
                <input
                  type="email"
                  placeholder="name@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubscribed}
                  className="bg-transparent text-xs font-sans text-white focus:outline-none flex-1 pl-2"
                />
                <button
                  type="submit"
                  disabled={isSubscribed}
                  className="bg-purple-600 hover:bg-purple-500 text-white p-2 rounded-lg transition-all cursor-pointer disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>

              {isSubscribed && (
                <div className="text-[11px] font-sans text-emerald-400 flex items-center space-x-1.5 pt-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Subscribed successfully! Welcome to Docket Security.</span>
                </div>
              )}
            </form>
          </div>

        </div>

        {/* LOWER BAR */}
        <div className="flex flex-col sm:flex-row justify-between items-center py-8 text-xs text-slate-500 font-sans">
          <span>&copy; {currentYear} Docket Bot Inc. All rights reserved.</span>
          <div className="flex space-x-6 mt-4 sm:mt-0">
            <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-white transition-colors">GDPR SLA</a>
          </div>
        </div>

      </div>
    </footer>
  );
}
