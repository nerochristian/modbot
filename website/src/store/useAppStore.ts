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
    overrides: defaultOverrideEntry(),
    cooldown: {
      perUser: 0,
      perGuild: 0,
    },
    rateLimit: {
      maxPerMinuteChannel: 30,
      maxPerMinuteGuild: 300,
    },
    logging: {
      logUsage: true,
      routeOverride: null,
    },
    visibility: {
      hideFromHelp: false,
      slashEnabled: true,
      prefixEnabled: true,
    },
  };
}

function normalizeCommandConfig(value: unknown, commandCap?: CommandCapability): CommandConfig {
  const source = isObject(value) ? value : {};
  const fallback = defaultCommandConfig(commandCap);
  const cooldown = isObject(source.cooldown) ? source.cooldown : {};
  const rateLimit = isObject(source.rateLimit) ? source.rateLimit : {};
  const logging = isObject(source.logging) ? source.logging : {};
  const visibility = isObject(source.visibility) ? source.visibility : {};

  return {
    enabled: typeof source.enabled === 'boolean' ? source.enabled : fallback.enabled,
    requiredPermission: typeof source.requiredPermission === 'string' ? source.requiredPermission : fallback.requiredPermission,
    overrides: normalizeOverrideEntry(source.overrides),
    cooldown: {
      perUser: typeof cooldown.perUser === 'number' ? cooldown.perUser : fallback.cooldown.perUser,
      perGuild: typeof cooldown.perGuild === 'number' ? cooldown.perGuild : fallback.cooldown.perGuild,
    },
    rateLimit: {
      maxPerMinuteChannel: typeof rateLimit.maxPerMinuteChannel === 'number'
        ? rateLimit.maxPerMinuteChannel
        : fallback.rateLimit.maxPerMinuteChannel,
      maxPerMinuteGuild: typeof rateLimit.maxPerMinuteGuild === 'number'
        ? rateLimit.maxPerMinuteGuild
        : fallback.rateLimit.maxPerMinuteGuild,
    },
    logging: {
      logUsage: typeof logging.logUsage === 'boolean' ? logging.logUsage : fallback.logging.logUsage,
      routeOverride: typeof logging.routeOverride === 'string' ? logging.routeOverride : null,
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
    },
  };
}

function normalizeLoggingConfigEntry(eventTypeId: string, value: unknown): LoggingRouteConfig {
  const source = isObject(value) ? value : {};
  const format = source.format === 'compact' ? 'compact' : 'detailed';
  return {
    eventTypeId,
    enabled: typeof source.enabled === 'boolean' ? source.enabled : false,
    channelId: typeof source.channelId === 'string' ? source.channelId : null,
    format,
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

      const guilds = user.guilds.filter(g => g.botInstalled);

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
        activeGuildId: guilds[0]?.id || null,
        loading: false,
      });

      if (guilds[0]) {
        await get().fetchConfig(guilds[0].id);
      }
    } catch (err) {
      set({ loading: false, error: err instanceof Error ? err.message : 'Failed to initialize' });
    }
  },

  setActiveGuild: (id: string) => {
    set({ activeGuildId: id, config: null, configDirty: false, channels: [], roles: [] });
    get().fetchConfig(id);
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
      set({ config: normalized, configVersion: version || normalized.version, configDirty: false });
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
