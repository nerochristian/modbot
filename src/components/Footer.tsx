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
    <footer className="relative bg-[#05070E] overflow-hidden pt-28 border-t border-white/10 text-left">
      
      {/* Glow Orbs */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[350px] bg-purple-600/10 rounded-full blur-[160px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* CTA Banner Card */}
        <div className="glow-card rounded-3xl p-8 sm:p-12 mb-20 overflow-hidden shadow-2xl border border-white/10 relative">
          <div className="absolute top-0 right-0 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative z-10">
            <div className="lg:col-span-8 space-y-4">
              <div className="inline-flex items-center space-x-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 py-1.5 px-4 rounded-full text-xs font-mono font-bold">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span>SHIELD YOUR GUILD TODAY</span>
              </div>
              <h3 className="font-heading font-extrabold text-3xl sm:text-5xl text-white tracking-tight">
                Ready to elevate your server security?
              </h3>
              <p className="font-sans text-slate-300 text-sm sm:text-base max-w-xl leading-relaxed">
                Set up Docket in under five minutes. Protect your server members, streamline moderator tasks, and enjoy peaceful, structured community growth.
              </p>
            </div>

            <div className="lg:col-span-4 flex flex-col sm:flex-row lg:flex-col sm:space-x-4 lg:space-x-0 lg:space-y-3 justify-end w-full">
              <a
                href="https://discord.com"
                target="_blank"
                rel="noreferrer"
                className="btn-primary inline-flex items-center justify-center space-x-2.5 py-3.5 px-6 rounded-xl font-heading text-sm font-bold uppercase tracking-wider text-center cursor-pointer shadow-[0_0_25px_rgba(124,58,237,0.5)]"
              >
                <Shield className="w-4 h-4" />
                <span>Add Docket to Discord</span>
              </a>
              <button
                onClick={() => {
                  const el = document.getElementById("dashboard");
                  if (el) el.scrollIntoView({ behavior: "smooth" });
                }}
                className="btn-secondary inline-flex items-center justify-center space-x-2 py-3.5 px-6 rounded-xl font-heading text-sm font-bold uppercase tracking-wider text-center mt-3 sm:mt-0 lg:mt-0 cursor-pointer"
              >
                <span>Explore Live Dashboard</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Site Navigation */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-10 mb-16 border-b border-white/10 pb-16">
          
          {/* Logo & Description */}
          <div className="lg:col-span-4 space-y-6">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-500 to-cyan-400 p-[1.5px] shadow-[0_0_15px_rgba(124,58,237,0.5)]">
                <div className="w-full h-full bg-[#05070E] rounded-[10px] flex items-center justify-center">
                  <Shield className="w-4 h-4 text-purple-400" />
                </div>
              </div>
              <span className="font-heading font-extrabold text-xl text-white tracking-tight">
                Doc<span className="bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">ket</span>
              </span>
            </div>
            <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed max-w-sm">
              Docket is a premium, sharded Discord moderation bot utilizing heuristic security layers and context-aware natural language scoring to shield top-tier server communities.
            </p>
            
            <div className="flex space-x-3">
              <a href="https://twitter.com" target="_blank" rel="noreferrer" className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-purple-500/40 hover:bg-purple-600/20 transition-all">
                <Twitter className="w-4 h-4" />
              </a>
              <a href="https://github.com" target="_blank" rel="noreferrer" className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-purple-500/40 hover:bg-purple-600/20 transition-all">
                <Github className="w-4 h-4" />
              </a>
              <a href="https://discord.com" target="_blank" rel="noreferrer" className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-purple-500/40 hover:bg-purple-600/20 transition-all">
                <MessageSquare className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Product links */}
          <div className="lg:col-span-2 space-y-4">
            <h4 className="font-heading font-bold text-xs uppercase tracking-wider text-white">Product</h4>
            <ul className="space-y-2.5 text-xs font-sans text-slate-400">
              <li><button onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })} className="hover:text-purple-300 transition-colors cursor-pointer">Bot Features</button></li>
              <li><button onClick={() => document.getElementById("smart-moderation")?.scrollIntoView({ behavior: "smooth" })} className="hover:text-purple-300 transition-colors cursor-pointer">AI Moderation</button></li>
              <li><button onClick={() => document.getElementById("commands")?.scrollIntoView({ behavior: "smooth" })} className="hover:text-purple-300 transition-colors cursor-pointer">Bot Commands</button></li>
              <li><button onClick={() => document.getElementById("pricing")?.scrollIntoView({ behavior: "smooth" })} className="hover:text-purple-300 transition-colors cursor-pointer">Pricing Plans</button></li>
            </ul>
          </div>

          {/* Resources links */}
          <div className="lg:col-span-2 space-y-4">
            <h4 className="font-heading font-bold text-xs uppercase tracking-wider text-white">Resources</h4>
            <ul className="space-y-2.5 text-xs font-sans text-slate-400">
              <li><a href="#" className="hover:text-purple-300 transition-colors flex items-center space-x-1"><span>Documentation</span> <ExternalLink className="w-3 h-3 text-slate-500" /></a></li>
              <li><a href="#" className="hover:text-purple-300 transition-colors flex items-center space-x-1"><span>Appeal Portal</span> <ExternalLink className="w-3 h-3 text-slate-500" /></a></li>
              <li><a href="#" className="hover:text-purple-300 transition-colors">Developer API</a></li>
              <li><a href="#" className="hover:text-purple-300 transition-colors">System Status</a></li>
            </ul>
          </div>

          {/* Newsletter */}
          <div className="lg:col-span-4 space-y-4">
            <h4 className="font-heading font-bold text-xs uppercase tracking-wider text-white">Security Dispatch Newsletter</h4>
            <p className="font-sans text-xs text-slate-400 leading-relaxed">
              Stay ahead of the latest phishing vectors, bot storms, and moderation strategies. Bimonthly updates straight to your inbox.
            </p>

            <form onSubmit={handleSubscribe} className="space-y-2">
              <div className="flex bg-[#090D1A] border border-white/10 p-1.5 rounded-2xl focus-within:border-purple-500/50 transition-all items-center backdrop-blur-xl">
                <Mail className="w-4 h-4 text-slate-400 ml-2.5" />
                <input
                  type="email"
                  placeholder="name@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubscribed}
                  className="bg-transparent text-xs font-sans text-white focus:outline-none flex-1 pl-2.5"
                />
                <button
                  type="submit"
                  disabled={isSubscribed}
                  className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white p-2.5 rounded-xl transition-all cursor-pointer disabled:opacity-50 shadow-md"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>

              {isSubscribed && (
                <div className="text-[11px] font-sans text-emerald-400 flex items-center space-x-1.5 pt-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Subscribed successfully! Welcome to Docket Security.</span>
                </div>
              )}
            </form>
          </div>

        </div>

        {/* Lower copyright bar */}
        <div className="flex flex-col sm:flex-row justify-between items-center py-8 text-xs text-slate-400 font-sans">
          <span>&copy; {currentYear} Docket Bot Inc. All rights reserved.</span>
          <div className="flex space-x-6 mt-4 sm:mt-0 font-medium">
            <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-white transition-colors">GDPR SLA</a>
          </div>
        </div>

      </div>
    </footer>
  );
}

