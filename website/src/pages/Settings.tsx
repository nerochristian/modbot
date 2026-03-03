import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Switch } from '@/components/ui/Switch';
import { Button } from '@/components/ui/Button';
import { Badge, SaveBar, PageSkeleton } from '@/components/ui/Shared';
import { ConfirmDialog } from '@/components/ui/Modal';
import { useAppStore } from '@/store/useAppStore';
import { realApiClient } from '@/lib/api';
import { Settings as SettingsIcon, Key, Database, RefreshCw, AlertTriangle, Download, Upload, Clock, Shield } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

export function Settings() {
  const { config, activeGuildId, updateConfigLocal, saveConfig, discardChanges, configDirty, error, setError } = useAppStore();
  const [saving, setSaving] = useState(false);
  const [resetDialog, setResetDialog] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try { await saveConfig(); } catch { /* handled */ }
    setSaving(false);
  };

  if (!config) return <PageSkeleton />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Settings</h1>
        <p className="text-slate-500 mt-1">General bot configuration, data management, and danger zone.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
                <SettingsIcon className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">General</CardTitle>
                <CardDescription>Core bot settings for this server.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">Command Prefix</label>
              <input
                type="text"
                value={config.prefix}
                onChange={(e) => updateConfigLocal({ prefix: e.target.value })}
                maxLength={5}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">Default Cooldown (seconds)</label>
              <input
                type="number"
                value={config.defaultCooldown}
                onChange={(e) => updateConfigLocal({ defaultCooldown: Number(e.target.value) })}
                min={0}
                max={60}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">Timezone</label>
              <select
                value={config.timezone}
                onChange={(e) => updateConfigLocal({ timezone: e.target.value })}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              >
                <option value="UTC">UTC</option>
                <option value="US/Eastern">US/Eastern</option>
                <option value="US/Pacific">US/Pacific</option>
                <option value="Europe/London">Europe/London</option>
                <option value="Europe/Berlin">Europe/Berlin</option>
                <option value="Asia/Tokyo">Asia/Tokyo</option>
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Sync & Status */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl">
                <RefreshCw className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Sync & Status</CardTitle>
                <CardDescription>Synchronize bot state with Discord.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <div>
                <h4 className="font-semibold text-sm text-slate-800">Slash Commands</h4>
                <p className="text-xs text-slate-500 mt-0.5">Sync slash command permissions with Discord</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                disabled={syncing}
                onClick={async () => {
                  if (!activeGuildId) return;
                  setSyncing(true);
                  try {
                    await realApiClient.syncCommands(activeGuildId);
                    setError(null);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : 'Failed to sync commands');
                  } finally {
                    setSyncing(false);
                  }
                }}
              >
                <RefreshCw className={cn('w-4 h-4', syncing && 'animate-spin')} />
                {syncing ? 'Syncing...' : 'Sync'}
              </Button>
            </div>

            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <div>
                <h4 className="font-semibold text-sm text-slate-800">Config Version</h4>
                <p className="text-xs text-slate-500 mt-0.5">Current configuration version</p>
              </div>
              <Badge variant="info">v{config.version}</Badge>
            </div>

            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <div>
                <h4 className="font-semibold text-sm text-slate-800">Last Updated</h4>
                <p className="text-xs text-slate-500 mt-0.5">When config was last saved</p>
              </div>
              <span className="text-sm text-slate-600 font-medium">
                {new Date(config.updatedAt).toLocaleDateString()}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Data Management */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-amber-50 text-amber-600 rounded-xl">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Data Management</CardTitle>
                <CardDescription>Export, import, and back up configuration.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Button variant="outline" className="gap-2">
                <Download className="w-4 h-4" />
                Export Config
              </Button>
              <Button variant="outline" className="gap-2">
                <Upload className="w-4 h-4" />
                Import Config
              </Button>
            </div>
            <Button variant="outline" className="gap-2 w-full">
              <Clock className="w-4 h-4" />
              Create Snapshot
            </Button>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-200">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-red-50 text-red-600 rounded-xl">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg text-red-700">Danger Zone</CardTitle>
                <CardDescription>Irreversible actions. Proceed with caution.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between p-4 bg-red-50 rounded-2xl border border-red-200">
              <div>
                <h4 className="font-semibold text-sm text-red-900">Reset All Configuration</h4>
                <p className="text-xs text-red-700 mt-0.5">Resets all settings to their default values.</p>
              </div>
              <Button variant="danger" size="sm" onClick={() => setResetDialog(true)}>
                Reset
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <ConfirmDialog
        open={resetDialog}
        onClose={() => setResetDialog(false)}
        onConfirm={() => { setResetDialog(false); }}
        title="Reset Configuration"
        description="This will reset ALL server configuration to default values. This action cannot be undone. Are you absolutely sure?"
        confirmLabel="Yes, Reset Everything"
        danger
      />

      <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
    </div>
  );
}
