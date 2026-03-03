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
    ApiError,
} from '@/types';

// ─── Error Classes ──────────────────────────────────────────────────────────

export class ApiHttpError extends Error {
    constructor(
        public status: number,
        public body: ApiError,
    ) {
        super(body.message);
        this.name = 'ApiHttpError';
    }
}

export class VersionConflictError extends ApiHttpError {
    constructor(body: ApiError) {
        super(409, body);
        this.name = 'VersionConflictError';
    }
}

// Base URL for API calls — served from same domain in production
export const API_BASE = '/api';

// Base URL for auth routes
export const AUTH_BASE = '';

function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

async function apiFetch<T>(
    path: string,
    options: RequestInit & { version?: number } = {}
): Promise<ApiResponse<T>> {
    const { version, ...fetchOpts } = options;

    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(fetchOpts.headers as Record<string, string> || {}),
    };

    if (version !== undefined) {
        headers['If-Match'] = String(version);
    }

    const res = await fetch(`${API_BASE}${path}`, {
        ...fetchOpts,
        headers,
        credentials: 'include',
    });

    if (!res.ok) {
        const body: ApiError = await res.json().catch(() => ({
            code: res.status,
            message: res.statusText,
        }));

        if (res.status === 409) {
            throw new VersionConflictError(body);
        }
        throw new ApiHttpError(res.status, body);
    }

    const data = await res.json() as T;
    const versionHeader = res.headers.get('ETag');
    return {
        data,
        version: versionHeader ? parseInt(versionHeader, 10) : undefined,
    };
}

async function apiFetchWithFallback<T>(
    paths: string[],
    options: RequestInit & { version?: number } = {}
): Promise<ApiResponse<T>> {
    let lastError: unknown = null;
    for (const path of paths) {
        try {
            return await apiFetch<T>(path, options);
        } catch (err) {
            if (err instanceof ApiHttpError && err.status === 404) {
                lastError = err;
                continue;
            }
            throw err;
        }
    }
    throw lastError || new Error(`No API path available for: ${paths.join(', ')}`);
}

function normalizeCaseAction(value: unknown): ModerationCase['action'] {
    return value === 'warn' || value === 'timeout' || value === 'kick' || value === 'ban' || value === 'unban' || value === 'quarantine'
        ? value
        : 'note';
}

function normalizeCaseRecord(value: unknown): ModerationCase {
    const source = isObject(value) ? value : {};
    const targetUser = isObject(source.targetUser) ? source.targetUser : {};
    const moderator = isObject(source.moderator) ? source.moderator : {};
    return {
        id: typeof source.id === 'number' ? source.id : 0,
        guildId: typeof source.guildId === 'string' ? source.guildId : '',
        userId: typeof source.userId === 'string'
            ? source.userId
            : (typeof targetUser.id === 'string' ? targetUser.id : ''),
        userName: typeof source.userName === 'string'
            ? source.userName
            : (typeof targetUser.username === 'string' ? targetUser.username : 'Unknown User'),
        userAvatar: typeof source.userAvatar === 'string' ? source.userAvatar : null,
        moderatorId: typeof source.moderatorId === 'string'
            ? source.moderatorId
            : (typeof moderator.id === 'string' ? moderator.id : ''),
        moderatorName: typeof source.moderatorName === 'string'
            ? source.moderatorName
            : (typeof moderator.username === 'string' ? moderator.username : 'Unknown Moderator'),
        action: normalizeCaseAction(source.action),
        reason: typeof source.reason === 'string' ? source.reason : 'No reason provided',
        duration: typeof source.duration === 'string' ? source.duration : null,
        createdAt: typeof source.createdAt === 'string' ? source.createdAt : new Date(0).toISOString(),
        active: typeof source.active === 'boolean' ? source.active : true,
    };
}

function normalizeCasesPage(value: unknown): PaginatedResponse<ModerationCase> {
    const source = isObject(value) ? value : {};
    const itemsRaw = Array.isArray(source.data)
        ? source.data
        : (Array.isArray(source.items) ? source.items : []);
    const data = itemsRaw.map(normalizeCaseRecord);
    const cursor = typeof source.cursor === 'string'
        ? source.cursor
        : (typeof source.nextCursor === 'string' ? source.nextCursor : null);
    const hasMore = typeof source.hasMore === 'boolean' ? source.hasMore : false;
    const total = typeof source.total === 'number' ? source.total : data.length;
    return { data, cursor, hasMore, total };
}

function normalizeAuditEntry(value: unknown): AuditLogEntry {
    const source = isObject(value) ? value : {};
    const id = typeof source.id === 'string' || typeof source.id === 'number'
        ? String(source.id)
        : `audit_${Date.now()}_${Math.floor(Math.random() * 1_000_000)}`;
    return {
        id,
        guildId: typeof source.guildId === 'string' ? source.guildId : '',
        userId: typeof source.userId === 'string' ? source.userId : '',
        userName: typeof source.userName === 'string' ? source.userName : 'Unknown User',
        action: typeof source.action === 'string' ? source.action : 'config_update',
        target: typeof source.target === 'string' ? source.target : 'config',
        changes: isObject(source.changes) ? source.changes as AuditLogEntry['changes'] : {},
        timestamp: typeof source.timestamp === 'string' ? source.timestamp : new Date(0).toISOString(),
    };
}

function normalizeAuditPage(value: unknown): PaginatedResponse<AuditLogEntry> {
    const source = isObject(value) ? value : {};
    const itemsRaw = Array.isArray(source.data)
        ? source.data
        : (Array.isArray(source.items) ? source.items : []);
    const data = itemsRaw.map(normalizeAuditEntry);
    const cursor = typeof source.cursor === 'string'
        ? source.cursor
        : (typeof source.nextCursor === 'string' ? source.nextCursor : null);
    const hasMore = typeof source.hasMore === 'boolean' ? source.hasMore : false;
    const total = typeof source.total === 'number' ? source.total : data.length;
    return { data, cursor, hasMore, total };
}

// ─── API Client Interface ───────────────────────────────────────────────────

export interface ApiClient {
    // Auth
    getMe(): Promise<AuthUser>;
    logout(): Promise<void>;

    // Guilds
    getGuilds(): Promise<GuildSummary[]>;
    getGuildSummary(guildId: string): Promise<GuildSummary>;

    // Discord resources
    getChannels(guildId: string): Promise<DiscordChannel[]>;
    getRoles(guildId: string): Promise<DiscordRole[]>;
    searchUsers(guildId: string, query: string): Promise<DiscordUser[]>;

    // Capabilities
    getCapabilities(): Promise<BotCapabilities>;

    // Config
    getConfig(guildId: string): Promise<ApiResponse<GuildConfig>>;
    updateConfig(guildId: string, config: GuildConfig, version: number): Promise<ApiResponse<GuildConfig>>;
    validateConfig(guildId: string, config: GuildConfig): Promise<{ valid: boolean; errors: string[] }>;
    createSnapshot(guildId: string): Promise<{ snapshotId: string }>;
    rollbackConfig(guildId: string, snapshotId: string): Promise<ApiResponse<GuildConfig>>;

    // Commands
    getCommands(guildId: string): Promise<Record<string, CommandConfig>>;
    updateCommand(guildId: string, commandName: string, config: CommandConfig, version: number): Promise<ApiResponse<GuildConfig>>;
    batchCommands(guildId: string, action: 'enable' | 'disable', commands: string[], version: number): Promise<ApiResponse<GuildConfig>>;
    syncCommands(guildId: string): Promise<void>;
    getSyncStatus(guildId: string): Promise<SyncStatus>;

    // Modules
    getModules(guildId: string): Promise<Record<string, ModuleConfig>>;
    updateModule(guildId: string, moduleId: string, config: ModuleConfig, version: number): Promise<ApiResponse<GuildConfig>>;

    // Logging
    getLogging(guildId: string): Promise<Record<string, LoggingRouteConfig>>;
    updateLogging(guildId: string, logging: Record<string, LoggingRouteConfig>, version: number): Promise<ApiResponse<GuildConfig>>;

    // Cases
    getCases(guildId: string, cursor?: string): Promise<PaginatedResponse<ModerationCase>>;
    getCase(guildId: string, caseId: number): Promise<ModerationCase>;

    // Audit
    getAuditLog(guildId: string, cursor?: string): Promise<PaginatedResponse<AuditLogEntry>>;
}

// ─── Real API Client ────────────────────────────────────────────────────────

export const realApiClient: ApiClient = {
    async getMe() {
        const { data } = await apiFetch<AuthUser>('/me');
        return data;
    },
    async logout() {
        await apiFetch('/auth/logout', { method: 'POST' });
    },
    async getGuilds() {
        const { data } = await apiFetch<GuildSummary[]>('/guilds');
        return data;
    },
    async getGuildSummary(guildId) {
        const { data } = await apiFetch<GuildSummary>(`/guilds/${guildId}/summary`);
        return data;
    },
    async getChannels(guildId) {
        const { data } = await apiFetchWithFallback<DiscordChannel[]>([
            `/guilds/${guildId}/discord/channels`,
            `/guilds/${guildId}/channels`,
        ]);
        return data;
    },
    async getRoles(guildId) {
        const { data } = await apiFetchWithFallback<DiscordRole[]>([
            `/guilds/${guildId}/discord/roles`,
            `/guilds/${guildId}/roles`,
        ]);
        return data;
    },
    async searchUsers(guildId, query) {
        try {
            const { data } = await apiFetchWithFallback<DiscordUser[]>([
                `/guilds/${guildId}/discord/users/search?q=${encodeURIComponent(query)}`,
                `/guilds/${guildId}/users/search?q=${encodeURIComponent(query)}`,
            ]);
            return data;
        } catch (err) {
            if (err instanceof ApiHttpError && err.status === 404) {
                return [];
            }
            throw err;
        }
    },
    async getCapabilities() {
        const { data } = await apiFetch<BotCapabilities>('/bot/capabilities');
        return data;
    },
    async getConfig(guildId) {
        return apiFetch<GuildConfig>(`/guilds/${guildId}/config`);
    },
    async updateConfig(guildId, config, version) {
        return apiFetch<GuildConfig>(`/guilds/${guildId}/config`, {
            method: 'PUT',
            body: JSON.stringify(config),
            version,
        });
    },
    async validateConfig(guildId, config) {
        const { data } = await apiFetch<{ valid: boolean; errors: string[] }>(`/guilds/${guildId}/config/validate`, {
            method: 'POST',
            body: JSON.stringify(config),
        });
        return data;
    },
    async createSnapshot(guildId) {
        const { data } = await apiFetch<{ snapshotId: string }>(`/guilds/${guildId}/config/snapshot`, { method: 'POST' });
        return data;
    },
    async rollbackConfig(guildId, snapshotId) {
        return apiFetch<GuildConfig>(`/guilds/${guildId}/config/rollback`, {
            method: 'POST',
            body: JSON.stringify({ snapshotId }),
        });
    },
    async getCommands(guildId) {
        const { data } = await apiFetch<Record<string, CommandConfig>>(`/guilds/${guildId}/commands`);
        return data;
    },
    async updateCommand(guildId, commandName, config, version) {
        return apiFetch<GuildConfig>(`/guilds/${guildId}/commands/${commandName}`, {
            method: 'PUT',
            body: JSON.stringify(config),
            version,
        });
    },
    async batchCommands(guildId, action, commands, version) {
        return apiFetch<GuildConfig>(`/guilds/${guildId}/commands/batch`, {
            method: 'POST',
            body: JSON.stringify({ action, commands }),
            version,
        });
    },
    async syncCommands(guildId) {
        await apiFetch(`/guilds/${guildId}/commands/sync`, { method: 'POST' });
    },
    async getSyncStatus(guildId) {
        const { data } = await apiFetch<SyncStatus>(`/guilds/${guildId}/commands/sync/status`);
        return data;
    },
    async getModules(guildId) {
        const { data } = await apiFetch<Record<string, ModuleConfig>>(`/guilds/${guildId}/modules`);
        return data;
    },
    async updateModule(guildId, moduleId, config, version) {
        return apiFetch<GuildConfig>(`/guilds/${guildId}/modules/${moduleId}`, {
            method: 'PUT',
            body: JSON.stringify(config),
            version,
        });
    },
    async getLogging(guildId) {
        const { data } = await apiFetch<Record<string, LoggingRouteConfig>>(`/guilds/${guildId}/logging`);
        return data;
    },
    async updateLogging(guildId, logging, version) {
        return apiFetch<GuildConfig>(`/guilds/${guildId}/logging`, {
            method: 'PUT',
            body: JSON.stringify(logging),
            version,
        });
    },
    async getCases(guildId, cursor) {
        const params = cursor ? `?cursor=${cursor}` : '';
        const { data } = await apiFetch(`/guilds/${guildId}/cases${params}`);
        return normalizeCasesPage(data);
    },
    async getCase(guildId, caseId) {
        const { data } = await apiFetch(`/guilds/${guildId}/cases/${caseId}`);
        return normalizeCaseRecord(data);
    },
    async getAuditLog(guildId, cursor) {
        const params = cursor ? `?cursor=${cursor}` : '';
        try {
            const { data } = await apiFetch(`/guilds/${guildId}/audit${params}`);
            return normalizeAuditPage(data);
        } catch (err) {
            if (err instanceof ApiHttpError && err.status === 404) {
                return { data: [], cursor: null, hasMore: false, total: 0 };
            }
            throw err;
        }
    },
};
