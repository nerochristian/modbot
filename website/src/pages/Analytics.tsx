import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Badge, PageSkeleton } from '@/components/ui/Shared';
import { useAppStore } from '@/store/useAppStore';
import { BarChart3, TrendingUp, Users, Shield, Clock } from 'lucide-react';

export function Analytics() {
  const { config, capabilities, loading } = useAppStore();

  if (loading || !config || !capabilities) return <PageSkeleton />;

  const enabledCommands = Object.values(config.commands).filter(c => c.enabled).length;
  const disabledCommands = Object.values(config.commands).filter(c => !c.enabled).length;
  const enabledModules = Object.values(config.modules).filter(m => m.enabled).length;
  const activeEvents = Object.values(config.logging).filter(l => l.enabled).length;

  // Mock analytics data
  const weekData = [
    { day: 'Mon', actions: 24 },
    { day: 'Tue', actions: 18 },
    { day: 'Wed', actions: 35 },
    { day: 'Thu', actions: 42 },
    { day: 'Fri', actions: 28 },
    { day: 'Sat', actions: 15 },
    { day: 'Sun', actions: 12 },
  ];
  const maxActions = Math.max(...weekData.map(d => d.actions));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Analytics</h1>
        <p className="text-slate-500 mt-1">Server activity and moderation statistics.</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Commands', value: enabledCommands + disabledCommands, sub: `${enabledCommands} enabled`, icon: BarChart3, color: 'text-indigo-600 bg-indigo-50' },
          { label: 'Active Modules', value: enabledModules, sub: `of ${Object.keys(config.modules).length} total`, icon: Shield, color: 'text-emerald-600 bg-emerald-50' },
          { label: 'Logged Events', value: activeEvents, sub: `of ${Object.keys(config.logging).length} types`, icon: TrendingUp, color: 'text-amber-600 bg-amber-50' },
          { label: 'Role Mappings', value: config.permissions.roleMappings.length, sub: 'configured', icon: Users, color: 'text-purple-600 bg-purple-50' },
        ].map(stat => (
          <Card key={stat.label}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <div className={`p-2.5 rounded-xl ${stat.color}`}>
                  <stat.icon className="w-5 h-5" />
                </div>
                <span className="text-xs font-medium text-slate-400 uppercase">{stat.label}</span>
              </div>
              <h3 className="text-2xl font-display font-bold text-slate-800">{stat.value}</h3>
              <p className="text-xs text-slate-500 mt-0.5 font-medium">{stat.sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Chart (simple bar chart) */}
        <Card className="col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Weekly Moderation Activity</CardTitle>
            <CardDescription>Actions taken per day this week.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3 h-48">
              {weekData.map(d => (
                <div key={d.day} className="flex-1 flex flex-col items-center gap-2">
                  <span className="text-xs font-semibold text-slate-700">{d.actions}</span>
                  <div
                    className="w-full bg-gradient-to-t from-indigo-500 to-indigo-400 rounded-t-xl transition-all duration-500 min-h-[4px]"
                    style={{ height: `${(d.actions / maxActions) * 100}%` }}
                  />
                  <span className="text-xs text-slate-500 font-medium">{d.day}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Action Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Action Breakdown</CardTitle>
            <CardDescription>Types of moderation actions.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { label: 'Warnings', count: 45, pct: 38, color: 'bg-amber-500' },
                { label: 'Timeouts', count: 28, pct: 24, color: 'bg-orange-500' },
                { label: 'Kicks', count: 18, pct: 15, color: 'bg-red-400' },
                { label: 'Bans', count: 12, pct: 10, color: 'bg-red-600' },
                { label: 'Notes', count: 15, pct: 13, color: 'bg-slate-400' },
              ].map(action => (
                <div key={action.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-700">{action.label}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">{action.count}</span>
                      <Badge variant="default">{action.pct}%</Badge>
                    </div>
                  </div>
                  <div className="h-2 bg-cream-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${action.color} transition-all duration-500`}
                      style={{ width: `${action.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
