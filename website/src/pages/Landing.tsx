import { useState } from 'react';
import {
  ArrowRight,
  Bot,
  ChevronRight,
  ExternalLink,
  Lock,
  ScrollText,
  Shield,
  Users,
  Zap,
} from 'lucide-react';
import { AUTH_BASE } from '@/lib/api';
import { getBotInviteUrl } from '@/lib/discord';

const OAUTH_URL = AUTH_BASE ? `${AUTH_BASE}/auth/login` : '/auth/login';
const BOT_INVITE_URL = getBotInviteUrl();

type DemoTab = 'dashboard' | 'commands' | 'modules' | 'logging' | 'cases' | 'permissions';

type DemoToggleItem = {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
};

const features = [
  {
    icon: Shield,
    title: 'Advanced Moderation',
    description: 'Ban, kick, warn, timeout with full case tracking and audit trails.',
    iconBg: 'bg-indigo-50 text-indigo-600',
  },
  {
    icon: Zap,
    title: 'Auto Moderation',
    description: 'AI-powered spam, link, and invite filtering with configurable thresholds.',
    iconBg: 'bg-amber-50 text-amber-600',
  },
  {
    icon: ScrollText,
    title: 'Granular Logging',
    description: 'Route 20+ event types to specific channels with per-event control.',
    iconBg: 'bg-emerald-50 text-emerald-600',
  },
  {
    icon: Users,
    title: 'Role-Based Access',
    description: 'Map Discord roles to dashboard permissions with privilege escalation prevention.',
    iconBg: 'bg-purple-50 text-purple-600',
  },
];

const stats = [
  { label: 'Servers', value: '500+' },
  { label: 'Commands', value: '50+' },
  { label: 'Events Logged', value: '1M+' },
];

const demoTabs: { id: DemoTab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'commands', label: 'Commands' },
  { id: 'modules', label: 'Modules' },
  { id: 'logging', label: 'Logging' },
  { id: 'cases', label: 'Cases' },
  { id: 'permissions', label: 'Permissions' },
];

const initialDemoCommands: DemoToggleItem[] = [
  { id: 'ban', label: '/ban', description: 'Ban a user from the server', enabled: true },
  { id: 'kick', label: '/kick', description: 'Kick a member', enabled: true },
  { id: 'timeout', label: '/timeout', description: 'Temporarily timeout a member', enabled: true },
  { id: 'warn', label: '/warn', description: 'Create a warning case', enabled: true },
  { id: 'clean', label: '/clean', description: 'Bulk delete messages', enabled: false },
];

const initialDemoModules: DemoToggleItem[] = [
  { id: 'automod', label: 'Auto Moderation', description: 'Spam, links, invites, and caps filtering', enabled: true },
  { id: 'antiraid', label: 'Anti-Raid', description: 'Mass-join detection and lockdown', enabled: false },
  { id: 'logging', label: 'Logging', description: 'Structured event logging routes', enabled: true },
  { id: 'tickets', label: 'Tickets', description: 'Staff support panel and ticket routing', enabled: false },
];

const initialDemoEvents: DemoToggleItem[] = [
  { id: 'member_join', label: 'Member Joined', description: 'Track new members joining', enabled: true },
  { id: 'message_delete', label: 'Message Deleted', description: 'Track deleted messages', enabled: true },
  { id: 'user_ban', label: 'User Banned', description: 'Track ban actions', enabled: true },
  { id: 'voice_join', label: 'Voice Join', description: 'Track voice channel joins', enabled: false },
];

export function Landing() {
  return (
    <div className="min-h-screen bg-app-bg overflow-hidden">
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-50 rounded-xl">
            <Bot className="w-6 h-6 text-indigo-600" />
          </div>
          <span className="font-display font-bold text-xl text-slate-800 tracking-tight">modbot</span>
        </div>
        <div className="flex items-center gap-3">
          <a
            href={BOT_INVITE_URL}
            className="px-4 py-2.5 border border-cream-300 bg-white hover:bg-cream-50 text-slate-700 text-sm font-semibold rounded-xl transition-colors inline-flex items-center gap-2"
          >
            Add to Server
            <ExternalLink className="w-4 h-4" />
          </a>
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

      <section className="max-w-6xl mx-auto px-6 pt-16 pb-24">
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-display font-bold text-slate-900 tracking-tight leading-[1.1] mb-6">
            Complete control over your
            <span className="block bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 bg-clip-text text-transparent">
              Discord server
            </span>
          </h1>

          <p className="text-lg text-slate-500 max-w-xl mx-auto mb-10 leading-relaxed">
            Modbot gives you Dyno-level control depth with granular configuration,
            layered overrides, and a full dashboard to manage everything.
          </p>

          <div className="flex items-center justify-center gap-4 flex-wrap">
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
              href={BOT_INVITE_URL}
              className="px-6 py-3.5 text-slate-700 hover:text-slate-900 font-semibold border border-cream-300 hover:border-slate-300 rounded-2xl transition-all duration-200 hover:bg-white hover:shadow-sm inline-flex items-center gap-2"
            >
              Add Bot to a Server
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>

          <div className="flex items-center justify-center gap-12 mt-14">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl font-display font-bold text-slate-800">{stat.value}</div>
                <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mt-0.5">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        <DashboardPlayground />
      </section>

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
          {features.map((feature) => (
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
            <div className="flex items-center justify-center gap-3 flex-wrap">
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
              <a
                href={BOT_INVITE_URL}
                className="inline-flex items-center gap-2 px-8 py-4 bg-indigo-500/20 border border-indigo-200/40 text-white font-semibold rounded-2xl hover:bg-indigo-500/30 transition-colors text-base"
              >
                Add Bot to Server
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </section>

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

function DashboardPlayground() {
  const [activeTab, setActiveTab] = useState<DemoTab>('dashboard');
  const [demoCommands, setDemoCommands] = useState(initialDemoCommands);
  const [demoModules, setDemoModules] = useState(initialDemoModules);
  const [demoEvents, setDemoEvents] = useState(initialDemoEvents);

  const enabledCommands = demoCommands.filter((item) => item.enabled).length;
  const enabledModules = demoModules.filter((item) => item.enabled).length;
  const enabledEvents = demoEvents.filter((item) => item.enabled).length;
  const automodEnabled = demoModules.find((item) => item.id === 'automod')?.enabled ?? false;
  const loggingEnabled = demoModules.find((item) => item.id === 'logging')?.enabled ?? false;
  const antiRaidEnabled = demoModules.find((item) => item.id === 'antiraid')?.enabled ?? false;

  return (
    <div className="mt-20 relative">
      <div className="absolute -inset-4 bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 rounded-[2.5rem] blur-3xl" />
      <div className="relative bg-white rounded-3xl border border-cream-300 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.08)] overflow-hidden">
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
          <div className="text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md px-2 py-0.5 font-semibold">
            Interactive Demo
          </div>
        </div>

        <div className="flex h-[380px]">
          <div className="w-56 bg-sidebar-bg border-r border-cream-200 p-4 space-y-1 shrink-0">
            <div className="flex items-center gap-2 px-3 py-2 mb-3">
              <div className="p-1.5 bg-indigo-50 rounded-lg"><Bot className="w-4 h-4 text-indigo-600" /></div>
              <span className="font-display font-bold text-sm text-slate-800">modbot</span>
            </div>
            {demoTabs.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  activeTab === item.id ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:bg-white/60'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="flex-1 p-6 space-y-4 overflow-y-auto">
            {activeTab === 'dashboard' && (
              <>
                <div className="flex gap-4">
                  {[
                    { label: 'Commands', val: `${enabledCommands}/${demoCommands.length}`, color: 'bg-indigo-50' },
                    { label: 'Modules', val: `${enabledModules}/${demoModules.length}`, color: 'bg-emerald-50' },
                    { label: 'Events', val: `${enabledEvents}/${demoEvents.length}`, color: 'bg-amber-50' },
                    { label: 'Members', val: '15,420', color: 'bg-purple-50' },
                  ].map((stat) => (
                    <div key={stat.label} className={`flex-1 p-3 ${stat.color} rounded-xl`}>
                      <div className="text-[10px] text-slate-400 font-semibold uppercase">{stat.label}</div>
                      <div className="text-lg font-display font-bold text-slate-800 mt-1">{stat.val}</div>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="col-span-2 bg-cream-50 rounded-xl p-4 border border-cream-200">
                    <div className="text-sm font-semibold text-slate-700 mb-3">Quick Actions</div>
                    <div className="grid grid-cols-2 gap-2">
                      <button onClick={() => setActiveTab('commands')} className="bg-white rounded-lg p-2.5 border border-cream-200 text-xs font-medium text-slate-600 hover:border-indigo-200 transition-colors">Manage Commands</button>
                      <button onClick={() => setActiveTab('modules')} className="bg-white rounded-lg p-2.5 border border-cream-200 text-xs font-medium text-slate-600 hover:border-indigo-200 transition-colors">Configure Modules</button>
                      <button onClick={() => setActiveTab('logging')} className="bg-white rounded-lg p-2.5 border border-cream-200 text-xs font-medium text-slate-600 hover:border-indigo-200 transition-colors">Event Logging</button>
                      <button onClick={() => setActiveTab('cases')} className="bg-white rounded-lg p-2.5 border border-cream-200 text-xs font-medium text-slate-600 hover:border-indigo-200 transition-colors">View Cases</button>
                    </div>
                  </div>
                  <div className="bg-cream-50 rounded-xl p-4 border border-cream-200">
                    <div className="text-sm font-semibold text-slate-700 mb-3">System Status</div>
                    <div className="space-y-2">
                      <StatusRow label="Bot Core" online />
                      <StatusRow label="Automod" online={automodEnabled} />
                      <StatusRow label="Anti-Raid" online={antiRaidEnabled} />
                      <StatusRow label="Logging" online={loggingEnabled} />
                    </div>
                  </div>
                </div>
              </>
            )}

            {activeTab === 'commands' && (
              <div className="space-y-2">
                {demoCommands.map((item) => (
                  <ToggleRow
                    key={item.id}
                    label={item.label}
                    description={item.description}
                    enabled={item.enabled}
                    onToggle={() => {
                      setDemoCommands((prev) => prev.map((current) => (
                        current.id === item.id ? { ...current, enabled: !current.enabled } : current
                      )));
                    }}
                  />
                ))}
              </div>
            )}

            {activeTab === 'modules' && (
              <div className="space-y-2">
                {demoModules.map((item) => (
                  <ToggleRow
                    key={item.id}
                    label={item.label}
                    description={item.description}
                    enabled={item.enabled}
                    onToggle={() => {
                      setDemoModules((prev) => prev.map((current) => (
                        current.id === item.id ? { ...current, enabled: !current.enabled } : current
                      )));
                    }}
                  />
                ))}
              </div>
            )}

            {activeTab === 'logging' && (
              <div className="space-y-2">
                {demoEvents.map((item) => (
                  <ToggleRow
                    key={item.id}
                    label={item.label}
                    description={item.description}
                    enabled={item.enabled}
                    onToggle={() => {
                      setDemoEvents((prev) => prev.map((current) => (
                        current.id === item.id ? { ...current, enabled: !current.enabled } : current
                      )));
                    }}
                  />
                ))}
              </div>
            )}

            {activeTab === 'cases' && (
              <div className="space-y-2">
                {[
                  { id: '#4931', action: 'warn', user: 'spam_bot_22', reason: 'Excessive mentions' },
                  { id: '#4932', action: 'timeout', user: 'capslockking', reason: 'Spam flood detected' },
                  { id: '#4933', action: 'ban', user: 'malicious_inviter', reason: 'Invite scam links' },
                ].map((entry) => (
                  <div key={entry.id} className="bg-cream-50 border border-cream-200 rounded-xl p-3 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-slate-700">{entry.id} - {entry.action.toUpperCase()}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{entry.user} - {entry.reason}</div>
                    </div>
                    <button className="text-xs font-semibold text-indigo-600 hover:text-indigo-700">Open</button>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'permissions' && (
              <div className="space-y-3">
                <div className="bg-cream-50 border border-cream-200 rounded-xl p-3">
                  <div className="text-sm font-semibold text-slate-700 mb-2">Role Mappings</div>
                  <div className="space-y-2">
                    {[
                      { role: '@Admin', access: 'Admin' },
                      { role: '@Moderator', access: 'Moderator' },
                      { role: '@Helpers', access: 'Viewer' },
                    ].map((mapping) => (
                      <div key={mapping.role} className="flex items-center justify-between text-xs bg-white border border-cream-200 rounded-lg p-2.5">
                        <span className="text-slate-700 font-medium">{mapping.role}</span>
                        <span className="text-indigo-700 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-md font-semibold">{mapping.access}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-start gap-2.5">
                  <Lock className="w-4 h-4 text-amber-700 mt-0.5 shrink-0" />
                  <p className="text-xs text-amber-800">
                    Permission checks are still validated server-side to prevent privilege escalation.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ToggleRow({ label, description, enabled, onToggle }: { label: string; description: string; enabled: boolean; onToggle: () => void }) {
  return (
    <div className={`rounded-xl border p-3 flex items-center justify-between ${enabled ? 'bg-cream-50 border-cream-200' : 'bg-white border-cream-100 opacity-70'}`}>
      <div className="min-w-0 pr-3">
        <div className="text-sm font-semibold text-slate-700">{label}</div>
        <div className="text-xs text-slate-500 truncate">{description}</div>
      </div>
      <button
        onClick={onToggle}
        className={`w-11 h-6 rounded-full transition-colors relative ${enabled ? 'bg-indigo-600' : 'bg-slate-300'}`}
        aria-label={`Toggle ${label}`}
      >
        <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${enabled ? 'translate-x-5 left-0.5' : 'translate-x-0 left-0.5'}`} />
      </button>
    </div>
  );
}

function StatusRow({ label, online }: { label: string; online: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-emerald-500' : 'bg-slate-300'}`} />
        <span className="text-xs text-slate-600">{label}</span>
      </div>
      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${online ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
        {online ? 'Online' : 'Offline'}
      </span>
    </div>
  );
}
