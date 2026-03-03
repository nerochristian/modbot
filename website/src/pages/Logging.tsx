import { useState, useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Switch } from '@/components/ui/Switch';
import { Button } from '@/components/ui/Button';
import { Badge, Select, SaveBar, PageSkeleton, SearchInput, Tabs } from '@/components/ui/Shared';
import { ScrollText, Settings, Download, Hash } from 'lucide-react';
import type { EventTypeCapability, LoggingRouteConfig } from '@/types';
import { MOCK_CHANNELS } from '@/lib/mock-data';
import { cn } from '@/lib/utils';

const CATEGORY_LABELS: Record<string, string> = {
  moderation: 'Moderation',
  automod: 'Automod',
  server: 'Server',
  messages: 'Messages',
  members: 'Members',
  voice: 'Voice',
};

const SEVERITY_BADGE: Record<string, 'info' | 'warning' | 'danger'> = {
  info: 'info',
  warning: 'warning',
  critical: 'danger',
};

export function Logging() {
  const { capabilities, config, updateConfigLocal, saveConfig, discardChanges, configDirty, error } = useAppStore();
  const [activeCategory, setActiveCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState(false);

  const eventTypes = capabilities?.eventTypes || [];
  const channelOptions = MOCK_CHANNELS.filter(c => c.type === 0).map(c => ({ label: `#${c.name}`, value: c.id }));

  const categories = useMemo(() => {
    const cats = new Set(eventTypes.map(e => e.category));
    return ['all', ...Array.from(cats)];
  }, [eventTypes]);

  const categoryTabs = useMemo(() => {
    return categories.map(cat => ({
      id: cat,
      label: cat === 'all' ? 'All' : CATEGORY_LABELS[cat] || cat,
      count: cat === 'all' ? eventTypes.length : eventTypes.filter(e => e.category === cat).length,
    }));
  }, [categories, eventTypes]);

  const filtered = useMemo(() => {
    let list = eventTypes;
    if (activeCategory !== 'all') list = list.filter(e => e.category === activeCategory);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(e => e.name.toLowerCase().includes(q) || e.description.toLowerCase().includes(q));
    }
    return list;
  }, [eventTypes, activeCategory, search]);

  const toggleEvent = (eventId: string) => {
    if (!config) return;
    const current = config.logging[eventId];
    if (!current) return;
    updateConfigLocal({
      logging: {
        ...config.logging,
        [eventId]: { ...current, enabled: !current.enabled },
      },
    });
  };

  const setChannel = (eventId: string, channelId: string) => {
    if (!config) return;
    const current = config.logging[eventId];
    if (!current) return;
    updateConfigLocal({
      logging: {
        ...config.logging,
        [eventId]: { ...current, channelId: channelId || null },
      },
    });
  };

  const setFormat = (eventId: string, format: 'compact' | 'detailed') => {
    if (!config) return;
    const current = config.logging[eventId];
    if (!current) return;
    updateConfigLocal({
      logging: {
        ...config.logging,
        [eventId]: { ...current, format },
      },
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try { await saveConfig(); } catch { /* handled */ }
    setSaving(false);
  };

  if (!capabilities || !config) return <PageSkeleton />;

  // Group by category for display
  const groupedByCategory = useMemo(() => {
    const map = new Map<string, EventTypeCapability[]>();
    for (const et of filtered) {
      const list = map.get(et.category) || [];
      list.push(et);
      map.set(et.category, list);
    }
    return map;
  }, [filtered]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Logging</h1>
          <p className="text-slate-500 mt-1">Route server events to specific channels with per-event control.</p>
        </div>
        <Button variant="outline" className="gap-2">
          <Download className="w-4 h-4" />
          Export Logs
        </Button>
      </div>

      <div className="flex items-center gap-4 flex-wrap">
        <SearchInput value={search} onChange={setSearch} placeholder="Search events..." className="w-64" />
        <Tabs tabs={categoryTabs} activeTab={activeCategory} onChange={setActiveCategory} />
      </div>

      <div className="space-y-6">
        {Array.from(groupedByCategory).map(([category, events]) => (
          <Card key={category}>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
                  <ScrollText className="w-4 h-4" />
                </div>
                <CardTitle className="text-lg">{CATEGORY_LABELS[category] || category} Events</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {events.map(et => {
                  const logConfig = config.logging[et.id];
                  return (
                    <div
                      key={et.id}
                      className={cn(
                        'flex items-center gap-4 p-3 rounded-xl border transition-colors',
                        logConfig?.enabled
                          ? 'bg-cream-50 border-cream-200'
                          : 'bg-white border-cream-100 opacity-60'
                      )}
                    >
                      <Switch
                        checked={logConfig?.enabled ?? false}
                        onCheckedChange={() => toggleEvent(et.id)}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-slate-700">{et.name}</span>
                          <Badge variant={SEVERITY_BADGE[et.severity]}>{et.severity}</Badge>
                        </div>
                        <p className="text-xs text-slate-500 truncate">{et.description}</p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <Select
                          value={logConfig?.channelId || ''}
                          onChange={(v) => setChannel(et.id, v)}
                          options={channelOptions}
                          placeholder="No channel"
                          className="w-40"
                          disabled={!logConfig?.enabled}
                        />
                        <Select
                          value={logConfig?.format || 'detailed'}
                          onChange={(v) => setFormat(et.id, v as 'compact' | 'detailed')}
                          options={[{ label: 'Detailed', value: 'detailed' }, { label: 'Compact', value: 'compact' }]}
                          className="w-28"
                          disabled={!logConfig?.enabled}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
    </div>
  );
}
