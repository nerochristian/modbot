import React, { useState, useEffect } from "react";
import { Terminal, Shield, Eye, HelpCircle, FileText, CheckSquare, Zap, MessageSquare, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { CommandExample } from "../types";

const COMMAND_EXAMPLES: CommandExample[] = [
  {
    id: "mute",
    name: "Natural Language Mute",
    command: "@Docket mute @Vandalizer for 10m for what they did",
    category: "moderation",
    description: "Uses natural language processing (NLP) to parse moderate triggers, duration units, target users, and intent reasons smoothly.",
    steps: [
      {
        sender: "user",
        username: "ModeratorJack",
        roleColor: "text-blue-400",
        timestamp: "Today at 11:32 AM",
        content: "@Docket mute @Vandalizer for 10m for what they did",
      },
      {
        sender: "docket",
        username: "Docket",
        isBot: true,
        timestamp: "Today at 11:32 AM",
        content: "⚠️ **Mute Enforcement Processed**",
        embed: {
          title: "Infraction Case File #48291",
          description: "Target user has been successfully restricted from sending messages across all text and voice hubs.",
          color: "border-l-4 border-red-500",
          fields: [
            { name: "Target Member", value: "@Vandalizer (ID: 981249)", inline: true },
            { name: "Enforcing Mod", value: "@ModeratorJack", inline: true },
            { name: "Enforced Action", value: "Temp Mute (10 Minutes)", inline: true },
            { name: "NLP Decoded Reason", value: "\"what they did\" → Resolved as: Repeated spamming in #announcements", inline: false },
          ],
          footer: "Docket Security System • Today at 11:32 AM",
        },
      },
    ],
  },
  {
    id: "moderate",
    name: "/moderate Interactive",
    command: "/moderate user:@Spammer scope:global reason:advertising",
    category: "moderation",
    description: "Quickly access administrative command panels with granular scopes and structured arguments.",
    steps: [
      {
        sender: "user",
        username: "AdminChloe",
        roleColor: "text-red-400",
        timestamp: "Today at 11:32 AM",
        content: "/moderate user:@Spammer scope:global reason:advertising",
      },
      {
        sender: "docket",
        username: "Docket",
        isBot: true,
        timestamp: "Today at 11:32 AM",
        content: "🛡️ **Moderate Dispatch Completed**",
        embed: {
          title: "Global Administrative Action Triggered",
          description: "Target accounts have been logged, flagged across linked shards, and removed.",
          color: "border-l-4 border-amber-500",
          fields: [
            { name: "User Status", value: "@Spammer (Banned globally)", inline: true },
            { name: "Reason Code", value: "TOS Breach: Direct Message Advertising Spam", inline: true },
            { name: "Audit Trail", value: "Logged in #mod-logs-global", inline: false },
          ],
          footer: "Docket Sharded Moderation Unit",
        },
      },
    ],
  },
  {
    id: "case",
    name: "/case review Logs",
    command: "/case review id:48291",
    category: "utility",
    description: "Query full history, context records, chat evidence backups, and AI-confidence analyses for any moderator case.",
    steps: [
      {
        sender: "user",
        username: "SupportStaff_Alex",
        roleColor: "text-emerald-400",
        timestamp: "Today at 11:32 AM",
        content: "/case review id:48291",
      },
      {
        sender: "docket",
        username: "Docket",
        isBot: true,
        timestamp: "Today at 11:32 AM",
        content: "📂 **Case Audit Retrieved successfully**",
        embed: {
          title: "Case Analysis #48291 - @Vandalizer",
          description: "Full contextual audit detailing the target infraction metrics.",
          color: "border-l-4 border-purple-500",
          fields: [
            { name: "Infraction Date", value: "2026-07-12 11:30:15 UTC", inline: true },
            { name: "Context Score", value: "Toxicity Level: 84% (High Risk)", inline: true },
            { name: "Logged Evidence", value: "\"I will keep pasting this link and you mods cannot ban me, stupid bots!\"", inline: false },
            { name: "AI Categorization", value: "Intentional disruption and ban evasion attempt", inline: false },
          ],
          footer: "Case Storage Database Node-A2",
        },
      },
    ],
  },
  {
    id: "automod",
    name: "/automod setup Wizards",
    command: "/automod setup profile:strict",
    category: "automation",
    description: "Initialize industry-standard protection templates in seconds. Tailor modules to suit your community's active density.",
    steps: [
      {
        sender: "user",
        username: "ServerOwner_Matt",
        roleColor: "text-purple-400",
        timestamp: "Today at 11:32 AM",
        content: "/automod setup profile:strict",
      },
      {
        sender: "docket",
        username: "Docket",
        isBot: true,
        timestamp: "Today at 11:32 AM",
        content: "⚙️ **Strict Security Profile Deployed**",
        embed: {
          title: "Automod Modules Successfully Updated",
          description: "All default thresholds configured to HIGH protection mode. Anti-Raid triggers activated.",
          color: "border-l-4 border-cyan-500",
          fields: [
            { name: "Link Safe Filter", value: "ON (Whitelisted domains only)", inline: true },
            { name: "Mass Mention Shield", value: "ON (Max 4 pings / 5s)", inline: true },
            { name: "Scam Detection Engine", value: "ON (AI-driven heuristic models)", inline: true },
            { name: "Joint Verification Gate", value: "ON (Captcha mandatory for accounts under 3 days old)", inline: false },
          ],
          footer: "Automod Control Panel",
        },
      },
    ],
  },
  {
    id: "appeal",
    name: "/appeal Secure Gateways",
    command: "/appeal ticket_id:app-91230",
    category: "appeals",
    description: "Permit muted or banned users to request staff review under structured, sandbox conditions.",
    steps: [
      {
        sender: "user",
        username: "AppealerGuy",
        roleColor: "text-gray-400",
        timestamp: "Today at 11:32 AM",
        content: "/appeal ticket_id:app-91230",
      },
      {
        sender: "docket",
        username: "Docket",
        isBot: true,
        timestamp: "Today at 11:32 AM",
        content: "✉️ **Appeal Submission Initiated**",
        embed: {
          title: "Appeal Portal Ticket #app-91230",
          description: "Submitted for moderation panel review. Please clarify details truthfully below.",
          color: "border-l-4 border-emerald-500",
          fields: [
            { name: "Involved Member", value: "@AppealerGuy (Banned for toxic chat)", inline: true },
            { name: "Appeal Reason", value: "\"I was angry because I lost a competitive game. I apologize, won't happen again.\"", inline: false },
            { name: "Review Queue Placement", value: "Position #2 (Estimated review time: 14 mins)", inline: true },
          ],
          footer: "Docket Appeal Service Center",
        },
      },
    ],
  },
];

export default function CommandDemo() {
  const [selectedCmd, setSelectedCmd] = useState<CommandExample>(COMMAND_EXAMPLES[0]);
  const [typingText, setTypingText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showResponse, setShowResponse] = useState(true);

  useEffect(() => {
    setIsTyping(true);
    setShowResponse(false);
    setTypingText("");

    let currentText = "";
    const targetText = selectedCmd.command;
    let index = 0;

    const interval = setInterval(() => {
      if (index < targetText.length) {
        currentText += targetText[index];
        setTypingText(currentText);
        index++;
      } else {
        clearInterval(interval);
        setIsTyping(false);
        setTimeout(() => {
          setShowResponse(true);
        }, 300);
      }
    }, 25);

    return () => clearInterval(interval);
  }, [selectedCmd]);

  return (
    <section id="commands" className="relative py-28 bg-[#05070E] overflow-hidden border-t border-white/10">
      
      {/* Ambient Orbs */}
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Title Block */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 py-1.5 px-4 rounded-full text-xs font-mono mb-4">
            <Terminal className="w-4 h-4 text-purple-400" />
            <span>COMMAND DEMONSTRATION</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl text-white tracking-tight mb-4">
            Enforce rules in plain language or <span className="bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">slash commands</span>.
          </h2>
          <p className="font-sans text-slate-300 text-base sm:text-lg leading-relaxed">
            Docket fits seamlessly into your staff workflows. Invoke actions with simple conversational mentions or formal discord commands that execute safely.
          </p>
        </div>

        {/* Workspace Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left Menu Selection */}
          <div className="lg:col-span-4 flex flex-col space-y-3">
            <span className="text-[11px] font-mono text-purple-300/80 text-left block pl-2 uppercase tracking-wider font-bold mb-1">
              SELECT COMMAND TEST CASE:
            </span>
            {COMMAND_EXAMPLES.map((cmd) => (
              <button
                key={cmd.id}
                onClick={() => {
                  if (!isTyping) setSelectedCmd(cmd);
                }}
                disabled={isTyping}
                className={`group p-4 text-left rounded-2xl border transition-all cursor-pointer ${
                  selectedCmd.id === cmd.id
                    ? "bg-[#090D1A] border-purple-500/50 text-white shadow-[0_0_25px_rgba(124,58,237,0.25)]"
                    : "bg-[#090D1A]/50 border-white/5 text-slate-400 hover:text-white hover:bg-white/5"
                } ${isTyping ? "opacity-60 cursor-not-allowed" : ""}`}
              >
                <div className="flex items-center space-x-3 mb-1.5">
                  <span className={`p-2 rounded-xl border ${
                    selectedCmd.id === cmd.id ? "bg-purple-600/20 border-purple-500/40 text-purple-300" : "bg-white/5 border-white/10 text-slate-400"
                  }`}>
                    {cmd.category === "moderation" && <Shield className="w-4 h-4" />}
                    {cmd.category === "automation" && <Zap className="w-4 h-4" />}
                    {cmd.category === "appeals" && <HelpCircle className="w-4 h-4" />}
                    {cmd.category === "utility" && <FileText className="w-4 h-4" />}
                  </span>
                  <span className="font-heading font-bold text-sm sm:text-base tracking-wide group-hover:text-purple-200 transition-colors">
                    {cmd.name}
                  </span>
                </div>
                <p className="font-sans text-xs text-slate-400 leading-relaxed pl-10">
                  {cmd.description}
                </p>
              </button>
            ))}
          </div>

          {/* Right Discord Console Display */}
          <div className="lg:col-span-8 bg-[#1E1F22] rounded-2xl overflow-hidden shadow-2xl border border-white/10 text-left">
            
            {/* Header bar */}
            <div className="bg-[#2B2D31] p-3.5 flex items-center justify-between border-b border-black/40">
              <div className="flex items-center space-x-2.5">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center font-heading font-extrabold text-white text-xs shadow-md">
                  D
                </div>
                <span className="font-sans font-bold text-xs text-white">Docket Security Hub</span>
                <span className="text-slate-400 text-xs font-mono bg-black/30 px-2 py-0.5 rounded border border-white/5">#mod-commands</span>
              </div>
              <div className="flex space-x-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]" />
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]" />
              </div>
            </div>

            {/* Chat Panel */}
            <div className="p-6 space-y-6 h-112 overflow-y-auto bg-[#313338]">
              
              <p className="text-[10px] font-mono text-slate-400 text-center uppercase tracking-widest py-1.5 border-b border-white/5">
                — DISPATCHING INTERACTIVE ENFORCEMENT ROUTINE —
              </p>

              {/* User Command */}
              <div className="flex space-x-4 items-start">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-sans text-xs font-black shadow-md">
                  {selectedCmd.steps[0].username.slice(0, 2).toUpperCase()}
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className={`font-sans font-bold text-sm ${selectedCmd.steps[0].roleColor || "text-slate-200"}`}>
                      {selectedCmd.steps[0].username}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">{selectedCmd.steps[0].timestamp}</span>
                  </div>
                  
                  <div className="font-mono text-xs text-purple-200 bg-[#1E1F22] p-3 rounded-xl border border-white/10 inline-block max-w-full shadow-inner">
                    <span className="text-cyan-400 font-bold">$</span> {typingText}
                    {isTyping && <span className="inline-block w-2 h-4 bg-purple-400 ml-1 animate-pulse" />}
                  </div>
                </div>
              </div>

              {/* Bot Response */}
              <AnimatePresence>
                {showResponse && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="flex space-x-4 items-start border-t border-white/5 pt-4"
                  >
                    <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-purple-600 to-cyan-500 flex items-center justify-center text-white font-sans text-xs font-black shadow-lg shadow-purple-500/20">
                      DK
                    </div>
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-sans font-extrabold text-sm text-white">Docket</span>
                        <span className="bg-purple-600 text-[10px] text-white px-2 py-0.5 rounded font-sans uppercase font-bold tracking-wider">
                          BOT
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">{selectedCmd.steps[1].timestamp}</span>
                      </div>
                      
                      <p className="text-slate-200 font-sans text-sm">{selectedCmd.steps[1].content}</p>

                      {/* Embed card */}
                      {selectedCmd.steps[1].embed && (
                        <div className={`bg-[#2B2D31] border-l-4 border-purple-500 rounded-r-2xl max-w-xl shadow-xl overflow-hidden border-y border-r border-white/5`}>
                          <div className="p-4 space-y-3">
                            {selectedCmd.steps[1].embed.title && (
                              <h4 className="font-heading font-bold text-white text-base">
                                {selectedCmd.steps[1].embed.title}
                              </h4>
                            )}
                            {selectedCmd.steps[1].embed.description && (
                              <p className="font-sans text-xs text-slate-300 leading-relaxed">
                                {selectedCmd.steps[1].embed.description}
                              </p>
                            )}
                            
                            {selectedCmd.steps[1].embed.fields && (
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                                {selectedCmd.steps[1].embed.fields.map((f, i) => (
                                  <div
                                    key={i}
                                    className={`${f.inline ? "col-span-1" : "col-span-1 sm:col-span-2"} space-y-1`}
                                  >
                                    <span className="text-[11px] font-mono font-bold text-slate-400 uppercase tracking-wide">
                                      {f.name}
                                    </span>
                                    <p className="text-xs font-sans text-slate-200 bg-[#1E1F22] p-2.5 rounded-lg border border-white/5">
                                      {f.value}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                          
                          {selectedCmd.steps[1].embed.footer && (
                            <div className="bg-[#1E1F22] px-4 py-2.5 text-[11px] text-slate-400 font-mono border-t border-white/5 flex items-center justify-between">
                              <span>{selectedCmd.steps[1].embed.footer}</span>
                              <span className="text-purple-400 font-bold uppercase tracking-wider">VERIFIED LOG</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {isTyping && (
                <div className="flex items-center space-x-2 pl-14 text-xs font-sans text-purple-300">
                  <div className="flex space-x-1">
                    <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                  <span>Docket is parsing request parameters...</span>
                </div>
              )}
            </div>

            {/* Input Footer */}
            <div className="bg-[#2B2D31] p-4 border-t border-black/40 flex items-center">
              <div className="bg-[#383A40] text-slate-400 flex-1 px-4 py-3 rounded-xl text-xs font-sans flex items-center justify-between select-none border border-white/5">
                <span>Send message in #mod-commands...</span>
                <span className="text-[10px] font-mono bg-[#2B2D31] px-2 py-0.5 rounded border border-white/10 text-slate-300 font-bold">
                  PRESS RETURN
                </span>
              </div>
            </div>

          </div>

        </div>

      </div>
    </section>
  );
}

