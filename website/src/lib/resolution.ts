import type {
    GuildConfig,
    CommandConfig,
    ModuleConfig,
    OverrideEntry,
    ResolutionContext,
    ResolutionResult,
    LoggingRouteConfig,
} from '@/types';

// ─── Override Check Helpers ─────────────────────────────────────────────────

function isInList(list: string[] | undefined, id: string): boolean {
    return Array.isArray(list) && list.length > 0 && list.includes(id);
}

function hasAnyRole(userRoles: string[], roleList: string[] | undefined): boolean {
    if (!Array.isArray(roleList) || roleList.length === 0) return false;
    return userRoles.some(r => roleList.includes(r));
}

function checkOverrides(
    overrides: OverrideEntry,
    ctx: ResolutionContext
): { blocked: boolean; allowed: boolean; reason: string } {
    // 1. Check ignored users (hard deny)
    if (isInList(overrides.ignoredUsers, ctx.userId)) {
        return { blocked: true, allowed: false, reason: 'User is in ignored users list' };
    }

    // 2. Check allowed users (explicit allow, overrides role/channel denies)
    if (isInList(overrides.allowedUsers, ctx.userId)) {
        return { blocked: false, allowed: true, reason: 'User is in allowed users list' };
    }

    // 3. Check ignored roles
    if (hasAnyRole(ctx.userRoles, overrides.ignoredRoles)) {
        return { blocked: true, allowed: false, reason: 'User has an ignored role' };
    }

    // 4. Check allowed roles (if allowedRoles is set and non-empty, user must have one)
    if (Array.isArray(overrides.allowedRoles) && overrides.allowedRoles.length > 0) {
        if (!hasAnyRole(ctx.userRoles, overrides.allowedRoles)) {
            return { blocked: true, allowed: false, reason: 'User does not have any allowed role' };
        }
    }

    // 5. Check ignored channels
    if (isInList(overrides.ignoredChannels, ctx.channelId)) {
        return { blocked: true, allowed: false, reason: 'Channel is in ignored channels list' };
    }

    // 6. Check allowed channels (if set and non-empty, channel must be in list)
    if (Array.isArray(overrides.allowedChannels) && overrides.allowedChannels.length > 0) {
        if (!isInList(overrides.allowedChannels, ctx.channelId)) {
            return { blocked: true, allowed: false, reason: 'Channel is not in allowed channels list' };
        }
    }

    return { blocked: false, allowed: false, reason: 'No override matched' };
}

// ─── Command Resolution ─────────────────────────────────────────────────────

/**
 * Determines if a user can run a given command in a given channel.
 *
 * Resolution order:
 * 1. Global bypass check (bypass roles/users always pass)
 * 2. Command disabled check
 * 3. Command-level overrides (allow/ignore users → roles → channels)
 * 4. Module-level overrides (if command belongs to a module)
 * 5. Default → allowed
 */
export function resolveCommandPermission(
    ctx: ResolutionContext,
    config: GuildConfig,
    commandName: string,
    moduleId?: string
): ResolutionResult {
    // Layer 0: Global bypass — admins/bypass roles always pass
    if (isInList(config.globalBypassUsers, ctx.userId)) {
        return { allowed: true, reason: 'User is in global bypass list', resolvedBy: 'global_bypass' };
    }
    if (hasAnyRole(ctx.userRoles, config.globalBypassRoles)) {
        return { allowed: true, reason: 'User has a global bypass role', resolvedBy: 'global_bypass' };
    }

    // Layer 1: Command exists and is enabled?
    const cmdConfig: CommandConfig | undefined = config.commands[commandName];
    if (cmdConfig && !cmdConfig.enabled) {
        return { allowed: false, reason: 'Command is disabled', resolvedBy: 'command_enabled' };
    }

    // Layer 2: Module enabled? (if command belongs to a module)
    if (moduleId) {
        const modConfig: ModuleConfig | undefined = config.modules[moduleId];
        if (modConfig && !modConfig.enabled) {
            return { allowed: false, reason: `Module "${moduleId}" is disabled`, resolvedBy: 'module_enabled' };
        }

        // Layer 3: Module overrides
        if (modConfig) {
            const modOverride = checkOverrides(modConfig.overrides, ctx);
            if (modOverride.blocked) {
                return { allowed: false, reason: modOverride.reason, resolvedBy: 'module_override' };
            }
        }
    }

    // Layer 4: Command overrides
    if (cmdConfig) {
        const cmdOverride = checkOverrides(cmdConfig.overrides, ctx);
        if (cmdOverride.blocked) {
            return { allowed: false, reason: cmdOverride.reason, resolvedBy: 'command_override' };
        }
        if (cmdOverride.allowed) {
            return { allowed: true, reason: cmdOverride.reason, resolvedBy: 'command_override' };
        }
    }

    // Layer 5: Default — allowed
    return { allowed: true, reason: 'No restrictions matched', resolvedBy: 'default' };
}

// ─── Module Resolution ──────────────────────────────────────────────────────

/**
 * Determines if a module should act on an event in a given context.
 *
 * Resolution order:
 * 1. Global bypass check
 * 2. Module disabled check
 * 3. Module overrides (users → roles → channels)
 * 4. Default → module acts
 */
export function resolveModuleEnabled(
    moduleId: string,
    ctx: ResolutionContext,
    config: GuildConfig
): ResolutionResult {
    // Global bypass — bypass users/roles skip automod modules
    if (isInList(config.globalBypassUsers, ctx.userId)) {
        return { allowed: false, reason: 'User is in global bypass list (module skipped)', resolvedBy: 'global_bypass' };
    }
    if (hasAnyRole(ctx.userRoles, config.globalBypassRoles)) {
        return { allowed: false, reason: 'User has a bypass role (module skipped)', resolvedBy: 'global_bypass' };
    }

    const modConfig = config.modules[moduleId];
    if (!modConfig) {
        return { allowed: false, reason: 'Module not configured', resolvedBy: 'missing_config' };
    }

    if (!modConfig.enabled) {
        return { allowed: false, reason: 'Module is disabled', resolvedBy: 'module_enabled' };
    }

    // Module overrides (for automod: "allowed" means the module SHOULD ACT)
    const overrideResult = checkOverrides(modConfig.overrides, ctx);
    if (overrideResult.blocked) {
        return { allowed: false, reason: overrideResult.reason, resolvedBy: 'module_override' };
    }

    return { allowed: true, reason: 'Module is enabled and no exemptions matched', resolvedBy: 'default' };
}

// ─── Logging Route Resolution ───────────────────────────────────────────────

/**
 * Determines where an event type should be logged.
 *
 * Resolution order:
 * 1. Module-level logging route override (if moduleId provided)
 * 2. Event-type specific logging config
 * 3. No logging (disabled/not configured)
 */
export function resolveLoggingRoute(
    eventTypeId: string,
    config: GuildConfig,
    moduleId?: string
): { enabled: boolean; channelId: string | null; format: 'compact' | 'detailed'; resolvedBy: string } {
    // Layer 1: Module-level route override
    if (moduleId) {
        const modConfig = config.modules[moduleId];
        if (modConfig?.loggingRouteOverride) {
            return {
                enabled: true,
                channelId: modConfig.loggingRouteOverride,
                format: 'detailed',
                resolvedBy: 'module_override',
            };
        }
    }

    // Layer 2: Event type specific config
    const logConfig: LoggingRouteConfig | undefined = config.logging[eventTypeId];
    if (logConfig) {
        return {
            enabled: logConfig.enabled,
            channelId: logConfig.channelId,
            format: logConfig.format,
            resolvedBy: 'event_config',
        };
    }

    // Layer 3: Not configured
    return {
        enabled: false,
        channelId: null,
        format: 'compact',
        resolvedBy: 'default',
    };
}
