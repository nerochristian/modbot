import { Bot, Shield, Zap, ScrollText, ArrowRight, ChevronRight, Star, Users, BarChart3 } from 'lucide-react';
import { AUTH_BASE } from '@/lib/api';

const CLIENT_ID = import.meta.env.VITE_DISCORD_CLIENT_ID || '1445812489840361656';
// OAuth callback goes to the API server (WispByte), not the frontend (Render)
const CALLBACK_URL = AUTH_BASE ? `${AUTH_BASE}/auth/callback` : `${window.location.origin}/auth/callback`;
const REDIRECT_URI = encodeURIComponent(CALLBACK_URL);
const OAUTH_URL = `https://discord.com/api/oauth2/authorize?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=identify+guilds`;

const features = [
    {
        icon: Shield,
        title: 'Advanced Moderation',
        description: 'Ban, kick, warn, timeout with full case tracking and audit trails.',
        color: 'from-indigo-500 to-indigo-600',
        iconBg: 'bg-indigo-50 text-indigo-600',
    },
    {
        icon: Zap,
        title: 'Auto Moderation',
        description: 'AI-powered spam, link, and invite filtering with configurable thresholds.',
        color: 'from-amber-500 to-orange-500',
        iconBg: 'bg-amber-50 text-amber-600',
    },
    {
        icon: ScrollText,
        title: 'Granular Logging',
        description: 'Route 20+ event types to specific channels with per-event control.',
        color: 'from-emerald-500 to-teal-500',
        iconBg: 'bg-emerald-50 text-emerald-600',
    },
    {
        icon: Users,
        title: 'Role-Based Access',
        description: 'Map Discord roles to dashboard permissions with privilege escalation prevention.',
        color: 'from-purple-500 to-pink-500',
        iconBg: 'bg-purple-50 text-purple-600',
    },
];

const stats = [
    { label: 'Servers', value: '500+' },
    { label: 'Commands', value: '50+' },
    { label: 'Events Logged', value: '1M+' },
];

export function Landing() {
    return (
        <div className="min-h-screen bg-app-bg overflow-hidden">
            {/* Navigation */}
            <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-50 rounded-xl">
                        <Bot className="w-6 h-6 text-indigo-600" />
                    </div>
                    <span className="font-display font-bold text-xl text-slate-800 tracking-tight">modbot</span>
                </div>
                <div className="flex items-center gap-3">
                    <a
                        href={OAUTH_URL}
                        className="px-5 py-2.5 bg-[#5865F2] hover:bg-[#4752C4] text-white text-sm font-semibold rounded-xl transition-all duration-200 shadow-[0_4px_14px_rgba(88,101,242,0.4)] hover:shadow-[0_6px_20px_rgba(88,101,242,0.5)] flex items-center gap-2"
                    >
                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z" />
                        </svg>
                        Connect Discord
                    </a>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="max-w-6xl mx-auto px-6 pt-16 pb-24">
                <div className="text-center max-w-3xl mx-auto">
                    {/* Pill badge */}
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo-50 border border-indigo-100 rounded-full mb-8">
                        <Star className="w-3.5 h-3.5 text-indigo-600" />
                        <span className="text-xs font-semibold text-indigo-700">Production-grade Discord moderation</span>
                    </div>

                    <h1 className="text-5xl md:text-6xl font-display font-bold text-slate-900 tracking-tight leading-[1.1] mb-6">
                        Complete control over your
                        <span className="block bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 bg-clip-text text-transparent">
                            Discord server
                        </span>
                    </h1>

                    <p className="text-lg text-slate-500 max-w-xl mx-auto mb-10 leading-relaxed">
                        Modbot gives you Dyno-level control depth with granular configuration,
                        layered overrides, and a beautiful dashboard to manage everything.
                    </p>

                    <div className="flex items-center justify-center gap-4">
                        <a
                            href={OAUTH_URL}
                            className="group px-8 py-3.5 bg-[#5865F2] hover:bg-[#4752C4] text-white font-semibold rounded-2xl transition-all duration-200 shadow-[0_8px_30px_rgba(88,101,242,0.35)] hover:shadow-[0_12px_40px_rgba(88,101,242,0.45)] hover:-translate-y-0.5 flex items-center gap-3 text-base"
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z" />
                            </svg>
                            Get Started with Discord
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </a>
                        <a
                            href="#features"
                            className="px-6 py-3.5 text-slate-600 hover:text-slate-900 font-semibold border border-cream-300 hover:border-slate-300 rounded-2xl transition-all duration-200 hover:bg-white hover:shadow-sm"
                        >
                            Learn More
                        </a>
                    </div>

                    {/* Stats row */}
                    <div className="flex items-center justify-center gap-12 mt-14">
                        {stats.map(stat => (
                            <div key={stat.label} className="text-center">
                                <div className="text-2xl font-display font-bold text-slate-800">{stat.value}</div>
                                <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mt-0.5">{stat.label}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Dashboard preview mock */}
                <div className="mt-20 relative">
                    <div className="absolute -inset-4 bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 rounded-[2.5rem] blur-3xl" />
                    <div className="relative bg-white rounded-3xl border border-cream-300 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.08)] overflow-hidden">
                        {/* Fake browser bar */}
                        <div className="flex items-center gap-2 px-6 py-3.5 bg-cream-50 border-b border-cream-200">
                            <div className="flex gap-1.5">
                                <div className="w-3 h-3 rounded-full bg-red-400" />
                                <div className="w-3 h-3 rounded-full bg-amber-400" />
                                <div className="w-3 h-3 rounded-full bg-emerald-400" />
                            </div>
                            <div className="flex-1 flex justify-center">
                                <div className="px-4 py-1 bg-white rounded-lg border border-cream-200 text-xs text-slate-400 font-mono">
                                    modbot.app/dashboard
                                </div>
                            </div>
                        </div>
                        {/* Fake dashboard */}
                        <div className="flex h-[320px]">
                            <div className="w-52 bg-sidebar-bg border-r border-cream-200 p-4 space-y-1 shrink-0">
                                <div className="flex items-center gap-2 px-3 py-2 mb-3">
                                    <div className="p-1.5 bg-indigo-50 rounded-lg"><Bot className="w-4 h-4 text-indigo-600" /></div>
                                    <span className="font-display font-bold text-sm text-slate-800">modbot</span>
                                </div>
                                {['Dashboard', 'Commands', 'Modules', 'Logging', 'Cases', 'Permissions'].map((item, i) => (
                                    <div key={item} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${i === 0 ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500'}`}>
                                        {item}
                                    </div>
                                ))}
                            </div>
                            <div className="flex-1 p-6 space-y-4">
                                <div className="flex gap-4">
                                    {[
                                        { label: 'Commands', val: '23/23', color: 'bg-indigo-50' },
                                        { label: 'Modules', val: '5/6', color: 'bg-emerald-50' },
                                        { label: 'Events', val: '7/21', color: 'bg-amber-50' },
                                        { label: 'Members', val: '15,420', color: 'bg-purple-50' },
                                    ].map(s => (
                                        <div key={s.label} className={`flex-1 p-3 ${s.color} rounded-xl`}>
                                            <div className="text-[10px] text-slate-400 font-semibold uppercase">{s.label}</div>
                                            <div className="text-lg font-display font-bold text-slate-800 mt-1">{s.val}</div>
                                        </div>
                                    ))}
                                </div>
                                <div className="flex gap-4">
                                    <div className="flex-[2] bg-cream-50 rounded-xl p-4 border border-cream-200">
                                        <div className="text-sm font-semibold text-slate-700 mb-3">Quick Actions</div>
                                        <div className="grid grid-cols-2 gap-2">
                                            {['Manage Commands', 'Configure Modules', 'Event Logging', 'View Cases'].map(a => (
                                                <div key={a} className="bg-white rounded-lg p-2.5 border border-cream-200 text-xs font-medium text-slate-600">{a}</div>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="flex-1 bg-cream-50 rounded-xl p-4 border border-cream-200">
                                        <div className="text-sm font-semibold text-slate-700 mb-3">System Status</div>
                                        <div className="space-y-2">
                                            {['Bot Core', 'Automod', 'Logging'].map(s => (
                                                <div key={s} className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                                        <span className="text-xs text-slate-600">{s}</span>
                                                    </div>
                                                    <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded font-medium">Online</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features */}
            <section id="features" className="max-w-6xl mx-auto px-6 py-20">
                <div className="text-center mb-14">
                    <h2 className="text-3xl md:text-4xl font-display font-bold text-slate-900 tracking-tight">
                        Everything you need to moderate
                    </h2>
                    <p className="text-slate-500 mt-3 max-w-lg mx-auto">
                        Built for server admins who need fine-grained control without the complexity.
                    </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {features.map(feature => (
                        <div
                            key={feature.title}
                            className="group p-6 bg-white rounded-3xl border border-cream-200 hover:border-indigo-200 shadow-[0_2px_8px_rgba(0,0,0,0.02)] hover:shadow-[0_20px_60px_-15px_rgba(0,0,0,0.08)] transition-all duration-300"
                        >
                            <div className={`inline-flex p-3 rounded-2xl ${feature.iconBg} mb-4`}>
                                <feature.icon className="w-6 h-6" />
                            </div>
                            <h3 className="text-lg font-display font-bold text-slate-800 mb-2">{feature.title}</h3>
                            <p className="text-sm text-slate-500 leading-relaxed">{feature.description}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* CTA */}
            <section className="max-w-6xl mx-auto px-6 py-20">
                <div className="relative bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 rounded-3xl p-12 text-center overflow-hidden">
                    <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
                    <div className="relative z-10">
                        <h2 className="text-3xl md:text-4xl font-display font-bold text-white mb-4">
                            Ready to take control?
                        </h2>
                        <p className="text-indigo-100 text-lg max-w-md mx-auto mb-8">
                            Connect your Discord and start managing your server in under a minute.
                        </p>
                        <a
                            href={OAUTH_URL}
                            className="inline-flex items-center gap-3 px-8 py-4 bg-white text-indigo-700 font-bold rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.15)] hover:shadow-[0_12px_40px_rgba(0,0,0,0.2)] hover:-translate-y-0.5 transition-all duration-200 text-base"
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#5865F2">
                                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z" />
                            </svg>
                            Connect Discord
                            <ChevronRight className="w-5 h-5" />
                        </a>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="max-w-6xl mx-auto px-6 py-8 border-t border-cream-300">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Bot className="w-4 h-4 text-slate-400" />
                        <span className="text-sm text-slate-400 font-medium">modbot</span>
                    </div>
                    <p className="text-xs text-slate-400">&copy; {new Date().getFullYear()} modbot. All rights reserved.</p>
                </div>
            </footer>
        </div>
    );
}
