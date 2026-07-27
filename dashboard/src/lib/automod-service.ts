import 'server-only'

import { botQuery } from '@/lib/bot-db'
import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'
import { getBotGuildResources } from '@/lib/discord'
import {
  AUTOMOD_DEFINITIONS,
  automodDefinition,
  displayAutomodAction,
  normalizeAutomodRuleId,
  parseAutomodPattern,
  parseAutomodPolicy,
  serializeAutomodPattern,
  severityForAutomodAction,
  type AutomodAction,
} from '@/lib/automod-contract'
import { TEMPLATE_ALLOWED_KEYS } from '@/lib/automod-templates'

export type AutomodRuleInput = {
  name?: string
  description?: string | null
  trigger?: string
  pattern?: string | null
  action?: AutomodAction
  durationSeconds?: number | null
  deleteMessage?: boolean
  exemptRoles?: string[]
  enabled?: boolean
}

type TelemetryRow = { rule: string; hits: string; last_triggered: Date | null }

export async function listAutomodRules(guildId: string) {
  const [settings, telemetry] = await Promise.all([
    getBotGuildSettings(guildId),
    botQuery<TelemetryRow>(
      `SELECT LOWER(rule) AS rule, COUNT(*)::int AS hits, MAX(created_at) AS last_triggered
       FROM automod_events WHERE guild_id = $1::bigint GROUP BY LOWER(rule)`,
      [guildId],
    ),
  ])
  const hits = new Map<string, { hits: number; lastTriggeredAt: string | null }>()
  for (const row of telemetry) {
    const id = normalizeAutomodRuleId(row.rule)
    if (!id) continue
    const current = hits.get(id) ?? { hits: 0, lastTriggeredAt: null }
    current.hits += Number(row.hits || 0)
    const timestamp = row.last_triggered ? new Date(row.last_triggered).toISOString() : null
    if (timestamp && (!current.lastTriggeredAt || timestamp > current.lastTriggeredAt)) current.lastTriggeredAt = timestamp
    hits.set(id, current)
  }
  const rawPolicies = settings.automod_rule_actions
  const policies = rawPolicies && typeof rawPolicies === 'object' && !Array.isArray(rawPolicies)
    ? rawPolicies as Record<string, unknown>
    : {}
  const fallback = String(settings.automod_punishment ?? 'warn')
  const bypassRoles = Array.isArray(settings.automod_bypass_roles)
    ? settings.automod_bypass_roles.map(String).filter((id) => /^\d{15,22}$/.test(id))
    : []
  const now = new Date().toISOString()
  const rows = AUTOMOD_DEFINITIONS.map((definition) => {
    const policy = parseAutomodPolicy(policies[definition.id], fallback)
    const action = displayAutomodAction(policy)
    const event = hits.get(definition.id)
    return {
      id: definition.id,
      name: definition.name,
      description: definition.description,
      trigger: definition.id,
      pattern: serializeAutomodPattern(definition, definition.pattern ? settings[definition.pattern.setting] : null),
      action,
      durationSeconds: policy.duration ?? null,
      deleteMessage: policy.delete,
      severity: severityForAutomodAction(action),
      exemptRoles: bypassRoles,
      enabled: settings.automod_enabled !== false && settings[definition.enabledKey] !== false,
      hits: event?.hits ?? 0,
      lastTriggeredAt: event?.lastTriggeredAt ?? null,
      createdAt: now,
      updatedAt: now,
    }
  })
  return {
    data: rows,
    totalHits: rows.reduce((total, row) => total + row.hits, 0),
    activeCount: rows.filter((row) => row.enabled).length,
  }
}

export async function updateAutomodRule(guildId: string, idOrAlias: string, input: AutomodRuleInput) {
  const definition = automodDefinition(idOrAlias)
  if (!definition) throw new Error('AutoMod rule not found')
  const settings = await getBotGuildSettings(guildId)
  const changes: Record<string, unknown> = {}
  if (input.enabled !== undefined) {
    changes[definition.enabledKey] = input.enabled
    if (input.enabled) changes.automod_enabled = true
  }
  if (input.action !== undefined || input.durationSeconds !== undefined || input.deleteMessage !== undefined) {
    const existing = settings.automod_rule_actions
    const policies = existing && typeof existing === 'object' && !Array.isArray(existing)
      ? { ...(existing as Record<string, unknown>) }
      : {}
    const current = parseAutomodPolicy(policies[definition.id], String(settings.automod_punishment ?? 'warn'))
    const requestedAction = input.action ?? current.action
    const normalized = requestedAction === 'mute' ? 'timeout' : requestedAction === 'delete' ? 'log' : requestedAction
    const policy: Record<string, unknown> = {
      action: normalized,
      delete: input.deleteMessage ?? (requestedAction === 'delete' ? true : current.delete),
    }
    const duration = input.durationSeconds ?? current.duration
    if (normalized === 'timeout' && duration) policy.duration = Math.max(60, Math.min(2_419_200, Math.trunc(duration)))
    policies[definition.id] = policy
    changes.automod_rule_actions = policies
  }
  if (definition.pattern && input.pattern !== undefined) {
    changes[definition.pattern.setting] = parseAutomodPattern(definition, input.pattern)
  }
  if (input.exemptRoles !== undefined) {
    const ids = [...new Set(input.exemptRoles)]
    if (ids.some((id) => !/^\d{15,22}$/.test(id))) throw new Error('Exempt roles must be Discord role IDs')
    const resources = await getBotGuildResources(guildId)
    const guildRoleIds = new Set(resources.roles.map((role) => role.id))
    if (ids.some((id) => !guildRoleIds.has(id))) {
      throw new Error('Exempt roles must belong to this server')
    }
    changes.automod_bypass_roles = ids
  }
  if (Object.keys(changes).length > 0) {
    const persisted = await patchBotGuildSettings(guildId, changes)
    const mismatched = Object.entries(changes)
      .filter(([key, value]) => JSON.stringify(persisted[key]) !== JSON.stringify(value))
      .map(([key]) => key)
    if (mismatched.length > 0) {
      throw new Error(`AutoMod settings were not persisted: ${mismatched.sort().join(', ')}`)
    }
  }
  return { id: definition.id, ...input, trigger: definition.id }
}

export async function disableAutomodRule(guildId: string, idOrAlias: string): Promise<string> {
  const definition = automodDefinition(idOrAlias)
  if (!definition) throw new Error('AutoMod rule not found')
  await patchBotGuildSettings(guildId, { [definition.enabledKey]: false })
  return definition.id
}

const TEMPLATE_LIST_KEYS = new Set([
  'automod_links_blocklist',
  'automod_links_whitelist',
  'automod_whitelisted_domains',
  'automod_badwords',
  'automod_allowed_invites',
])
const TEMPLATE_DOMAIN_LIST_KEYS = new Set([
  'automod_links_blocklist',
  'automod_links_whitelist',
  'automod_whitelisted_domains',
])
const TEMPLATE_ACTION_KEYS = new Set(['automod_newaccount_join_action', 'automod_raid_punishment'])
const TEMPLATE_INT_KEYS = new Set([
  'automod_max_mentions',
  'automod_caps_percentage',
  'automod_caps_min_length',
  'automod_duplicate_threshold',
  'automod_emoji_spam_threshold',
  'automod_spam_threshold',
  'automod_fast_message_threshold',
  'automod_newaccount_days',
])

/**
 * Apply an AutoMod template: a validated map of flat `automod_*` keys written
 * atomically to the guild settings blob. Applying always arms the module.
 */
export async function applyAutomodTemplate(guildId: string, rawSettings: Record<string, unknown>) {
  const changes: Record<string, unknown> = { automod_enabled: true }
  for (const [key, value] of Object.entries(rawSettings)) {
    const ruleDefinition = AUTOMOD_DEFINITIONS.find((definition) => definition.enabledKey === key)
    if (ruleDefinition) {
      changes[key] = value === true
      continue
    }
    if (!TEMPLATE_ALLOWED_KEYS.has(key)) throw new Error(`Template key not allowed: ${key}`)
    if (key === 'automod_rule_actions') {
      const policies: Record<string, unknown> = {}
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        for (const [ruleId, policy] of Object.entries(value as Record<string, unknown>)) {
          const definition = automodDefinition(ruleId)
          if (!definition) throw new Error(`Unknown rule in template actions: ${ruleId}`)
          policies[definition.id] = parseAutomodPolicy(policy)
        }
      }
      changes[key] = policies
      continue
    }
    if (key === 'automod_links_mode') {
      const mode = String(value).trim().toLowerCase()
      if (!['dangerous', 'allowlist'].includes(mode)) throw new Error('Link mode must be "dangerous" or "allowlist"')
      changes[key] = mode
      continue
    }
    if (TEMPLATE_ACTION_KEYS.has(key)) {
      const action = String(value).trim().toLowerCase()
      if (!['none', 'log', 'warn', 'mute', 'timeout', 'kick', 'ban'].includes(action)) {
        throw new Error(`${key} must be a valid action`)
      }
      changes[key] = action
      continue
    }
    if (key === 'automod_delete_violations') {
      changes[key] = value === true
      continue
    }
    if (TEMPLATE_LIST_KEYS.has(key)) {
      if (!Array.isArray(value) || value.length > 300 || value.some((item) => typeof item !== 'string' || !item.trim() || item.length > 120)) {
        throw new Error(`${key} must be a list of up to 300 entries of at most 120 characters`)
      }
      const normalized = [...new Set(value.map((item) => TEMPLATE_DOMAIN_LIST_KEYS.has(key) ? item.trim().toLowerCase() : item.trim()))]
      changes[key] = normalized
      continue
    }
    if (TEMPLATE_INT_KEYS.has(key)) {
      const parsed = Number(value)
      if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > 500) {
        throw new Error(`${key} must be a whole number between 1 and 500`)
      }
      changes[key] = parsed
      continue
    }
  }
  const persisted = await patchBotGuildSettings(guildId, changes)
  const mismatched = Object.entries(changes)
    .filter(([key, value]) => JSON.stringify(persisted[key]) !== JSON.stringify(value))
    .map(([key]) => key)
  if (mismatched.length > 0) {
    throw new Error(`AutoMod template was not persisted: ${mismatched.sort().join(', ')}`)
  }
  return { applied: Object.keys(changes).sort() }
}
