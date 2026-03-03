import { useState, useEffect } from 'react';
import { Badge, SearchInput, PageSkeleton, EmptyState } from '@/components/ui/Shared';
import { Card, CardContent } from '@/components/ui/Card';
import { useAppStore } from '@/store/useAppStore';
import { realApiClient } from '@/lib/api';
import type { AuditLogEntry } from '@/types';
import { History, Settings, ToggleLeft, RefreshCw, FileText } from 'lucide-react';

const ACTION_ICONS: Record<string, typeof Settings> = {
  config_update: Settings,
  command_toggle: ToggleLeft,
  module_toggle: ToggleLeft,
  sync_commands: RefreshCw,
};

const ACTION_LABELS: Record<string, string> = {
  config_update: 'Config Updated',
  command_toggle: 'Command Toggled',
  module_toggle: 'Module Toggled',
  sync_commands: 'Commands Synced',
};

export function Audit() {
  const { activeGuildId } = useAppStore();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (!activeGuildId) return;
    setLoading(true);
    realApiClient
      .getAuditLog(activeGuildId)
      .then((res) => {
        setEntries(res.data);
        setLoading(false);
      })
      .catch(() => {
        setEntries([]);
        setLoading(false);
      });
  }, [activeGuildId]);

  if (loading) return <PageSkeleton />;

  const filtered = entries.filter((entry) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      entry.userName.toLowerCase().includes(q) ||
      entry.action.toLowerCase().includes(q) ||
      entry.target.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Audit Log</h1>
        <p className="text-slate-500 mt-1">Track all configuration changes and administrative actions.</p>
      </div>

      <SearchInput
        value={search}
        onChange={setSearch}
        placeholder="Search by user, action, or target..."
        className="w-80"
      />

      {filtered.length === 0 ? (
        <EmptyState
          icon={<History className="w-8 h-8" />}
          title="No audit entries"
          description="No audit log entries match your search."
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((entry) => {
            const Icon = ACTION_ICONS[entry.action] || FileText;
            const label = ACTION_LABELS[entry.action] || entry.action;
            const timeAgo = getTimeAgo(entry.timestamp);
            const changes = entry.changes || {};
            const changeKeys = Object.keys(changes);

            return (
              <Card key={entry.id} className="transition-all hover:shadow-[0_12px_40px_rgb(0,0,0,0.06)]">
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <div className="p-2.5 bg-cream-100 text-slate-500 rounded-xl shrink-0">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-sm text-slate-800">{label}</span>
                        <Badge variant="default">{entry.target}</Badge>
                      </div>
                      <p className="text-xs text-slate-500">
                        by <span className="font-medium text-slate-600">{entry.userName}</span>
                      </p>
                      {changeKeys.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {changeKeys.map((key) => {
                            const raw = changes[key] as unknown;
                            const parsed = typeof raw === 'object' && raw !== null ? (raw as Record<string, unknown>) : null;
                            const before = parsed && Object.prototype.hasOwnProperty.call(parsed, 'from') ? parsed.from : null;
                            const after = parsed && Object.prototype.hasOwnProperty.call(parsed, 'to') ? parsed.to : raw;

                            return (
                              <div key={key} className="flex items-center gap-2 text-xs">
                                <span className="font-mono text-slate-500">{key}:</span>
                                <span className="px-1.5 py-0.5 bg-red-50 text-red-600 rounded font-mono line-through">
                                  {JSON.stringify(before)}
                                </span>
                                <span className="text-slate-400">-&gt;</span>
                                <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded font-mono">
                                  {JSON.stringify(after)}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-slate-400 shrink-0">{timeAgo}</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function getTimeAgo(isoString: string): string {
  const timestamp = new Date(isoString).getTime();
  if (Number.isNaN(timestamp)) return 'unknown';

  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
