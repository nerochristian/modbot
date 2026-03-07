import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge, PageSkeleton } from '@/components/ui/Shared';
import { ShieldAlert, Users, MessageSquare, Activity, ShieldCheck, AlertTriangle, Command, Package, Zap, ArrowRight, Settings2 } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { NavLink } from 'react-router-dom';
import { cn, formatCount } from '@/lib/utils';

export function Overview() {
  const { guilds, activeGuildId, config, loading } = useAppStore();
  const activeServer = guilds.find(s => s.id === activeGuildId);

  if (loading || !config) return <PageSkeleton />;

  const enabledCommands = Object.values(config.commands).filter(c => c.enabled).length;
  const totalCommands = Object.keys(config.commands).length;
  const enabledModules = Object.values(config.modules).filter(m => m.enabled).length;
  const totalModules = Object.keys(config.modules).length;
  const activeLogEvents = Object.values(config.logging).filter(l => l.enabled).length;
  const totalLogEvents = Object.keys(config.logging).length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Dashboard</h1>
        <p className="text-slate-500 mt-1">Control panel overview for {activeServer?.name}</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <QuickStatCard
          title="Commands"
          value={`${enabledCommands}/${totalCommands}`}
          subtitle="enabled"
          icon={Command}
          color="text-indigo-500"
          bg="bg-indigo-50"
          link="/dashboard/commands"
        />
        <QuickStatCard
          title="Modules"
          value={`${enabledModules}/${totalModules}`}
          subtitle="active"
          icon={Package}
          color="text-emerald-500"
          bg="bg-emerald-50"
          link="/dashboard/modules"
        />
        <QuickStatCard
          title="Logged Events"
          value={`${activeLogEvents}/${totalLogEvents}`}
          subtitle="tracked"
          icon={Zap}
          color="text-amber-500"
          bg="bg-amber-50"
          link="/dashboard/logging"
        />
        <QuickStatCard
          title="Members"
          value={formatCount(activeServer?.memberCount)}
          subtitle="total"
          icon={Users}
          color="text-purple-500"
          bg="bg-purple-50"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <Card className="col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Quick Actions</CardTitle>
            <CardDescription>Common configuration shortcuts.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { label: 'Run Setup', desc: 'Configure the server-wide foundation', icon: Settings2, link: '/dashboard/setup', color: 'text-blue-600 bg-blue-50' },
                { label: 'Manage Commands', desc: 'Toggle and configure bot commands', icon: Command, link: '/dashboard/commands', color: 'text-indigo-600 bg-indigo-50' },
                { label: 'Configure Modules', desc: 'Enable features and set thresholds', icon: Package, link: '/dashboard/modules', color: 'text-emerald-600 bg-emerald-50' },
                { label: 'Event Logging', desc: 'Route events to Discord channels', icon: Zap, link: '/dashboard/logging', color: 'text-amber-600 bg-amber-50' },
                { label: 'View Cases', desc: 'Browse moderation case history', icon: ShieldAlert, link: '/dashboard/cases', color: 'text-red-600 bg-red-50' },
              ].map(action => (
                <NavLink
                  key={action.link}
                  to={action.link}
                  className="flex items-center gap-4 p-4 bg-cream-50 rounded-2xl border border-cream-200 hover:border-indigo-200 hover:shadow-sm transition-all group"
                >
                  <div className={cn('p-2.5 rounded-xl', action.color)}>
                    <action.icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-slate-800">{action.label}</h4>
                    <p className="text-xs text-slate-500">{action.desc}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 transition-colors" />
                </NavLink>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">System Status</CardTitle>
            <CardDescription>Current health of bot systems.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { name: 'Bot Core', status: 'Online', ok: true },
                { name: 'Auto Moderation', status: config.modules.automod?.enabled ? 'Active' : 'Disabled', ok: config.modules.automod?.enabled },
                { name: 'Anti-Raid', status: config.modules.antiraid?.enabled ? 'Active' : 'Disabled', ok: config.modules.antiraid?.enabled },
                { name: 'Logging', status: config.modules.logging?.enabled ? 'Active' : 'Disabled', ok: config.modules.logging?.enabled },
                { name: 'Moderation', status: config.modules.moderation?.enabled ? 'Active' : 'Disabled', ok: config.modules.moderation?.enabled },
              ].map((sys, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-cream-50 border border-cream-200">
                  <div className="flex items-center gap-3">
                    <div className={cn('w-2 h-2 rounded-full', sys.ok ? 'bg-emerald-500' : 'bg-slate-300')} />
                    <span className="text-sm font-medium text-slate-700">{sys.name}</span>
                  </div>
                  <Badge variant={sys.ok ? 'success' : 'default'}>{sys.status}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

interface QuickStatCardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: typeof Command;
  color: string;
  bg: string;
  link?: string;
}

function QuickStatCard({ title, value, subtitle, icon: Icon, color, bg, link }: QuickStatCardProps) {
  const content = (
    <Card className={cn(link && 'hover:shadow-[0_12px_40px_rgb(0,0,0,0.06)] transition-all cursor-pointer')}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-3">
          <div className={cn('p-2.5 rounded-xl', bg, color)}>
            <Icon className="w-5 h-5" />
          </div>
          <span className="text-xs font-medium text-slate-400 uppercase">{title}</span>
        </div>
        <div>
          <h3 className="text-2xl font-display font-bold text-slate-800">{value}</h3>
          <p className="text-xs text-slate-500 mt-0.5 font-medium">{subtitle}</p>
        </div>
      </CardContent>
    </Card>
  );

  if (link) {
    return <NavLink to={link}>{content}</NavLink>;
  }
  return content;
}
