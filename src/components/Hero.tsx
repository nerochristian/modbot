import React, { useState, useEffect } from "react";
import { Shield, Sparkles, MessageSquare, Terminal, Eye, AlertCircle, CheckCircle2, Zap, Users, Globe } from "lucide-react";
import { motion } from "motion/react";

export default function Hero() {
  const [activeTab, setActiveTab] = useState<"automod" | "case">("automod");

  // Simple interval to toggle or simulate active states in the preview
  const [pulseCount, setPulseCount] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      setPulseCount((prev) => prev + 1);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const scrollToId = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative min-h-screen pt-32 pb-20 overflow-hidden flex flex-col justify-center bg-[#05060B]">
      {/* Security Grid & Glow Background */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,#1f29370a_1px,transparent_1px),linear-gradient(to_bottom,#1f29370a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)]" />
      
      {/* Light Beams/Glow */}
      <div className="absolute top-12 left-[-10%] w-[40%] h-[40%] bg-purple-900/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyan-900/20 blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          
          {/* Hero Left Content */}
          <div className="lg:col-span-6 flex flex-col items-start space-y-6 text-left">
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center space-x-2 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-500/10 text-[11px] font-bold text-purple-400 uppercase tracking-widest mb-6"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
              </span>
              <span>v4.0.0 Now Live with Neural Moderation</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="font-display font-bold text-4xl sm:text-5xl lg:text-6xl tracking-tight leading-[1.1] bg-gradient-to-b from-white to-slate-400 bg-clip-text text-transparent"
            >
              Moderation that <br />
              understands <span className="text-white italic font-serif">the situation.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="font-sans text-base sm:text-lg text-slate-400 max-w-xl leading-relaxed"
            >
              Stop wrestling with basic blocklists. Docket uses advanced intent analysis and configurable AI automation to shield your community from toxicity, bad links, raids, and complex security exploits before they escalate.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col sm:flex-row items-center space-y-4 sm:space-y-0 sm:space-x-4 w-full sm:w-auto"
            >
              <a
                href="https://discord.com"
                target="_blank"
                rel="noreferrer"
                className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3 bg-white text-black rounded-full text-sm font-bold hover:bg-slate-200 transition-all shadow-[0_0_20px_rgba(255,255,255,0.15)] cursor-pointer"
              >
                <Shield className="w-4 h-4 text-purple-600" />
                <span>Add to Discord</span>
              </a>
              <button
                onClick={() => scrollToId("dashboard")}
                className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 text-sm font-medium text-slate-400 hover:text-purple-400 transition-colors py-3 px-6 cursor-pointer"
              >
                <Terminal className="w-4 h-4 text-purple-400" />
                <span>View Live Dashboard</span>
              </button>
            </motion.div>

            {/* Quick Metrics Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="grid grid-cols-3 gap-6 pt-6 border-t border-slate-800 w-full max-w-lg"
            >
              <div>
                <p className="font-display font-bold text-2xl text-white">12ms</p>
                <p className="font-sans text-xs text-slate-500">Avg response time</p>
              </div>
              <div>
                <p className="font-display font-bold text-2xl text-white">99.8%</p>
                <p className="font-sans text-xs text-slate-500">Moderation accuracy</p>
              </div>
              <div>
                <p className="font-display font-bold text-2xl text-white">100%</p>
                <p className="font-sans text-xs text-slate-500">GDPR compliant</p>
              </div>
            </motion.div>
          </div>

          {/* Hero Right Product Showcase */}
          <div className="lg:col-span-6 relative flex justify-center lg:justify-end">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative w-full max-w-xl bg-[#0E111A] border border-slate-800 rounded-2xl shadow-2xl shadow-black/80 p-5 overflow-hidden backdrop-blur-sm"
            >
              {/* Card top bar */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 rounded-full bg-red-500/80" />
                  <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <span className="w-3 h-3 rounded-full bg-green-500/80" />
                  <span className="text-xs font-mono text-slate-500 ml-2">docket-engine-v4.sh</span>
                </div>
                <div className="flex space-x-1.5 bg-[#05060B] p-0.5 rounded-lg border border-slate-800">
                  <button
                    onClick={() => setActiveTab("automod")}
                    className={`px-3 py-1 text-xs font-sans rounded-md transition-all cursor-pointer ${
                      activeTab === "automod"
                        ? "bg-purple-950/80 text-purple-300 font-medium"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    Automod AI
                  </button>
                  <button
                    onClick={() => setActiveTab("case")}
                    className={`px-3 py-1 text-xs font-sans rounded-md transition-all cursor-pointer ${
                      activeTab === "case"
                        ? "bg-purple-950/80 text-purple-300 font-medium"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    Case Logic
                  </button>
                </div>
              </div>

              {/* Dynamic Content Frame */}
              <div className="h-76 font-mono text-xs overflow-y-auto pt-4 space-y-4 pr-1">
                {activeTab === "automod" ? (
                  <>
                    {/* Simulated Chat & Action Sequence */}
                    <div className="flex space-x-3 items-start opacity-75">
                      <div className="w-8 h-8 rounded-full bg-slate-900 flex items-center justify-center border border-slate-800 font-sans text-slate-400 text-xs font-bold">
                        U1
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-slate-300 font-sans font-semibold">GamerGuy88</span>
                          <span className="text-[10px] text-slate-500">Today at 11:32 AM</span>
                        </div>
                        <p className="text-slate-400 font-sans leading-relaxed">
                          Check this out, FREE DISCORD NITRO FOR ALL! 👉 CLICK HERE: <span className="text-cyan-400 underline cursor-pointer">dlscord-glft.ru/nitro-free-10382</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex space-x-3 items-start bg-purple-950/20 border-l-2 border-purple-500/80 p-2.5 rounded-r-lg">
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center font-sans text-white text-xs font-bold shadow animate-pulse">
                        D
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-white font-sans font-semibold">Docket</span>
                          <span className="bg-purple-900/80 text-[9px] text-purple-300 px-1 rounded font-sans uppercase font-bold">BOT</span>
                          <span className="text-[10px] text-slate-500">Today at 11:32 AM</span>
                        </div>
                        <div className="text-slate-300 font-sans space-y-2">
                          <p className="text-red-400 font-semibold flex items-center space-x-1.5">
                            <AlertCircle className="w-3.5 h-3.5 inline animate-bounce" />
                            <span>Exploit Link Filter Triggered</span>
                          </p>
                          <p className="text-xs text-slate-400 leading-normal">
                            Malicious domain impersonating <code className="text-slate-300 bg-slate-950 px-1 rounded">discord.gift</code> detected. URL redirected through Russian registry proxies.
                          </p>
                          <div className="bg-[#05060B] border border-red-500/20 p-2 rounded text-[11px] font-mono text-slate-400 grid grid-cols-2 gap-2 mt-1">
                            <div>• <span className="text-slate-500">Action:</span> Delete Message</div>
                            <div>• <span className="text-slate-500">Punishment:</span> Temp Mute (1h)</div>
                            <div>• <span className="text-slate-500">Risk Confidence:</span> 99.8%</div>
                            <div>• <span className="text-slate-500">Context Status:</span> User account created 2h ago</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    {/* Simulated Case Review and AI Categorization */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400 font-medium">Case Analysis #14892</span>
                        <span className="bg-red-950/60 text-red-400 border border-red-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">HIGH RISK</span>
                      </div>
                      <div className="bg-[#05060B] border border-slate-800 rounded-lg p-3 space-y-2 text-slate-400">
                        <div className="grid grid-cols-2 gap-3 text-[11px]">
                          <div>
                            <span className="text-slate-500">Server Member:</span> <br />
                            <span className="text-white font-sans">vibe_master#1099</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Violation Category:</span> <br />
                            <span className="text-cyan-400">Targeted Toxicity / Raiding</span>
                          </div>
                        </div>
                        <div className="pt-2 border-t border-slate-800/80">
                          <span className="text-slate-500">System Evidence Log:</span>
                          <p className="text-slate-300 font-sans italic text-xs mt-1 bg-[#0E111A] p-2 rounded border border-slate-800 leading-normal">
                            "everyone ping the admins now and post the raid link!! @everyone join the server: spam.gg/exploit they cannot stop us"
                          </p>
                        </div>
                      </div>
                      <div className="bg-purple-950/20 border border-purple-500/20 p-3 rounded-lg space-y-2">
                        <div className="flex items-center space-x-1.5 text-purple-300 font-sans font-semibold">
                          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                          <span>AI Context Assessment</span>
                        </div>
                        <p className="text-xs text-slate-400 leading-normal font-sans">
                          User coordinates with 4 incoming accounts to trigger simultaneous <code className="text-slate-300 bg-slate-950 px-1">@everyone</code> and <code className="text-slate-300 bg-slate-950 px-1">@here</code> notifications. Sent 6 messages across 3 channels in under 4.2 seconds.
                        </p>
                        <div className="flex space-x-2 mt-2">
                          <span className="bg-purple-900/60 text-purple-300 px-2 py-0.5 rounded text-[10px] font-sans font-semibold">Auto-Ban Initiated</span>
                          <span className="bg-cyan-900/60 text-cyan-300 px-2 py-0.5 rounded text-[10px] font-sans font-semibold">Raid Mode Activated</span>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Glowing decorative border effect */}
              <div className="absolute -bottom-1 -left-1 -right-1 h-[2px] bg-gradient-to-r from-purple-500 via-pink-500 to-cyan-500 opacity-60" />
            </motion.div>

            {/* Floating Case Widget Overlay 1 */}
            <motion.div
              animate={{
                y: [0, -8, 0],
              }}
              transition={{
                duration: 5,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="absolute -top-6 -left-8 hidden sm:flex items-center space-x-2 bg-[#0E111A]/90 border border-emerald-500/20 p-2.5 px-4 rounded-xl shadow-lg backdrop-blur"
            >
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <div className="text-left font-sans text-xs">
                <span className="text-slate-500 font-semibold text-[10px] uppercase block">SHIELD STATUS</span>
                <span className="text-white font-bold">Raid Protection: Active</span>
              </div>
            </motion.div>

            {/* Floating Metric Widget Overlay 2 */}
            <motion.div
              animate={{
                y: [0, 8, 0],
              }}
              transition={{
                duration: 6,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 0.5,
              }}
              className="absolute -bottom-8 -right-4 hidden sm:flex items-center space-x-3 bg-[#0E111A]/90 border border-slate-800 p-2.5 px-4 rounded-xl shadow-lg backdrop-blur"
            >
              <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Zap className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-left font-sans text-xs">
                <span className="text-slate-500 font-semibold text-[10px] uppercase block">DECISION ENGINE</span>
                <span className="text-white font-bold">142,429 cases resolved</span>
              </div>
            </motion.div>
          </div>

        </div>
      </div>

      {/* Trusted By Strip */}
      <div className="relative z-10 w-full mt-20 border-t border-b border-slate-800/50 bg-black/50 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs font-mono tracking-[0.2em] text-slate-500 uppercase mb-5">
            Empowering moderators across top-tier server communities
          </p>
          <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-6 opacity-40 grayscale hover:opacity-75 transition-opacity duration-300">
            <div className="flex items-center space-x-2 text-white">
              <Users className="w-4 h-4 text-purple-400" />
              <span className="font-display font-bold text-sm tracking-wide">REDDIT COMMUNITIES</span>
            </div>
            <div className="flex items-center space-x-2 text-white">
              <Zap className="w-4 h-4 text-cyan-400" />
              <span className="font-display font-bold text-sm tracking-wide">GAMING HUB ALPHA</span>
            </div>
            <div className="flex items-center space-x-2 text-white">
              <Globe className="w-4 h-4 text-emerald-400" />
              <span className="font-display font-bold text-sm tracking-wide">WEB3 OFFICIALS</span>
            </div>
            <div className="flex items-center space-x-2 text-white">
              <Shield className="w-4 h-4 text-yellow-400" />
              <span className="font-display font-bold text-sm tracking-wide">CRITICAL DISCORD HUB</span>
            </div>
            <div className="flex items-center space-x-2 text-white">
              <MessageSquare className="w-4 h-4 text-blue-400" />
              <span className="font-display font-bold text-sm tracking-wide">DEV CHANNELS</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
