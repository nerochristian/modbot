import { useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Switch } from '@/components/ui/Switch';
import { Button } from '@/components/ui/Button';
import { Badge, SaveBar, PageSkeleton } from '@/components/ui/Shared';
import { ShieldAlert, Lock, UserPlus, ShieldCheck, AlertOctagon } from 'lucide-react';
import { cn } from '@/lib/utils';

export function AntiRaid() {
  const { config, updateConfigLocal, saveConfig, discardChanges, configDirty, error } = useAppStore();
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try { await saveConfig(); } catch { /* handled */ }
    setSaving(false);
  };

  if (!config) return <PageSkeleton />;

  const raidConfig = config.modules.antiraid;
  const raidSettings = raidConfig?.settings || {};

  const toggleRaid = () => {
    if (!raidConfig) return;
    updateConfigLocal({
      modules: {
        ...config.modules,
        antiraid: { ...raidConfig, enabled: !raidConfig.enabled },
      },
    });
  };

  const updateSetting = (key: string, value: unknown) => {
    if (!raidConfig) return;
    updateConfigLocal({
      modules: {
        ...config.modules,
        antiraid: { ...raidConfig, settings: { ...raidConfig.settings, [key]: value } },
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Anti-Raid</h1>
          <p className="text-slate-500 mt-1">Protect your server from coordinated attacks and bot raids.</p>
        </div>
        <Button variant="danger" className="gap-2 shadow-sm">
          <AlertOctagon className="w-5 h-5" />
          Panic Mode
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className={cn(!raidConfig?.enabled && 'opacity-60')}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-red-50 text-red-600 rounded-xl">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <CardTitle className="text-lg">Join Rate Detection</CardTitle>
                  <CardDescription>Trigger defenses when too many users join at once.</CardDescription>
                </div>
              </div>
              <Switch checked={raidConfig?.enabled ?? false} onCheckedChange={toggleRaid} />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-slate-700 mb-1.5 block">Join Threshold</label>
                <input
                  type="number"
                  value={Number(raidSettings.joinThreshold) || 10}
                  onChange={(e) => updateSetting('joinThreshold', Number(e.target.value))}
                  min={3}
                  max={50}
                  className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700 mb-1.5 block">Time Window (s)</label>
                <input
                  type="number"
                  value={Number(raidSettings.timeWindow) || 5}
                  onChange={(e) => updateSetting('timeWindow', Number(e.target.value))}
                  min={1}
                  max={30}
                  className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
                <Lock className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Auto-Defenses</CardTitle>
                <CardDescription>Actions to take when a raid is detected.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { key: 'lockdownEnabled', name: 'Auto-Lockdown', desc: 'Prevent new users from seeing channels', icon: Lock },
              { key: 'kickNewAccounts', name: 'Kick New Accounts', desc: 'Kick accounts younger than threshold', icon: UserPlus },
            ].map(def => (
              <div key={def.key} className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-white rounded-lg border border-cream-200 text-slate-500">
                    <def.icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm text-slate-800">{def.name}</h4>
                    <p className="text-xs text-slate-500">{def.desc}</p>
                  </div>
                </div>
                <Switch
                  checked={Boolean(raidSettings[def.key])}
                  onCheckedChange={(v) => updateSetting(def.key, v)}
                />
              </div>
            ))}

            {raidSettings.kickNewAccounts && (
              <div className="pl-12">
                <label className="text-sm font-medium text-slate-700 mb-1.5 block">Min Account Age (hours)</label>
                <input
                  type="number"
                  value={Number(raidSettings.accountAgeHours) || 24}
                  onChange={(e) => updateSetting('accountAgeHours', Number(e.target.value))}
                  min={1}
                  max={720}
                  className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
    </div>
  );
}
