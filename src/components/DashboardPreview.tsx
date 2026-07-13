import React, { useState } from "react";
import { LayoutDashboard, ShieldAlert, Settings, BarChart3, HelpCircle, Activity, ChevronRight, Check, X, ShieldCheck, ToggleLeft, ToggleRight, Trash2, Calendar, Sparkles, Server } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { CaseLog } from "../types";

const INITIAL_CASES: CaseLog[] = [
  {
    id: "4810",
    user: "AlphaSpammer#1129",
    userId: "41924109",
    moderator: "Docket_AI",
    action: "BAN",
    reason: "Severe scam link dissemination (Phishing)",
    timestamp: "11:29:45 AM",
    severity: "high",
    aiSummary: "Automated analysis matched known Russian redirect. Banned on first violation."
  },
  {
    id: "4809",
    user: "ToxicGamer#8841",
    userId: "88412093",
    moderator: "ModChloe",
    action: "WARN",
    reason: "Repeated toxic slurs in #general after verbal warning",
    timestamp: "11:24:10 AM",
    severity: "medium",
    aiSummary: "Context evaluation classified 84% toxic confidence score."
  },
  {
    id: "4808",
    user: "AdBot_404#2023",
    userId: "20231924",
    moderator: "Docket_AI",
    action: "MUTE",
    reason: "Invite link spam in off-topic channel",
    timestamp: "11:15:32 AM",
    severity: "low",
    aiSummary: "Sent 5 invite links within 2.8 seconds. Muted for 1 hour."
  },
  {
    id: "4807",
    user: "RegularDude#0001",
    userId: "00019284",
    moderator: "ModJack",
    action: "RESOLVED",
    reason: "Appeal approved: Account was compromised and recovered",
    timestamp: "11:02:15 AM",
    severity: "medium",
    aiSummary: "Manual staff intervention. Verification matched original owner login."
  }
];

interface AppealItem {
  id: string;
  user: string;
  reason: string;
  action: string;
  status: "pending" | "approved" | "rejected";
}

const INITIAL_APPEALS: AppealItem[] = [
  { id: "app-1", user: "SadGamer#4040", reason: "I was super angry during the clan match, I apologize for typing that. I won't do it again.", action: "MUTE (6h)", status: "pending" },
  { id: "app-2", user: "FriendlyBot#1234", reason: "My account got hacked by a phishing bot. I have added 2FA now.", action: "BAN (Perm)", status: "pending" },
];

export default function DashboardPreview() {
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [cases, setCases] = useState<CaseLog[]>(INITIAL_CASES);
  const [appeals, setAppeals] = useState<AppealItem[]>(INITIAL_APPEALS);

  const [automodConfig, setAutomodConfig] = useState({
    raidShield: true,
    spamFilter: true,
    scamDetector: true,
    toxicityFilter: false,
    verificationCaptcha: true,
  });

  const toggleConfig = (key: keyof typeof automodConfig) => {
    setAutomodConfig(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const handleAppeal = (id: string, decision: "approved" | "rejected") => {
    setAppeals(prev =>
      prev.map(app => (app.id === id ? { ...app, status: decision } : app))
    );
  };

  const deleteCase = (id: string) => {
    setCases(prev => prev.filter(c => c.id !== id));
  };

  return (
    <section id="dashboard" className="relative py-28 bg-[#05070E] overflow-hidden border-t border-white/10">
      
      {/* Background Lighting */}
      <div className="absolute top-1/4 right-1/4 w-[450px] h-[450px] bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Title Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 py-1.5 px-4 rounded-full text-xs font-mono mb-4">
            <LayoutDashboard className="w-4 h-4 text-cyan-400" />
            <span>INTERACTIVE CLOUD COCKPIT</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl text-white tracking-tight mb-4">
            Manage server security from one <span className="bg-gradient-to-r from-cyan-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">central control room</span>.
          </h2>
          <p className="font-sans text-slate-300 text-base sm:text-lg leading-relaxed">
            No complicated Discord text prompts required. Set thresholds, analyze real-time infraction metrics, review appeals, and view full case history through our ultra-responsive web dashboard interface.
          </p>
        </div>

        {/* Dashboard Mockup Window */}
        <div className="glow-card rounded-3xl overflow-hidden shadow-2xl flex flex-col md:flex-row h-[560px] text-left border border-white/10">
          
          {/* Left Sidebar */}
          <div className="w-full md:w-64 bg-[#090D1A] border-r border-white/10 flex flex-col p-4 space-y-1.5">
            <div className="pb-4 mb-3 border-b border-white/10 flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center shadow-md">
                <ShieldCheck className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="font-heading font-bold text-sm text-white block">Docket Cloud</span>
                <span className="text-[10px] text-purple-300/80 font-mono">v4.2 Neural Shard</span>
              </div>
            </div>

            {/* Nav Items */}
            <button
              onClick={() => setActiveTab("overview")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                activeTab === "overview"
                  ? "bg-purple-600/20 text-purple-200 border-purple-500/40 shadow-[0_0_15px_rgba(124,58,237,0.3)] font-bold"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border-transparent"
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Server Overview</span>
            </button>

            <button
              onClick={() => setActiveTab("cases")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                activeTab === "cases"
                  ? "bg-purple-600/20 text-purple-200 border-purple-500/40 shadow-[0_0_15px_rgba(124,58,237,0.3)] font-bold"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border-transparent"
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span className="flex-1 text-left">Case Logs</span>
              <span className="bg-purple-500/30 text-[10px] text-purple-200 px-2 py-0.5 rounded-full font-mono font-bold">
                {cases.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("automod")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                activeTab === "automod"
                  ? "bg-purple-600/20 text-purple-200 border-purple-500/40 shadow-[0_0_15px_rgba(124,58,237,0.3)] font-bold"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border-transparent"
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Automod Config</span>
            </button>

            <button
              onClick={() => setActiveTab("analytics")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                activeTab === "analytics"
                  ? "bg-purple-600/20 text-purple-200 border-purple-500/40 shadow-[0_0_15px_rgba(124,58,237,0.3)] font-bold"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border-transparent"
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Analytics</span>
            </button>

            <button
              onClick={() => setActiveTab("appeals")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                activeTab === "appeals"
                  ? "bg-purple-600/20 text-purple-200 border-purple-500/40 shadow-[0_0_15px_rgba(124,58,237,0.3)] font-bold"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border-transparent"
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span className="flex-1 text-left">Appeals Queue</span>
              {appeals.filter(a => a.status === "pending").length > 0 && (
                <span className="bg-rose-500 text-[10px] text-white px-2 py-0.5 rounded-full font-mono font-black animate-pulse">
                  {appeals.filter(a => a.status === "pending").length}
                </span>
              )}
            </button>

            <div className="mt-auto pt-4 border-t border-white/10 flex items-center space-x-2 text-[11px] font-mono text-slate-400">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
              <span>Cluster-US East Active</span>
            </div>
          </div>

          {/* Right Content */}
          <div className="flex-1 bg-[#05070E]/80 backdrop-blur-xl overflow-y-auto p-6 text-slate-300">
            
            {/* OVERVIEW */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                <div>
                  <h4 className="font-heading font-extrabold text-xl text-white">Server Intelligence Briefing</h4>
                  <p className="font-sans text-xs text-slate-400">Real-time threat status and member telemetry data.</p>
                </div>

                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="glass-panel p-4 rounded-2xl border border-white/5">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Total Guild Members</span>
                    <p className="font-heading font-extrabold text-2xl text-white mt-1">14,285</p>
                    <span className="text-[10px] text-emerald-400 font-sans block mt-1">+142 this week</span>
                  </div>
                  <div className="glass-panel p-4 rounded-2xl border border-white/5">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Security Status</span>
                    <p className="font-heading font-extrabold text-2xl text-emerald-400 mt-1">CONTAINED</p>
                    <span className="text-[10px] text-slate-400 font-sans block mt-1">0 active attacks</span>
                  </div>
                  <div className="glass-panel p-4 rounded-2xl border border-white/5">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Total Mod Cases</span>
                    <p className="font-heading font-extrabold text-2xl text-white mt-1">412</p>
                    <span className="text-[10px] text-purple-300 font-sans block mt-1">99.2% AI Auto-Resolved</span>
                  </div>
                  <div className="glass-panel p-4 rounded-2xl border border-white/5">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Neural Shield</span>
                    <p className="font-heading font-extrabold text-2xl text-cyan-400 mt-1">ENABLED</p>
                    <span className="text-[10px] text-slate-400 font-sans block mt-1">Confidence Target: 95%</span>
                  </div>
                </div>

                <div className="glass-panel rounded-2xl p-5 space-y-3 border border-white/10">
                  <div className="flex justify-between items-center pb-3 border-b border-white/5">
                    <span className="font-mono text-xs text-purple-300 font-bold tracking-wider">LIVE TELEMETRY STREAM</span>
                    <span className="text-[10px] font-mono text-emerald-400">ACTIVE FEED</span>
                  </div>
                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex justify-between hover:bg-white/5 p-2 rounded-xl transition-all">
                      <span className="text-purple-300">• AUTOMOD RULE #03: Phishing domain redirect blocked</span>
                      <span className="text-slate-500">2 mins ago</span>
                    </div>
                    <div className="flex justify-between hover:bg-white/5 p-2 rounded-xl transition-all">
                      <span className="text-cyan-300">• RAID LOCKDOWN: Joint verification engaged</span>
                      <span className="text-slate-500">14 mins ago</span>
                    </div>
                    <div className="flex justify-between hover:bg-white/5 p-2 rounded-xl transition-all">
                      <span className="text-amber-300">• INFRACTION LOG #4812: Mute logged for @Scammer</span>
                      <span className="text-slate-500">22 mins ago</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* CASES */}
            {activeTab === "cases" && (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-heading font-extrabold text-xl text-white">Sharded Infraction Logs</h4>
                    <p className="font-sans text-xs text-slate-400">Auditable, immutable case records for this guild shard.</p>
                  </div>
                  <span className="text-xs bg-[#090D1A] border border-white/10 px-3 py-1.5 rounded-xl text-purple-300 font-mono font-semibold">
                    Shards Connected: 24
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="border-b border-white/10 text-slate-400 font-mono">
                        <th className="py-3 px-2">CASE ID</th>
                        <th className="py-3 px-2">MEMBER</th>
                        <th className="py-3 px-2">ENFORCEMENT</th>
                        <th className="py-3 px-2">REASON</th>
                        <th className="py-3 px-2">TIME</th>
                        <th className="py-3 px-2 text-right">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {cases.map((c) => (
                        <tr key={c.id} className="hover:bg-white/5 transition-colors group">
                          <td className="py-3 px-2 font-mono font-bold text-purple-400">#{c.id}</td>
                          <td className="py-3 px-2 font-sans font-bold text-white">{c.user}</td>
                          <td className="py-3 px-2 font-mono">
                            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              c.action === "BAN" ? "bg-rose-500/20 text-rose-300 border border-rose-500/40" :
                              c.action === "MUTE" ? "bg-purple-500/20 text-purple-300 border border-purple-500/40" :
                              c.action === "WARN" ? "bg-amber-500/20 text-amber-300 border border-amber-500/40" :
                              "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            }`}>
                              {c.action}
                            </span>
                          </td>
                          <td className="py-3 px-2 text-slate-300 max-w-xs truncate">{c.reason}</td>
                          <td className="py-3 px-2 text-slate-400 font-mono text-[11px]">{c.timestamp}</td>
                          <td className="py-3 px-2 text-right">
                            <button
                              onClick={() => deleteCase(c.id)}
                              className="text-slate-400 hover:text-rose-400 transition-colors p-1.5 rounded-lg hover:bg-rose-500/10 cursor-pointer"
                              title="Delete case record"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* AUTOMOD */}
            {activeTab === "automod" && (
              <div className="space-y-6">
                <div>
                  <h4 className="font-heading font-extrabold text-xl text-white">Automod Engine Switches</h4>
                  <p className="font-sans text-xs text-slate-400">Enable or tune active AI shield filters in real time.</p>
                </div>

                <div className="space-y-3.5">
                  <div className="glass-panel p-4 rounded-2xl border border-white/10 flex items-center justify-between">
                    <div>
                      <span className="font-heading font-bold text-sm text-white block">Raid Protection Lock</span>
                      <span className="font-sans text-xs text-slate-400">Engages anti-bot queue if member join velocity exceeds threshold.</span>
                    </div>
                    <button onClick={() => toggleConfig("raidShield")} className="cursor-pointer">
                      {automodConfig.raidShield ? (
                        <ToggleRight className="w-9 h-9 text-purple-400 drop-shadow-[0_0_10px_rgba(168,85,247,0.6)]" />
                      ) : (
                        <ToggleLeft className="w-9 h-9 text-slate-600" />
                      )}
                    </button>
                  </div>

                  <div className="glass-panel p-4 rounded-2xl border border-white/10 flex items-center justify-between">
                    <div>
                      <span className="font-heading font-bold text-sm text-white block">Unsolicited Invite Shield</span>
                      <span className="font-sans text-xs text-slate-400">Deletes unauthorized server invite links instantly.</span>
                    </div>
                    <button onClick={() => toggleConfig("spamFilter")} className="cursor-pointer">
                      {automodConfig.spamFilter ? (
                        <ToggleRight className="w-9 h-9 text-purple-400 drop-shadow-[0_0_10px_rgba(168,85,247,0.6)]" />
                      ) : (
                        <ToggleLeft className="w-9 h-9 text-slate-600" />
                      )}
                    </button>
                  </div>

                  <div className="glass-panel p-4 rounded-2xl border border-white/10 flex items-center justify-between">
                    <div>
                      <span className="font-heading font-bold text-sm text-white block">Anti-Phishing Heuristic Engine</span>
                      <span className="font-sans text-xs text-slate-400">Destroys fraudulent domains imitating Nitro or wallet sites.</span>
                    </div>
                    <button onClick={() => toggleConfig("scamDetector")} className="cursor-pointer">
                      {automodConfig.scamDetector ? (
                        <ToggleRight className="w-9 h-9 text-purple-400 drop-shadow-[0_0_10px_rgba(168,85,247,0.6)]" />
                      ) : (
                        <ToggleLeft className="w-9 h-9 text-slate-600" />
                      )}
                    </button>
                  </div>

                  <div className="glass-panel p-4 rounded-2xl border border-white/10 flex items-center justify-between">
                    <div>
                      <span className="font-heading font-bold text-sm text-white block">NLP Sentiment Harassment Filter</span>
                      <span className="font-sans text-xs text-slate-400">Classifies hostility and slurs with context awareness.</span>
                    </div>
                    <button onClick={() => toggleConfig("toxicityFilter")} className="cursor-pointer">
                      {automodConfig.toxicityFilter ? (
                        <ToggleRight className="w-9 h-9 text-purple-400 drop-shadow-[0_0_10px_rgba(168,85,247,0.6)]" />
                      ) : (
                        <ToggleLeft className="w-9 h-9 text-slate-600" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ANALYTICS */}
            {activeTab === "analytics" && (
              <div className="space-y-6">
                <div>
                  <h4 className="font-heading font-extrabold text-xl text-white">Security Analytics</h4>
                  <p className="font-sans text-xs text-slate-400">Real-time threat graphs and prevention metric trends.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="glass-panel p-5 rounded-2xl border border-white/10">
                    <span className="text-[10px] font-mono text-purple-300 uppercase font-bold block mb-3">Threat Interceptions (Weekly)</span>
                    <div className="h-32 flex items-end space-x-3 pt-4">
                      <div className="flex-1 bg-purple-500/20 hover:bg-purple-500/40 transition-colors h-16 rounded-t-lg relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[10px] px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">14</span>
                      </div>
                      <div className="flex-1 bg-purple-500/30 hover:bg-purple-500/50 transition-colors h-24 rounded-t-lg relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[10px] px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">22</span>
                      </div>
                      <div className="flex-1 bg-purple-500/20 hover:bg-purple-500/40 transition-colors h-12 rounded-t-lg relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[10px] px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">9</span>
                      </div>
                      <div className="flex-1 bg-purple-500/60 hover:bg-purple-500/80 transition-colors h-28 rounded-t-lg relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[10px] px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">34</span>
                      </div>
                      <div className="flex-1 bg-purple-500/40 hover:bg-purple-500/60 transition-colors h-18 rounded-t-lg relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[10px] px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">16</span>
                      </div>
                      <div className="flex-1 bg-cyan-400 hover:bg-cyan-300 transition-colors h-32 rounded-t-lg relative group shadow-[0_0_15px_rgba(34,211,238,0.5)]">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-cyan-950 border border-cyan-400 text-[10px] px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity font-bold">45</span>
                      </div>
                    </div>
                    <div className="flex justify-between text-[11px] text-slate-400 font-mono mt-3">
                      <span>Mon</span>
                      <span>Tue</span>
                      <span>Wed</span>
                      <span>Thu</span>
                      <span>Fri</span>
                      <span className="text-cyan-300 font-bold">Today</span>
                    </div>
                  </div>

                  <div className="glass-panel p-5 rounded-2xl border border-white/10 space-y-4">
                    <span className="text-[10px] font-mono text-cyan-300 uppercase font-bold block">Threat Distribution</span>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-xs text-slate-300 mb-1 font-semibold">
                          <span>Crypto & Phishing Scams</span>
                          <span className="text-purple-400 font-mono">42%</span>
                        </div>
                        <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                          <div className="bg-purple-500 h-full rounded-full" style={{ width: "42%" }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs text-slate-300 mb-1 font-semibold">
                          <span>Invite & Promo Spam</span>
                          <span className="text-cyan-400 font-mono">34%</span>
                        </div>
                        <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                          <div className="bg-cyan-400 h-full rounded-full" style={{ width: "34%" }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-xs text-slate-300 mb-1 font-semibold">
                          <span>Toxicity & Slur Violations</span>
                          <span className="text-amber-400 font-mono">24%</span>
                        </div>
                        <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                          <div className="bg-amber-400 h-full rounded-full" style={{ width: "24%" }} />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* APPEALS */}
            {activeTab === "appeals" && (
              <div className="space-y-4">
                <div>
                  <h4 className="font-heading font-extrabold text-xl text-white">Pending Appeals Ticket Queue</h4>
                  <p className="font-sans text-xs text-slate-400">Review restricted user responses under sandbox conditions.</p>
                </div>

                <div className="space-y-3">
                  {appeals.map((app) => (
                    <div key={app.id} className="glass-panel p-4 rounded-2xl border border-white/10 flex flex-col md:flex-row justify-between md:items-center gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-heading font-bold text-sm text-white">{app.user}</span>
                          <span className="text-[10px] font-mono bg-purple-500/20 text-purple-200 px-2 py-0.5 rounded-full border border-purple-500/30 font-semibold">
                            {app.action}
                          </span>
                        </div>
                        <p className="font-sans text-xs text-slate-300 italic">"{app.reason}"</p>
                      </div>

                      <div className="flex items-center space-x-2 justify-end">
                        {app.status === "pending" ? (
                          <>
                            <button
                              onClick={() => handleAppeal(app.id, "approved")}
                              className="bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 px-3 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-1 cursor-pointer transition-all"
                            >
                              <Check className="w-4 h-4" />
                              <span>Approve</span>
                            </button>
                            <button
                              onClick={() => handleAppeal(app.id, "rejected")}
                              className="bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 px-3 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-1 cursor-pointer transition-all"
                            >
                              <X className="w-4 h-4" />
                              <span>Reject</span>
                            </button>
                          </>
                        ) : (
                          <span className={`text-xs font-mono font-bold uppercase px-3 py-1 rounded-full ${
                            app.status === "approved" ? "text-emerald-300 bg-emerald-500/20 border border-emerald-500/40" : "text-rose-300 bg-rose-500/20 border border-rose-500/40"
                          }`}>
                            Appeal {app.status}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}

                  {appeals.length === 0 && (
                    <p className="text-center py-8 font-sans text-xs text-slate-500">No pending appeal tickets in queue.</p>
                  )}
                </div>
              </div>
            )}

          </div>

        </div>

      </div>
    </section>
  );
}

