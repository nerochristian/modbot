import React, { useState } from "react";
import { LayoutDashboard, ShieldAlert, Settings, BarChart3, HelpCircle, Activity, ChevronRight, Check, X, ShieldCheck, ToggleLeft, ToggleRight, Trash2, Calendar } from "lucide-react";
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

  // Automod toggles state
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
    <section id="dashboard" className="relative py-24 bg-[#05060B] overflow-hidden border-t border-slate-800/80">
      {/* Abstract mesh grids */}
      <div className="absolute top-1/4 right-1/4 -translate-y-1/2 w-[350px] h-[350px] bg-purple-500/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 translate-y-1/2 w-[350px] h-[350px] bg-cyan-500/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Section Heading */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-cyan-950/40 border border-cyan-500/20 text-cyan-400 py-1 px-3 rounded-full text-xs font-mono mb-4">
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>INTERACTIVE DASHBOARD</span>
          </div>
          <h2 className="font-display font-bold text-3xl sm:text-4xl text-white tracking-tight mb-4">
            Manage server security from one central, cloud cockpit.
          </h2>
          <p className="font-sans text-slate-400 text-base sm:text-lg">
            No complicated Discord text prompts required. Set thresholds, analyze real-time infraction metrics, review appeals, and view full case history through our ultra-responsive web dashboard interface.
          </p>
        </div>

        {/* Dynamic Dashboard Frame Mock */}
        <div className="bg-[#0E111A] border border-slate-800 rounded-3xl overflow-hidden shadow-2xl shadow-black/80 flex flex-col md:flex-row h-[550px] text-left">
          
          {/* Dashboard Left Sidebar */}
          <div className="w-full md:w-64 bg-[#05060B] border-r border-slate-800/60 flex flex-col p-4 space-y-1">
            <div className="pb-4 mb-4 border-b border-slate-800/50 flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-purple-600/10 flex items-center justify-center border border-purple-500/20">
                <ShieldCheck className="w-4 h-4 text-purple-400" />
              </div>
              <div>
                <span className="font-display font-bold text-sm text-white block">Docket Cloud</span>
                <span className="text-[10px] text-slate-500 font-mono">v4.0.0 Stable</span>
              </div>
            </div>

            {/* Sidebar Navigation */}
            <button
              onClick={() => setActiveTab("overview")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3 rounded-lg text-xs font-sans font-medium transition-all cursor-pointer border ${
                activeTab === "overview"
                  ? "bg-purple-950/40 text-purple-300 border-purple-500/20"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/30 border-transparent"
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Server Overview</span>
            </button>

            <button
              onClick={() => setActiveTab("cases")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3 rounded-lg text-xs font-sans font-medium transition-all cursor-pointer border ${
                activeTab === "cases"
                  ? "bg-purple-950/40 text-purple-300 border-purple-500/20"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/30 border-transparent"
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span className="flex-1 text-left">Moderation Cases</span>
              <span className="bg-slate-800 text-[10px] text-white px-1.5 py-0.2 rounded-full font-mono">
                {cases.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("automod")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3 rounded-lg text-xs font-sans font-medium transition-all cursor-pointer border ${
                activeTab === "automod"
                  ? "bg-purple-950/40 text-purple-300 border-purple-500/20"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/30 border-transparent"
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Automod Config</span>
            </button>

            <button
              onClick={() => setActiveTab("analytics")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3 rounded-lg text-xs font-sans font-medium transition-all cursor-pointer border ${
                activeTab === "analytics"
                  ? "bg-purple-950/40 text-purple-300 border-purple-500/20"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/30 border-transparent"
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Analytics</span>
            </button>

            <button
              onClick={() => setActiveTab("appeals")}
              className={`w-full flex items-center space-x-3 py-2.5 px-3 rounded-lg text-xs font-sans font-medium transition-all cursor-pointer border ${
                activeTab === "appeals"
                  ? "bg-purple-950/40 text-purple-300 border-purple-500/20"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/30 border-transparent"
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span className="flex-1 text-left">Member Appeals</span>
              {appeals.filter(a => a.status === "pending").length > 0 && (
                <span className="bg-red-500 text-[10px] text-white px-1.5 py-0.2 rounded-full font-mono font-bold animate-pulse">
                  {appeals.filter(a => a.status === "pending").length}
                </span>
              )}
            </button>

            <div className="mt-auto pt-4 border-t border-slate-800/50 flex items-center space-x-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-mono text-slate-500">Node-West API Online</span>
            </div>
          </div>

          {/* Dashboard Content Pane */}
          <div className="flex-1 bg-[#0E111A] overflow-y-auto p-6 text-slate-300">
            
            {/* OVERVIEW TAB */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                <div>
                  <h4 className="font-display font-bold text-lg text-white">Server Cockpit</h4>
                  <p className="font-sans text-xs text-slate-500">Real-time indicators and general community health metrics.</p>
                </div>

                {/* Dashboard Stats Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">Total Members</span>
                    <p className="font-display font-bold text-xl text-white mt-1">14,285</p>
                    <span className="text-[9px] text-emerald-400 font-sans block mt-1">+142 this week</span>
                  </div>
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">Threat Level</span>
                    <p className="font-display font-bold text-xl text-emerald-400 mt-1">Secure</p>
                    <span className="text-[9px] text-slate-500 font-sans block mt-1">0 active raids detected</span>
                  </div>
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">Total Cases</span>
                    <p className="font-display font-bold text-xl text-white mt-1">412</p>
                    <span className="text-[9px] text-purple-400 font-sans block mt-1">98.4% auto-resolved</span>
                  </div>
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">Raid Shield</span>
                    <p className="font-display font-bold text-xl text-cyan-400 mt-1">ACTIVE</p>
                    <span className="text-[9px] text-slate-500 font-sans block mt-1">Confidence Filter: 92%</span>
                  </div>
                </div>

                {/* Recent Event activity strip */}
                <div className="bg-[#05060B] border border-slate-800 rounded-xl p-4 space-y-3">
                  <div className="flex justify-between items-center pb-2 border-b border-slate-800/40">
                    <span className="font-mono text-xs text-slate-400 font-bold">LATEST SECURITY DISPATCHES</span>
                    <span className="text-[10px] font-sans text-slate-500">Live feed</span>
                  </div>
                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex justify-between hover:bg-slate-900/50 p-1.5 rounded transition-all">
                      <span className="text-purple-400">• AUTOMOD BLOCK: Malicious link deleted</span>
                      <span className="text-slate-500">2 mins ago</span>
                    </div>
                    <div className="flex justify-between hover:bg-slate-900/50 p-1.5 rounded transition-all">
                      <span className="text-cyan-400">• RAID SHIELD: Triggered Joint Cap Verification</span>
                      <span className="text-slate-500">14 mins ago</span>
                    </div>
                    <div className="flex justify-between hover:bg-slate-900/50 p-1.5 rounded transition-all">
                      <span className="text-amber-400">• MOD CASE #4812: Warning logged against @Scammer</span>
                      <span className="text-slate-500">22 mins ago</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* CASES TAB */}
            {activeTab === "cases" && (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-display font-bold text-lg text-white">Active Moderation Cases</h4>
                    <p className="font-sans text-xs text-slate-500">Auditable infraction logs for this guild shard.</p>
                  </div>
                  <span className="text-xs bg-[#05060B] border border-slate-800 p-2 rounded-lg text-slate-400">
                    Shards Linked: 24
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800/50 text-slate-500 font-mono">
                        <th className="py-2.5">CASE ID</th>
                        <th className="py-2.5">MEMBER</th>
                        <th className="py-2.5">ACTION</th>
                        <th className="py-2.5">VIOLATION REASON</th>
                        <th className="py-2.5">TIME</th>
                        <th className="py-2.5 text-right">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/30">
                      {cases.map((c) => (
                        <tr key={c.id} className="hover:bg-[#05060B]/30 transition-colors group">
                          <td className="py-3 font-mono font-bold text-slate-400">#{c.id}</td>
                          <td className="py-3 font-sans font-semibold text-white">{c.user}</td>
                          <td className="py-3 font-mono">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              c.action === "BAN" ? "bg-red-950/80 text-red-400 border border-red-900/30" :
                              c.action === "MUTE" ? "bg-purple-950/80 text-purple-400 border border-purple-900/30" :
                              c.action === "WARN" ? "bg-amber-950/80 text-amber-400 border border-amber-900/30" :
                              "bg-emerald-950/80 text-emerald-400 border border-emerald-900/30"
                            }`}>
                              {c.action}
                            </span>
                          </td>
                          <td className="py-3 text-slate-400 max-w-xs truncate">{c.reason}</td>
                          <td className="py-3 text-slate-500">{c.timestamp}</td>
                          <td className="py-3 text-right">
                            <button
                              onClick={() => deleteCase(c.id)}
                              className="text-slate-500 hover:text-red-400 transition-colors p-1"
                              title="Delete case log"
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

            {/* AUTOMOD CONFIG TAB */}
            {activeTab === "automod" && (
              <div className="space-y-6">
                <div>
                  <h4 className="font-display font-bold text-lg text-white">Automod Configuration</h4>
                  <p className="font-sans text-xs text-slate-500">Fine-tune automated triggers to fit your community's rules.</p>
                </div>

                <div className="space-y-4">
                  {/* Row 1 */}
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="font-display font-bold text-sm text-white block">Raid Protection Shield</span>
                      <span className="font-sans text-xs text-slate-500">Automatically locks down channels if 10+ accounts join in under 15 seconds.</span>
                    </div>
                    <button onClick={() => toggleConfig("raidShield")} className="cursor-pointer">
                      {automodConfig.raidShield ? (
                        <ToggleRight className="w-10 h-10 text-purple-400" />
                      ) : (
                        <ToggleLeft className="w-10 h-10 text-slate-800" />
                      )}
                    </button>
                  </div>

                  {/* Row 2 */}
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="font-display font-bold text-sm text-white block">Invite Spam Link Blocker</span>
                      <span className="font-sans text-xs text-slate-500">Deletes any unsolicited discord.gg links from unverified members.</span>
                    </div>
                    <button onClick={() => toggleConfig("spamFilter")} className="cursor-pointer">
                      {automodConfig.spamFilter ? (
                        <ToggleRight className="w-10 h-10 text-purple-400" />
                      ) : (
                        <ToggleLeft className="w-10 h-10 text-slate-800" />
                      )}
                    </button>
                  </div>

                  {/* Row 3 */}
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="font-display font-bold text-sm text-white block">Anti-Scam Phishing Detector</span>
                      <span className="font-sans text-xs text-slate-500">Uses Docket AI heuristics to analyze and block domain redirects mimicking major platforms.</span>
                    </div>
                    <button onClick={() => toggleConfig("scamDetector")} className="cursor-pointer">
                      {automodConfig.scamDetector ? (
                        <ToggleRight className="w-10 h-10 text-purple-400" />
                      ) : (
                        <ToggleLeft className="w-10 h-10 text-slate-800" />
                      )}
                    </button>
                  </div>

                  {/* Row 4 */}
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="font-display font-bold text-sm text-white block">AI Sentiment Toxicity filter</span>
                      <span className="font-sans text-xs text-slate-500">Filters harassment and aggressive speech dynamically based on threshold slider score.</span>
                    </div>
                    <button onClick={() => toggleConfig("toxicityFilter")} className="cursor-pointer">
                      {automodConfig.toxicityFilter ? (
                        <ToggleRight className="w-10 h-10 text-purple-400" />
                      ) : (
                        <ToggleLeft className="w-10 h-10 text-slate-800" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ANALYTICS TAB */}
            {activeTab === "analytics" && (
              <div className="space-y-6">
                <div>
                  <h4 className="font-display font-bold text-lg text-white">Security Analytics</h4>
                  <p className="font-sans text-xs text-slate-500">Visual logs tracking threat density and moderation throughput.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Chart 1: Messages processed */}
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl">
                    <span className="text-[10px] font-mono text-slate-500 uppercase block mb-3">Threat volume prevented (Weekly)</span>
                    <div className="h-32 flex items-end space-x-2.5 pt-4">
                      <div className="flex-1 bg-purple-500/10 hover:bg-purple-500/30 transition-colors h-16 rounded-t-md relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">14</span>
                      </div>
                      <div className="flex-1 bg-purple-500/10 hover:bg-purple-500/30 transition-colors h-24 rounded-t-md relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">22</span>
                      </div>
                      <div className="flex-1 bg-purple-500/10 hover:bg-purple-500/30 transition-colors h-12 rounded-t-md relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">9</span>
                      </div>
                      <div className="flex-1 bg-purple-500/40 hover:bg-purple-500/60 transition-colors h-28 rounded-t-md relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">34</span>
                      </div>
                      <div className="flex-1 bg-purple-500/20 hover:bg-purple-500/30 transition-colors h-18 rounded-t-md relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">16</span>
                      </div>
                      <div className="flex-1 bg-purple-500/80 hover:bg-purple-500/90 transition-colors h-32 rounded-t-md relative group">
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-950 border border-purple-500 text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">45</span>
                      </div>
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-2">
                      <span>Mon</span>
                      <span>Tue</span>
                      <span>Wed</span>
                      <span>Thu</span>
                      <span>Fri</span>
                      <span>Today</span>
                    </div>
                  </div>

                  {/* Chart 2: Spam types */}
                  <div className="bg-[#05060B] border border-slate-800 p-4 rounded-xl space-y-3">
                    <span className="text-[10px] font-mono text-slate-500 uppercase block">Trigger Type Distribution</span>
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                          <span>Crypto scams</span>
                          <span>42%</span>
                        </div>
                        <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                          <div className="bg-purple-500 h-full" style={{ width: "42%" }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                          <span>Advertising / Invite links</span>
                          <span>34%</span>
                        </div>
                        <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                          <div className="bg-cyan-500 h-full" style={{ width: "34%" }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                          <span>Harassment / Slurs</span>
                          <span>24%</span>
                        </div>
                        <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                          <div className="bg-amber-500 h-full" style={{ width: "24%" }} />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* APPEALS TAB */}
            {activeTab === "appeals" && (
              <div className="space-y-4">
                <div>
                  <h4 className="font-display font-bold text-lg text-white">Active Appeals Docket</h4>
                  <p className="font-sans text-xs text-slate-500">Muted or restricted members requesting human team review.</p>
                </div>

                <div className="space-y-3">
                  {appeals.map((app) => (
                    <div key={app.id} className="bg-[#05060B] border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row justify-between md:items-center gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-sans font-bold text-sm text-white">{app.user}</span>
                          <span className="text-[10px] font-mono bg-[#0E111A] text-slate-400 px-2 py-0.5 rounded border border-slate-800">
                            Action: {app.action}
                          </span>
                        </div>
                        <p className="font-sans text-xs text-slate-400 italic">"{app.reason}"</p>
                      </div>

                      <div className="flex items-center space-x-2 justify-end">
                        {app.status === "pending" ? (
                          <>
                            <button
                              onClick={() => handleAppeal(app.id, "approved")}
                              className="bg-emerald-950 hover:bg-emerald-900 text-emerald-400 border border-emerald-800 p-1.5 rounded-lg text-xs font-sans font-semibold flex items-center space-x-1 cursor-pointer"
                            >
                              <Check className="w-4 h-4" />
                              <span>Approve</span>
                            </button>
                            <button
                              onClick={() => handleAppeal(app.id, "rejected")}
                              className="bg-red-950 hover:bg-red-900 text-red-400 border border-red-800 p-1.5 rounded-lg text-xs font-sans font-semibold flex items-center space-x-1 cursor-pointer"
                            >
                              <X className="w-4 h-4" />
                              <span>Reject</span>
                            </button>
                          </>
                        ) : (
                          <span className={`text-xs font-sans font-bold uppercase ${
                            app.status === "approved" ? "text-emerald-400 bg-emerald-950/40 p-1.5 rounded" : "text-red-400 bg-red-950/40 p-1.5 rounded"
                          }`}>
                            Appeal {app.status}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}

                  {appeals.length === 0 && (
                    <p className="text-center py-8 font-sans text-xs text-slate-500">No pending appeal tickets.</p>
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
