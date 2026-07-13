import React, { useState, useEffect } from "react";
import { Activity, ShieldCheck, Zap, Server, BarChart3 } from "lucide-react";

export default function Stats() {
  const [messagesCount, setMessagesCount] = useState(142481209);
  const [threatsCount, setThreatsCount] = useState(1482410);

  useEffect(() => {
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
    <section id="stats" className="relative py-24 bg-[#05070E] overflow-hidden border-t border-white/10">
      
      {/* Background Lighting */}
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[350px] h-[350px] bg-cyan-500/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-left">
        
        <div className="glow-card rounded-3xl p-8 sm:p-10 relative overflow-hidden border border-white/10 backdrop-blur-2xl">
          <div className="absolute top-0 left-0 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

          {/* Grid Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 items-center divide-y lg:divide-y-0 lg:divide-x divide-white/10">
            
            {/* Stat 1 */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-purple-300 font-mono text-[10px] font-bold uppercase tracking-wider">
                <Activity className="w-4 h-4 text-purple-400 animate-pulse" />
                <span>MESSAGES REVIEWED LIVE</span>
              </div>
              <p className="font-heading font-extrabold text-2xl sm:text-3xl text-white tracking-tight font-mono">
                {formatNumber(messagesCount)}
              </p>
              <p className="font-sans text-xs text-slate-400 leading-relaxed">
                Scanned across all active sharded channels.
              </p>
            </div>

            {/* Stat 2 */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-rose-300 font-mono text-[10px] font-bold uppercase tracking-wider">
                <ShieldCheck className="w-4 h-4 text-rose-400" />
                <span>THREATS MITIGATED LIVE</span>
              </div>
              <p className="font-heading font-extrabold text-2xl sm:text-3xl text-rose-400 tracking-tight font-mono">
                {formatNumber(threatsCount)}
              </p>
              <p className="font-sans text-xs text-slate-400 leading-relaxed">
                Phishing domains, raid bots, and spam halted.
              </p>
            </div>

            {/* Stat 3 */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-cyan-300 font-mono text-[10px] font-bold uppercase tracking-wider">
                <Server className="w-4 h-4 text-cyan-400" />
                <span>ACTIVE GUILD SHARDS</span>
              </div>
              <p className="font-heading font-extrabold text-2xl sm:text-3xl text-white tracking-tight">
                142,429
              </p>
              <p className="font-sans text-xs text-slate-400 leading-relaxed">
                Verified server communities secured.
              </p>
            </div>

            {/* Stat 4 */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-amber-300 font-mono text-[10px] font-bold uppercase tracking-wider">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>RESPONSE LATENCY</span>
              </div>
              <p className="font-heading font-extrabold text-2xl sm:text-3xl text-emerald-400 tracking-tight">
                12ms
              </p>
              <p className="font-sans text-xs text-slate-400 leading-relaxed">
                Uncompromising real-time enforcement.
              </p>
            </div>

            {/* Stat 5 */}
            <div className="space-y-2 pt-6 lg:pt-0 lg:px-4">
              <div className="flex items-center space-x-1.5 text-indigo-300 font-mono text-[10px] font-bold uppercase tracking-wider">
                <BarChart3 className="w-4 h-4 text-indigo-400" />
                <span>ACCURACY RATING</span>
              </div>
              <p className="font-heading font-extrabold text-2xl sm:text-3xl text-white tracking-tight">
                99.8%
              </p>
              <p className="font-sans text-xs text-slate-400 leading-relaxed">
                Heuristics fine-tuned to avoid false positives.
              </p>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
}

