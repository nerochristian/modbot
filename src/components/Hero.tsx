import React, { useState, useEffect } from "react";
import { Shield, Sparkles, MessageSquare, Terminal, Eye, AlertCircle, CheckCircle2, Zap, Users, Globe, Lock, Cpu, ArrowUpRight, Play, Server, Layers } from "lucide-react";
import { motion } from "motion/react";

export default function Hero() {
  const [activeTab, setActiveTab] = useState<"automod" | "case" | "liveStream">("automod");
  const [activeCount, setActiveCount] = useState(148290);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveCount((prev) => prev + Math.floor(Math.random() * 3) + 1);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const scrollToId = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative min-h-[92vh] pt-36 pb-24 overflow-hidden flex flex-col justify-center bg-[#05070E]">
      
      {/* Background Cyber Mesh Grid */}
      <div className="absolute inset-0 z-0 bg-mesh-grid [mask-image:radial-gradient(ellipse_75%_60%_at_50%_40%,#000_65%,transparent_100%)] opacity-70 pointer-events-none" />

      {/* Vibrant Ambient Glowing Orbs */}
      <div className="absolute top-[-5%] left-[15%] w-[45rem] h-[45rem] bg-gradient-to-br from-violet-600/30 via-purple-600/10 to-transparent blur-[140px] rounded-full pointer-events-none animate-pulse-glow" />
      <div className="absolute bottom-[0%] right-[10%] w-[40rem] h-[40rem] bg-gradient-to-tl from-cyan-500/25 via-indigo-600/15 to-transparent blur-[140px] rounded-full pointer-events-none" />
      <div className="absolute top-[30%] right-[25%] w-[25rem] h-[25rem] bg-gradient-to-tr from-pink-500/15 via-purple-500/10 to-transparent blur-[100px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-10 items-center">
          
          {/* Hero Left Copy */}
          <div className="lg:col-span-6 flex flex-col items-start space-y-7 text-left">
            
            {/* Version Pill */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center space-x-2.5 px-4 py-1.5 rounded-full border border-purple-500/30 bg-purple-500/10 backdrop-blur-md text-xs font-semibold text-purple-300 shadow-[0_0_15px_rgba(168,85,247,0.25)]"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-400"></span>
              </span>
              <span className="font-mono text-[11px] tracking-wide">v4.2 NEURAL SECURITY ENGINE</span>
              <span className="bg-purple-400/20 text-purple-200 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase">LIVE</span>
            </motion.div>

            {/* Main Headline */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="font-heading font-extrabold text-4xl sm:text-5xl lg:text-6xl tracking-tight leading-[1.08] text-white"
            >
              AI Moderation that <br />
              <span className="bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">
                understands context
              </span>{" "}
              & intent.
            </motion.h1>

            {/* Paragraph Subtext */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="font-sans text-base sm:text-lg text-slate-300/90 max-w-xl leading-relaxed"
            >
              Protect your Discord community with proactive neural filters, instant scam link destruction, automated raid lockdown, and zero-false-positive intent evaluation.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 w-full sm:w-auto pt-2"
            >
              <a
                href="https://discord.com"
                target="_blank"
                rel="noreferrer"
                className="btn-primary inline-flex items-center justify-center space-x-3 px-7 py-4 rounded-2xl text-sm font-bold tracking-wide uppercase cursor-pointer group"
              >
                <Shield className="w-5 h-5 text-cyan-300 group-hover:scale-110 transition-transform" />
                <span>Add to Discord Server</span>
                <ArrowUpRight className="w-4 h-4 text-purple-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </a>
              
              <button
                onClick={() => scrollToId("dashboard")}
                className="btn-secondary inline-flex items-center justify-center space-x-2.5 px-6 py-4 rounded-2xl text-sm font-semibold cursor-pointer group"
              >
                <Terminal className="w-4 h-4 text-purple-400 group-hover:text-cyan-400 transition-colors" />
                <span>Live Interactive Demo</span>
              </button>
            </motion.div>

            {/* Highlight Metric Pills */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="grid grid-cols-3 gap-4 pt-6 border-t border-white/10 w-full max-w-lg"
            >
              <div className="glass-panel p-3.5 rounded-xl border border-white/5">
                <p className="font-heading font-extrabold text-2xl text-white">12ms</p>
                <p className="text-[11px] font-medium text-slate-400">Response Speed</p>
              </div>
              <div className="glass-panel p-3.5 rounded-xl border border-white/5">
                <p className="font-heading font-extrabold text-2xl text-cyan-400">99.8%</p>
                <p className="text-[11px] font-medium text-slate-400">Accuracy Score</p>
              </div>
              <div className="glass-panel p-3.5 rounded-xl border border-white/5">
                <p className="font-heading font-extrabold text-2xl text-purple-400">{activeCount.toLocaleString()}</p>
                <p className="text-[11px] font-medium text-slate-400">Threats Neutralized</p>
              </div>
            </motion.div>
          </div>

          {/* Hero Right Interactive Mock Showcase */}
          <div className="lg:col-span-6 relative flex justify-center lg:justify-end">
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="glow-card w-full max-w-xl p-5 overflow-hidden backdrop-blur-2xl relative"
            >
              
              {/* Window Header */}
              <div className="flex items-center justify-between pb-4 border-b border-white/10">
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 rounded-full bg-rose-500/90 shadow-[0_0_8px_rgba(244,63,94,0.6)]" />
                  <span className="w-3 h-3 rounded-full bg-amber-500/90 shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
                  <span className="w-3 h-3 rounded-full bg-emerald-500/90 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
                  <span className="text-xs font-mono text-slate-400 ml-2 flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-purple-400" />
                    <span>docket-neural-guard.v4</span>
                  </span>
                </div>

                {/* Interactive Tab Selector */}
                <div className="flex space-x-1 bg-[#05070E] p-1 rounded-xl border border-white/10">
                  <button
                    onClick={() => setActiveTab("automod")}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                      activeTab === "automod"
                        ? "bg-purple-600 text-white shadow-[0_0_12px_rgba(124,58,237,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    Automod
                  </button>
                  <button
                    onClick={() => setActiveTab("case")}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                      activeTab === "case"
                        ? "bg-purple-600 text-white shadow-[0_0_12px_rgba(124,58,237,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    Case Stream
                  </button>
                  <button
                    onClick={() => setActiveTab("liveStream")}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                      activeTab === "liveStream"
                        ? "bg-purple-600 text-white shadow-[0_0_12px_rgba(124,58,237,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    AI Rules
                  </button>
                </div>
              </div>

              {/* Console Body */}
              <div className="h-80 font-mono text-xs overflow-y-auto pt-4 space-y-4 pr-1">
                {activeTab === "automod" && (
                  <>
                    <div className="flex space-x-3 items-start opacity-75">
                      <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center border border-white/10 text-slate-300 text-xs font-bold">
                        U1
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-slate-200 font-sans font-bold">GamerGuy88</span>
                          <span className="text-[10px] text-slate-400">11:32 AM</span>
                        </div>
                        <p className="text-slate-300 font-sans leading-relaxed bg-white/5 p-2 rounded-lg border border-white/5">
                          CLAIM FREE NITRO GIFT RIGHT NOW! 👉 <span className="text-cyan-400 underline cursor-pointer">dlscord-nitro-free.ru/auth</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex space-x-3 items-start bg-purple-950/30 border-l-4 border-purple-500 p-3.5 rounded-r-xl shadow-lg border-y border-r border-purple-500/20">
                      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center font-sans text-white text-xs font-black shadow-lg animate-pulse">
                        D
                      </div>
                      <div className="flex-1 space-y-1.5">
                        <div className="flex items-center space-x-2">
                          <span className="text-white font-sans font-extrabold">DOCKET</span>
                          <span className="bg-purple-600 text-[9px] text-white px-1.5 py-0.5 rounded font-sans uppercase font-bold tracking-wider">AI BOT</span>
                          <span className="text-[10px] text-purple-300">Instant Execution (11ms)</span>
                        </div>
                        <div className="text-slate-200 font-sans space-y-2">
                          <p className="text-rose-400 font-bold flex items-center space-x-1.5 text-xs">
                            <AlertCircle className="w-4 h-4 text-rose-400 inline animate-bounce" />
                            <span>Phishing Domain & Identity Fraud Detected</span>
                          </p>
                          <div className="bg-[#05070E] border border-rose-500/30 p-2.5 rounded-lg text-[11px] font-mono text-slate-300 grid grid-cols-2 gap-2">
                            <div>• <span className="text-slate-400">Filter:</span> Zero-Day Phish</div>
                            <div>• <span className="text-slate-400">Action:</span> Purged & Muted</div>
                            <div>• <span className="text-slate-400">Confidence:</span> 99.98%</div>
                            <div>• <span className="text-slate-400">Risk Level:</span> Critical</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {activeTab === "case" && (
                  <div className="space-y-3 font-sans">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300 font-bold text-xs">Raid Incident Ticket #9482</span>
                      <span className="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] px-2 py-0.5 rounded-full font-bold">CONTAINED</span>
                    </div>
                    <div className="bg-[#05070E] border border-white/10 rounded-xl p-3 space-y-2 text-slate-300">
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <span className="text-slate-400 text-[11px]">Flagged Account:</span>
                          <p className="text-white font-semibold">troll_swarm_92#4011</p>
                        </div>
                        <div>
                          <span className="text-slate-400 text-[11px]">Primary Breach:</span>
                          <p className="text-cyan-400 font-semibold">Mass Mention Flooding</p>
                        </div>
                      </div>
                      <div className="pt-2 border-t border-white/10">
                        <span className="text-slate-400 text-[10px] uppercase font-mono">Telemetry Log Snip:</span>
                        <p className="text-slate-300 font-mono text-[11px] bg-slate-900/80 p-2 rounded border border-white/5 mt-1">
                          [TRIGGER] 14 messages in 1.8s across #general, #lounge. Auto-AntiRaid lockdown engaged.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "liveStream" && (
                  <div className="space-y-3 font-mono text-xs text-slate-300">
                    <div className="p-3 bg-purple-950/20 border border-purple-500/30 rounded-xl space-y-2">
                      <div className="flex items-center justify-between text-purple-300 font-bold">
                        <span>Rule #01: Smart Toxicity Threshold</span>
                        <span className="text-cyan-400 text-[10px]">ACTIVE</span>
                      </div>
                      <p className="text-slate-400 text-[11px] font-sans">
                        Dynamic NLP sentiment parsing evaluates toxic phrasing versus friendly banter using server history metrics.
                      </p>
                    </div>
                    <div className="p-3 bg-cyan-950/20 border border-cyan-500/30 rounded-xl space-y-2">
                      <div className="flex items-center justify-between text-cyan-300 font-bold">
                        <span>Rule #02: Anti-Raid Gateway Shield</span>
                        <span className="text-emerald-400 text-[10px]">AUTO-LOCK</span>
                      </div>
                      <p className="text-slate-400 text-[11px] font-sans">
                        Automatically restricts new account verifications when join velocity spikes past 15 users/sec.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Glowing Line Bottom */}
              <div className="absolute -bottom-1 -left-1 -right-1 h-[2px] bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-500 opacity-80" />
            </motion.div>

            {/* Floating Floating Pill 1 */}
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
              className="absolute -top-6 -left-6 hidden sm:flex items-center space-x-3 bg-[#090D1A]/90 border border-emerald-500/30 p-3 px-4 rounded-2xl shadow-xl backdrop-blur-xl z-20"
            >
              <div className="w-3 h-3 rounded-full bg-emerald-400 animate-ping" />
              <div className="text-left font-sans text-xs">
                <span className="text-slate-400 font-mono text-[10px] uppercase block">SHIELD MONITOR</span>
                <span className="text-white font-bold">Anti-Raid Active</span>
              </div>
            </motion.div>

            {/* Floating Pill 2 */}
            <motion.div
              animate={{ y: [0, 10, 0] }}
              transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
              className="absolute -bottom-8 -right-4 hidden sm:flex items-center space-x-3 bg-[#090D1A]/90 border border-purple-500/30 p-3 px-4 rounded-2xl shadow-xl backdrop-blur-xl z-20"
            >
              <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center">
                <Zap className="w-4 h-4 text-purple-300" />
              </div>
              <div className="text-left font-sans text-xs">
                <span className="text-slate-400 font-mono text-[10px] uppercase block">DECISION LATENCY</span>
                <span className="text-cyan-300 font-bold">Sub-15ms Global</span>
              </div>
            </motion.div>

          </div>

        </div>
      </div>

      {/* Trusted Communities Strip */}
      <div className="relative z-10 w-full mt-24 border-y border-white/10 bg-[#090D1A]/60 py-8 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs font-mono tracking-[0.25em] text-purple-300/80 uppercase mb-6 font-bold">
            TRUSTED BY OVER 15,000+ HIGH-VOLUME DISCORD COMMUNITIES WORLDWIDE
          </p>
          <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-6 opacity-60 hover:opacity-100 transition-opacity duration-300">
            <div className="flex items-center space-x-2.5 text-white font-heading font-extrabold text-sm tracking-wider hover:text-purple-400 transition-colors cursor-pointer">
              <Users className="w-5 h-5 text-purple-400" />
              <span>REDDIT ALLIANCE</span>
            </div>
            <div className="flex items-center space-x-2.5 text-white font-heading font-extrabold text-sm tracking-wider hover:text-cyan-400 transition-colors cursor-pointer">
              <Zap className="w-5 h-5 text-cyan-400" />
              <span>ESPORTS SYNDICATE</span>
            </div>
            <div className="flex items-center space-x-2.5 text-white font-heading font-extrabold text-sm tracking-wider hover:text-emerald-400 transition-colors cursor-pointer">
              <Globe className="w-5 h-5 text-emerald-400" />
              <span>WEB3 GLOBAL ECOSYSTEM</span>
            </div>
            <div className="flex items-center space-x-2.5 text-white font-heading font-extrabold text-sm tracking-wider hover:text-indigo-400 transition-colors cursor-pointer">
              <Shield className="w-5 h-5 text-indigo-400" />
              <span>DEFI GUARDIANS</span>
            </div>
            <div className="flex items-center space-x-2.5 text-white font-heading font-extrabold text-sm tracking-wider hover:text-pink-400 transition-colors cursor-pointer">
              <MessageSquare className="w-5 h-5 text-pink-400" />
              <span>DEVELOPER NETWORKS</span>
            </div>
          </div>
        </div>
      </div>

    </section>
  );
}

