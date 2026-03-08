import { create } from 'zustand';
import type {
  AuthUser,
  BotCapabilities,
  CommandCapability,
  CommandConfig,
  DashboardCapability,
  DashboardRole,
  DashboardPermissionMapping,
  DashboardUserOverride,
  DiscordChannel,
  DiscordRole,
  EventTypeCapability,
  GuildConfig,
  GuildSetupConfig,
  LoggingRouteConfig,
  ModuleCapability,
  ModuleConfig,
  OverrideEntry,
} from '@/types';
import type { ApiClient } from '@/lib/api';
import { realApiClient } from '@/lib/api';

// Use real API client — backend serves /api/* routes
const api: ApiClient = realApiClient;
const THEME_TRANSITION_DURATION_MS = 520;
let themeTransitionCleanupTimer: number | null = null;

type ViewTransitionCapableDocument = Document & {
  startViewTransition?: (update: () => void | Promise<void>) => { finished: Promise<void> };
};

interface AppState {
  // Auth
  user: AuthUser | null;
  loading: boolean;
  error: string | null;

  // Preferences
  theme: 'light' | 'dark';

  // Guilds
  guilds: { id: string; name: string; icon: string | null; memberCount: number; botInstalled: boolean }[];
  activeGuildId: string | null;
  channels: DiscordChannel[];
  roles: DiscordRole[];

  // Capabilities (global, fetched once)
  capabilities: BotCapabilities | null;

  // Guild config (fetched per guild)
  config: GuildConfig | null;
  configVersion: number;
  configDirty: boolean;

  // Actions
  initialize: () => Promise<void>;
  refreshGuilds: () => Promise<void>;
  setActiveGuild: (id: string) => void;
  fetchGuildResources: (guildId: string) => Promise<void>;
  fetchConfig: (guildId: string) => Promise<void>;
  updateConfigLocal: (partial: Partial<GuildConfig>) => void;
  saveConfig: () => Promise<void>;
  discardChanges: () => void;
  setError: (err: string | null) => void;
  toggleTheme: () => void;
}

let originalConfig: GuildConfig | null = null;

function sortGuilds(guilds: AuthUser['guilds']) {
  return [...guilds].sort((a, b) => {
    if (a.botInstalled !== b.botInstalled) {
      return a.botInstalled ? -1 : 1;
    }
    return a.name.localeCompare(b.name);
  });
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function clone<T>(value: T): T {
  if (value === null || value === undefined) {
    return value;
  }
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return value;
  }
}

function normalizeTextArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === 'string');
}

function defaultOverrideEntry(): OverrideEntry {
  return {
    allowedChannels: [],
    ignoredChannels: [],
    allowedRoles: [],
    ignoredRoles: [],
    allowedUsers: [],
    ignoredUsers: [],
  };
}

function normalizeOverrideEntry(value: unknown): OverrideEntry {
  if (!isObject(value)) {
    return defaultOverrideEntry();
  }
  return {
    allowedChannels: normalizeTextArray(value.allowedChannels),
    ignoredChannels: normalizeTextArray(value.ignoredChannels),
    allowedRoles: normalizeTextArray(value.allowedRoles),
    ignoredRoles: normalizeTextArray(value.ignoredRoles),
    allowedUsers: normalizeTextArray(value.allowedUsers),
    ignoredUsers: normalizeTextArray(value.ignoredUsers),
  };
}

function normalizeModuleCapability(value: unknown, index: number): ModuleCapability {
  const source = isObject(value) ? value : {};
  const id = typeof source.id === 'string' && source.id ? source.id : `module_${index}`;
  const premiumTier = source.premiumTier === 'premium' || source.premiumTier === 'enterprise' ? source.premiumTier : 'free';
  return {
    id,
    name: typeof source.name === 'string' && source.name ? source.name : id,
    description: typeof source.description === 'string' ? source.description : `${id} module`,
    iconHint: typeof source.iconHint === 'string' ? source.iconHint : 'Package',
    category: typeof source.category === 'string' ? source.category : 'General',
    premiumTier,
    supportsOverrides: Boolean(source.supportsOverrides),
    settingsSchema: Array.isArray(source.settingsSchema) ? source.settingsSchema as ModuleCapability['settingsSchema'] : [],
  };
}

function normalizeCommandCapability(value: unknown, index: number): CommandCapability {
  const source = isObject(value) ? value : {};
  const name = typeof source.name === 'string' && source.name ? source.name : `command_${index}`;
  const type = source.type === 'slash' || source.type === 'prefix' || source.type === 'both' ? source.type : 'both';
  const premiumTier = source.premiumTier === 'premium' || source.premiumTier === 'enterprise' ? source.premiumTier : 'free';
  const hints = isObject(source.configHints) ? source.configHints : {};
  return {
    name,
    group: typeof source.group === 'string'
      ? source.group
      : (typeof source.category === 'string' ? source.category : 'General'),
    description: typeof source.description === 'string' ? source.description : '',
    type,
    supportsOverrides: source.supportsOverrides === undefined ? true : Boolean(source.supportsOverrides),
    defaultRequiredPermission: typeof source.defaultRequiredPermission === 'string'
      ? source.defaultRequiredPermission
      : 'send_messages',
    premiumTier,
    settingsSchema: Array.isArray(source.settingsSchema) ? source.settingsSchema as CommandCapability['settingsSchema'] : [],
    configHints: {
      supportsReason: Boolean(hints.supportsReason),
      supportsConfirmation: Boolean(hints.supportsConfirmation),
      supportsRoleHierarchy: Boolean(hints.supportsRoleHierarchy),
    },
  };
}

function normalizeEventTypeCapability(value: unknown, index: number): EventTypeCapability {
  const source = isObject(value) ? value : {};
  const category = source.category === 'automod' || source.category === 'server' || source.category === 'messages' || source.category === 'members' || source.category === 'voice'
    ? source.category
    : 'moderation';
  const severity = source.severity === 'warning' || source.severity === 'critical' ? source.severity : 'info';
  const id = typeof source.id === 'string' && source.id ? source.id : `event_${index}`;
  return {
    id,
    name: typeof source.name === 'string' && source.name ? source.name : id,
    category,
    description: typeof source.description === 'string' ? source.description : '',
    severity,
  };
}

function normalizeCapabilities(raw: unknown): BotCapabilities {
  const source = isObject(raw) ? raw : {};
  const modules = Array.isArray(source.modules) ? source.modules.map(normalizeModuleCapability) : [];
  const rawCommands = Array.isArray(source.commands) ? source.commands.map(normalizeCommandCapability) : [];
  const commandsByName = new Map<string, CommandCapability>();
  for (const command of rawCommands) {
    const existing = commandsByName.get(command.name);
    if (!existing) {
      commandsByName.set(command.name, command);
      continue;
    }
    const mergedType = existing.type === command.type ? existing.type : 'both';
    const mergedPremiumTier = existing.premiumTier === 'enterprise' || command.premiumTier === 'enterprise'
      ? 'enterprise'
      : (existing.premiumTier === 'premium' || command.premiumTier === 'premium' ? 'premium' : 'free');
    commandsByName.set(command.name, {
      ...existing,
      type: mergedType,
      description: existing.description || command.description,
      group: existing.group || command.group,
      supportsOverrides: existing.supportsOverrides || command.supportsOverrides,
      settingsSchema: existing.settingsSchema.length >= command.settingsSchema.length
        ? existing.settingsSchema
        : command.settingsSchema,
      defaultRequiredPermission: existing.defaultRequiredPermission !== 'send_messages'
        ? existing.defaultRequiredPermission
        : command.defaultRequiredPermission,
      premiumTier: mergedPremiumTier,
    });
  }
  const commands = Array.from(commandsByName.values()).sort((a, b) => a.name.localeCompare(b.name));
  const eventTypes = Array.isArray(source.eventTypes) ? source.eventTypes.map(normalizeEventTypeCapability) : [];
  return {
    version: typeof source.version === 'string'
      ? source.version
      : (typeof source.botVersion === 'string' ? source.botVersion : 'unknown'),
    buildInfo: typeof source.buildInfo === 'string' ? source.buildInfo : '',
    modules,
    commands,
    eventTypes,
    permissionCapabilities: Array.isArray(source.permissionCapabilities)
      ? source.permissionCapabilities as DashboardCapability[]
      : [],
  };
}

function defaultModuleConfig(moduleCap?: ModuleCapability): ModuleConfig {
  const settings: Record<string, unknown> = {};
  if (moduleCap?.settingsSchema) {
    for (const field of moduleCap.settingsSchema) {
      settings[field.key] = clone(field.defaultValue);
    }
  }
  return {
    enabled: true,
    settings,
    overrides: defaultOverrideEntry(),
    loggingRouteOverride: null,
  };
}

function normalizeModuleConfig(value: unknown, moduleCap?: ModuleCapability): ModuleConfig {
  const source = isObject(value) ? value : {};
  return {
    enabled: typeof source.enabled === 'boolean' ? source.enabled : true,
    settings: isObject(source.settings) ? source.settings : defaultModuleConfig(moduleCap).settings,
    overrides: normalizeOverrideEntry(source.overrides),
    loggingRouteOverride: typeof source.loggingRouteOverride === 'string' ? source.loggingRouteOverride : null,
  };
}

function defaultCommandConfig(commandCap?: CommandCapability): CommandConfig {
  return {
    enabled: true,
    requiredPermission: commandCap?.defaultRequiredPermission || 'send_messages',
    minimumStaffLevel: 'everyone',
    enforceRoleHierarchy: false,
    requireReason: false,
    requireConfirmation: false,
    channelMode: 'enabled_everywhere',
    disableInThreads: false,
    disableInForumPosts: false,
    disableInDMs: false,
    overrides: defaultOverrideEntry(),
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
}

function normalizeCommandConfig(value: unknown, commandCap?: CommandCapability): CommandConfig {
  const source = isObject(value) ? value : {};
  const fallback = defaultCommandConfig(commandCap);
  const cooldown = isObject(source.cooldown) ? source.cooldown : {};
  const rateLimit = isObject(source.rateLimit) ? source.rateLimit : {};
  const logging = isObject(source.logging) ? source.logging : {};
  const visibility = isObject(source.visibility) ? source.visibility : {};
  const staffLevel = source.minimumStaffLevel;
  const channelMode = source.channelMode;
  const responseVisibility = visibility.defaultResponseVisibility;
  const extras = isObject(source.extras) ? source.extras : {};

  return {
    enabled: typeof source.enabled === 'boolean' ? source.enabled : fallback.enabled,
    requiredPermission: typeof source.requiredPermission === 'string' ? source.requiredPermission : fallback.requiredPermission,
    minimumStaffLevel: staffLevel === 'everyone' || staffLevel === 'staff' || staffLevel === 'mod' || staffLevel === 'admin' || staffLevel === 'supervisor' || staffLevel === 'owner'
      ? staffLevel
      : fallback.minimumStaffLevel,
    enforceRoleHierarchy: typeof source.enforceRoleHierarchy === 'boolean' ? source.enforceRoleHierarchy : fallback.enforceRoleHierarchy,
    requireReason: typeof source.requireReason === 'boolean' ? source.requireReason : fallback.requireReason,
    requireConfirmation: typeof source.requireConfirmation === 'boolean' ? source.requireConfirmation : fallback.requireConfirmation,
    channelMode: channelMode === 'enabled_everywhere' || channelMode === 'only_allowed' || channelMode === 'disabled_in_ignored'
      ? channelMode
      : fallback.channelMode,
    disableInThreads: typeof source.disableInThreads === 'boolean' ? source.disableInThreads : fallback.disableInThreads,
    disableInForumPosts: typeof source.disableInForumPosts === 'boolean' ? source.disableInForumPosts : fallback.disableInForumPosts,
    disableInDMs: typeof source.disableInDMs === 'boolean' ? source.disableInDMs : fallback.disableInDMs,
    overrides: normalizeOverrideEntry(source.overrides),
    cooldown: {
      global: typeof cooldown.global === 'number' ? cooldown.global : fallback.cooldown.global,
      perUser: typeof cooldown.perUser === 'number' ? cooldown.perUser : fallback.cooldown.perUser,
      perGuild: typeof cooldown.perGuild === 'number' ? cooldown.perGuild : fallback.cooldown.perGuild,
      perChannel: typeof cooldown.perChannel === 'number' ? cooldown.perChannel : fallback.cooldown.perChannel,
    },
    rateLimit: {
      maxPerMinute: typeof rateLimit.maxPerMinute === 'number'
        ? rateLimit.maxPerMinute
        : fallback.rateLimit.maxPerMinute,
      maxPerHour: typeof rateLimit.maxPerHour === 'number'
        ? rateLimit.maxPerHour
        : fallback.rateLimit.maxPerHour,
      concurrentLimit: typeof rateLimit.concurrentLimit === 'number'
        ? rateLimit.concurrentLimit
        : fallback.rateLimit.concurrentLimit,
      maxPerMinuteChannel: typeof rateLimit.maxPerMinuteChannel === 'number'
        ? rateLimit.maxPerMinuteChannel
        : fallback.rateLimit.maxPerMinuteChannel,
      maxPerMinuteGuild: typeof rateLimit.maxPerMinuteGuild === 'number'
        ? rateLimit.maxPerMinuteGuild
        : fallback.rateLimit.maxPerMinuteGuild,
    },
    cooldownBypassRoles: normalizeTextArray(source.cooldownBypassRoles),
    cooldownBypassUsers: normalizeTextArray(source.cooldownBypassUsers),
    logging: {
      logUsage: typeof logging.logUsage === 'boolean' ? logging.logUsage : fallback.logging.logUsage,
      routeOverride: typeof logging.routeOverride === 'string' ? logging.routeOverride : null,
      recordToAuditLog: typeof logging.recordToAuditLog === 'boolean'
        ? logging.recordToAuditLog
        : fallback.logging.recordToAuditLog,
    },
    visibility: {
      hideFromHelp: typeof visibility.hideFromHelp === 'boolean'
        ? visibility.hideFromHelp
        : fallback.visibility.hideFromHelp,
      slashEnabled: typeof visibility.slashEnabled === 'boolean'
        ? visibility.slashEnabled
        : fallback.visibility.slashEnabled,
      prefixEnabled: typeof visibility.prefixEnabled === 'boolean'
        ? visibility.prefixEnabled
        : fallback.visibility.prefixEnabled,
      hideFromAutocomplete: typeof visibility.hideFromAutocomplete === 'boolean'
        ? visibility.hideFromAutocomplete
        : fallback.visibility.hideFromAutocomplete,
      defaultResponseVisibility: responseVisibility === 'auto' || responseVisibility === 'ephemeral' || responseVisibility === 'public'
        ? responseVisibility
        : fallback.visibility.defaultResponseVisibility,
    },
    disableDuringMaintenanceMode: typeof source.disableDuringMaintenanceMode === 'boolean'
      ? source.disableDuringMaintenanceMode
      : fallback.disableDuringMaintenanceMode,
    disableDuringRaidMode: typeof source.disableDuringRaidMode === 'boolean'
      ? source.disableDuringRaidMode
      : fallback.disableDuringRaidMode,
    syncWithDiscordSlashPermissions: typeof source.syncWithDiscordSlashPermissions === 'boolean'
      ? source.syncWithDiscordSlashPermissions
      : fallback.syncWithDiscordSlashPermissions,
    defaultMemberPermissions: typeof source.defaultMemberPermissions === 'string'
      ? source.defaultMemberPermissions
      : fallback.defaultMemberPermissions,
    extras,
  };
}

function normalizeLoggingConfigEntry(eventTypeId: string, value: unknown): LoggingRouteConfig {
  const source = isObject(value) ? value : {};
  const format = source.format === 'compact' ? 'compact' : 'detailed';
  return {
    eventTypeId,
    enabled: typeof source.enabled === 'boolean' ? source.enabled : true,
    channelId: typeof source.channelId === 'string' ? source.channelId : null,
    format,
  };
}

function defaultSetupConfig(): GuildSetupConfig {
  return {
    ownerRole: '',
    managerRole: '',
    adminRole: '',
    supervisorRole: '',
    seniorModRole: '',
    moderatorRole: '',
    trialModRole: '',
    staffRole: '',
    mutedRole: '',
    quarantineRole: '',
    logsAccessRole: '',
    bypassRole: '',
    whitelistedRole: '',
    autoRole: '',
    verifiedRole: '',
    unverifiedRole: '',
    welcomeChannel: '',
    staffChatChannel: '',
    staffCommandsChannel: '',
    staffAnnouncementsChannel: '',
    staffGuideChannel: '',
    staffUpdatesChannel: '',
    staffSanctionsChannel: '',
    supervisorLogChannel: '',
  };
}

function normalizeSetupConfig(value: unknown): GuildSetupConfig {
  const source = isObject(value) ? value : {};
  const fallback = defaultSetupConfig();
  return {
    ownerRole: typeof source.ownerRole === 'string' ? source.ownerRole : fallback.ownerRole,
    managerRole: typeof source.managerRole === 'string' ? source.managerRole : fallback.managerRole,
    adminRole: typeof source.adminRole === 'string' ? source.adminRole : fallback.adminRole,
    supervisorRole: typeof source.supervisorRole === 'string' ? source.supervisorRole : fallback.supervisorRole,
    seniorModRole: typeof source.seniorModRole === 'string' ? source.seniorModRole : fallback.seniorModRole,
    moderatorRole: typeof source.moderatorRole === 'string' ? source.moderatorRole : fallback.moderatorRole,
    trialModRole: typeof source.trialModRole === 'string' ? source.trialModRole : fallback.trialModRole,
    staffRole: typeof source.staffRole === 'string' ? source.staffRole : fallback.staffRole,
    mutedRole: typeof source.mutedRole === 'string' ? source.mutedRole : fallback.mutedRole,
    quarantineRole: typeof source.quarantineRole === 'string' ? source.quarantineRole : fallback.quarantineRole,
    logsAccessRole: typeof source.logsAccessRole === 'string' ? source.logsAccessRole : fallback.logsAccessRole,
    bypassRole: typeof source.bypassRole === 'string' ? source.bypassRole : fallback.bypassRole,
    whitelistedRole: typeof source.whitelistedRole === 'string' ? source.whitelistedRole : fallback.whitelistedRole,
    autoRole: typeof source.autoRole === 'string' ? source.autoRole : fallback.autoRole,
    verifiedRole: typeof source.verifiedRole === 'string' ? source.verifiedRole : fallback.verifiedRole,
    unverifiedRole: typeof source.unverifiedRole === 'string' ? source.unverifiedRole : fallback.unverifiedRole,
    welcomeChannel: typeof source.welcomeChannel === 'string' ? source.welcomeChannel : fallback.welcomeChannel,
    staffChatChannel: typeof source.staffChatChannel === 'string' ? source.staffChatChannel : fallback.staffChatChannel,
    staffCommandsChannel: typeof source.staffCommandsChannel === 'string' ? source.staffCommandsChannel : fallback.staffCommandsChannel,
    staffAnnouncementsChannel: typeof source.staffAnnouncementsChannel === 'string' ? source.staffAnnouncementsChannel : fallback.staffAnnouncementsChannel,
    staffGuideChannel: typeof source.staffGuideChannel === 'string' ? source.staffGuideChannel : fallback.staffGuideChannel,
    staffUpdatesChannel: typeof source.staffUpdatesChannel === 'string' ? source.staffUpdatesChannel : fallback.staffUpdatesChannel,
    staffSanctionsChannel: typeof source.staffSanctionsChannel === 'string' ? source.staffSanctionsChannel : fallback.staffSanctionsChannel,
    supervisorLogChannel: typeof source.supervisorLogChannel === 'string' ? source.supervisorLogChannel : fallback.supervisorLogChannel,
  };
}

function normalizeRoleMappings(value: unknown): DashboardPermissionMapping[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isObject).map((entry) => {
    const dashboardRole: DashboardRole = entry.dashboardRole === 'owner' || entry.dashboardRole === 'admin' || entry.dashboardRole === 'moderator'
      ? entry.dashboardRole
      : 'viewer';
    return {
      roleId: typeof entry.roleId === 'string' ? entry.roleId : '',
      dashboardRole,
      capabilities: Array.isArray(entry.capabilities)
        ? entry.capabilities.filter((cap): cap is DashboardCapability => typeof cap === 'string')
        : [],
    };
  }).filter((entry) => entry.roleId.length > 0);
}

function normalizeUserOverrides(value: unknown): DashboardUserOverride[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isObject).map((entry) => {
    const dashboardRole: DashboardRole = entry.dashboardRole === 'owner' || entry.dashboardRole === 'admin' || entry.dashboardRole === 'moderator'
      ? entry.dashboardRole
      : 'viewer';
    return {
      userId: typeof entry.userId === 'string' ? entry.userId : '',
      dashboardRole,
      capabilities: Array.isArray(entry.capabilities)
        ? entry.capabilities.filter((cap): cap is DashboardCapability => typeof cap === 'string')
        : [],
    };
  }).filter((entry) => entry.userId.length > 0);
}

function normalizeConfig(rawConfig: unknown, guildId: string, capabilities: BotCapabilities | null): GuildConfig {
  const source = isObject(rawConfig) ? rawConfig : {};
  const modulesSource = isObject(source.modules) ? source.modules : {};
  const commandsSource = isObject(source.commands) ? source.commands : {};
  const loggingSource = isObject(source.logging) ? source.logging : {};
  const permissionsSource = isObject(source.permissions) ? source.permissions : {};

  const moduleCapabilities = capabilities?.modules || [];
  const commandCapabilities = capabilities?.commands || [];
  const eventTypeCapabilities = capabilities?.eventTypes || [];

  const modules: Record<string, ModuleConfig> = {};
  for (const [key, value] of Object.entries(modulesSource)) {
    const moduleCap = moduleCapabilities.find((mod) => mod.id === key);
    modules[key] = normalizeModuleConfig(value, moduleCap);
  }
  for (const moduleCap of moduleCapabilities) {
    if (!modules[moduleCap.id]) {
      modules[moduleCap.id] = defaultModuleConfig(moduleCap);
    }
  }

  const commands: Record<string, CommandConfig> = {};
  for (const [key, value] of Object.entries(commandsSource)) {
    const commandCap = commandCapabilities.find((command) => command.name === key);
    commands[key] = normalizeCommandConfig(value, commandCap);
  }
  for (const commandCap of commandCapabilities) {
    if (!commands[commandCap.name]) {
      commands[commandCap.name] = defaultCommandConfig(commandCap);
    }
  }

  const logging: Record<string, LoggingRouteConfig> = {};
  for (const [eventTypeId, value] of Object.entries(loggingSource)) {
    logging[eventTypeId] = normalizeLoggingConfigEntry(eventTypeId, value);
  }
  for (const eventType of eventTypeCapabilities) {
    if (!logging[eventType.id]) {
      logging[eventType.id] = normalizeLoggingConfigEntry(eventType.id, {});
    }
  }

  const roleMappings = normalizeRoleMappings(
    Array.isArray(permissionsSource.roleMappings)
      ? permissionsSource.roleMappings
      : permissionsSource.dashboardRoleMappings
  );
  const userOverrides = normalizeUserOverrides(permissionsSource.userOverrides);

  return {
    guildId: typeof source.guildId === 'string' ? source.guildId : guildId,
    version: typeof source.version === 'number' ? source.version : 1,
    updatedAt: typeof source.updatedAt === 'string' ? source.updatedAt : new Date().toISOString(),
    prefix: typeof source.prefix === 'string' ? source.prefix : ',',
    defaultCooldown: typeof source.defaultCooldown === 'number' ? source.defaultCooldown : 0,
    timezone: typeof source.timezone === 'string' ? source.timezone : 'UTC',
    setup: normalizeSetupConfig(source.setup),
    modules,
    commands,
    logging,
    permissions: {
      roleMappings,
      userOverrides,
    },
    globalBypassRoles: normalizeTextArray(source.globalBypassRoles),
    globalBypassUsers: normalizeTextArray(source.globalBypassUsers),
  };
}

function prepareConfigForApi(config: GuildConfig): GuildConfig & { permissions: GuildConfig['permissions'] & { dashboardRoleMappings: DashboardPermissionMapping[] } } {
  return {
    ...config,
    permissions: {
      ...config.permissions,
      dashboardRoleMappings: config.permissions.roleMappings,
    },
  };
}

export const useAppStore = create<AppState>((set, get) => ({
  user: null,
  loading: true,
  error: null,
  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  guilds: [],
  activeGuildId: null,
  channels: [],
  roles: [],
  capabilities: null,
  config: null,
  configVersion: 0,
  configDirty: false,

  initialize: async () => {
    try {
      set({ loading: true, error: null });

      // Try to fetch user — if 401, user is not logged in
      let user: AuthUser;
      try {
        user = await api.getMe();
      } catch (err: any) {
        if (err?.status === 401) {
          // Not logged in — this is expected
          set({ loading: false, user: null });
          return;
        }
        throw err;
      }

      const guilds = sortGuilds(user.guilds);
      const initialGuild = guilds.find((guild) => guild.botInstalled) || guilds[0] || null;

      let capabilities: BotCapabilities | null = null;
      try {
        capabilities = normalizeCapabilities(await api.getCapabilities());
      } catch {
        // Bot might not expose capabilities yet
      }

      set({
        user,
        guilds,
        capabilities,
        activeGuildId: initialGuild?.id || null,
        loading: false,
      });

      if (initialGuild?.botInstalled) {
        await get().fetchConfig(initialGuild.id);
      }
    } catch (err) {
      set({ loading: false, error: err instanceof Error ? err.message : 'Failed to initialize' });
    }
  },

  refreshGuilds: async () => {
    const { user, activeGuildId, guilds: previousGuilds } = get();
    if (!user) {
      return;
    }

    try {
      const refreshedGuilds = sortGuilds(await api.getGuilds());
      const hasActiveGuild = Boolean(activeGuildId && refreshedGuilds.some((guild) => guild.id === activeGuildId));
      const nextActiveGuildId = hasActiveGuild
        ? activeGuildId
        : (refreshedGuilds.find((guild) => guild.botInstalled)?.id || refreshedGuilds[0]?.id || null);

      const previousActiveGuild = previousGuilds.find((guild) => guild.id === nextActiveGuildId);
      const refreshedActiveGuild = refreshedGuilds.find((guild) => guild.id === nextActiveGuildId);
      const botJustInstalled = Boolean(
        nextActiveGuildId
        && refreshedActiveGuild?.botInstalled
        && !previousActiveGuild?.botInstalled
      );

      set({
        guilds: refreshedGuilds,
        activeGuildId: nextActiveGuildId,
      });

      if (nextActiveGuildId && refreshedActiveGuild?.botInstalled && (botJustInstalled || get().config?.guildId !== nextActiveGuildId)) {
        await get().fetchConfig(nextActiveGuildId);
      }
    } catch {
      // Silent failure: this runs on focus/menu-open and should not spam error banners.
    }
  },

  setActiveGuild: (id: string) => {
    if (!id || get().activeGuildId === id) {
      return;
    }
    set({ activeGuildId: id, config: null, configDirty: false, channels: [], roles: [] });
    const selectedGuild = get().guilds.find((guild) => guild.id === id);
    if (selectedGuild?.botInstalled) {
      get().fetchConfig(id);
    }
  },

  fetchGuildResources: async (guildId: string) => {
    try {
      const [channels, roles] = await Promise.all([
        api.getChannels(guildId).catch(() => []),
        api.getRoles(guildId).catch(() => []),
      ]);
      set({ channels, roles });
    } catch {
      set({ channels: [], roles: [] });
    }
  },

  fetchConfig: async (guildId: string) => {
    try {
      const { data, version } = await api.getConfig(guildId);
      const normalized = normalizeConfig(data, guildId, get().capabilities);
      originalConfig = clone(normalized);
      set({ config: normalized, configVersion: version || normalized.version, configDirty: false, error: null });
      await get().fetchGuildResources(guildId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to fetch config' });
    }
  },

  updateConfigLocal: (partial) => {
    const current = get().config;
    if (!current) return;
    set({ config: { ...current, ...partial }, configDirty: true });
  },

  saveConfig: async () => {
    const { config, configVersion, activeGuildId, capabilities } = get();
    if (!config || !activeGuildId) return;
    try {
      const payload = prepareConfigForApi(config);
      const { data, version } = await api.updateConfig(activeGuildId, payload, configVersion);
      const normalized = normalizeConfig(data, activeGuildId, capabilities);
      originalConfig = clone(normalized);
      set({ config: normalized, configVersion: version || normalized.version, configDirty: false, error: null });
    } catch (err) {
      if (err instanceof Error && err.message.includes('conflict')) {
        set({ error: 'Config was updated by someone else. Please refresh and try again.' });
      } else {
        set({ error: err instanceof Error ? err.message : 'Failed to save config' });
      }
      throw err;
    }
  },

  discardChanges: () => {
    if (originalConfig) {
      set({ config: clone(originalConfig), configDirty: false });
    }
  },

  setError: (err) => set({ error: err }),

  toggleTheme: () => {
    const current = get().theme;
    const next = current === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', next);

    const root = document.documentElement;
    const applyTheme = () => {
      if (next === 'dark') {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
      set({ theme: next });
    };

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) {
      applyTheme();
      return;
    }

    root.classList.add('theme-transitioning');
    if (themeTransitionCleanupTimer !== null) {
      window.clearTimeout(themeTransitionCleanupTimer);
    }

    const vtDocument = document as ViewTransitionCapableDocument;
    if (typeof vtDocument.startViewTransition === 'function') {
      vtDocument.startViewTransition(() => {
        applyTheme();
      });
    } else {
      applyTheme();
    }

    themeTransitionCleanupTimer = window.setTimeout(() => {
      root.classList.remove('theme-transitioning');
      themeTransitionCleanupTimer = null;
    }, THEME_TRANSITION_DURATION_MS);
  },
}));
