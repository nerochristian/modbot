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

// ─── Base Fetch Wrapper ─────────────────────────────────────────────────────

const API_BASE = '/api';

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
        const { data } = await apiFetch<DiscordChannel[]>(`/guilds/${guildId}/discord/channels`);
        return data;
    },
    async getRoles(guildId) {
        const { data } = await apiFetch<DiscordRole[]>(`/guilds/${guildId}/discord/roles`);
        return data;
    },
    async searchUsers(guildId, query) {
        const { data } = await apiFetch<DiscordUser[]>(`/guilds/${guildId}/discord/users/search?q=${encodeURIComponent(query)}`);
        return data;
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
        const { data } = await apiFetch<PaginatedResponse<ModerationCase>>(`/guilds/${guildId}/cases${params}`);
        return data;
    },
    async getCase(guildId, caseId) {
        const { data } = await apiFetch<ModerationCase>(`/guilds/${guildId}/cases/${caseId}`);
        return data;
    },
    async getAuditLog(guildId, cursor) {
        const params = cursor ? `?cursor=${cursor}` : '';
        const { data } = await apiFetch<PaginatedResponse<AuditLogEntry>>(`/guilds/${guildId}/audit${params}`);
        return data;
    },
};
