import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Hash,
  MessageSquare,
  RefreshCw,
  Settings2,
  Shield,
  Sparkles,
  Ticket,
  Users,
} from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge, PageSkeleton, SaveBar, Select } from '@/components/ui/Shared';
import { Switch } from '@/components/ui/Switch';
import { realApiClient } from '@/lib/api';
import { toChannelOptions } from '@/lib/channels';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/store/useAppStore';
import type { ModuleConfig, SetupSummary } from '@/types';

function emptyModuleConfig(): ModuleConfig {
  return {
    enabled: true,
    settings: {},
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

interface SelectFieldProps {
  label: string;
  value: string;
  options: { label: string; value: string }[];
  placeholder: string;
  onChange: (value: string) => void;
}

function SelectField({ label, value, options, placeholder, onChange }: SelectFieldProps) {
  return (
    <div>
      <label className="text-sm font-medium text-slate-700 mb-1.5 block">{label}</label>
      <Select value={value} onChange={onChange} options={options} placeholder={placeholder} />
    </div>
  );
}

export function Setup() {
  const {
    activeGuildId,
    channels,
    config,
    discardChanges,
    error,
    fetchConfig,
    saveConfig,
    configDirty,
    roles,
    setError,
    updateConfigLocal,
  } = useAppStore();

  const [summary, setSummary] = useState<SetupSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [quickstartRunning, setQuickstartRunning] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const channelOptions = useMemo(() => toChannelOptions(channels), [channels]);
  const categoryOptions = useMemo(
    () =>
      channels
        .filter((channel) => channel.type === 4)
        .map((channel) => ({ label: channel.name, value: channel.id })),
    [channels],
  );
  const roleOptions = useMemo(
    () =>
      roles
        .filter((role) => !role.managed)
        .sort((left, right) => right.position - left.position)
        .map((role) => ({ label: role.name, value: role.id })),
    [roles],
  );

  useEffect(() => {
    if (!activeGuildId) {
      setSummary(null);
      return;
    }

    let cancelled = false;
    const loadSummary = async () => {
      setSummaryLoading(true);
      try {
        const nextSummary = await realApiClient.getSetupSummary(activeGuildId);
        if (!cancelled) {
          setSummary(nextSummary);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load setup summary');
        }
      } finally {
        if (!cancelled) {
          setSummaryLoading(false);
        }
      }
    };

    void loadSummary();
    return () => {
      cancelled = true;
    };
  }, [activeGuildId, config?.updatedAt, setError]);

  if (!config) {
    return <PageSkeleton />;
  }

  const setup = config.setup;

  const getModule = (moduleId: string): ModuleConfig => config.modules[moduleId] || emptyModuleConfig();

  const updateSetup = (partial: Partial<typeof setup>) => {
    updateConfigLocal({
      setup: {
        ...config.setup,
        ...partial,
      },
    });
  };

  const updateModuleSetting = (moduleId: string, key: string, value: unknown) => {
    const current = getModule(moduleId);
    updateConfigLocal({
      modules: {
        ...config.modules,
        [moduleId]: {
          ...current,
          settings: {
            ...current.settings,
            [key]: value,
          },
        },
      },
    });
  };

  const updateModuleEnabled = (moduleId: string, enabled: boolean) => {
    const current = getModule(moduleId);
    updateConfigLocal({
      modules: {
        ...config.modules,
        [moduleId]: {
          ...current,
          enabled,
        },
      },
    });
  };

  const moduleSettingValue = (moduleId: string, key: string): string => {
    const value = getModule(moduleId).settings[key];
    return typeof value === 'string' ? value : '';
  };

  const moduleEnabledValue = (moduleId: string): boolean => Boolean(getModule(moduleId).enabled);

  const handleSave = async () => {
    setSaving(true);
    setActionMessage(null);
    try {
      await saveConfig();
      setActionMessage('Setup settings saved.');
    } catch {
      // handled in store
    } finally {
      setSaving(false);
    }
  };

  const handleQuickstart = async () => {
    if (!activeGuildId) {
      return;
    }

    setQuickstartRunning(true);
    setActionMessage(null);
    try {
      const result = await realApiClient.runSetupQuickstart(activeGuildId);
      await fetchConfig(activeGuildId);
      setSummary(result.summary);
      setError(null);
      setActionMessage(
        `Quickstart created ${result.createdRoles.length} role(s), ${result.createdChannels.length} channel/category item(s), and synced verification access on ${result.permissionUpdates} channel(s).`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Quickstart failed');
    } finally {
      setQuickstartRunning(false);
    }
  };

  const applyRecommendedToggles = () => {
    const recommended: Record<string, boolean> = {
      logging: true,
      automod: true,
      antiraid: false,
      verification: false,
      tickets: false,
      modmail: false,
      aimod: false,
      whitelist: false,
    };

    const nextModules = { ...config.modules };
    for (const [moduleId, enabled] of Object.entries(recommended)) {
      nextModules[moduleId] = {
        ...getModule(moduleId),
        enabled,
      };
    }

    updateConfigLocal({ modules: nextModules });
    setActionMessage('Recommended module toggles applied locally. Save when ready.');
  };

  const summaryPercent = summary?.percent ?? 0;
  const summaryComplete = summary?.complete ?? 0;
  const summaryTotal = summary?.total ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Setup</h1>
          <p className="text-slate-500 mt-1">
            Configure the server-wide foundation for roles, channels, logs, verification, tickets, and other core bot systems.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button
            variant="outline"
            className="gap-2"
            onClick={applyRecommendedToggles}
          >
            <Sparkles className="w-4 h-4" />
            Apply Recommended Toggles
          </Button>
          <Button
            className="gap-2"
            onClick={handleQuickstart}
            disabled={!activeGuildId || quickstartRunning}
          >
            <RefreshCw className={cn('w-4 h-4', quickstartRunning && 'animate-spin')} />
            {quickstartRunning ? 'Creating Core Roles...' : 'Create Core Roles'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="xl:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
                <Settings2 className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Setup Progress</CardTitle>
                <CardDescription>Track how much of the core server configuration is in place.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant={summaryPercent >= 90 ? 'success' : summaryPercent >= 50 ? 'warning' : 'danger'}>
                {summaryLoading ? 'Refreshing...' : `${summaryPercent}% complete`}
              </Badge>
              <Badge variant="info">
                {summaryComplete}/{summaryTotal} checks complete
              </Badge>
              {summary?.setupComplete && <Badge variant="success">Setup marked complete</Badge>}
            </div>

            <div className="h-3 rounded-full bg-cream-100 overflow-hidden">
              <div
                className={cn(
                  'h-full transition-all',
                  summaryPercent >= 90 ? 'bg-emerald-500' : summaryPercent >= 50 ? 'bg-amber-500' : 'bg-red-500',
                )}
                style={{ width: `${summaryPercent}%` }}
              />
            </div>

            {actionMessage && (
              <div className="rounded-2xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-700">
                {actionMessage}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="rounded-2xl border border-cream-200 bg-cream-50 p-4">
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  <span className="text-sm font-medium">Completed</span>
                </div>
                <div className="mt-2 text-2xl font-display font-bold text-slate-800">{summaryComplete}</div>
              </div>
              <div className="rounded-2xl border border-cream-200 bg-cream-50 p-4">
                <div className="flex items-center gap-2 text-slate-600">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  <span className="text-sm font-medium">Remaining</span>
                </div>
                <div className="mt-2 text-2xl font-display font-bold text-slate-800">
                  {Math.max(0, summaryTotal - summaryComplete)}
                </div>
              </div>
              <div className="rounded-2xl border border-cream-200 bg-cream-50 p-4">
                <div className="flex items-center gap-2 text-slate-600">
                  <Bot className="w-4 h-4 text-indigo-500" />
                  <span className="text-sm font-medium">Recommended Flow</span>
                </div>
                <div className="mt-2 text-sm text-slate-600">
                  Create core roles, route channels manually, then enable protections.
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Recommended Order</CardTitle>
                <CardDescription>Use this sequence to avoid partial setup states.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {[ 
              'Create the core safety roles only.',
              'Assign staff hierarchy and safety roles.',
              'Route logs, tickets, modmail, and verification channels.',
              'Turn modules on only after their routes and roles are set.',
            ].map((item, index) => (
              <div key={item} className="flex gap-3 rounded-2xl border border-cream-200 bg-cream-50 p-3">
                <div className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center shrink-0">
                  {index + 1}
                </div>
                <p className="text-sm text-slate-700">{item}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-red-50 text-red-600 rounded-xl">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Staff Hierarchy</CardTitle>
                <CardDescription>Map the moderation ladder used by the bot.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectField label="Owner Role" value={setup.ownerRole} options={roleOptions} placeholder="Select owner role" onChange={(value) => updateSetup({ ownerRole: value })} />
            <SelectField label="Manager Role" value={setup.managerRole} options={roleOptions} placeholder="Select manager role" onChange={(value) => updateSetup({ managerRole: value })} />
            <SelectField label="Admin Role" value={setup.adminRole} options={roleOptions} placeholder="Select admin role" onChange={(value) => updateSetup({ adminRole: value })} />
            <SelectField label="Supervisor Role" value={setup.supervisorRole} options={roleOptions} placeholder="Select supervisor role" onChange={(value) => updateSetup({ supervisorRole: value })} />
            <SelectField label="Senior Moderator Role" value={setup.seniorModRole} options={roleOptions} placeholder="Select senior mod role" onChange={(value) => updateSetup({ seniorModRole: value })} />
            <SelectField label="Moderator Role" value={setup.moderatorRole} options={roleOptions} placeholder="Select moderator role" onChange={(value) => updateSetup({ moderatorRole: value })} />
            <SelectField label="Trial Moderator Role" value={setup.trialModRole} options={roleOptions} placeholder="Select trial mod role" onChange={(value) => updateSetup({ trialModRole: value })} />
            <SelectField label="Staff Role" value={setup.staffRole} options={roleOptions} placeholder="Select staff role" onChange={(value) => updateSetup({ staffRole: value })} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-amber-50 text-amber-600 rounded-xl">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">System Roles</CardTitle>
                <CardDescription>Roles the bot uses for moderation and recovery flows.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectField label="Muted Role" value={setup.mutedRole} options={roleOptions} placeholder="Select muted role" onChange={(value) => updateSetup({ mutedRole: value })} />
            <SelectField label="Quarantine Role" value={setup.quarantineRole} options={roleOptions} placeholder="Select quarantine role" onChange={(value) => updateSetup({ quarantineRole: value })} />
            <SelectField label="Logs Access Role" value={setup.logsAccessRole} options={roleOptions} placeholder="Select logs access role" onChange={(value) => updateSetup({ logsAccessRole: value })} />
            <SelectField label="Bypass Role" value={setup.bypassRole} options={roleOptions} placeholder="Select bypass role" onChange={(value) => updateSetup({ bypassRole: value })} />
            <SelectField label="Whitelisted Role" value={setup.whitelistedRole} options={roleOptions} placeholder="Select whitelisted role" onChange={(value) => updateSetup({ whitelistedRole: value })} />
            <SelectField label="Auto Join Role" value={setup.autoRole} options={roleOptions} placeholder="Select auto join role" onChange={(value) => updateSetup({ autoRole: value })} />
            <SelectField label="Verified Role" value={setup.verifiedRole} options={roleOptions} placeholder="Select verified role" onChange={(value) => updateSetup({ verifiedRole: value })} />
            <SelectField label="Unverified Role" value={setup.unverifiedRole} options={roleOptions} placeholder="Select unverified role" onChange={(value) => updateSetup({ unverifiedRole: value })} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
                <Hash className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Welcome and Staff Spaces</CardTitle>
                <CardDescription>Flat setup fields that are not covered by the module pages.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectField label="Welcome Channel" value={setup.welcomeChannel} options={channelOptions} placeholder="Select welcome channel" onChange={(value) => updateSetup({ welcomeChannel: value })} />
            <SelectField label="Staff Chat" value={setup.staffChatChannel} options={channelOptions} placeholder="Select staff chat" onChange={(value) => updateSetup({ staffChatChannel: value })} />
            <SelectField label="Staff Commands" value={setup.staffCommandsChannel} options={channelOptions} placeholder="Select staff commands channel" onChange={(value) => updateSetup({ staffCommandsChannel: value })} />
            <SelectField label="Staff Announcements" value={setup.staffAnnouncementsChannel} options={channelOptions} placeholder="Select staff announcements channel" onChange={(value) => updateSetup({ staffAnnouncementsChannel: value })} />
            <SelectField label="Staff Guide" value={setup.staffGuideChannel} options={channelOptions} placeholder="Select staff guide channel" onChange={(value) => updateSetup({ staffGuideChannel: value })} />
            <SelectField label="Staff Updates" value={setup.staffUpdatesChannel} options={channelOptions} placeholder="Select staff updates channel" onChange={(value) => updateSetup({ staffUpdatesChannel: value })} />
            <SelectField label="Staff Sanctions" value={setup.staffSanctionsChannel} options={channelOptions} placeholder="Select staff sanctions channel" onChange={(value) => updateSetup({ staffSanctionsChannel: value })} />
            <SelectField label="Supervisor Logs" value={setup.supervisorLogChannel} options={channelOptions} placeholder="Select supervisor logs channel" onChange={(value) => updateSetup({ supervisorLogChannel: value })} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
                <MessageSquare className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Moderation and Verification Routing</CardTitle>
                <CardDescription>Choose the channels used by the core moderation systems.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectField label="Verification Channel" value={moduleSettingValue('verification', 'verifyChannel')} options={channelOptions} placeholder="Select verification channel" onChange={(value) => updateModuleSetting('verification', 'verifyChannel', value)} />
            <SelectField label="Verification Logs" value={moduleSettingValue('verification', 'verifyLogChannel')} options={channelOptions} placeholder="Select verification log channel" onChange={(value) => updateModuleSetting('verification', 'verifyLogChannel', value)} />
            <SelectField label="Moderation Logs" value={moduleSettingValue('logging', 'modChannel')} options={channelOptions} placeholder="Select mod logs" onChange={(value) => updateModuleSetting('logging', 'modChannel', value)} />
            <SelectField label="Audit Logs" value={moduleSettingValue('logging', 'auditChannel')} options={channelOptions} placeholder="Select audit logs" onChange={(value) => updateModuleSetting('logging', 'auditChannel', value)} />
            <SelectField label="Message Logs" value={moduleSettingValue('logging', 'messageChannel')} options={channelOptions} placeholder="Select message logs" onChange={(value) => updateModuleSetting('logging', 'messageChannel', value)} />
            <SelectField label="Voice Logs" value={moduleSettingValue('logging', 'voiceChannel')} options={channelOptions} placeholder="Select voice logs" onChange={(value) => updateModuleSetting('logging', 'voiceChannel', value)} />
            <SelectField label="AutoMod Logs" value={moduleSettingValue('logging', 'automodChannel')} options={channelOptions} placeholder="Select automod logs" onChange={(value) => updateModuleSetting('logging', 'automodChannel', value)} />
            <SelectField label="Report Logs" value={moduleSettingValue('logging', 'reportChannel')} options={channelOptions} placeholder="Select report logs" onChange={(value) => updateModuleSetting('logging', 'reportChannel', value)} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-purple-50 text-purple-600 rounded-xl">
                <Ticket className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Support Routing</CardTitle>
                <CardDescription>Configure the categories and log channels used by tickets and modmail.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectField label="Ticket Category" value={moduleSettingValue('tickets', 'category')} options={categoryOptions} placeholder="Select ticket category" onChange={(value) => updateModuleSetting('tickets', 'category', value)} />
            <SelectField label="Ticket Log Channel" value={moduleSettingValue('tickets', 'logChannel')} options={channelOptions} placeholder="Select ticket log channel" onChange={(value) => updateModuleSetting('tickets', 'logChannel', value)} />
            <SelectField label="Modmail Category" value={moduleSettingValue('modmail', 'categoryId')} options={categoryOptions} placeholder="Select modmail category" onChange={(value) => updateModuleSetting('modmail', 'categoryId', value)} />
            <SelectField label="Modmail Log Channel" value={moduleSettingValue('modmail', 'logChannel')} options={channelOptions} placeholder="Select modmail log channel" onChange={(value) => updateModuleSetting('modmail', 'logChannel', value)} />
            <SelectField label="Forum Alerts" value={moduleSettingValue('forum_moderation', 'alertsChannel')} options={channelOptions} placeholder="Select forum alerts channel" onChange={(value) => updateModuleSetting('forum_moderation', 'alertsChannel', value)} />
            <SelectField label="AI Confirmation Channel" value={moduleSettingValue('aimod', 'confirmationChannel')} options={channelOptions} placeholder="Select AI confirmation channel" onChange={(value) => updateModuleSetting('aimod', 'confirmationChannel', value)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Feature Toggles</CardTitle>
                <CardDescription>Turn modules on only after their required roles and channels are mapped.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { id: 'logging', label: 'Logging', help: 'Enable route-aware event logging.' },
              { id: 'automod', label: 'AutoMod', help: 'Enable automated content moderation rules.' },
              { id: 'antiraid', label: 'Anti-Raid', help: 'Enable raid detection and response.' },
              { id: 'verification', label: 'Verification', help: 'Enable verification commands and flows.' },
              { id: 'tickets', label: 'Tickets', help: 'Enable support ticket creation and handling.' },
              { id: 'modmail', label: 'Modmail', help: 'Enable DM-to-staff ticket bridging.' },
              { id: 'aimod', label: 'AI Moderation', help: 'Enable AI moderation workflows.' },
              { id: 'whitelist', label: 'Whitelist', help: 'Restrict access to approved members only.' },
            ].map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-4 rounded-2xl border border-cream-200 bg-cream-50 p-4">
                <div>
                  <h4 className="text-sm font-semibold text-slate-800">{item.label}</h4>
                  <p className="text-xs text-slate-500 mt-0.5">{item.help}</p>
                </div>
                <Switch checked={moduleEnabledValue(item.id)} onCheckedChange={(checked) => updateModuleEnabled(item.id, checked)} />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-cream-100 text-slate-600 rounded-xl">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Checklist</CardTitle>
              <CardDescription>Live view of what the backend still considers missing.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {summaryLoading && !summary ? (
            <div className="text-sm text-slate-500">Loading setup summary...</div>
          ) : !summary ? (
            <div className="text-sm text-slate-500">No setup summary available yet.</div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {summary.sections.map((section) => (
                <div key={section.id} className="rounded-2xl border border-cream-200 bg-cream-50 p-4">
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <h3 className="text-sm font-semibold text-slate-800">{section.label}</h3>
                    <Badge variant={section.complete === section.total ? 'success' : 'warning'}>
                      {section.complete}/{section.total}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    {section.items.map((item) => (
                      <div key={item.key} className="flex items-start justify-between gap-3 text-sm">
                        <div className="flex items-start gap-2">
                          <span className={cn('mt-0.5 w-2 h-2 rounded-full shrink-0', item.configured ? 'bg-emerald-500' : 'bg-red-400')} />
                          <span className="text-slate-700">{item.label}</span>
                        </div>
                        <span className={cn('text-xs shrink-0', item.configured ? 'text-emerald-700' : 'text-slate-400')}>
                          {item.value || 'Missing'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
    </div>
  );
}
