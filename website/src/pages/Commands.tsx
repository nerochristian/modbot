import { useCallback, useEffect, useMemo, useState } from 'react';
import { Command, HelpCircle, RefreshCw, Settings2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { Select, MultiSelect, Tabs, SaveBar, SearchInput, PageSkeleton, EmptyState, Badge } from '@/components/ui/Shared';
import { Switch } from '@/components/ui/Switch';
import { realApiClient } from '@/lib/api';
import { resolveCommandProfile, STAFF_LEVEL_OPTIONS, CHANNEL_MODE_OPTIONS, RESPONSE_VISIBILITY_OPTIONS, type CommandExtraField, type CommandTabId } from '@/lib/commandProfiles';
import { useAppStore } from '@/store/useAppStore';
import type { CommandCapability, CommandConfig } from '@/types';
import { cn } from '@/lib/utils';
import { toChannelOptions } from '@/lib/channels';

const PERMISSION_OPTIONS = [
  { label: 'Send Messages', value: 'send_messages' },
  { label: 'Read Message History', value: 'read_message_history' },
  { label: 'Moderate Members', value: 'moderate_members' },
  { label: 'Manage Messages', value: 'manage_messages' },
  { label: 'Kick Members', value: 'kick_members' },
  { label: 'Ban Members', value: 'ban_members' },
  { label: 'Manage Nicknames', value: 'manage_nicknames' },
  { label: 'Manage Roles', value: 'manage_roles' },
  { label: 'Manage Channels', value: 'manage_channels' },
  { label: 'Manage Guild', value: 'manage_guild' },
  { label: 'Manage Threads', value: 'manage_threads' },
  { label: 'Manage Webhooks', value: 'manage_webhooks' },
  { label: 'Manage Expressions', value: 'manage_expressions' },
  { label: 'Mute Members', value: 'mute_members' },
  { label: 'Move Members', value: 'move_members' },
  { label: 'View Audit Log', value: 'view_audit_log' },
  { label: 'Administrator', value: 'administrator' },
  { label: 'Custom: Bot Permission', value: 'custom_bot_permission' },
];

const DEFAULT_MEMBER_PERMISSION_PRESETS = [
  { label: 'None', value: '' },
  { label: 'Send Messages (2048)', value: '2048' },
  { label: 'Manage Messages (8192)', value: '8192' },
  { label: 'Manage Channels (16)', value: '16' },
  { label: 'Manage Roles (268435456)', value: '268435456' },
  { label: 'Moderate Members (1099511627776)', value: '1099511627776' },
  { label: 'Administrator (8)', value: '8' },
];

function clone<T>(value: T): T {
  if (value === null || value === undefined) return value;
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return value;
  }
}

function mergeCommandConfig(base: CommandConfig, incoming: Partial<CommandConfig> | undefined): CommandConfig {
  if (!incoming) return base;
  return {
    ...base,
    ...incoming,
    overrides: { ...base.overrides, ...(incoming.overrides || {}) },
    cooldown: { ...base.cooldown, ...(incoming.cooldown || {}) },
    rateLimit: { ...base.rateLimit, ...(incoming.rateLimit || {}) },
    logging: { ...base.logging, ...(incoming.logging || {}) },
    visibility: { ...base.visibility, ...(incoming.visibility || {}) },
    cooldownBypassRoles: incoming.cooldownBypassRoles ?? base.cooldownBypassRoles,
    cooldownBypassUsers: incoming.cooldownBypassUsers ?? base.cooldownBypassUsers,
    extras: { ...(base.extras || {}), ...(incoming.extras || {}) },
  };
}

function profileRequiredPermission(commandName: string): string | undefined {
  return resolveCommandProfile(commandName).requiredPermission;
}

function createDefaultCommandConfig(commandName: string, fallbackPermission = 'send_messages'): CommandConfig {
  const profile = resolveCommandProfile(commandName);
  const base: CommandConfig = {
    enabled: true,
    requiredPermission: profile.requiredPermission || fallbackPermission,
    minimumStaffLevel: 'everyone',
    enforceRoleHierarchy: false,
    requireReason: false,
    requireConfirmation: false,
    channelMode: 'enabled_everywhere',
    disableInThreads: false,
    disableInForumPosts: false,
    disableInDMs: false,
    overrides: {
      allowedChannels: [],
      ignoredChannels: [],
      allowedRoles: [],
      ignoredRoles: [],
      allowedUsers: [],
      ignoredUsers: [],
    },
    cooldown: {
      global: 0,
      perUser: 0,
      perGuild: 0,
      perChannel: 0,
    },
    rateLimit: {
      maxPerMinute: 0,
      maxPerHour: 0,
      concurrentLimit: 1,
      maxPerMinuteChannel: 30,
      maxPerMinuteGuild: 300,
    },
    cooldownBypassRoles: [],
    cooldownBypassUsers: [],
    logging: {
      logUsage: true,
      routeOverride: null,
      recordToAuditLog: true,
    },
    visibility: {
      hideFromHelp: false,
      slashEnabled: true,
      prefixEnabled: true,
      hideFromAutocomplete: false,
      defaultResponseVisibility: 'auto',
    },
    disableDuringMaintenanceMode: false,
    disableDuringRaidMode: false,
    syncWithDiscordSlashPermissions: false,
    defaultMemberPermissions: '',
    extras: {},
  };

  const merged = mergeCommandConfig(base, profile.defaults);
  const extras = { ...(merged.extras || {}) };
  for (const field of profile.extraFields) {
    if (extras[field.key] === undefined) {
      extras[field.key] = clone(field.defaultValue);
    }
  }
  merged.extras = extras;
  return merged;
}

function ensureCommandConfig(current: CommandConfig | undefined, commandName: string, fallbackPermission: string): CommandConfig {
  const defaults = createDefaultCommandConfig(commandName, fallbackPermission);
  const merged = mergeCommandConfig(defaults, current);

  if ((!current?.cooldown || current.cooldown.global === undefined) && typeof current?.cooldown?.perGuild === 'number') {
    merged.cooldown.global = current.cooldown.perGuild;
  }
  if ((!current?.rateLimit || current.rateLimit.maxPerMinute === undefined) && typeof current?.rateLimit?.maxPerMinuteChannel === 'number') {
    merged.rateLimit.maxPerMinute = current.rateLimit.maxPerMinuteChannel;
  }
  if (profileRequiredPermission(commandName) && !current?.requiredPermission) {
    merged.requiredPermission = profileRequiredPermission(commandName) as string;
  }

  return merged;
}

function ExtraField({
  field,
  value,
  onChange,
  channels,
  roles,
}: {
  field: CommandExtraField;
  value: unknown;
  onChange: (value: unknown) => void;
  channels: { label: string; value: string }[];
  roles: { label: string; value: string; color?: number }[];
}) {
  if (field.kind === 'boolean') {
    return (
      <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
        <div>
          <h4 className="font-semibold text-sm text-slate-800">{field.label}</h4>
          {field.helpText && <p className="text-xs text-slate-500 mt-0.5">{field.helpText}</p>}
        </div>
        <Switch checked={Boolean(value)} onCheckedChange={(v) => onChange(v)} />
      </div>
    );
  }

  if (field.kind === 'number') {
    return (
      <div>
        <label className="text-sm font-medium text-slate-700 mb-2 block">{field.label}</label>
        <input
          type="number"
          value={typeof value === 'number' ? value : Number(value) || 0}
          onChange={(e) => onChange(Number(e.target.value))}
          min={field.min}
          max={field.max}
          className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
        />
      </div>
    );
  }

  if (field.kind === 'string') {
    return (
      <div>
        <label className="text-sm font-medium text-slate-700 mb-2 block">{field.label}</label>
        <input
          type="text"
          value={String(value || '')}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
        />
      </div>
    );
  }

  if (field.kind === 'textArea') {
    return (
      <div>
        <label className="text-sm font-medium text-slate-700 mb-2 block">{field.label}</label>
        <textarea
          value={String(value || '')}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          placeholder={field.placeholder}
          className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all resize-none"
        />
      </div>
    );
  }

  if (field.kind === 'select') {
    return (
      <div>
        <label className="text-sm font-medium text-slate-700 mb-2 block">{field.label}</label>
        <Select value={String(value || '')} onChange={(v) => onChange(v)} options={field.options || []} />
      </div>
    );
  }

  if (field.kind === 'roleMulti') {
    return (
      <div>
        <label className="text-sm font-medium text-slate-700 mb-2 block">{field.label}</label>
        <MultiSelect
          values={Array.isArray(value) ? (value as string[]) : []}
          onChange={(v) => onChange(v)}
          options={roles}
          placeholder="No roles selected"
        />
      </div>
    );
  }

  if (field.kind === 'channelMulti') {
    return (
      <div>
        <label className="text-sm font-medium text-slate-700 mb-2 block">{field.label}</label>
        <MultiSelect
          values={Array.isArray(value) ? (value as string[]) : []}
          onChange={(v) => onChange(v)}
          options={channels}
          placeholder="No channels selected"
        />
      </div>
    );
  }

  if (field.kind === 'channel') {
    return (
      <div>
        <label className="text-sm font-medium text-slate-700 mb-2 block">{field.label}</label>
        <Select value={String(value || '')} onChange={(v) => onChange(v)} options={channels} placeholder="Select channel" />
      </div>
    );
  }

  if (field.kind === 'role') {
    return (
      <div>
        <label className="text-sm font-medium text-slate-700 mb-2 block">{field.label}</label>
        <Select value={String(value || '')} onChange={(v) => onChange(v)} options={roles.map((r) => ({ label: r.label, value: r.value }))} placeholder="Select role" />
      </div>
    );
  }

  return (
    <StringListInput
      label={field.label}
      values={Array.isArray(value) ? (value as string[]) : []}
      onChange={(v) => onChange(v)}
      placeholder={field.placeholder || 'Add value'}
    />
  );
}

function StringListInput({
  label,
  values,
  onChange,
  placeholder,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState('');

  const addValue = () => {
    const next = draft.trim();
    if (!next) return;
    if (!values.includes(next)) {
      onChange([...values, next]);
    }
    setDraft('');
  };

  return (
    <div>
      <label className="text-sm font-medium text-slate-700 mb-2 block">{label}</label>
      <div className="space-y-2">
        {values.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {values.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onChange(values.filter((entry) => entry !== item))}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-indigo-50 border border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-100"
              >
                {item}
                <span className="text-indigo-500">x</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500">No values added.</p>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addValue();
              }
            }}
            placeholder={placeholder}
            className="flex-1 bg-cream-50 border border-cream-300 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
          />
          <Button variant="outline" size="sm" onClick={addValue}>Add</Button>
        </div>
      </div>
    </div>
  );
}
export function Commands() {
  const { capabilities, config, activeGuildId, channels, roles, updateConfigLocal, saveConfig, discardChanges, configDirty, error, setError } = useAppStore();
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [settingsModal, setSettingsModal] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showSyncBanner, setShowSyncBanner] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const commands = useMemo(() => {
    if (capabilities?.commands?.length) {
      return capabilities.commands;
    }
    if (!config) {
      return [];
    }
    return Object.entries(config.commands).map(([name, commandConfig]) => ({
      name,
      group: 'General',
      description: '',
      type: 'both' as const,
      supportsOverrides: true,
      defaultRequiredPermission: commandConfig.requiredPermission || profileRequiredPermission(name) || 'send_messages',
      premiumTier: 'free' as const,
      settingsSchema: [],
    }));
  }, [capabilities?.commands, config]);

  useEffect(() => {
    if (!activeGuildId) {
      setShowSyncBanner(false);
      return;
    }
    realApiClient
      .getSyncStatus(activeGuildId)
      .then((status) => {
        setShowSyncBanner(Boolean(status.syncRequired));
      })
      .catch(() => {
        setShowSyncBanner(false);
      });
  }, [activeGuildId]);

  const categories = useMemo(() => {
    const groups = new Map<string, CommandCapability[]>();
    for (const cmd of commands) {
      const group = cmd.group || 'General';
      const list = groups.get(group) || [];
      list.push(cmd);
      groups.set(group, list);
    }
    return groups;
  }, [commands]);

  const categoryTabs = useMemo(() => {
    const tabs = [{ id: 'all', label: 'All', count: commands.length }];
    for (const [group, cmds] of categories) {
      tabs.push({ id: group, label: group, count: cmds.length });
    }
    return tabs;
  }, [categories, commands.length]);

  const filteredCommands = useMemo(() => {
    let list = commands;
    if (activeCategory !== 'all') {
      list = list.filter((c) => (c.group || 'General') === activeCategory);
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((c) => c.name.toLowerCase().includes(q) || c.description.toLowerCase().includes(q));
    }
    return list;
  }, [commands, activeCategory, search]);

  const commandCapabilityByName = useMemo(() => {
    const map = new Map<string, CommandCapability>();
    for (const command of commands) {
      map.set(command.name, command);
    }
    return map;
  }, [commands]);

  const toggleCommand = useCallback((name: string) => {
    if (!config) return;
    const current = ensureCommandConfig(
      config.commands[name],
      name,
      commandCapabilityByName.get(name)?.defaultRequiredPermission || 'send_messages',
    );
    updateConfigLocal({
      commands: {
        ...config.commands,
        [name]: { ...current, enabled: !current.enabled },
      },
    });
  }, [commandCapabilityByName, config, updateConfigLocal]);

  const batchToggle = useCallback((action: 'enable' | 'disable') => {
    if (!config) return;
    const updates = { ...config.commands };
    for (const cmd of filteredCommands) {
      const current = ensureCommandConfig(updates[cmd.name], cmd.name, cmd.defaultRequiredPermission);
      updates[cmd.name] = { ...current, enabled: action === 'enable' };
    }
    updateConfigLocal({ commands: updates });
  }, [config, filteredCommands, updateConfigLocal]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveConfig();
    } catch {
      // handled in store
    }
    setSaving(false);
  };

  const handleSync = async () => {
    if (!activeGuildId) return;
    setSyncing(true);
    try {
      await realApiClient.syncCommands(activeGuildId);
      setShowSyncBanner(false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to sync commands');
    } finally {
      setSyncing(false);
    }
  };

  if (!config) return <PageSkeleton />;

  const channelOptions = toChannelOptions(channels);
  const roleOptions = roles
    .filter((r) => !r.managed)
    .map((r) => ({ label: r.name, value: r.id, color: r.color }));

  return (
    <div className="space-y-6">
      {showSyncBanner && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center gap-4">
          <div className="p-2 bg-amber-100 rounded-xl text-amber-600">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-amber-900 text-sm">Slash Command Sync Required</h4>
            <p className="text-xs text-amber-700 mt-0.5">
              Command permissions changed. Sync with Discord to apply updates.
            </p>
          </div>
          <Button onClick={handleSync} disabled={syncing} size="sm" className="gap-2">
            <RefreshCw className={cn('w-4 h-4', syncing && 'animate-spin')} />
            {syncing ? 'Syncing...' : 'Sync Now'}
          </Button>
        </div>
      )}

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Commands</h1>
          <p className="text-slate-500 mt-1">Manage bot commands - toggle, configure permissions, and set command-specific controls.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => batchToggle('enable')}>Enable All</Button>
          <Button variant="outline" size="sm" onClick={() => batchToggle('disable')}>Disable All</Button>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Search commands..." className="w-72" />
        <Tabs tabs={categoryTabs} activeTab={activeCategory} onChange={setActiveCategory} />
      </div>

      {filteredCommands.length === 0 ? (
        <EmptyState
          icon={<Command className="w-8 h-8" />}
          title="No commands found"
          description="No commands match your current search or filters."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredCommands.map((cmd) => {
            const cmdConfig = ensureCommandConfig(config.commands[cmd.name], cmd.name, cmd.defaultRequiredPermission);

            return (
              <Card key={cmd.name} className={cn('group transition-all duration-200 hover:shadow-[0_12px_40px_rgb(0,0,0,0.06)]', !cmdConfig.enabled && 'opacity-60')}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={cn('p-2 rounded-xl', cmdConfig.enabled ? 'bg-indigo-50 text-indigo-600' : 'bg-cream-100 text-slate-400')}>
                        <Command className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="font-display font-semibold text-slate-800">/{cmd.name}</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <Badge variant={cmd.premiumTier === 'premium' ? 'premium' : 'default'}>
                            {cmd.premiumTier === 'premium' ? 'Premium' : cmd.group}
                          </Badge>
                          <Badge variant="info">{cmd.type}</Badge>
                        </div>
                      </div>
                    </div>
                    <Switch checked={cmdConfig.enabled} onCheckedChange={() => toggleCommand(cmd.name)} />
                  </div>

                  <p className="text-sm text-slate-500 mb-4 line-clamp-2">{cmd.description}</p>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSettingsModal(cmd.name)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-cream-50 hover:bg-cream-100 border border-cream-200 rounded-lg transition-colors"
                    >
                      <Settings2 className="w-3.5 h-3.5" />
                      Settings
                    </button>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors">
                      <HelpCircle className="w-3.5 h-3.5" />
                      Help
                    </button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {settingsModal && (() => {
        const selectedCommand = commands.find((c) => c.name === settingsModal);
        if (!selectedCommand) return null;
        return (
          <CommandSettingsModal
            commandName={settingsModal}
            command={selectedCommand}
            config={ensureCommandConfig(
              config.commands[settingsModal],
              settingsModal,
              selectedCommand.defaultRequiredPermission,
            )}
            channels={channelOptions}
            roles={roleOptions}
            onClose={() => setSettingsModal(null)}
            onSave={(updated) => {
              updateConfigLocal({
                commands: { ...config.commands, [settingsModal]: updated },
              });
              setSettingsModal(null);
            }}
          />
        );
      })()}

      <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
    </div>
  );
}

interface CommandSettingsModalProps {
  commandName: string;
  command: CommandCapability;
  config: CommandConfig;
  channels: { label: string; value: string }[];
  roles: { label: string; value: string; color?: number }[];
  onClose: () => void;
  onSave: (config: CommandConfig) => void;
}
function CommandSettingsModal({ commandName, command, config, channels, roles, onClose, onSave }: CommandSettingsModalProps) {
  const [local, setLocal] = useState<CommandConfig>(clone(config));
  const [activeTab, setActiveTab] = useState<CommandTabId>('permissions');
  const profile = useMemo(() => resolveCommandProfile(commandName), [commandName]);

  const updateOverride = (key: keyof CommandConfig['overrides'], value: string[]) => {
    setLocal((prev) => ({ ...prev, overrides: { ...prev.overrides, [key]: value } }));
  };

  const updateExtra = (key: string, value: unknown) => {
    setLocal((prev) => ({ ...prev, extras: { ...(prev.extras || {}), [key]: value } }));
  };

  const tabFields = useMemo(() => {
    const grouped = new Map<CommandTabId, CommandExtraField[]>();
    grouped.set('permissions', []);
    grouped.set('channels', []);
    grouped.set('cooldowns', []);
    grouped.set('advanced', []);
    for (const field of profile.extraFields) {
      const list = grouped.get(field.tab) || [];
      list.push(field);
      grouped.set(field.tab, list);
    }
    return grouped;
  }, [profile.extraFields]);

  const tabs = [
    { id: 'permissions', label: 'Permissions' },
    { id: 'channels', label: 'Channels' },
    { id: 'cooldowns', label: 'Cooldowns' },
    { id: 'advanced', label: 'Advanced' },
  ];

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={`/${commandName} Settings`}
      description={command.description}
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => onSave(local)}>Save Settings</Button>
        </>
      }
    >
      <Tabs tabs={tabs} activeTab={activeTab} onChange={(id) => setActiveTab(id as CommandTabId)} className="mb-6" />

      {activeTab === 'permissions' && (
        <div className="space-y-5">
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Required Permission</label>
            <Select
              value={local.requiredPermission}
              onChange={(v) => setLocal((prev) => ({ ...prev, requiredPermission: v }))}
              options={PERMISSION_OPTIONS}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Minimum Staff Level</label>
            <Select
              value={local.minimumStaffLevel || 'everyone'}
              onChange={(v) => setLocal((prev) => ({ ...prev, minimumStaffLevel: v as CommandConfig['minimumStaffLevel'] }))}
              options={STAFF_LEVEL_OPTIONS}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Allowed Roles</label>
            <MultiSelect values={local.overrides.allowedRoles} onChange={(v) => updateOverride('allowedRoles', v)} options={roles} placeholder="No role restriction" />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Ignored Roles</label>
            <MultiSelect values={local.overrides.ignoredRoles} onChange={(v) => updateOverride('ignoredRoles', v)} options={roles} placeholder="No ignored roles" />
          </div>
          <StringListInput
            label="Allowed Users (User IDs)"
            values={local.overrides.allowedUsers}
            onChange={(v) => updateOverride('allowedUsers', v)}
            placeholder="Add user ID"
          />
          <StringListInput
            label="Ignored Users (User IDs)"
            values={local.overrides.ignoredUsers}
            onChange={(v) => updateOverride('ignoredUsers', v)}
            placeholder="Add user ID"
          />
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <div>
                <h4 className="font-semibold text-sm text-slate-800">Enforce Role Hierarchy</h4>
                <p className="text-xs text-slate-500 mt-0.5">Relevant for target-user commands.</p>
              </div>
              <Switch checked={Boolean(local.enforceRoleHierarchy)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, enforceRoleHierarchy: v }))} />
            </div>
            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <div>
                <h4 className="font-semibold text-sm text-slate-800">Require Reason</h4>
                <p className="text-xs text-slate-500 mt-0.5">Relevant for moderation commands.</p>
              </div>
              <Switch checked={Boolean(local.requireReason)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, requireReason: v }))} />
            </div>
            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <div>
                <h4 className="font-semibold text-sm text-slate-800">Require Confirmation</h4>
                <p className="text-xs text-slate-500 mt-0.5">Recommended for destructive actions.</p>
              </div>
              <Switch checked={Boolean(local.requireConfirmation)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, requireConfirmation: v }))} />
            </div>
          </div>

          {(tabFields.get('permissions') || []).map((field) => (
            <ExtraField
              key={`permissions_${field.key}`}
              field={field}
              value={(local.extras || {})[field.key] ?? field.defaultValue}
              onChange={(v) => updateExtra(field.key, v)}
              channels={channels}
              roles={roles}
            />
          ))}
        </div>
      )}

      {activeTab === 'channels' && (
        <div className="space-y-5">
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Channel Mode</label>
            <Select
              value={local.channelMode || 'enabled_everywhere'}
              onChange={(v) => setLocal((prev) => ({ ...prev, channelMode: v as CommandConfig['channelMode'] }))}
              options={CHANNEL_MODE_OPTIONS}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Allowed Channels</label>
            <MultiSelect values={local.overrides.allowedChannels} onChange={(v) => updateOverride('allowedChannels', v)} options={channels} placeholder="All channels allowed" />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Ignored Channels</label>
            <MultiSelect values={local.overrides.ignoredChannels} onChange={(v) => updateOverride('ignoredChannels', v)} options={channels} placeholder="No ignored channels" />
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <h4 className="font-semibold text-sm text-slate-800">Disable In Threads</h4>
              <Switch checked={Boolean(local.disableInThreads)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, disableInThreads: v }))} />
            </div>
            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <h4 className="font-semibold text-sm text-slate-800">Disable In Forum Posts</h4>
              <Switch checked={Boolean(local.disableInForumPosts)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, disableInForumPosts: v }))} />
            </div>
            <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
              <h4 className="font-semibold text-sm text-slate-800">Disable In DMs</h4>
              <Switch checked={Boolean(local.disableInDMs)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, disableInDMs: v }))} />
            </div>
          </div>

          {(tabFields.get('channels') || []).map((field) => (
            <ExtraField
              key={`channels_${field.key}`}
              field={field}
              value={(local.extras || {})[field.key] ?? field.defaultValue}
              onChange={(v) => updateExtra(field.key, v)}
              channels={channels}
              roles={roles}
            />
          ))}
        </div>
      )}
      {activeTab === 'cooldowns' && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Global Cooldown (sec)</label>
              <input
                type="number"
                value={local.cooldown.global || 0}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  setLocal((prev) => ({ ...prev, cooldown: { ...prev.cooldown, global: next, perGuild: next } }));
                }}
                min={0}
                max={86400}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Per User Cooldown (sec)</label>
              <input
                type="number"
                value={local.cooldown.perUser}
                onChange={(e) => setLocal((prev) => ({ ...prev, cooldown: { ...prev.cooldown, perUser: Number(e.target.value) } }))}
                min={0}
                max={86400}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Per Channel Cooldown (sec)</label>
              <input
                type="number"
                value={local.cooldown.perChannel || 0}
                onChange={(e) => setLocal((prev) => ({ ...prev, cooldown: { ...prev.cooldown, perChannel: Number(e.target.value) } }))}
                min={0}
                max={86400}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Max Uses / Minute</label>
              <input
                type="number"
                value={local.rateLimit.maxPerMinute || 0}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  setLocal((prev) => ({ ...prev, rateLimit: { ...prev.rateLimit, maxPerMinute: next, maxPerMinuteChannel: next } }));
                }}
                min={0}
                max={100000}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Max Uses / Hour</label>
              <input
                type="number"
                value={local.rateLimit.maxPerHour || 0}
                onChange={(e) => setLocal((prev) => ({ ...prev, rateLimit: { ...prev.rateLimit, maxPerHour: Number(e.target.value) } }))}
                min={0}
                max={1000000}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Concurrent Execution Limit</label>
              <input
                type="number"
                value={local.rateLimit.concurrentLimit || 1}
                onChange={(e) => setLocal((prev) => ({ ...prev, rateLimit: { ...prev.rateLimit, concurrentLimit: Number(e.target.value) } }))}
                min={1}
                max={1000}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Cooldown Bypass Roles</label>
            <MultiSelect
              values={local.cooldownBypassRoles || []}
              onChange={(v) => setLocal((prev) => ({ ...prev, cooldownBypassRoles: v }))}
              options={roles}
              placeholder="No bypass roles"
            />
          </div>
          <StringListInput
            label="Cooldown Bypass Users (User IDs)"
            values={local.cooldownBypassUsers || []}
            onChange={(v) => setLocal((prev) => ({ ...prev, cooldownBypassUsers: v }))}
            placeholder="Add user ID"
          />

          {(tabFields.get('cooldowns') || []).map((field) => (
            <ExtraField
              key={`cooldowns_${field.key}`}
              field={field}
              value={(local.extras || {})[field.key] ?? field.defaultValue}
              onChange={(v) => updateExtra(field.key, v)}
              channels={channels}
              roles={roles}
            />
          ))}
        </div>
      )}

      {activeTab === 'advanced' && (
        <div className="space-y-5">
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <div>
              <h4 className="font-semibold text-sm text-slate-800">Enabled</h4>
              <p className="text-xs text-slate-500 mt-0.5">Enable or disable this command.</p>
            </div>
            <Switch checked={local.enabled} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, enabled: v }))} />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <div>
              <h4 className="font-semibold text-sm text-slate-800">Visible In Help</h4>
              <p className="text-xs text-slate-500 mt-0.5">Show command in help listings.</p>
            </div>
            <Switch checked={!local.visibility.hideFromHelp} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, visibility: { ...prev.visibility, hideFromHelp: !v } }))} />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <div>
              <h4 className="font-semibold text-sm text-slate-800">Hide From Autocomplete</h4>
              <p className="text-xs text-slate-500 mt-0.5">Keep command out of slash autocomplete.</p>
            </div>
            <Switch checked={Boolean(local.visibility.hideFromAutocomplete)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, visibility: { ...prev.visibility, hideFromAutocomplete: v } }))} />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Default Response Visibility</label>
            <Select
              value={local.visibility.defaultResponseVisibility || 'auto'}
              onChange={(v) => setLocal((prev) => ({ ...prev, visibility: { ...prev.visibility, defaultResponseVisibility: v as 'auto' | 'ephemeral' | 'public' } }))}
              options={RESPONSE_VISIBILITY_OPTIONS}
            />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <div>
              <h4 className="font-semibold text-sm text-slate-800">Log Usage</h4>
              <p className="text-xs text-slate-500 mt-0.5">Record command usage in logs.</p>
            </div>
            <Switch checked={local.logging.logUsage} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, logging: { ...prev.logging, logUsage: v } }))} />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Log Channel Override</label>
            <Select
              value={local.logging.routeOverride || ''}
              onChange={(v) => setLocal((prev) => ({ ...prev, logging: { ...prev.logging, routeOverride: v || null } }))}
              options={channels}
              placeholder="Use default log channel"
            />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <h4 className="font-semibold text-sm text-slate-800">Record To Audit Log</h4>
            <Switch checked={Boolean(local.logging.recordToAuditLog)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, logging: { ...prev.logging, recordToAuditLog: v } }))} />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <h4 className="font-semibold text-sm text-slate-800">Disable During Maintenance Mode</h4>
            <Switch checked={Boolean(local.disableDuringMaintenanceMode)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, disableDuringMaintenanceMode: v }))} />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <h4 className="font-semibold text-sm text-slate-800">Disable During Raid Mode</h4>
            <Switch checked={Boolean(local.disableDuringRaidMode)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, disableDuringRaidMode: v }))} />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <h4 className="font-semibold text-sm text-slate-800">Sync With Discord Slash Permissions</h4>
            <Switch checked={Boolean(local.syncWithDiscordSlashPermissions)} onCheckedChange={(v) => setLocal((prev) => ({ ...prev, syncWithDiscordSlashPermissions: v }))} />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Default Member Permissions (bitfield preset)</label>
            <Select
              value={local.defaultMemberPermissions || ''}
              onChange={(v) => setLocal((prev) => ({ ...prev, defaultMemberPermissions: v }))}
              options={DEFAULT_MEMBER_PERMISSION_PRESETS}
            />
            <input
              type="text"
              value={local.defaultMemberPermissions || ''}
              onChange={(e) => setLocal((prev) => ({ ...prev, defaultMemberPermissions: e.target.value }))}
              placeholder="Custom bitfield value"
              className="w-full mt-2 bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            />
          </div>

          {(tabFields.get('advanced') || []).map((field) => (
            <ExtraField
              key={`advanced_${field.key}`}
              field={field}
              value={(local.extras || {})[field.key] ?? field.defaultValue}
              onChange={(v) => updateExtra(field.key, v)}
              channels={channels}
              roles={roles}
            />
          ))}
        </div>
      )}
    </Modal>
  );
}
