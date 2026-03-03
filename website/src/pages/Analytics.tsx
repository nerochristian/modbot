import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Badge, PageSkeleton, EmptyState } from '@/components/ui/Shared';
import { useAppStore } from '@/store/useAppStore';
import { realApiClient } from '@/lib/api';
import type { CaseAction, ModerationCase } from '@/types';
import { BarChart3, TrendingUp, Users, Shield, Clock } from 'lucide-react';

interface GuildStats {
  memberCount: number;
  channelCount: number;
  roleCount: number;
  caseCount: number;
  warningCount: number;
  commandCount: number;
  cogCount: number;
  botOnline: boolean;
}

const ACTION_LABELS: Record<CaseAction, string> = {
  warn: 'Warnings',
  timeout: 'Timeouts',
  kick: 'Kicks',
  ban: 'Bans',
  unban: 'Unbans',
  note: 'Notes',
  quarantine: 'Quarantines',
};

const ACTION_COLORS: Record<CaseAction, string> = {
  warn: 'bg-amber-500',
  timeout: 'bg-orange-500',
  kick: 'bg-red-400',
  ban: 'bg-red-600',
  unban: 'bg-emerald-500',
  note: 'bg-slate-400',
  quarantine: 'bg-purple-500',
};

export function Analytics() {
  const { config, activeGuildId, loading } = useAppStore();
  const [cases, setCases] = useState<ModerationCase[]>([]);
  const [stats, setStats] = useState<GuildStats | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  useEffect(() => {
    if (!activeGuildId) {
      setCases([]);
      setStats(null);
      return;
    }

    setAnalyticsLoading(true);

    Promise.all([
      realApiClient.getCases(activeGuildId).then((res) => res.data).catch(() => []),
      fetch(`/api/guilds/${activeGuildId}/stats`, { credentials: 'include' })
        .then((res) => (res.ok ? res.json() : null))
        .catch(() => null),
    ])
      .then(([caseData, guildStats]) => {
        setCases(caseData);
        setStats(guildStats);
      })
      .finally(() => {
        setAnalyticsLoading(false);
      });
  }, [activeGuildId]);

  if (loading || !config) return <PageSkeleton />;
  if (analyticsLoading && !stats && cases.length === 0) return <PageSkeleton />;

  const commands = config.commands || {};
  const modules = config.modules || {};
  const logging = config.logging || {};
  const roleMappings = config.permissions?.roleMappings || [];

  const enabledCommands = Object.values(commands).filter((c) => c?.enabled).length;
  const disabledCommands = Object.values(commands).filter((c) => !c?.enabled).length;
  const enabledModules = Object.values(modules).filter((m) => m?.enabled).length;
  const activeEvents = Object.values(logging).filter((l) => l?.enabled).length;

  const weekData = useMemo(() => {
    const now = new Date();
    const rows: { day: string; key: string; actions: number }[] = [];
    const formatter = new Intl.DateTimeFormat('en-US', { weekday: 'short' });

    for (let i = 6; i >= 0; i -= 1) {
      const d = new Date(now);
      d.setHours(0, 0, 0, 0);
      d.setDate(now.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      rows.push({ day: formatter.format(d), key, actions: 0 });
    }

    for (const entry of cases) {
      const created = new Date(entry.createdAt);
      if (Number.isNaN(created.getTime())) continue;
      const key = created.toISOString().slice(0, 10);
      const slot = rows.find((row) => row.key === key);
      if (slot) {
        slot.actions += 1;
      }
    }

    return rows.map(({ day, actions }) => ({ day, actions }));
  }, [cases]);

  const maxActions = Math.max(1, ...weekData.map((d) => d.actions));

  const actionBreakdown = useMemo(() => {
    const counts: Record<CaseAction, number> = {
      warn: 0,
      timeout: 0,
      kick: 0,
      ban: 0,
      unban: 0,
      note: 0,
      quarantine: 0,
    };

    for (const entry of cases) {
      counts[entry.action] += 1;
    }

    const total = cases.length || 1;

    return (Object.keys(counts) as CaseAction[])
      .filter((action) => counts[action] > 0)
      .sort((a, b) => counts[b] - counts[a])
      .map((action) => ({
        action,
        label: ACTION_LABELS[action],
        count: counts[action],
        pct: Math.round((counts[action] / total) * 100),
        color: ACTION_COLORS[action],
      }));
  }, [cases]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Analytics</h1>
        <p className="text-slate-500 mt-1">Server activity and moderation statistics.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Commands', value: enabledCommands + disabledCommands, sub: `${enabledCommands} enabled`, icon: BarChart3, color: 'text-indigo-600 bg-indigo-50' },
          { label: 'Active Modules', value: enabledModules, sub: `of ${Object.keys(modules).length} total`, icon: Shield, color: 'text-emerald-600 bg-emerald-50' },
          { label: 'Logged Events', value: activeEvents, sub: `of ${Object.keys(logging).length} types`, icon: TrendingUp, color: 'text-amber-600 bg-amber-50' },
          { label: 'Role Mappings', value: roleMappings.length, sub: 'configured', icon: Users, color: 'text-purple-600 bg-purple-50' },
        ].map((stat) => (
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
        <Card className="col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Weekly Moderation Activity</CardTitle>
            <CardDescription>Actions recorded per day in the last 7 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3 h-48">
              {weekData.map((d) => (
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

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Action Breakdown</CardTitle>
            <CardDescription>Based on real moderation cases.</CardDescription>
          </CardHeader>
          <CardContent>
            {actionBreakdown.length === 0 ? (
              <EmptyState
                icon={<Clock className="w-8 h-8" />}
                title="No case data"
                description="No moderation cases found yet for this guild."
              />
            ) : (
              <div className="space-y-3">
                {actionBreakdown.map((action) => (
                  <div key={action.action}>
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
            )}
          </CardContent>
        </Card>
      </div>

      {stats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Guild Runtime Stats</CardTitle>
            <CardDescription>Live counts from the bot and database.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-cream-50 border border-cream-200">
                <p className="text-xs text-slate-500">Members</p>
                <p className="text-lg font-semibold text-slate-800">{stats.memberCount}</p>
              </div>
              <div className="p-3 rounded-xl bg-cream-50 border border-cream-200">
                <p className="text-xs text-slate-500">Channels</p>
                <p className="text-lg font-semibold text-slate-800">{stats.channelCount}</p>
              </div>
              <div className="p-3 rounded-xl bg-cream-50 border border-cream-200">
                <p className="text-xs text-slate-500">Cases</p>
                <p className="text-lg font-semibold text-slate-800">{stats.caseCount}</p>
              </div>
              <div className="p-3 rounded-xl bg-cream-50 border border-cream-200">
                <p className="text-xs text-slate-500">Bot</p>
                <p className="text-lg font-semibold text-slate-800">{stats.botOnline ? 'Online' : 'Offline'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
