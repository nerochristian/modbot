import React, { useState, useEffect } from "react";
import { Activity, ShieldCheck, Zap, Server, BarChart3 } from "lucide-react";

export default function Stats() {
  // Live counters state
  const [messagesCount, setMessagesCount] = useState(142481209);
  const [threatsCount, setThreatsCount] = useState(1482410);

  useEffect(() => {
    // Tick the counters upwards to simulate live activity
    const interval = setInterval(() => {
      setMessagesCount((prev) => prev + Math.floor(Math.random() * 8) + 2);
      setThreatsCount((prev) => prev + (Math.random() > 0.7 ? 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  return (
    <section id="stats" className="relative py-20 bg-[#05060B] overflow-hidden border-t border-slate-800/80">
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[250px] h-[250px] bg-cyan-500/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        <div className="bg-[#0E111A] border border-slate-800 rounded-3xl p-6 sm:p-10 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-32 h-32 bg-purple-500/5 rounded-full blur-2xl pointer-events-none" />

          {/* Grid layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 items-center divide-y lg:divide-y-0 lg:divide-x divide-slate-800/60">
            
            {/* Stat 1 (Live Messages) */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                <Activity className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
                <span>MESSAGES REVIEWED LIVE</span>
              </div>
              <p className="font-display font-bold text-2xl sm:text-3xl text-white tracking-tight font-mono">
                {formatNumber(messagesCount)}
              </p>
              <p className="font-sans text-xs text-slate-500 leading-normal">
                Scanned across all active sharded channels.
              </p>
            </div>

            {/* Stat 2 (Live Threats) */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                <ShieldCheck className="w-3.5 h-3.5 text-red-400" />
                <span>THREATS MITIGATED LIVE</span>
              </div>
              <p className="font-display font-bold text-2xl sm:text-3xl text-red-400 tracking-tight font-mono">
                {formatNumber(threatsCount)}
              </p>
              <p className="font-sans text-xs text-slate-500 leading-normal">
                Phishing domains, raid bots, and spam halted.
              </p>
            </div>

            {/* Stat 3 (Active Servers) */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                <Server className="w-3.5 h-3.5 text-cyan-400" />
                <span>ACTIVE SHARD GUILDS</span>
              </div>
              <p className="font-display font-bold text-2xl sm:text-3xl text-white tracking-tight">
                142,429
              </p>
              <p className="font-sans text-xs text-slate-500 leading-normal">
                Verified server communities secured.
              </p>
            </div>

            {/* Stat 4 (Response Latency) */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                <Zap className="w-3.5 h-3.5 text-yellow-400" />
                <span>RESPONSE LATENCY</span>
              </div>
              <p className="font-display font-bold text-2xl sm:text-3xl text-emerald-400 tracking-tight">
                12ms
              </p>
              <p className="font-sans text-xs text-slate-500 leading-normal">
                Uncompromising real-time enforcement.
              </p>
            </div>

            {/* Stat 5 (Accuracy) */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
                <span>MOD CONFIDENCE ACCURACY</span>
              </div>
              <p className="font-display font-bold text-2xl sm:text-3xl text-white tracking-tight">
                99.8%
              </p>
              <p className="font-sans text-xs text-slate-500 leading-normal">
                Heuristics fine-tuned to avoid false positives.
              </p>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
}
