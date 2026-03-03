import type {
    ApiClient,
} from '@/lib/api';
import type {
    AuthUser,
    GuildSummary,
    BotCapabilities,
    GuildConfig,
    CommandConfig,
    ModuleConfig,
    LoggingRouteConfig,
    ModerationCase,
    AuditLogEntry,
    SyncStatus,
    DiscordChannel,
    DiscordRole,
    DiscordUser,
    ApiResponse,
    PaginatedResponse,
} from '@/types';

// ─── Mock Discord Resources ────────────────────────────────────────────────

const MOCK_CHANNELS: DiscordChannel[] = [
    { id: 'ch_general', name: 'general', type: 0, parentId: null, position: 0 },
    { id: 'ch_mods', name: 'mod-chat', type: 0, parentId: null, position: 1 },
    { id: 'ch_bot', name: 'bot-commands', type: 0, parentId: null, position: 2 },
    { id: 'ch_logs', name: 'mod-logs', type: 0, parentId: null, position: 3 },
    { id: 'ch_msg_logs', name: 'message-logs', type: 0, parentId: null, position: 4 },
    { id: 'ch_join', name: 'join-leave', type: 0, parentId: null, position: 5 },
    { id: 'ch_voice', name: 'General Voice', type: 2, parentId: null, position: 6 },
    { id: 'ch_announce', name: 'announcements', type: 5, parentId: null, position: 7 },
    { id: 'ch_staff', name: 'staff-chat', type: 0, parentId: null, position: 8 },
    { id: 'ch_tickets', name: 'tickets', type: 0, parentId: null, position: 9 },
];

const MOCK_ROLES: DiscordRole[] = [
    { id: 'role_owner', name: 'Owner', color: 0xe74c3c, position: 10, permissions: '8', managed: false },
    { id: 'role_admin', name: 'Admin', color: 0x3498db, position: 9, permissions: '0', managed: false },
    { id: 'role_mod', name: 'Moderator', color: 0x2ecc71, position: 8, permissions: '0', managed: false },
    { id: 'role_helper', name: 'Helper', color: 0xf39c12, position: 7, permissions: '0', managed: false },
    { id: 'role_member', name: 'Member', color: 0x95a5a6, position: 1, permissions: '0', managed: false },
    { id: 'role_muted', name: 'Muted', color: 0x7f8c8d, position: 2, permissions: '0', managed: false },
    { id: 'role_bot', name: 'ModBot', color: 0x6366f1, position: 11, permissions: '8', managed: true },
    { id: 'role_booster', name: 'Server Booster', color: 0xf47fff, position: 5, permissions: '0', managed: true },
];

// ─── Mock Capabilities ──────────────────────────────────────────────────────

const MOCK_CAPABILITIES: BotCapabilities = {
    version: '3.3.0',
    buildInfo: 'modbot v3.3.0 — production',
    modules: [
        {
            id: 'automod',
            name: 'Auto Moderation',
            description: 'Automatically filter messages, detect spam, and enforce content rules.',
            iconHint: 'Zap',
            category: 'Moderation',
            premiumTier: 'free',
            supportsOverrides: true,
            settingsSchema: [
                { key: 'antiSpam', label: 'Anti-Spam', type: 'boolean', defaultValue: true, section: 'Filters' },
                { key: 'spamThreshold', label: 'Spam Threshold', type: 'number', defaultValue: 5, constraints: { min: 2, max: 20, helpText: 'Messages in 3s window' }, section: 'Filters' },
                { key: 'antiLink', label: 'Anti-Link', type: 'boolean', defaultValue: false, section: 'Filters' },
                { key: 'linkWhitelist', label: 'Allowed Domains', type: 'stringList', defaultValue: [], constraints: { placeholder: 'discord.com' }, section: 'Filters', advanced: true },
                { key: 'antiInvite', label: 'Anti-Invite', type: 'boolean', defaultValue: true, section: 'Filters' },
                { key: 'bannedWords', label: 'Banned Words', type: 'stringList', defaultValue: [], constraints: { helpText: 'One word/phrase per entry' }, section: 'Content' },
                { key: 'capsThreshold', label: 'Max Caps %', type: 'number', defaultValue: 70, constraints: { min: 0, max: 100 }, section: 'Content', advanced: true },
                { key: 'mentionLimit', label: 'Mention Spam Limit', type: 'number', defaultValue: 5, constraints: { min: 1, max: 50 }, section: 'Content' },
                { key: 'action', label: 'Default Action', type: 'select', defaultValue: 'warn', constraints: { options: [{ label: 'Warn', value: 'warn' }, { label: 'Delete', value: 'delete' }, { label: 'Timeout', value: 'timeout' }, { label: 'Kick', value: 'kick' }] }, section: 'Actions' },
                { key: 'timeoutDuration', label: 'Timeout Duration', type: 'duration', defaultValue: 300, constraints: { min: 60, max: 604800 }, section: 'Actions', advanced: true },
            ],
        },
        {
            id: 'antiraid',
            name: 'Anti-Raid',
            description: 'Protect against coordinated join attacks and bot raids.',
            iconHint: 'ShieldAlert',
            category: 'Protection',
            premiumTier: 'free',
            supportsOverrides: false,
            settingsSchema: [
                { key: 'joinThreshold', label: 'Join Threshold', type: 'number', defaultValue: 10, constraints: { min: 3, max: 50, helpText: 'Users joining within time window' }, section: 'Detection' },
                { key: 'timeWindow', label: 'Time Window (seconds)', type: 'number', defaultValue: 5, constraints: { min: 1, max: 30 }, section: 'Detection' },
                { key: 'lockdownEnabled', label: 'Auto-Lockdown', type: 'boolean', defaultValue: true, section: 'Response' },
                { key: 'kickNewAccounts', label: 'Kick New Accounts', type: 'boolean', defaultValue: false, section: 'Response' },
                { key: 'accountAgeHours', label: 'Min Account Age (hours)', type: 'number', defaultValue: 24, constraints: { min: 1, max: 720 }, section: 'Response', advanced: true },
            ],
        },
        {
            id: 'logging',
            name: 'Logging',
            description: 'Track server events and moderation actions with detailed logs.',
            iconHint: 'ScrollText',
            category: 'Utility',
            premiumTier: 'free',
            supportsOverrides: false,
            settingsSchema: [
                { key: 'embedColor', label: 'Embed Color', type: 'color', defaultValue: '#6366f1', section: 'Appearance' },
                { key: 'compactMode', label: 'Compact Mode', type: 'boolean', defaultValue: false, section: 'Appearance' },
                { key: 'includeAvatars', label: 'Include Avatars', type: 'boolean', defaultValue: true, section: 'Appearance' },
            ],
        },
        {
            id: 'moderation',
            name: 'Moderation',
            description: 'Comprehensive moderation tools with case tracking and escalation.',
            iconHint: 'Shield',
            category: 'Moderation',
            premiumTier: 'free',
            supportsOverrides: true,
            settingsSchema: [
                { key: 'warningExpiry', label: 'Warning Expiry', type: 'select', defaultValue: 'never', constraints: { options: [{ label: 'Never', value: 'never' }, { label: '30 Days', value: '30d' }, { label: '60 Days', value: '60d' }, { label: '90 Days', value: '90d' }] }, section: 'Warnings' },
                { key: 'dmOnAction', label: 'DM User on Action', type: 'boolean', defaultValue: true, section: 'Notifications' },
                { key: 'dmTemplate', label: 'DM Template', type: 'textArea', defaultValue: 'You have been {action} in {server} for: {reason}', constraints: { helpText: 'Variables: {action}, {server}, {reason}, {moderator}, {duration}' }, section: 'Notifications', advanced: true },
                { key: 'requireReason', label: 'Require Reason', type: 'boolean', defaultValue: true, section: 'General' },
            ],
        },
        {
            id: 'tickets',
            name: 'Tickets',
            description: 'Support ticket system with categories and staff assignment.',
            iconHint: 'Ticket',
            category: 'Utility',
            premiumTier: 'free',
            supportsOverrides: true,
            settingsSchema: [
                { key: 'maxTickets', label: 'Max Open Tickets per User', type: 'number', defaultValue: 3, constraints: { min: 1, max: 10 }, section: 'Limits' },
                { key: 'autoClose', label: 'Auto-Close Inactive', type: 'boolean', defaultValue: true, section: 'Automation' },
                { key: 'autoCloseHours', label: 'Inactivity Hours', type: 'number', defaultValue: 48, constraints: { min: 1, max: 720 }, section: 'Automation', advanced: true },
                { key: 'transcriptEnabled', label: 'Save Transcripts', type: 'boolean', defaultValue: true, section: 'Logging' },
            ],
        },
        {
            id: 'verification',
            name: 'Verification',
            description: 'Gate new members with verification steps before granting access.',
            iconHint: 'UserCheck',
            category: 'Protection',
            premiumTier: 'free',
            supportsOverrides: false,
            settingsSchema: [
                { key: 'type', label: 'Verification Type', type: 'select', defaultValue: 'button', constraints: { options: [{ label: 'Button Click', value: 'button' }, { label: 'Reaction', value: 'reaction' }, { label: 'Captcha', value: 'captcha' }] }, section: 'Setup' },
                { key: 'verifiedRole', label: 'Verified Role', type: 'rolePicker', defaultValue: '', section: 'Setup' },
                { key: 'pendingRole', label: 'Pending Role', type: 'rolePicker', defaultValue: '', section: 'Setup' },
            ],
        },
    ],
    commands: [
        { name: 'ban', group: 'Moderation', description: 'Ban a user from the server', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'ban_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'kick', group: 'Moderation', description: 'Kick a user from the server', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'kick_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'warn', group: 'Moderation', description: 'Issue a warning to a user', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'moderate_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'timeout', group: 'Moderation', description: 'Timeout a user for a specified duration', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'moderate_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'unban', group: 'Moderation', description: 'Unban a previously banned user', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'ban_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'case', group: 'Moderation', description: 'View a specific moderation case', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'moderate_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'cases', group: 'Moderation', description: "View a user's moderation history", type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'moderate_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'purge', group: 'Moderation', description: 'Bulk delete messages in a channel', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'manage_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'slowmode', group: 'Moderation', description: 'Set channel slowmode', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'manage_channels', premiumTier: 'free', settingsSchema: [] },
        { name: 'quarantine', group: 'Moderation', description: 'Quarantine a user, removing all roles', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'moderate_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'note', group: 'Moderation', description: 'Add a moderator note to a user', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'moderate_members', premiumTier: 'free', settingsSchema: [] },
        { name: 'report', group: 'Utility', description: 'Report a user to moderators', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'send_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'help', group: 'Utility', description: 'View bot commands and features', type: 'both', supportsOverrides: true, defaultRequiredPermission: 'send_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'ping', group: 'Utility', description: 'Check bot latency', type: 'slash', supportsOverrides: false, defaultRequiredPermission: 'send_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'serverinfo', group: 'Utility', description: 'View server information', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'send_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'userinfo', group: 'Utility', description: 'View information about a user', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'send_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'avatar', group: 'Utility', description: "View a user's avatar", type: 'slash', supportsOverrides: false, defaultRequiredPermission: 'send_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'poll', group: 'Utility', description: 'Create a poll', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'send_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'ticket', group: 'Utility', description: 'Create a support ticket', type: 'slash', supportsOverrides: true, defaultRequiredPermission: 'send_messages', premiumTier: 'free', settingsSchema: [] },
        { name: 'setup', group: 'Admin', description: 'Interactive bot setup wizard', type: 'slash', supportsOverrides: false, defaultRequiredPermission: 'administrator', premiumTier: 'free', settingsSchema: [] },
        { name: 'settings', group: 'Admin', description: 'View/edit server bot settings', type: 'slash', supportsOverrides: false, defaultRequiredPermission: 'manage_guild', premiumTier: 'free', settingsSchema: [] },
        { name: 'automod', group: 'Admin', description: 'Configure auto-moderation rules', type: 'slash', supportsOverrides: false, defaultRequiredPermission: 'manage_guild', premiumTier: 'free', settingsSchema: [] },
        { name: 'prefix', group: 'Admin', description: 'Set the bot command prefix', type: 'slash', supportsOverrides: false, defaultRequiredPermission: 'manage_guild', premiumTier: 'free', settingsSchema: [] },
    ],
    eventTypes: [
        { id: 'message_delete', name: 'Message Deleted', category: 'messages', description: 'A message was deleted', severity: 'info' },
        { id: 'message_edit', name: 'Message Edited', category: 'messages', description: 'A message was edited', severity: 'info' },
        { id: 'message_bulk_delete', name: 'Bulk Delete', category: 'messages', description: 'Messages were bulk deleted', severity: 'warning' },
        { id: 'member_join', name: 'Member Joined', category: 'members', description: 'A member joined the server', severity: 'info' },
        { id: 'member_leave', name: 'Member Left', category: 'members', description: 'A member left the server', severity: 'info' },
        { id: 'member_role_update', name: 'Role Updated', category: 'members', description: "A member's roles changed", severity: 'info' },
        { id: 'member_nick_update', name: 'Nickname Changed', category: 'members', description: "A member's nickname changed", severity: 'info' },
        { id: 'user_ban', name: 'User Banned', category: 'moderation', description: 'A user was banned', severity: 'critical' },
        { id: 'user_unban', name: 'User Unbanned', category: 'moderation', description: 'A user was unbanned', severity: 'warning' },
        { id: 'user_kick', name: 'User Kicked', category: 'moderation', description: 'A user was kicked', severity: 'warning' },
        { id: 'user_warn', name: 'User Warned', category: 'moderation', description: 'A user was warned', severity: 'warning' },
        { id: 'user_timeout', name: 'User Timed Out', category: 'moderation', description: 'A user was timed out', severity: 'warning' },
        { id: 'automod_trigger', name: 'Automod Triggered', category: 'automod', description: 'An automod rule triggered', severity: 'warning' },
        { id: 'automod_action', name: 'Automod Action', category: 'automod', description: 'An automod action was taken', severity: 'warning' },
        { id: 'channel_create', name: 'Channel Created', category: 'server', description: 'A channel was created', severity: 'info' },
        { id: 'channel_delete', name: 'Channel Deleted', category: 'server', description: 'A channel was deleted', severity: 'warning' },
        { id: 'role_create', name: 'Role Created', category: 'server', description: 'A role was created', severity: 'info' },
        { id: 'role_delete', name: 'Role Deleted', category: 'server', description: 'A role was deleted', severity: 'warning' },
        { id: 'server_update', name: 'Server Updated', category: 'server', description: 'Server settings changed', severity: 'info' },
        { id: 'voice_join', name: 'Voice Join', category: 'voice', description: 'A member joined voice', severity: 'info' },
        { id: 'voice_leave', name: 'Voice Leave', category: 'voice', description: 'A member left voice', severity: 'info' },
    ],
    permissionCapabilities: [
        'view_dashboard', 'view_commands', 'manage_commands', 'view_modules', 'manage_modules',
        'view_logging', 'manage_logging', 'view_cases', 'manage_cases', 'view_automod',
        'manage_automod', 'manage_permissions', 'export_data', 'danger_zone_actions',
        'run_sync_operations', 'view_audit',
    ],
};

// ─── Mock Guild Config ──────────────────────────────────────────────────────

function createDefaultOverrides() {
    return { allowedChannels: [], ignoredChannels: [], allowedRoles: [], ignoredRoles: [], allowedUsers: [], ignoredUsers: [] };
}

function createDefaultCommandConfig(enabled = true): CommandConfig {
    return {
        enabled,
        requiredPermission: 'moderate_members',
        overrides: createDefaultOverrides(),
        cooldown: { perUser: 3, perGuild: 0 },
        rateLimit: { maxPerMinuteChannel: 10, maxPerMinuteGuild: 30 },
        logging: { logUsage: true, routeOverride: null },
        visibility: { hideFromHelp: false, slashEnabled: true, prefixEnabled: false },
    };
}

const MOCK_CONFIG: GuildConfig = {
    guildId: '1',
    version: 1,
    updatedAt: new Date().toISOString(),
    prefix: '!',
    defaultCooldown: 3,
    timezone: 'UTC',
    modules: {
        automod: { enabled: true, settings: { antiSpam: true, spamThreshold: 5, antiLink: false, antiInvite: true, bannedWords: ['badword'], capsThreshold: 70, mentionLimit: 5, action: 'warn', timeoutDuration: 300, linkWhitelist: [] }, overrides: createDefaultOverrides(), loggingRouteOverride: null },
        antiraid: { enabled: true, settings: { joinThreshold: 10, timeWindow: 5, lockdownEnabled: true, kickNewAccounts: false, accountAgeHours: 24 }, overrides: createDefaultOverrides(), loggingRouteOverride: null },
        logging: { enabled: true, settings: { embedColor: '#6366f1', compactMode: false, includeAvatars: true }, overrides: createDefaultOverrides(), loggingRouteOverride: null },
        moderation: { enabled: true, settings: { warningExpiry: 'never', dmOnAction: true, dmTemplate: 'You have been {action} in {server} for: {reason}', requireReason: true }, overrides: createDefaultOverrides(), loggingRouteOverride: 'ch_logs' },
        tickets: { enabled: true, settings: { maxTickets: 3, autoClose: true, autoCloseHours: 48, transcriptEnabled: true }, overrides: createDefaultOverrides(), loggingRouteOverride: null },
        verification: { enabled: false, settings: { type: 'button', verifiedRole: 'role_member', pendingRole: '' }, overrides: createDefaultOverrides(), loggingRouteOverride: null },
    },
    commands: Object.fromEntries(
        MOCK_CAPABILITIES.commands.map(cmd => [cmd.name, createDefaultCommandConfig(true)])
    ),
    logging: Object.fromEntries(
        MOCK_CAPABILITIES.eventTypes.map(et => [
            et.id,
            { eventTypeId: et.id, enabled: ['moderation', 'automod'].includes(et.category), channelId: et.category === 'moderation' ? 'ch_logs' : et.category === 'messages' ? 'ch_msg_logs' : et.category === 'members' ? 'ch_join' : null, format: 'detailed' as const },
        ])
    ),
    permissions: {
        roleMappings: [
            { roleId: 'role_owner', dashboardRole: 'owner', capabilities: [] },
            { roleId: 'role_admin', dashboardRole: 'admin', capabilities: [] },
            { roleId: 'role_mod', dashboardRole: 'moderator', capabilities: [] },
        ],
        userOverrides: [],
    },
    globalBypassRoles: ['role_owner', 'role_admin'],
    globalBypassUsers: [],
};

// ─── Mock Cases ─────────────────────────────────────────────────────────────

const MOCK_CASES: ModerationCase[] = [
    { id: 1, guildId: '1', userId: 'u1', userName: 'spammer#1234', userAvatar: null, moderatorId: '123456789', moderatorName: 'AdminUser', action: 'ban', reason: 'Sending phishing links in multiple channels', duration: null, createdAt: new Date(Date.now() - 600000).toISOString(), active: true },
    { id: 2, guildId: '1', userId: 'u2', userName: 'angry_user', userAvatar: null, moderatorId: '123456789', moderatorName: 'AdminUser', action: 'warn', reason: 'Excessive profanity after being asked to stop', duration: null, createdAt: new Date(Date.now() - 3600000).toISOString(), active: true },
    { id: 3, guildId: '1', userId: 'u3', userName: 'rulebreaker', userAvatar: null, moderatorId: '123456789', moderatorName: 'AdminUser', action: 'timeout', reason: 'Spamming the same message repeatedly', duration: '1h', createdAt: new Date(Date.now() - 7200000).toISOString(), active: true },
    { id: 4, guildId: '1', userId: 'u4', userName: 'troublemaker', userAvatar: null, moderatorId: '123456789', moderatorName: 'AdminUser', action: 'kick', reason: 'Continued rule violations after 3 warnings', duration: null, createdAt: new Date(Date.now() - 86400000).toISOString(), active: false },
    { id: 5, guildId: '1', userId: 'u5', userName: 'advertiser_bot', userAvatar: null, moderatorId: 'bot', moderatorName: 'ModBot', action: 'ban', reason: 'Automod: Mass DM advertising detected', duration: null, createdAt: new Date(Date.now() - 172800000).toISOString(), active: true },
    { id: 6, guildId: '1', userId: 'u2', userName: 'angry_user', userAvatar: null, moderatorId: '123456789', moderatorName: 'AdminUser', action: 'warn', reason: 'Disrespecting staff members', duration: null, createdAt: new Date(Date.now() - 259200000).toISOString(), active: true },
];

// ─── Mock Audit Log ─────────────────────────────────────────────────────────

const MOCK_AUDIT: AuditLogEntry[] = [
    { id: 'a1', guildId: '1', userId: '123456789', userName: 'AdminUser', action: 'config_update', target: 'automod.antiSpam', changes: { antiSpam: { from: false, to: true } }, timestamp: new Date(Date.now() - 3600000).toISOString() },
    { id: 'a2', guildId: '1', userId: '123456789', userName: 'AdminUser', action: 'command_toggle', target: 'ban', changes: { enabled: { from: true, to: false } }, timestamp: new Date(Date.now() - 7200000).toISOString() },
    { id: 'a3', guildId: '1', userId: '123456789', userName: 'AdminUser', action: 'module_toggle', target: 'verification', changes: { enabled: { from: true, to: false } }, timestamp: new Date(Date.now() - 86400000).toISOString() },
    { id: 'a4', guildId: '1', userId: '123456789', userName: 'AdminUser', action: 'sync_commands', target: 'slash_commands', changes: {}, timestamp: new Date(Date.now() - 172800000).toISOString() },
];

// ─── Simulate Network Delay ────────────────────────────────────────────────

function delay(ms = 300): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Deep clone to prevent mutation
function clone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj));
}

// In-memory state
let currentConfig = clone(MOCK_CONFIG);

// ─── Mock API Client ────────────────────────────────────────────────────────

export const mockApiClient: ApiClient = {
    async getMe() {
        await delay(200);
        return {
            id: '123456789',
            username: 'AdminUser',
            avatar: 'https://cdn.discordapp.com/embed/avatars/0.png',
            guilds: [
                { id: '1', name: 'Global Gaming Community', icon: 'https://cdn.discordapp.com/embed/avatars/1.png', owner: true, memberCount: 15420, botInstalled: true },
                { id: '2', name: 'Dev Support Server', icon: 'https://cdn.discordapp.com/embed/avatars/2.png', owner: false, memberCount: 3200, botInstalled: true },
                { id: '3', name: 'Private Friends', icon: 'https://cdn.discordapp.com/embed/avatars/3.png', owner: true, memberCount: 45, botInstalled: false },
            ],
        };
    },

    async logout() { await delay(100); },

    async getGuilds() {
        await delay(200);
        return [
            { id: '1', name: 'Global Gaming Community', icon: 'https://cdn.discordapp.com/embed/avatars/1.png', owner: true, memberCount: 15420, botInstalled: true },
            { id: '2', name: 'Dev Support Server', icon: 'https://cdn.discordapp.com/embed/avatars/2.png', owner: false, memberCount: 3200, botInstalled: true },
            { id: '3', name: 'Private Friends', icon: 'https://cdn.discordapp.com/embed/avatars/3.png', owner: true, memberCount: 45, botInstalled: false },
        ];
    },

    async getGuildSummary(guildId) {
        await delay(150);
        const guilds = await this.getGuilds();
        return guilds.find(g => g.id === guildId) || guilds[0];
    },

    async getChannels() {
        await delay(150);
        return clone(MOCK_CHANNELS);
    },

    async getRoles() {
        await delay(150);
        return clone(MOCK_ROLES);
    },

    async searchUsers(_guildId, query) {
        await delay(200);
        const users: DiscordUser[] = [
            { id: 'u1', username: 'spammer', discriminator: '1234', avatar: null, globalName: 'Spammer' },
            { id: 'u2', username: 'angry_user', discriminator: '0', avatar: null, globalName: 'Angry User' },
            { id: 'u3', username: 'rulebreaker', discriminator: '0', avatar: null, globalName: 'Rule Breaker' },
            { id: 'u7', username: 'helper_jane', discriminator: '0', avatar: null, globalName: 'Jane' },
            { id: 'u8', username: 'mod_mike', discriminator: '0', avatar: null, globalName: 'Mike' },
        ];
        if (!query) return users.slice(0, 3);
        return users.filter(u => u.username.toLowerCase().includes(query.toLowerCase()));
    },

    async getCapabilities() {
        await delay(200);
        return clone(MOCK_CAPABILITIES);
    },

    async getConfig() {
        await delay(300);
        return { data: clone(currentConfig), version: currentConfig.version };
    },

    async updateConfig(_guildId, config, version) {
        await delay(400);
        if (version !== currentConfig.version) {
            const { ApiHttpError } = await import('@/lib/api');
            throw new ApiHttpError(409, { code: 409, message: 'Version conflict. Config was updated by another user.' });
        }
        currentConfig = { ...clone(config), version: config.version + 1, updatedAt: new Date().toISOString() };
        return { data: clone(currentConfig), version: currentConfig.version };
    },

    async validateConfig(_guildId, _config) {
        await delay(200);
        return { valid: true, errors: [] };
    },

    async createSnapshot() {
        await delay(300);
        return { snapshotId: `snap_${Date.now()}` };
    },

    async rollbackConfig() {
        await delay(500);
        currentConfig = clone(MOCK_CONFIG);
        return { data: clone(currentConfig), version: currentConfig.version };
    },

    async getCommands() {
        await delay(200);
        return clone(currentConfig.commands);
    },

    async updateCommand(_guildId, commandName, config, version) {
        await delay(300);
        if (version !== currentConfig.version) {
            const { ApiHttpError } = await import('@/lib/api');
            throw new ApiHttpError(409, { code: 409, message: 'Version conflict' });
        }
        currentConfig.commands[commandName] = clone(config);
        currentConfig.version++;
        currentConfig.updatedAt = new Date().toISOString();
        return { data: clone(currentConfig), version: currentConfig.version };
    },

    async batchCommands(_guildId, action, commands, version) {
        await delay(400);
        if (version !== currentConfig.version) {
            const { ApiHttpError } = await import('@/lib/api');
            throw new ApiHttpError(409, { code: 409, message: 'Version conflict' });
        }
        for (const cmd of commands) {
            if (currentConfig.commands[cmd]) {
                currentConfig.commands[cmd].enabled = action === 'enable';
            }
        }
        currentConfig.version++;
        currentConfig.updatedAt = new Date().toISOString();
        return { data: clone(currentConfig), version: currentConfig.version };
    },

    async syncCommands() {
        await delay(2000);
    },

    async getSyncStatus() {
        await delay(150);
        return {
            status: 'complete' as const,
            lastSyncedAt: new Date(Date.now() - 86400000).toISOString(),
            error: null,
            progress: 100,
            syncRequired: false,
        };
    },

    async getModules() {
        await delay(200);
        return clone(currentConfig.modules);
    },

    async updateModule(_guildId, moduleId, config, version) {
        await delay(300);
        if (version !== currentConfig.version) {
            const { ApiHttpError } = await import('@/lib/api');
            throw new ApiHttpError(409, { code: 409, message: 'Version conflict' });
        }
        currentConfig.modules[moduleId] = clone(config);
        currentConfig.version++;
        currentConfig.updatedAt = new Date().toISOString();
        return { data: clone(currentConfig), version: currentConfig.version };
    },

    async getLogging() {
        await delay(200);
        return clone(currentConfig.logging);
    },

    async updateLogging(_guildId, logging, version) {
        await delay(300);
        if (version !== currentConfig.version) {
            const { ApiHttpError } = await import('@/lib/api');
            throw new ApiHttpError(409, { code: 409, message: 'Version conflict' });
        }
        currentConfig.logging = clone(logging);
        currentConfig.version++;
        currentConfig.updatedAt = new Date().toISOString();
        return { data: clone(currentConfig), version: currentConfig.version };
    },

    async getCases(_guildId, _cursor) {
        await delay(300);
        return { data: clone(MOCK_CASES), cursor: null, hasMore: false, total: MOCK_CASES.length };
    },

    async getCase(_guildId, caseId) {
        await delay(200);
        const found = MOCK_CASES.find(c => c.id === caseId);
        if (!found) throw new Error('Case not found');
        return clone(found);
    },

    async getAuditLog(_guildId, _cursor) {
        await delay(300);
        return { data: clone(MOCK_AUDIT), cursor: null, hasMore: false, total: MOCK_AUDIT.length };
    },
};

export { MOCK_CAPABILITIES, MOCK_CHANNELS, MOCK_ROLES };
