import 'server-only'

import { botQuery } from '@/lib/bot-db'
import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'
import { getBotGuildResources } from '@/lib/discord'
import {
  MODULE_DEFINITIONS,
  isDiscordSnowflake,
  moduleDefinition,
  moduleEnabled,
  type ModuleDefinition,
  type ModuleField,
  type TicketOption,
  type TicketQuestion,
  DEFAULT_TICKET_OPTIONS,
  DEFAULT_APPEAL_QUESTIONS,
} from '@/lib/modules-contract'
import {
  legacyThresholdSnapshot,
  moderationAutopunishRulesFromSettings,
  parseModerationAutopunishRules,
  type ModerationAutopunishRule,
} from '@/lib/moderation-contract'

export type ModuleValues = Record<
  string,
  string | number | boolean | string[] | ModerationAutopunishRule[] | TicketOption[] | TicketQuestion[] | null
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

const SETTING_ALIASES: Readonly<Record<string, readonly string[]>> = {
  verified_role: ['verification_role'],
  verify_channel: ['verification_channel'],
  verify_log_channel: ['verification_log_channel'],
  audit_log_channel: ['log_channel_audit'],
  message_log_channel: ['log_channel_message'],
  voice_log_channel: ['log_channel_voice'],
  automod_log_channel: ['log_channel_automod'],
  report_log_channel: ['log_channel_report'],
  ticket_log_channel: ['log_channel_ticket'],
}

function settingValue(settings: Record<string, unknown>, key: string): unknown {
  if (settings[key] !== undefined && settings[key] !== null) return settings[key]
  for (const alias of SETTING_ALIASES[key] ?? []) {
    if (settings[alias] !== undefined && settings[alias] !== null) return settings[alias]
  }
  return undefined
}

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
  const raw = settingValue(settings, field.key)
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
    case 'multiSelect': {
      const allowed = new Set(field.options?.map((option) => option.value) ?? [])
      const fallback = Array.isArray(field.fallback) ? field.fallback.map(String) : []
      if (!Array.isArray(raw)) return fallback.filter((value) => allowed.has(value))
      return [...new Set(raw.map(String).filter((value) => allowed.has(value)))]
    }
    case 'autopunishRules':
      return moderationAutopunishRulesFromSettings(settings)
    case 'ticketOptions': {
      const source = Array.isArray(raw) ? raw : (field.fallback ?? DEFAULT_TICKET_OPTIONS)
      return structuredClone(source as TicketOption[])
    }
    case 'appealQuestions': {
      const source = Array.isArray(raw) ? raw : (field.fallback ?? DEFAULT_APPEAL_QUESTIONS)
      return structuredClone(source as TicketQuestion[])
    }
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
    case 'ticketOptions': {
      if (!Array.isArray(value) || value.length < 1 || value.length > 10) {
        throw new ModuleValidationError('Tickets need between 1 and 10 panel options')
      }
      const ids = new Set<string>()
      return value.map((rawOption, optionIndex) => {
        if (!rawOption || typeof rawOption !== 'object' || Array.isArray(rawOption)) {
          throw new ModuleValidationError(`Ticket option ${optionIndex + 1} is invalid`)
        }
        const option = rawOption as Record<string, unknown>
        const id = String(option.id ?? '').trim().toLowerCase()
        const label = String(option.label ?? '').trim()
        const description = String(option.description ?? '').trim()
        const emoji = String(option.emoji ?? '').trim()
        if (!/^[a-z0-9_-]{2,40}$/.test(id) || ids.has(id)) throw new ModuleValidationError('Every ticket option needs a unique ID')
        if (label.length < 2 || label.length > 100) throw new ModuleValidationError('Ticket option labels must be 2–100 characters')
        if (description.length > 100) throw new ModuleValidationError('Ticket option descriptions can be at most 100 characters')
        if (emoji.length > 64) throw new ModuleValidationError('Ticket option emoji is too long')
        ids.add(id)
        if (!Array.isArray(option.questions) || option.questions.length < 1 || option.questions.length > 5) {
          throw new ModuleValidationError(`${label} needs between 1 and 5 questions`)
        }
        const questionIds = new Set<string>()
        const questions = option.questions.map((rawQuestion, questionIndex) => {
          if (!rawQuestion || typeof rawQuestion !== 'object' || Array.isArray(rawQuestion)) {
            throw new ModuleValidationError(`${label} question ${questionIndex + 1} is invalid`)
          }
          const question = rawQuestion as Record<string, unknown>
          const questionId = String(question.id ?? '').trim().toLowerCase()
          const questionLabel = String(question.label ?? '').trim()
          const placeholder = String(question.placeholder ?? '').trim()
          const style = question.style === 'short' ? 'short' : 'paragraph'
          if (!/^[a-z0-9_-]{2,40}$/.test(questionId) || questionIds.has(questionId)) throw new ModuleValidationError(`${label} question IDs must be unique`)
          if (questionLabel.length < 2 || questionLabel.length > 45) throw new ModuleValidationError(`${label} question labels must be 2–45 characters`)
          if (placeholder.length > 100) throw new ModuleValidationError(`${label} question placeholders can be at most 100 characters`)
          questionIds.add(questionId)
          return { id: questionId, label: questionLabel, placeholder, style, required: question.required !== false }
        })
        return { id, label, description, emoji, questions }
      })
    }
    case 'appealQuestions': {
      if (!Array.isArray(value) || value.length < 1 || value.length > 5) {
        throw new ModuleValidationError('Appeals need between 1 and 5 questions')
      }
      const ids = new Set<string>()
      return value.map((rawQuestion, index) => {
        if (!rawQuestion || typeof rawQuestion !== 'object' || Array.isArray(rawQuestion)) {
          throw new ModuleValidationError(`Appeal question ${index + 1} is invalid`)
        }
        const question = rawQuestion as Record<string, unknown>
        const id = String(question.id ?? '').trim().toLowerCase()
        const label = String(question.label ?? '').trim()
        const placeholder = String(question.placeholder ?? '').trim()
        const style = question.style === 'short' ? 'short' : 'paragraph'
        if (!/^[a-z0-9_-]{2,40}$/.test(id) || ids.has(id)) throw new ModuleValidationError('Appeal question IDs must be unique')
        if (label.length < 2 || label.length > 80) throw new ModuleValidationError('Appeal question labels must be 2–80 characters')
        if (placeholder.length > 160) throw new ModuleValidationError('Appeal question placeholders can be at most 160 characters')
        ids.add(id)
        return { id, label, placeholder, style, required: question.required !== false }
      })
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
    case 'multiSelect': {
      if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
        throw new ModuleValidationError(`${field.label} must be sent as a list of options`)
      }
      const allowed = new Set(field.options?.map((option) => option.value) ?? [])
      const selections = [...new Set(value.map((item) => item.trim()).filter(Boolean))]
      if (selections.length > 30) throw new ModuleValidationError(`${field.label} has too many selections`)
      if (selections.some((item) => !allowed.has(item))) {
        throw new ModuleValidationError(`${field.label} contains an unsupported option`)
      }
      return selections
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
  const resourceFields = def.fields.filter((field) => (
    field.key in changes
    && ['roleId', 'roleIds', 'channelId', 'channelIds'].includes(field.type)
  ))
  if (resourceFields.length > 0) {
    const resources = await getBotGuildResources(guildId)
    const roleIds = new Set(resources.roles.map((role) => role.id))
    const channelTypes = new Map(resources.channels.map((channel) => [channel.id, channel.type]))
    for (const field of resourceFields) {
      const values = Array.isArray(changes[field.key])
        ? changes[field.key] as string[]
        : changes[field.key]
          ? [String(changes[field.key])]
          : []
      if (field.type === 'roleId' || field.type === 'roleIds') {
        if (values.some((id) => !roleIds.has(id))) {
          throw new ModuleValidationError(`${field.label} must belong to this server`)
        }
      } else {
        const allowedTypes = new Set(field.channelTypes ?? [0, 5])
        if (values.some((id) => !channelTypes.has(id) || !allowedTypes.has(channelTypes.get(id)!))) {
          throw new ModuleValidationError(`${field.label} must be a compatible channel in this server`)
        }
      }
    }
  }
  const currentSettings = await getBotGuildSettings(guildId)
  const mergedSettings = { ...currentSettings, ...changes }
  if (def.id === 'antiraid') {
    const quarantineSelected = ['antiraid_action', 'antiraid_raidmode_action']
      .some((key) => mergedSettings[key] === 'quarantine')
    if (quarantineSelected && !isDiscordSnowflake(mergedSettings.antiraid_quarantine_role)) {
      throw new ModuleValidationError('Select a quarantine role before using the quarantine response')
    }
    if (mergedSettings.antiraid_action === 'lockdown') {
      const channels = mergedSettings.lockdown_channels
      if (!Array.isArray(channels) || channels.length === 0) {
        throw new ModuleValidationError('Select at least one lockdown channel before using the lockdown response')
      }
    }
  }
  if (def.id === 'verification' && mergedSettings.voice_verification_enabled) {
    if (!isDiscordSnowflake(mergedSettings.waiting_verify_voice_channel)) {
      throw new ModuleValidationError('Select a voice waiting room before enabling voice verification')
    }
  }
  if (def.id === 'verification' && mergedSettings.verification_method === 'website' && (
    !process.env.TURNSTILE_SITE_KEY?.trim() || !process.env.TURNSTILE_SECRET_KEY?.trim()
  )) {
    throw new ModuleValidationError('Website verification needs TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY on the dashboard server')
  }
  if (
    def.id === 'verification'
    && isDiscordSnowflake(settingValue(mergedSettings, 'verified_role'))
    && settingValue(mergedSettings, 'verified_role') === mergedSettings.unverified_role
  ) {
    throw new ModuleValidationError('Verified and unverified roles must be different')
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
  for (const [key, aliases] of Object.entries(SETTING_ALIASES)) {
    if (!(key in changes)) continue
    for (const alias of aliases) changes[alias] = changes[key]
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
  const resourceBackedModules = new Set(['verification', 'tickets', 'appeals', 'welcome', 'autoroles', 'antiraid'])
  const resources = enabled && resourceBackedModules.has(def.id)
    ? await getBotGuildResources(guildId)
    : null
  const roleIds = new Set(resources?.roles.map((role) => role.id) ?? [])
  const channelTypes = new Map(resources?.channels.map((channel) => [channel.id, channel.type]) ?? [])
  const hasRole = (value: unknown) => typeof value === 'string' && roleIds.has(value)
  const hasChannel = (value: unknown, allowedTypes: number[]) => (
    typeof value === 'string'
    && channelTypes.has(value)
    && allowedTypes.includes(channelTypes.get(value)!)
  )
  if (enabled && def.id === 'verification' && (
    !hasRole(settingValue(settings, 'verified_role'))
    || !hasRole(settings.unverified_role)
    || settingValue(settings, 'verified_role') === settings.unverified_role
    || !hasChannel(settingValue(settings, 'verify_channel'), [0, 5])
  )) {
    throw new ModuleValidationError('Set a verification channel plus two different server roles before enabling verification')
  }
  if (enabled && def.id === 'verification' && settings.voice_verification_enabled && (
    !hasChannel(settings.waiting_verify_voice_channel, [2, 13])
  )) {
    throw new ModuleValidationError('Set a voice waiting room before enabling voice verification')
  }
  if (enabled && def.id === 'tickets' && !hasChannel(settings.ticket_category, [4])) {
    throw new ModuleValidationError('Set a ticket category before enabling tickets')
  }
  if (enabled && def.id === 'appeals' && !hasChannel(settings.appeal_staff_channel, [0, 5])) {
    throw new ModuleValidationError('Set a staff review channel before enabling appeals')
  }
  if (enabled && def.id === 'welcome' && !hasChannel(settings.welcome_channel, [0, 5])) {
    throw new ModuleValidationError('Set a welcome channel before enabling the welcome card')
  }
  if (enabled && def.id === 'autoroles' && !hasRole(settings.auto_role)) {
    throw new ModuleValidationError('Set a join role before enabling auto roles')
  }
  if (enabled && def.id === 'antiraid') {
    const quarantineSelected = ['antiraid_action', 'antiraid_raidmode_action']
      .some((key) => settings[key] === 'quarantine')
    if (quarantineSelected && !hasRole(settings.antiraid_quarantine_role)) {
      throw new ModuleValidationError('Set a quarantine role before enabling Anti-Raid')
    }
    if (settings.antiraid_action === 'lockdown') {
      const channels = settings.lockdown_channels
      if (!Array.isArray(channels) || channels.length === 0 || channels.some((id) => !hasChannel(id, [0, 5]))) {
        throw new ModuleValidationError('Set at least one lockdown channel before enabling Anti-Raid')
      }
    }
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
