import { useState, useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent } from '@/components/ui/Card';
import { Switch } from '@/components/ui/Switch';
import { Button } from '@/components/ui/Button';
import { Badge, SaveBar, SearchInput, PageSkeleton, EmptyState } from '@/components/ui/Shared';
import { Zap, Plus, Settings2, ShieldAlert, AlertTriangle, Filter, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ModuleConfig } from '@/types';

function defaultAutomodConfig(): ModuleConfig {
  return {
    enabled: false,
    settings: {
      antiSpam: true,
      antiLink: true,
      antiInvite: true,
      spamThreshold: 5,
      mentionLimit: 5,
      capsThreshold: 70,
      action: 'warn',
    },
    overrides: {
      allowedChannels: [],
      ignoredChannels: [],
      allowedRoles: [],
      ignoredRoles: [],
      allowedUsers: [],
      ignoredUsers: [],
    },
    loggingRouteOverride: null,
  };
}

export function Automod() {
  const { config, capabilities, updateConfigLocal, saveConfig, discardChanges, configDirty, error } = useAppStore();
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try { await saveConfig(); } catch { /* handled */ }
    setSaving(false);
  };

  if (!capabilities || !config) return <PageSkeleton />;

  const automodConfig = config.modules.automod || defaultAutomodConfig();
  const automodSettings = automodConfig?.settings || {};

  const toggleAutomod = () => {
    updateConfigLocal({
      modules: {
        ...config.modules,
        automod: { ...automodConfig, enabled: !automodConfig.enabled },
      },
    });
  };

  const updateSetting = (key: string, value: unknown) => {
    updateConfigLocal({
      modules: {
        ...config.modules,
        automod: { ...automodConfig, settings: { ...automodConfig.settings, [key]: value } },
      },
    });
  };

  const filterRules = [
    { key: 'antiSpam', name: 'Anti-Spam', desc: 'Block users sending too many messages in a short time', icon: Zap, type: 'danger' as const },
    { key: 'antiLink', name: 'Anti-Link', desc: 'Automatically remove messages containing links', icon: Filter, type: 'warning' as const },
    { key: 'antiInvite', name: 'Anti-Invite', desc: 'Block Discord invite links from being posted', icon: ShieldAlert, type: 'danger' as const },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Auto Moderation</h1>
          <p className="text-slate-500 mt-1">Configure automated message filtering and content moderation rules.</p>
        </div>
        <div className="flex items-center gap-3 bg-cream-50 px-4 py-2 rounded-xl border border-cream-200">
          <span className="text-sm font-medium text-slate-600">Automod System</span>
          <Switch checked={automodConfig?.enabled ?? false} onCheckedChange={toggleAutomod} />
        </div>
      </div>

      {!automodConfig?.enabled ? (
        <EmptyState
          icon={<Zap className="w-8 h-8" />}
          title="Automod Disabled"
          description="Enable the automod system to start configuring content moderation rules."
          action={<Button onClick={toggleAutomod}>Enable Automod</Button>}
        />
      ) : (
        <div className="space-y-6">
          {/* Filter Rules */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {filterRules.map(rule => {
              const enabled = Boolean(automodSettings[rule.key]);
              return (
                <Card key={rule.key} className={cn('transition-all', !enabled && 'opacity-60')}>
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div className={cn(
                        'p-2.5 rounded-xl',
                        enabled
                          ? rule.type === 'danger' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
                          : 'bg-cream-100 text-slate-400'
                      )}>
                        <rule.icon className="w-5 h-5" />
                      </div>
                      <Switch checked={enabled} onCheckedChange={(v) => updateSetting(rule.key, v)} />
                    </div>
                    <h3 className="font-display font-semibold text-slate-800 mb-1">{rule.name}</h3>
                    <p className="text-sm text-slate-500">{rule.desc}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Thresholds */}
          <Card>
            <CardContent className="p-6">
              <h3 className="font-display font-semibold text-slate-800 mb-4">Thresholds & Limits</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1.5 block">Spam Threshold</label>
                  <p className="text-xs text-slate-500 mb-2">Messages within 3 second window</p>
                  <input
                    type="number"
                    value={Number(automodSettings.spamThreshold) || 5}
                    onChange={(e) => updateSetting('spamThreshold', Number(e.target.value))}
                    min={2}
                    max={20}
                    className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1.5 block">Mention Limit</label>
                  <p className="text-xs text-slate-500 mb-2">Maximum mentions per message</p>
                  <input
                    type="number"
                    value={Number(automodSettings.mentionLimit) || 5}
                    onChange={(e) => updateSetting('mentionLimit', Number(e.target.value))}
                    min={1}
                    max={50}
                    className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1.5 block">Max Caps %</label>
                  <p className="text-xs text-slate-500 mb-2">Maximum uppercase percentage</p>
                  <input
                    type="number"
                    value={Number(automodSettings.capsThreshold) || 70}
                    onChange={(e) => updateSetting('capsThreshold', Number(e.target.value))}
                    min={0}
                    max={100}
                    className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Default Action */}
          <Card>
            <CardContent className="p-6">
              <h3 className="font-display font-semibold text-slate-800 mb-4">Default Action</h3>
              <p className="text-sm text-slate-500 mb-4">What happens when automod detects a violation.</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {['warn', 'delete', 'timeout', 'kick'].map(action => (
                  <button
                    key={action}
                    onClick={() => updateSetting('action', action)}
                    className={cn(
                      'p-3 rounded-xl border text-sm font-medium transition-all text-center capitalize',
                      automodSettings.action === action
                        ? 'bg-indigo-50 border-indigo-200 text-indigo-700 shadow-sm'
                        : 'bg-cream-50 border-cream-200 text-slate-600 hover:border-indigo-200 hover:bg-indigo-50'
                    )}
                  >
                    {action}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
    </div>
  );
}
