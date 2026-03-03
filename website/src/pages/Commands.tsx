import { useState, useMemo, useCallback } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent } from '@/components/ui/Card';
import { Switch } from '@/components/ui/Switch';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Badge, Select, MultiSelect, Tabs, SaveBar, SearchInput, PageSkeleton, EmptyState } from '@/components/ui/Shared';
import { Command, Settings2, HelpCircle, RefreshCw, AlertTriangle, Zap, ChevronDown } from 'lucide-react';
import type { CommandConfig, CommandCapability, DiscordChannel, DiscordRole } from '@/types';
import { MOCK_CHANNELS, MOCK_ROLES } from '@/lib/mock-data';
import { cn } from '@/lib/utils';

const PERMISSION_OPTIONS = [
  { label: 'Send Messages', value: 'send_messages' },
  { label: 'Moderate Members', value: 'moderate_members' },
  { label: 'Manage Messages', value: 'manage_messages' },
  { label: 'Kick Members', value: 'kick_members' },
  { label: 'Ban Members', value: 'ban_members' },
  { label: 'Manage Channels', value: 'manage_channels' },
  { label: 'Manage Guild', value: 'manage_guild' },
  { label: 'Administrator', value: 'administrator' },
];

export function Commands() {
  const { capabilities, config, configVersion, updateConfigLocal, saveConfig, discardChanges, configDirty, error } = useAppStore();
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [settingsModal, setSettingsModal] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showSyncBanner, setShowSyncBanner] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const commands = capabilities?.commands || [];

  // Group commands by category
  const categories = useMemo(() => {
    const groups = new Map<string, CommandCapability[]>();
    for (const cmd of commands) {
      const list = groups.get(cmd.group) || [];
      list.push(cmd);
      groups.set(cmd.group, list);
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
      list = list.filter(c => c.group === activeCategory);
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(c => c.name.toLowerCase().includes(q) || c.description.toLowerCase().includes(q));
    }
    return list;
  }, [commands, activeCategory, search]);

  const toggleCommand = useCallback((name: string) => {
    if (!config) return;
    const current = config.commands[name];
    if (!current) return;
    updateConfigLocal({
      commands: {
        ...config.commands,
        [name]: { ...current, enabled: !current.enabled },
      },
    });
  }, [config, updateConfigLocal]);

  const batchToggle = useCallback((action: 'enable' | 'disable') => {
    if (!config) return;
    const updates = { ...config.commands };
    for (const cmd of filteredCommands) {
      if (updates[cmd.name]) {
        updates[cmd.name] = { ...updates[cmd.name], enabled: action === 'enable' };
      }
    }
    updateConfigLocal({ commands: updates });
  }, [config, filteredCommands, updateConfigLocal]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveConfig();
    } catch { /* error handled in store */ }
    setSaving(false);
  };

  const handleSync = async () => {
    setSyncing(true);
    // Simulate sync
    await new Promise(r => setTimeout(r, 2000));
    setSyncing(false);
    setShowSyncBanner(false);
  };

  if (!capabilities || !config) return <PageSkeleton />;

  const channelOptions = MOCK_CHANNELS.filter(c => c.type === 0).map(c => ({ label: `#${c.name}`, value: c.id }));
  const roleOptions = MOCK_ROLES.filter(r => !r.managed).map(r => ({ label: r.name, value: r.id, color: r.color }));

  return (
    <div className="space-y-6">
      {/* Sync Required Banner */}
      {showSyncBanner && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center gap-4">
          <div className="p-2 bg-amber-100 rounded-xl text-amber-600">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-amber-900 text-sm">Slash Command Sync Required</h4>
            <p className="text-xs text-amber-700 mt-0.5">
              Command permissions have changed. Sync with Discord to apply updates.
            </p>
          </div>
          <Button
            onClick={handleSync}
            disabled={syncing}
            size="sm"
            className="gap-2"
          >
            <RefreshCw className={cn('w-4 h-4', syncing && 'animate-spin')} />
            {syncing ? 'Syncing...' : 'Sync Now'}
          </Button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Commands</h1>
          <p className="text-slate-500 mt-1">Manage bot commands — toggle, configure permissions, and set overrides.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => batchToggle('enable')}>Enable All</Button>
          <Button variant="outline" size="sm" onClick={() => batchToggle('disable')}>Disable All</Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Search commands..." className="w-72" />
        <Tabs tabs={categoryTabs} activeTab={activeCategory} onChange={setActiveCategory} />
      </div>

      {/* Commands Grid */}
      {filteredCommands.length === 0 ? (
        <EmptyState
          icon={<Command className="w-8 h-8" />}
          title="No commands found"
          description="No commands match your current search or filters."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredCommands.map(cmd => {
            const cmdConfig = config.commands[cmd.name];
            if (!cmdConfig) return null;

            return (
              <Card key={cmd.name} className={cn('group transition-all duration-200 hover:shadow-[0_12px_40px_rgb(0,0,0,0.06)]', !cmdConfig.enabled && 'opacity-60')}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        'p-2 rounded-xl',
                        cmdConfig.enabled ? 'bg-indigo-50 text-indigo-600' : 'bg-cream-100 text-slate-400'
                      )}>
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
                    <Switch
                      checked={cmdConfig.enabled}
                      onCheckedChange={() => toggleCommand(cmd.name)}
                    />
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

      {/* Command Settings Modal */}
      {settingsModal && (
        <CommandSettingsModal
          commandName={settingsModal}
          command={commands.find(c => c.name === settingsModal)!}
          config={config.commands[settingsModal]}
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
      )}

      {/* Save Bar */}
      <SaveBar
        dirty={configDirty}
        saving={saving}
        onSave={handleSave}
        onDiscard={discardChanges}
        error={error}
      />
    </div>
  );
}

// ─── Command Settings Modal ─────────────────────────────────────────────────

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
  const [local, setLocal] = useState<CommandConfig>(JSON.parse(JSON.stringify(config)));
  const [activeTab, setActiveTab] = useState('permissions');

  const updateOverride = (key: keyof typeof local.overrides, value: string[]) => {
    setLocal(prev => ({
      ...prev,
      overrides: { ...prev.overrides, [key]: value },
    }));
  };

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
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} className="mb-6" />

      {activeTab === 'permissions' && (
        <div className="space-y-5">
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Required Permission</label>
            <Select
              value={local.requiredPermission}
              onChange={(v) => setLocal(prev => ({ ...prev, requiredPermission: v }))}
              options={PERMISSION_OPTIONS}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Allowed Roles</label>
            <p className="text-xs text-slate-500 mb-2">Only users with these roles can use this command. Leave empty for no restriction.</p>
            <MultiSelect
              values={local.overrides.allowedRoles}
              onChange={(v) => updateOverride('allowedRoles', v)}
              options={roles}
              placeholder="All roles allowed"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Ignored Roles</label>
            <p className="text-xs text-slate-500 mb-2">Users with these roles cannot use this command.</p>
            <MultiSelect
              values={local.overrides.ignoredRoles}
              onChange={(v) => updateOverride('ignoredRoles', v)}
              options={roles}
              placeholder="No roles ignored"
            />
          </div>
        </div>
      )}

      {activeTab === 'channels' && (
        <div className="space-y-5">
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Allowed Channels</label>
            <p className="text-xs text-slate-500 mb-2">Restrict this command to specific channels. Leave empty to allow all.</p>
            <MultiSelect
              values={local.overrides.allowedChannels}
              onChange={(v) => updateOverride('allowedChannels', v)}
              options={channels}
              placeholder="All channels allowed"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Ignored Channels</label>
            <p className="text-xs text-slate-500 mb-2">This command won&apos;t work in these channels.</p>
            <MultiSelect
              values={local.overrides.ignoredChannels}
              onChange={(v) => updateOverride('ignoredChannels', v)}
              options={channels}
              placeholder="No channels ignored"
            />
          </div>
        </div>
      )}

      {activeTab === 'cooldowns' && (
        <div className="space-y-5">
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Per-User Cooldown (seconds)</label>
            <input
              type="number"
              value={local.cooldown.perUser}
              onChange={(e) => setLocal(prev => ({ ...prev, cooldown: { ...prev.cooldown, perUser: Number(e.target.value) } }))}
              min={0}
              max={3600}
              className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Per-Guild Cooldown (seconds)</label>
            <input
              type="number"
              value={local.cooldown.perGuild}
              onChange={(e) => setLocal(prev => ({ ...prev, cooldown: { ...prev.cooldown, perGuild: Number(e.target.value) } }))}
              min={0}
              max={3600}
              className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Rate Limit (per channel/min)</label>
              <input
                type="number"
                value={local.rateLimit.maxPerMinuteChannel}
                onChange={(e) => setLocal(prev => ({ ...prev, rateLimit: { ...prev.rateLimit, maxPerMinuteChannel: Number(e.target.value) } }))}
                min={1}
                max={100}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Rate Limit (per guild/min)</label>
              <input
                type="number"
                value={local.rateLimit.maxPerMinuteGuild}
                onChange={(e) => setLocal(prev => ({ ...prev, rateLimit: { ...prev.rateLimit, maxPerMinuteGuild: Number(e.target.value) } }))}
                min={1}
                max={500}
                className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'advanced' && (
        <div className="space-y-5">
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <div>
              <h4 className="font-semibold text-sm text-slate-800">Log Command Usage</h4>
              <p className="text-xs text-slate-500 mt-0.5">Record when this command is used</p>
            </div>
            <Switch
              checked={local.logging.logUsage}
              onCheckedChange={(v) => setLocal(prev => ({ ...prev, logging: { ...prev.logging, logUsage: v } }))}
            />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <div>
              <h4 className="font-semibold text-sm text-slate-800">Hide from Help</h4>
              <p className="text-xs text-slate-500 mt-0.5">Don&apos;t show in /help command list</p>
            </div>
            <Switch
              checked={local.visibility.hideFromHelp}
              onCheckedChange={(v) => setLocal(prev => ({ ...prev, visibility: { ...prev.visibility, hideFromHelp: v } }))}
            />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <div>
              <h4 className="font-semibold text-sm text-slate-800">Slash Command</h4>
              <p className="text-xs text-slate-500 mt-0.5">Enable as slash command (/)</p>
            </div>
            <Switch
              checked={local.visibility.slashEnabled}
              onCheckedChange={(v) => setLocal(prev => ({ ...prev, visibility: { ...prev.visibility, slashEnabled: v } }))}
            />
          </div>
          <div className="flex items-center justify-between p-4 bg-cream-50 rounded-2xl border border-cream-200">
            <div>
              <h4 className="font-semibold text-sm text-slate-800">Prefix Command</h4>
              <p className="text-xs text-slate-500 mt-0.5">Enable as prefix command (!)</p>
            </div>
            <Switch
              checked={local.visibility.prefixEnabled}
              onCheckedChange={(v) => setLocal(prev => ({ ...prev, visibility: { ...prev.visibility, prefixEnabled: v } }))}
            />
          </div>
        </div>
      )}
    </Modal>
  );
}
