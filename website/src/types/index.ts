// ─── Discord Resource Types ──────────────────────────────────────────────────

export interface DiscordChannel {
    id: string;
    name: string;
    type: number; // 0=text, 2=voice, 4=category, 5=announcement, 13=stage, 15=forum
    parentId: string | null;
    position: number;
}

export interface DiscordRole {
    id: string;
    name: string;
    color: number;
    position: number;
    permissions: string;
    managed: boolean;
}

export interface DiscordUser {
    id: string;
    username: string;
    discriminator: string;
    avatar: string | null;
    globalName: string | null;
}

// ─── Auth & Guild Types ─────────────────────────────────────────────────────

export interface AuthUser {
    id: string;
    username: string;
    avatar: string;
    guilds: GuildSummary[];
}

export interface GuildSummary {
    id: string;
    name: string;
    icon: string | null;
    owner: boolean;
    memberCount: number;
    botInstalled: boolean;
}

// ─── Dashboard Permission Types ─────────────────────────────────────────────

export type DashboardRole = 'owner' | 'admin' | 'moderator' | 'viewer';

export type DashboardCapability =
    | 'view_dashboard'
    | 'view_commands'
    | 'manage_commands'
    | 'view_modules'
    | 'manage_modules'
    | 'view_logging'
    | 'manage_logging'
    | 'view_cases'
    | 'manage_cases'
    | 'view_automod'
    | 'manage_automod'
    | 'manage_permissions'
    | 'export_data'
    | 'danger_zone_actions'
    | 'run_sync_operations'
    | 'view_audit';

export interface DashboardPermissionMapping {
    roleId: string; // Discord role ID
    dashboardRole: DashboardRole;
    capabilities: DashboardCapability[];
}

export interface DashboardUserOverride {
    userId: string;
    dashboardRole: DashboardRole;
    capabilities: DashboardCapability[];
}

export const DASHBOARD_ROLE_CAPABILITIES: Record<DashboardRole, DashboardCapability[]> = {
    owner: [
        'view_dashboard', 'view_commands', 'manage_commands', 'view_modules', 'manage_modules',
        'view_logging', 'manage_logging', 'view_cases', 'manage_cases', 'view_automod',
        'manage_automod', 'manage_permissions', 'export_data', 'danger_zone_actions',
        'run_sync_operations', 'view_audit',
    ],
    admin: [
        'view_dashboard', 'view_commands', 'manage_commands', 'view_modules', 'manage_modules',
        'view_logging', 'manage_logging', 'view_cases', 'manage_cases', 'view_automod',
        'manage_automod', 'export_data', 'run_sync_operations', 'view_audit',
    ],
    moderator: [
        'view_dashboard', 'view_commands', 'view_modules', 'view_logging',
        'view_cases', 'manage_cases', 'view_automod', 'view_audit',
    ],
    viewer: ['view_dashboard', 'view_commands', 'view_modules', 'view_logging', 'view_cases'],
};

// ─── Schema-Driven Field Types ──────────────────────────────────────────────

export type FieldType =
    | 'boolean'
    | 'number'
    | 'string'
    | 'select'
    | 'multiselect'
    | 'duration'
    | 'channelPicker'
    | 'rolePicker'
    | 'userPicker'
    | 'textArea'
    | 'regex'
    | 'color'
    | 'stringList';

export interface FieldConstraints {
    min?: number;
    max?: number;
    required?: boolean;
    placeholder?: string;
    helpText?: string;
    pattern?: string;
    options?: { label: string; value: string }[];
}

export interface SettingsFieldSchema {
    key: string;
    label: string;
    type: FieldType;
    defaultValue: unknown;
    constraints?: FieldConstraints;
    section?: string;
    advanced?: boolean;
}

// ─── Bot Capability Types ───────────────────────────────────────────────────

export interface BotCapabilities {
    version: string;
    buildInfo: string;
    modules: ModuleCapability[];
    commands: CommandCapability[];
    eventTypes: EventTypeCapability[];
    permissionCapabilities: DashboardCapability[];
}

export interface ModuleCapability {
    id: string;
    name: string;
    description: string;
    iconHint: string;
    category: string;
    premiumTier: 'free' | 'premium' | 'enterprise';
    supportsOverrides: boolean;
    settingsSchema: SettingsFieldSchema[];
}

export interface CommandCapability {
    name: string;
    group: string;
    description: string;
    type: 'slash' | 'prefix' | 'both';
    supportsOverrides: boolean;
    defaultRequiredPermission: string;
    premiumTier: 'free' | 'premium' | 'enterprise';
    settingsSchema: SettingsFieldSchema[];
    configHints?: {
        supportsReason?: boolean;
        supportsConfirmation?: boolean;
        supportsRoleHierarchy?: boolean;
    };
}

export interface EventTypeCapability {
    id: string;
    name: string;
    category: 'moderation' | 'automod' | 'server' | 'messages' | 'members' | 'voice';
    description: string;
    severity: 'info' | 'warning' | 'critical';
}

// ─── Override & Config Types ────────────────────────────────────────────────

export interface OverrideEntry {
    allowedChannels: string[];
    ignoredChannels: string[];
    allowedRoles: string[];
    ignoredRoles: string[];
    allowedUsers: string[];
    ignoredUsers: string[];
}

export interface CommandConfig {
    enabled: boolean;
    requiredPermission: string;
    minimumStaffLevel?: 'everyone' | 'staff' | 'mod' | 'admin' | 'supervisor' | 'owner';
    enforceRoleHierarchy?: boolean;
    requireReason?: boolean;
    requireConfirmation?: boolean;
    channelMode?: 'enabled_everywhere' | 'only_allowed' | 'disabled_in_ignored';
    disableInThreads?: boolean;
    disableInForumPosts?: boolean;
    disableInDMs?: boolean;
    overrides: OverrideEntry;
    cooldown: {
        global?: number; // seconds
        perUser: number;  // seconds
        perGuild: number; // seconds
        perChannel?: number; // seconds
    };
    rateLimit: {
        maxPerMinute?: number;
        maxPerHour?: number;
        concurrentLimit?: number;
        maxPerMinuteChannel: number;
        maxPerMinuteGuild: number;
    };
    cooldownBypassRoles?: string[];
    cooldownBypassUsers?: string[];
    logging: {
        logUsage: boolean;
        routeOverride: string | null; // channel ID override
        recordToAuditLog?: boolean;
    };
    visibility: {
        hideFromHelp: boolean;
        slashEnabled: boolean;
        prefixEnabled: boolean;
        hideFromAutocomplete?: boolean;
        defaultResponseVisibility?: 'auto' | 'ephemeral' | 'public';
    };
    disableDuringMaintenanceMode?: boolean;
    disableDuringRaidMode?: boolean;
    syncWithDiscordSlashPermissions?: boolean;
    defaultMemberPermissions?: string;
    extras?: Record<string, unknown>;
}

export interface ModuleConfig {
    enabled: boolean;
    settings: Record<string, unknown>;
    overrides: OverrideEntry;
    loggingRouteOverride: string | null;
}

export interface LoggingRouteConfig {
    eventTypeId: string;
    enabled: boolean;
    channelId: string | null;
    format: 'compact' | 'detailed';
}

export interface GuildConfig {
    guildId: string;
    version: number;
    updatedAt: string;

    // Global defaults
    prefix: string;
    defaultCooldown: number;
    timezone: string;

    // Module configs (keyed by module ID)
    modules: Record<string, ModuleConfig>;

    // Command configs (keyed by command name)
    commands: Record<string, CommandConfig>;

    // Logging routing (keyed by event type ID)
    logging: Record<string, LoggingRouteConfig>;

    // Dashboard permissions
    permissions: {
        roleMappings: DashboardPermissionMapping[];
        userOverrides: DashboardUserOverride[];
    };

    // Global ignore/bypass lists
    globalBypassRoles: string[];
    globalBypassUsers: string[];
}

// ─── Moderation Case Types ──────────────────────────────────────────────────

export type CaseAction = 'warn' | 'timeout' | 'kick' | 'ban' | 'unban' | 'note' | 'quarantine';

export interface ModerationCase {
    id: number;
    guildId: string;
    userId: string;
    userName: string;
    userAvatar: string | null;
    moderatorId: string;
    moderatorName: string;
    action: CaseAction;
    reason: string;
    duration: string | null;
    createdAt: string;
    active: boolean;
}

// ─── Audit Log Types ────────────────────────────────────────────────────────

export interface AuditLogEntry {
    id: string;
    guildId: string;
    userId: string;
    userName: string;
    action: string;
    target: string;
    changes: Record<string, { from: unknown; to: unknown }>;
    timestamp: string;
}

// ─── API Response Types ─────────────────────────────────────────────────────

export interface ApiResponse<T> {
    data: T;
    version?: number;
}

export interface ApiError {
    code: number;
    message: string;
    details?: Record<string, string[]>;
}

export interface PaginatedResponse<T> {
    data: T[];
    cursor: string | null;
    hasMore: boolean;
    total: number;
}

// ─── Sync Types ─────────────────────────────────────────────────────────────

export interface SyncStatus {
    status: 'idle' | 'syncing' | 'error' | 'complete';
    lastSyncedAt: string | null;
    error: string | null;
    progress: number; // 0-100
    syncRequired: boolean;
}

export interface PanicModeResponse {
    ok: boolean;
    enabled: boolean;
    channelsAffected: number;
    updatedAt: string;
}

// ─── Resolution Context ─────────────────────────────────────────────────────

export interface ResolutionContext {
    userId: string;
    userRoles: string[];
    channelId: string;
    guildId: string;
}

export interface ResolutionResult {
    allowed: boolean;
    reason: string;
    resolvedBy: string; // which layer resolved this
}
