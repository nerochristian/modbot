import 'server-only'

import { botQuery } from '@/lib/bot-db'
import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'
import {
  MODULE_DEFINITIONS,
  isDiscordSnowflake,
  moduleDefinition,
  moduleEnabled,
  type ModuleDefinition,
  type ModuleField,
} from '@/lib/modules-contract'
import {
  legacyThresholdSnapshot,
  moderationAutopunishRulesFromSettings,
  parseModerationAutopunishRules,
  type ModerationAutopunishRule,
} from '@/lib/moderation-contract'

export type ModuleValues = Record<
  string,
  string | number | boolean | string[] | ModerationAutopunishRule[] | null
>

export class ModuleValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ModuleValidationError'
  }
}

const MODERATION_RESPONSE_KEYS = new Set([
  'moderation_ban_response',
  'moderation_unban_response',
  'moderation_softban_response',
  'moderation_kick_response',
  'moderation_mute_response',
  'moderation_unmute_response',
])
const MODERATION_RESPONSE_TOKENS = new Set(['user', 'reason', 'moderator', 'duration'])
const LEGACY_MODERATION_ROLE_KEYS = [
  'owner_role',
  'admin_role',
  'manager_role',
  'supervisor_role',
  'senior_mod_role',
  'mod_role',
  'trial_mod_role',
  'staff_role',
] as const
const LEGACY_MODERATION_ROLE_LIST_KEYS = [
  'admin_roles',
  'manager_roles',
  'supervisor_roles',
  'senior_mod_roles',
  'moderator_roles',
] as const

export type ModuleView = {
  id: string
  name: string
  description: string
  category: string
  badge?: string
  enableKey: string | null
  settingsHref?: string
  special?: string
  toggleable: boolean
  enabled: boolean
  fields: ModuleField[]
  values: ModuleValues
}

function readValue(settings: Record<string, unknown>, field: ModuleField): ModuleValues[string] {
  if (field.key === 'moderation_use_timeouts') return true
  const raw = settings[field.key]
  switch (field.type) {
    case 'toggle':
      return raw === undefined || raw === null
        ? Boolean(field.fallback ?? false)
        : Boolean(raw === true || raw === 1 || raw === 'true' || raw === 'on' || raw === 'yes')
    case 'number': {
      const n = Number(raw)
      return Number.isFinite(n) ? n : (typeof field.fallback === 'number' ? field.fallback : null)
    }
    case 'roleIds':
    case 'channelIds':
      return Array.isArray(raw) ? raw.map(String).filter(isDiscordSnowflake) : []
    case 'autopunishRules':
      return moderationAutopunishRulesFromSettings(settings)
    default: {
      if (raw === undefined || raw === null) return field.fallback !== undefined ? String(field.fallback) : ''
      return String(raw)
    }
  }
}

function viewFor(def: ModuleDefinition, settings: Record<string, unknown>): ModuleView {
  const values: ModuleValues = {}
  for (const field of def.fields) values[field.key] = readValue(settings, field)
  return {
    id: def.id,
    name: def.name,
    description: def.description,
    category: def.category,
    badge: def.badge,
    enableKey: def.enableKey,
    settingsHref: def.settingsHref,
    special: def.special,
    toggleable: def.enableKey !== null,
    enabled: moduleEnabled(settings, def),
    fields: def.fields,
    values,
  }
}

export async function listModules(guildId: string): Promise<{ data: ModuleView[]; enabledCount: number }> {
  const settings = await getBotGuildSettings(guildId)
  const data = MODULE_DEFINITIONS.map((def) => viewFor(def, settings))
  return { data, enabledCount: data.filter((m) => m.enabled).length }
}

export async function getModule(guildId: string, id: string): Promise<ModuleView> {
  const def = moduleDefinition(id)
  if (!def) throw new Error('Module not found')
  const settings = await getBotGuildSettings(guildId)
  return viewFor(def, settings)
}

/** Coerce/validate an incoming field value against its declared type. */
function coerceField(field: ModuleField, value: unknown): unknown {
  switch (field.type) {
    case 'toggle':
      if (typeof value !== 'boolean') throw new ModuleValidationError(`${field.label} must be true or false`)
      return value
    case 'number': {
      const raw = typeof value === 'number'
        ? value
        : typeof value === 'string' && /^-?\d+$/.test(value.trim())
          ? Number(value.trim())
          : Number.NaN
      if (!Number.isSafeInteger(raw)) throw new ModuleValidationError(`${field.label} must be a whole number`)
      const n = raw
      if (field.min !== undefined && n < field.min) throw new ModuleValidationError(`${field.label} must be ≥ ${field.min}`)
      if (field.max !== undefined && n > field.max) throw new ModuleValidationError(`${field.label} must be ≤ ${field.max}`)
      return n
    }
    case 'roleId':
    case 'channelId': {
      if (value !== null && value !== undefined && typeof value !== 'string') {
        throw new ModuleValidationError(`${field.label} must be sent as a Discord ID string`)
      }
      const s = String(value ?? '').trim()
      if (s === '') return null
      if (!isDiscordSnowflake(s)) throw new ModuleValidationError(`${field.label} must be a valid Discord ID or blank`)
      return s
    }
    case 'roleIds':
    case 'channelIds': {
      if (Array.isArray(value) && value.some((item) => typeof item !== 'string')) {
        throw new ModuleValidationError(`${field.label} must be sent as Discord ID strings`)
      }
      if (!Array.isArray(value) && typeof value !== 'string') {
        throw new ModuleValidationError(`${field.label} must be sent as Discord ID strings`)
      }
      const list = Array.isArray(value)
        ? value.map((v) => v.trim())
        : value.split(',').map((v) => v.trim())
      const ids = [...new Set(list.filter(Boolean))]
      if (ids.some((id) => !isDiscordSnowflake(id))) throw new ModuleValidationError(`${field.label} must be valid Discord IDs`)
      return ids
    }
    case 'autopunishRules': {
      try {
        return parseModerationAutopunishRules(value)
      } catch (error) {
        throw new ModuleValidationError(error instanceof Error ? error.message : 'Invalid autopunish rules')
      }
    }
    case 'url': {
      if (value !== null && value !== undefined && typeof value !== 'string') {
        throw new ModuleValidationError(`${field.label} must be a URL string`)
      }
      const s = String(value ?? '').trim()
      if (s === '') return null
      if (s.length > (field.maxLength ?? 2048)) throw new ModuleValidationError(`${field.label} is too long`)
      try {
        const u = new URL(s)
        if (u.protocol !== 'https:') throw new Error()
      } catch {
        throw new ModuleValidationError(`${field.label} must be a valid HTTPS URL or blank`)
      }
      return s
    }
    case 'select': {
      if (typeof value !== 'string') throw new ModuleValidationError(`${field.label} must be a valid option`)
      const candidate = value.trim()
      if (!field.options?.some((option) => option.value === candidate)) {
        throw new ModuleValidationError(`${field.label} must be a valid option`)
      }
      return candidate
    }
    default: {
      if (value !== null && value !== undefined && typeof value !== 'string') {
        throw new ModuleValidationError(`${field.label} must be text`)
      }
      const s = String(value ?? '').trim()
      if (s.length > (field.maxLength ?? 200)) throw new ModuleValidationError(`${field.label} is too long`)
      return s === '' ? null : s
    }
  }
}

export async function updateModuleSettings(
  guildId: string,
  id: string,
  patch: Record<string, unknown>,
): Promise<ModuleView> {
  const def = moduleDefinition(id)
  if (!def) throw new Error('Module not found')
  const changes: Record<string, unknown> = {}
  const allowedKeys = new Set(def.fields.map((field) => field.key))
  const unknownKeys = Object.keys(patch).filter((key) => !allowedKeys.has(key))
  if (unknownKeys.length > 0) {
    throw new ModuleValidationError(`Unsupported setting: ${unknownKeys.join(', ')}`)
  }
  for (const field of def.fields) {
    if (!(field.key in patch)) continue
    changes[field.key] = coerceField(field, patch[field.key])
    if (field.key === 'moderation_use_timeouts' && changes[field.key] !== true) {
      throw new ModuleValidationError('Discord timeouts are required for mute actions')
    }
    if (MODERATION_RESPONSE_KEYS.has(field.key) && typeof changes[field.key] === 'string') {
      const tokens = Array.from((changes[field.key] as string).matchAll(/\{([^{}]+)\}/g), (match) => match[1])
      const unsupported = [...new Set(tokens.filter((token) => !MODERATION_RESPONSE_TOKENS.has(token)))]
      if (unsupported.length) {
        throw new ModuleValidationError(`Unsupported response placeholder: {${unsupported[0]}}`)
      }
    }
  }
  if ('moderation_autopunish_rules' in changes) {
    Object.assign(
      changes,
      legacyThresholdSnapshot(changes.moderation_autopunish_rules as ModerationAutopunishRule[]),
    )
  }
  if ('mod_roles' in changes) {
    for (const key of LEGACY_MODERATION_ROLE_KEYS) changes[key] = null
    for (const key of LEGACY_MODERATION_ROLE_LIST_KEYS) changes[key] = []
  }
  if ('mod_log_channel' in changes) {
    changes.log_channel_mod = changes.mod_log_channel
  }
  if (Object.keys(changes).length > 0) await patchBotGuildSettings(guildId, changes)
  const updatedSettings = await getBotGuildSettings(guildId)
  return viewFor(def, updatedSettings)
}

export async function setModuleEnabled(
  guildId: string,
  id: string,
  enabled: boolean,
): Promise<ModuleView> {
  const def = moduleDefinition(id)
  if (!def) throw new Error('Module not found')
  if (!def.enableKey) throw new Error(`${def.name} cannot be toggled`)
  const settings = await getBotGuildSettings(guildId)
  if (enabled && def.id === 'verification' && (
    !isDiscordSnowflake(settings.verified_role) || !isDiscordSnowflake(settings.unverified_role)
  )) {
    throw new ModuleValidationError('Set both verified and unverified roles before enabling verification')
  }
  if (enabled && def.id === 'tickets' && !isDiscordSnowflake(settings.ticket_category)) {
    throw new ModuleValidationError('Set a ticket category before enabling tickets')
  }
  if (enabled && def.id === 'welcome' && !isDiscordSnowflake(settings.welcome_channel)) {
    throw new ModuleValidationError('Set a welcome channel before enabling the welcome card')
  }
  const changes: Record<string, unknown> = { [def.enableKey]: enabled }
  if (enabled && def.enableAlso) Object.assign(changes, def.enableAlso)
  await patchBotGuildSettings(guildId, changes)
  const updatedSettings = await getBotGuildSettings(guildId)
  return viewFor(def, updatedSettings)
}

// ---------------------------------------------------------------------------
// Whitelist — lives in its own bot table, not the settings blob.
// Mirrors db/access_mixin.py (whitelist: guild_id, user_id, added_by, created_at).
// ---------------------------------------------------------------------------

export type WhitelistEntry = { userId: string; addedBy: string | null; createdAt: string | null }

export async function listWhitelist(guildId: string): Promise<WhitelistEntry[]> {
  const rows = await botQuery<{ user_id: string; added_by: string | null; created_at: Date | null }>(
    `SELECT user_id, added_by, created_at FROM whitelist WHERE guild_id = $1::bigint ORDER BY created_at DESC NULLS LAST`,
    [guildId],
  )
  return rows.map((r) => ({
    userId: String(r.user_id),
    addedBy: r.added_by ? String(r.added_by) : null,
    createdAt: r.created_at ? new Date(r.created_at).toISOString() : null,
  }))
}

export async function addWhitelist(guildId: string, userId: string, addedBy: string): Promise<boolean> {
  if (!isDiscordSnowflake(userId)) throw new ModuleValidationError('User must be a valid Discord ID')
  const rows = await botQuery<{ user_id: string }>(
    `INSERT INTO whitelist (guild_id, user_id, added_by)
     VALUES ($1::bigint, $2::bigint, $3::bigint)
     ON CONFLICT (guild_id, user_id) DO NOTHING
     RETURNING user_id`,
    [guildId, userId, addedBy],
  )
  return rows.length > 0
}

export async function removeWhitelist(guildId: string, userId: string): Promise<boolean> {
  if (!isDiscordSnowflake(userId)) throw new ModuleValidationError('User must be a valid Discord ID')
  const rows = await botQuery<{ user_id: string }>(
    `DELETE FROM whitelist WHERE guild_id = $1::bigint AND user_id = $2::bigint RETURNING user_id`,
    [guildId, userId],
  )
  return rows.length > 0
}
