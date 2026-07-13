import React, { useState } from "react";
import { Brain, ShieldCheck, Scale, Sliders, Play, AlertTriangle, Shield, CheckCircle, Sparkles } from "lucide-react";

interface SampleMessage {
  id: string;
  label: string;
  text: string;
  toxicityScore: number; // percentage
  categories: { spam: boolean; scam: boolean; toxic: boolean; promotion: boolean };
  recommendedAction: string;
  reason: string;
}

const SAMPLE_MESSAGES: SampleMessage[] = [
  {
    id: "scam",
    label: "Crypto Scam",
    text: "🔥 FREE $ETH INSTATNLY! Send 0.1 ETH to receive 1.0 ETH back. Limited slot left, click here: trust-wallet-rewards-node.ru/airdrop",
    toxicityScore: 98,
    categories: { spam: true, scam: true, toxic: false, promotion: false },
    recommendedAction: "AUTO-BAN & PURGE MESSAGES",
    reason: "High confidence crypto phishing domain redirected through multi-hop proxy proxies.",
  },
  {
    id: "toxic",
    label: "Toxicity / Harassment",
    text: "You are an absolute idiot. Nobody likes you, why don't you just leave this server and delete your account, trash admin.",
    toxicityScore: 89,
    categories: { spam: false, scam: false, toxic: true, promotion: false },
    recommendedAction: "TEMP-MUTE (6 Hours) & WARN",
    reason: "Severe targeted hostility, emotional abuse, and harassment vectors detected.",
  },
  {
    id: "spam",
    label: "Link Spam / Promo",
    text: "JOIN MY NEW SERVER GUYS! we have giveaways, chatting, active staff, and nitro! JOIN NOW: discord.gg/fakeinvitepromo",
    toxicityScore: 62,
    categories: { spam: true, scam: false, toxic: false, promotion: true },
    recommendedAction: "DELETE MESSAGE & ISSUE WARNING",
    reason: "Unsolicited promotional invite spamming without verified media partner roles.",
  },
  {
    id: "friendly",
    label: "Friendly Chat",
    text: "Honestly, the new raid boss is pretty tough but if we coordinate our tanks and healers we can easily clear it tonight!",
    toxicityScore: 4,
    categories: { spam: false, scam: false, toxic: false, promotion: false },
    recommendedAction: "ALLOW MESSAGE (SAFE)",
    reason: "Safe organic dialogue regarding gaming content. Toxicity metrics within regular bounds.",
  }
];

export default function SmartModeration() {
  const [selectedMsg, setSelectedMsg] = useState<SampleMessage>(SAMPLE_MESSAGES[0]);
  const [threshold, setThreshold] = useState<number>(75);

  const isTriggered = selectedMsg.toxicityScore >= threshold;

  return (
    <section id="smart-moderation" className="relative py-28 bg-[#05070E] overflow-hidden border-t border-white/10">
      
      {/* Glow Ambient Lights */}
      <div className="absolute top-1/2 right-0 -translate-y-1/2 w-[400px] h-[400px] bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-[350px] h-[350px] bg-cyan-500/10 rounded-full blur-[130px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 py-1.5 px-4 rounded-full text-xs font-mono mb-4">
            <Brain className="w-4 h-4 text-cyan-300" />
            <span>CONTEXT-AWARE MODERATION</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl text-white tracking-tight mb-4">
            Intelligence that understands intent, <span className="bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">not just keywords</span>.
          </h2>
          <p className="font-sans text-slate-300 text-base sm:text-lg leading-relaxed">
            Traditional bots search for matching letters. Docket evaluates the entire user’s behavior history, server standing, and conversational context to make precise, human-grade calls in milliseconds.
          </p>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          
          <div className="glass-panel-hover p-7 rounded-2xl text-left">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-500/30 flex items-center justify-center text-purple-300 mb-6 shadow-md">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-heading font-bold text-lg text-white mb-2">Contextual Recommendations</h3>
            <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
              Docket analyses user roles, past infractions, account creation dates, and message frequency to suggest contextually sound punishments, protecting your community without false positives.
            </p>
          </div>

          <div className="glass-panel-hover p-7 rounded-2xl text-left">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-300 mb-6 shadow-md">
              <Sliders className="w-6 h-6" />
            </div>
            <h3 className="font-heading font-bold text-lg text-white mb-2">Customizable Thresholds</h3>
            <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
              Define exact limits for toxicity, raid alerts, link bans, and caps. Set specific rules for different channels (e.g. permit more relaxed speech in NSFW, tight filters in announcements).
            </p>
          </div>

          <div className="glass-panel-hover p-7 rounded-2xl text-left">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 mb-6 shadow-md">
              <Scale className="w-6 h-6" />
            </div>
            <h3 className="font-heading font-bold text-lg text-white mb-2">Human Appeal Integration</h3>
            <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
              Avoid absolute lockdowns. Docket creates temporary appeal instances, allowing mistakenly muted users to explain, review case notes, and request staff review in a secure dedicated sub-thread.
            </p>
          </div>

        </div>

        {/* INTERACTIVE COMPONENT: Moderation Engine Simulator */}
        <div className="glow-card rounded-3xl p-6 sm:p-8 lg:p-10 shadow-2xl relative overflow-hidden text-left border border-white/10">
          <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            
            {/* Control Panel */}
            <div className="lg:col-span-5 space-y-6">
              <div>
                <span className="text-[11px] font-mono uppercase tracking-widest text-purple-300 font-bold block mb-1">
                  INTERACTIVE SENTIMENT LABS
                </span>
                <h3 className="font-heading font-extrabold text-2xl text-white">
                  Test the Decision Engine
                </h3>
                <p className="font-sans text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
                  Select a typical server message below and adjust the filter sensitivity threshold to simulate real automod responses.
                </p>
              </div>

              {/* Message Selectors */}
              <div className="space-y-2">
                <span className="text-[11px] font-mono text-slate-400 block font-semibold">SELECT CHAT MESSAGE SCENARIO:</span>
                <div className="grid grid-cols-2 gap-2.5">
                  {SAMPLE_MESSAGES.map((msg) => (
                    <button
                      key={msg.id}
                      onClick={() => setSelectedMsg(msg)}
                      className={`py-3 px-3.5 text-xs font-heading font-bold rounded-xl text-left transition-all border cursor-pointer ${
                        selectedMsg.id === msg.id
                          ? "bg-purple-600/30 border-purple-500/60 text-white shadow-[0_0_15px_rgba(124,58,237,0.3)]"
                          : "bg-[#090D1A] border-white/5 text-slate-400 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      {msg.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Threshold Slider */}
              <div className="space-y-2.5 bg-[#090D1A] p-4.5 rounded-2xl border border-white/10">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-slate-400 font-semibold">AUTOMOD SENSITIVITY:</span>
                  <span className="text-purple-300 font-bold bg-purple-500/20 px-2 py-0.5 rounded border border-purple-500/40">
                    {threshold}% Confidence
                  </span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="95"
                  value={threshold}
                  onChange={(e) => setThreshold(parseInt(e.target.value))}
                  className="w-full accent-purple-500 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>Permissive (10%)</span>
                  <span>Strict (95%)</span>
                </div>
              </div>
            </div>

            {/* Live Terminal Output */}
            <div className="lg:col-span-7 bg-[#090D1A] border border-white/10 rounded-2xl p-6 font-mono text-xs text-slate-200 relative shadow-2xl">
              <div className="flex items-center justify-between pb-3.5 border-b border-white/10 mb-4">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]" />
                  <span className="text-[11px] text-slate-400 font-mono">docket-ai-inference-stream</span>
                </div>
                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/30 font-bold">
                  LIVE INFERENCE
                </span>
              </div>

              {/* Input Packet Bubble */}
              <div className="mb-4 bg-white/5 border border-white/10 p-3.5 rounded-xl">
                <span className="text-[10px] text-purple-300 font-bold block mb-1">INCOMING PACKET DATA:</span>
                <p className="font-sans text-xs text-white leading-relaxed">{selectedMsg.text}</p>
              </div>

              {/* Output parameters */}
              <div className="space-y-3.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-400">ANALYZING SENTIMENT VECTOR:</span>
                  <span className={`font-bold ${selectedMsg.toxicityScore > 70 ? "text-rose-400" : "text-emerald-400"}`}>
                    {selectedMsg.toxicityScore}% Violation Vector
                  </span>
                </div>

                {/* Score bar */}
                <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${
                      selectedMsg.toxicityScore > 70
                        ? "bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.6)]"
                        : selectedMsg.toxicityScore > 40
                        ? "bg-amber-400"
                        : "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.6)]"
                    }`}
                    style={{ width: `${selectedMsg.toxicityScore}%` }}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4 pt-3.5 border-t border-white/10 text-[11px]">
                  <div>
                    <span className="text-slate-400 block">THRESHOLD EVALUATION:</span>
                    {isTriggered ? (
                      <span className="text-rose-400 font-bold flex items-center space-x-1 mt-1">
                        <AlertTriangle className="w-3.5 h-3.5 inline animate-bounce" />
                        <span>TRIGGERED ({selectedMsg.toxicityScore}% &gt;= {threshold}%)</span>
                      </span>
                    ) : (
                      <span className="text-emerald-400 font-bold flex items-center space-x-1 mt-1">
                        <CheckCircle className="w-3.5 h-3.5 inline animate-pulse" />
                        <span>PASSED ({selectedMsg.toxicityScore}% &lt; {threshold}%)</span>
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-400 block">AI DIAGNOSTIC METRIC:</span>
                    <span className="text-slate-200 block mt-1 font-sans leading-tight">
                      {selectedMsg.reason}
                    </span>
                  </div>
                </div>

                {/* Directive Box */}
                <div className={`mt-4 p-3.5 rounded-xl border flex items-center justify-between transition-all ${
                  isTriggered
                    ? "bg-rose-500/10 border-rose-500/30"
                    : "bg-emerald-500/10 border-emerald-500/30"
                }`}>
                  <div>
                    <span className="text-[10px] text-slate-400 font-mono block">DECISION DIRECTIVE:</span>
                    <span className={`text-xs font-bold font-mono tracking-wider ${
                      isTriggered ? "text-rose-300" : "text-emerald-300"
                    }`}>
                      {isTriggered ? selectedMsg.recommendedAction : "ALLOW MESSAGE IN CHANNEL"}
                    </span>
                  </div>
                  <div className={`p-2 rounded-xl ${isTriggered ? "bg-rose-500/20 text-rose-300" : "bg-emerald-500/20 text-emerald-300"}`}>
                    {isTriggered ? <Shield className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
                  </div>
                </div>
              </div>

            </div>

          </div>
        </div>

      </div>
    </section>
  );
}

