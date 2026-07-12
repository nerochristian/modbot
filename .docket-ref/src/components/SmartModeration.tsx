import React, { useState } from "react";
import { Brain, ShieldCheck, Scale, Sliders, Play, AlertTriangle, Shield, CheckCircle } from "lucide-react";

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
    <section id="smart-moderation" className="relative py-24 bg-[#05060B] overflow-hidden border-t border-slate-800/80">
      {/* Visual accents */}
      <div className="absolute top-1/2 right-0 -translate-y-1/2 w-[300px] h-[300px] bg-purple-500/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-[250px] h-[250px] bg-cyan-500/5 rounded-full blur-[90px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Header Block */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-cyan-950/40 border border-cyan-500/20 text-cyan-400 py-1 px-3 rounded-full text-xs font-mono mb-4">
            <Brain className="w-3.5 h-3.5" />
            <span>CONTEXT-AWARE MODERATION</span>
          </div>
          <h2 className="font-display font-bold text-3xl sm:text-4xl text-white tracking-tight mb-4">
            Intelligence that understands intent, not just words.
          </h2>
          <p className="font-sans text-slate-400 text-base sm:text-lg">
            Traditional bots search for matching letters. Docket evaluates the entire user’s behavior history, server standing, and conversational context to make precise, human-grade calls in milliseconds.
          </p>
        </div>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          
          <div className="bg-[#0E111A] border border-slate-800 p-6 rounded-2xl text-left hover:border-purple-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400 mb-5 group-hover:bg-purple-500/20 transition-all">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-display font-bold text-lg text-white mb-2">Contextual Recommendations</h3>
            <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
              Docket analyses user roles, past infractions, account creation dates, and message frequency to suggest contextually sound punishments, protecting your community without false positives.
            </p>
          </div>

          <div className="bg-[#0E111A] border border-slate-800 p-6 rounded-2xl text-left hover:border-cyan-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 mb-5 group-hover:bg-cyan-500/20 transition-all">
              <Sliders className="w-6 h-6" />
            </div>
            <h3 className="font-display font-bold text-lg text-white mb-2">Customizable Thresholds</h3>
            <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
              Define exact limits for toxicity, raid alerts, link bans, and caps. Set specific rules for different channels (e.g. permit more relaxed speech in NSFW, tight filters in announcements).
            </p>
          </div>

          <div className="bg-[#0E111A] border border-slate-800 p-6 rounded-2xl text-left hover:border-violet-500/40 transition-all group">
            <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center text-violet-400 mb-5 group-hover:bg-violet-500/20 transition-all">
              <Scale className="w-6 h-6" />
            </div>
            <h3 className="font-display font-bold text-lg text-white mb-2">Human Appeal Integration</h3>
            <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
              Avoid absolute lockdowns. Docket creates temporary appeal instances, allowing mistakenly muted users to explain, review case notes, and request staff review in a secure dedicated sub-thread.
            </p>
          </div>

        </div>

        {/* INTERACTIVE COMPONENT: Moderation Engine Simulator */}
        <div className="bg-[#0E111A] border border-slate-800 rounded-3xl p-6 sm:p-8 lg:p-10 shadow-2xl shadow-black/60 relative overflow-hidden text-left">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 rounded-full blur-2xl pointer-events-none" />
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            
            {/* Control Panel (Left Side of Interactive) */}
            <div className="lg:col-span-5 space-y-6">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-widest text-purple-400 font-semibold block mb-1">
                  INTERACTIVE LABS
                </span>
                <h3 className="font-display font-bold text-2xl text-white">
                  Test the Decision Engine
                </h3>
                <p className="font-sans text-xs sm:text-sm text-slate-400 mt-2 leading-relaxed">
                  Select a typical server message below and adjust the filter sensitivity threshold to simulate real automod responses.
                </p>
              </div>

              {/* Message selectors */}
              <div className="space-y-2">
                <span className="text-[11px] font-mono text-slate-500 block">SELECT CHAT MESSAGE TYPE:</span>
                <div className="grid grid-cols-2 gap-2">
                  {SAMPLE_MESSAGES.map((msg) => (
                    <button
                      key={msg.id}
                      onClick={() => setSelectedMsg(msg)}
                      className={`py-2.5 px-3 text-xs font-sans font-medium rounded-lg text-left transition-all border cursor-pointer ${
                        selectedMsg.id === msg.id
                          ? "bg-purple-950/40 border-purple-500/50 text-white shadow-md shadow-purple-950/20"
                          : "bg-[#05060B] border-slate-800 text-slate-400 hover:text-white hover:bg-slate-900/50"
                      }`}
                    >
                      {msg.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Threshold Slider */}
              <div className="space-y-2 bg-[#05060B] p-4 rounded-xl border border-slate-800">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-slate-500">AUTOMOD SENSITIVITY:</span>
                  <span className="text-purple-400 font-bold">{threshold}% Confidence</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="95"
                  value={threshold}
                  onChange={(e) => setThreshold(parseInt(e.target.value))}
                  className="w-full accent-purple-500 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-600 font-mono">
                  <span>Lax (10%)</span>
                  <span>Strict (95%)</span>
                </div>
              </div>
            </div>

            {/* Live Terminal Output (Right Side of Interactive) */}
            <div className="lg:col-span-7 bg-[#05060B] border border-slate-800 rounded-2xl p-5 sm:p-6 font-mono text-xs text-slate-300 relative">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
                  <span className="text-[10px] text-slate-500 font-mono">docket-ai-inference-logs</span>
                </div>
                <span className="text-[10px] text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-900/30">
                  ONLINE
                </span>
              </div>

              {/* Chat Text Input Bubble */}
              <div className="mb-4 bg-[#0E111A] border border-slate-800 p-3 rounded-xl">
                <span className="text-[9px] text-purple-400 font-bold block mb-1">INCOMING PACKET:</span>
                <p className="font-sans text-xs text-white leading-relaxed">{selectedMsg.text}</p>
              </div>

              {/* Output parameters */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span>ANALYZING SENTIMENT SCORE:</span>
                  <span className={`font-bold ${selectedMsg.toxicityScore > 70 ? "text-red-400" : "text-emerald-400"}`}>
                    {selectedMsg.toxicityScore}% Violation Vector
                  </span>
                </div>

                {/* Score bar */}
                <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      selectedMsg.toxicityScore > 70
                        ? "bg-red-500"
                        : selectedMsg.toxicityScore > 40
                        ? "bg-yellow-500"
                        : "bg-emerald-500"
                    }`}
                    style={{ width: `${selectedMsg.toxicityScore}%` }}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4 pt-3 border-t border-slate-800 text-[11px]">
                  <div>
                    <span className="text-slate-500 block">THRESHOLD MATCH:</span>
                    {isTriggered ? (
                      <span className="text-red-400 font-bold flex items-center space-x-1 mt-0.5">
                        <AlertTriangle className="w-3.5 h-3.5 inline animate-pulse" />
                        <span>TRIGGERED ({selectedMsg.toxicityScore}% &gt;= {threshold}%)</span>
                      </span>
                    ) : (
                      <span className="text-emerald-400 font-bold flex items-center space-x-1 mt-0.5">
                        <CheckCircle className="w-3.5 h-3.5 inline animate-pulse" />
                        <span>SURPASSED ({selectedMsg.toxicityScore}% &lt; {threshold}%)</span>
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-500 block">AI DIAGNOSTIC:</span>
                    <span className="text-slate-300 block mt-0.5 font-sans leading-tight">
                      {selectedMsg.reason}
                    </span>
                  </div>
                </div>

                {/* Simulated action box */}
                <div className={`mt-4 p-3 rounded-lg border flex items-center justify-between transition-all ${
                  isTriggered
                    ? "bg-red-950/20 border-red-500/20"
                    : "bg-emerald-950/10 border-emerald-500/10"
                }`}>
                  <div>
                    <span className="text-[10px] text-slate-500 font-mono block">DECISION DIRECTIVE:</span>
                    <span className={`text-xs font-bold font-mono tracking-wider ${
                      isTriggered ? "text-red-400" : "text-emerald-400"
                    }`}>
                      {isTriggered ? selectedMsg.recommendedAction : "ALLOW MESSAGE IN CHANNEL"}
                    </span>
                  </div>
                  <div className={`p-1.5 rounded-full ${isTriggered ? "bg-red-500/10 text-red-400" : "bg-emerald-500/10 text-emerald-400"}`}>
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
