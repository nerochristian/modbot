export const AUTOMOD_ACTIONS = ['none', 'log', 'warn', 'mute', 'timeout', 'kick', 'ban', 'delete'] as const
export type AutomodAction = (typeof AUTOMOD_ACTIONS)[number]

export type AutomodPolicy = {
  action: 'none' | 'log' | 'warn' | 'timeout' | 'kick' | 'ban'
  delete: boolean
  duration?: number
}

type PatternDefinition = {
  setting: string
  kind: 'integer' | 'list'
  min?: number
  max?: number
}

export type AutomodDefinition = {
  id: string
  name: string
  enabledKey: string
  pattern?: PatternDefinition
  aliases: readonly string[]
}

export const AUTOMOD_DEFINITIONS: readonly AutomodDefinition[] = [
  { id: 'badwords', name: 'Blocked words', enabledKey: 'automod_badwords_enabled', pattern: { setting: 'automod_badwords', kind: 'list' }, aliases: ['keyword', 'keywords', 'blocked_words'] },
  { id: 'scams', name: 'Scam protection', enabledKey: 'automod_scam_protection', aliases: ['scam', 'phishing'] },
  { id: 'spam', name: 'Spam protection', enabledKey: 'automod_spam_enabled', pattern: { setting: 'automod_spam_threshold', kind: 'integer', min: 2, max: 20 }, aliases: [] },
  { id: 'links', name: 'Dangerous links', enabledKey: 'automod_links_enabled', aliases: ['link'] },
  { id: 'invites', name: 'Discord invites', enabledKey: 'automod_invites_enabled', aliases: ['invite'] },
  { id: 'mentions', name: 'Mention spam', enabledKey: 'automod_mentions_enabled', pattern: { setting: 'automod_max_mentions', kind: 'integer', min: 1, max: 50 }, aliases: ['mention_spam'] },
  { id: 'caps', name: 'Excessive caps', enabledKey: 'automod_caps_enabled', pattern: { setting: 'automod_caps_percentage', kind: 'integer', min: 10, max: 100 }, aliases: [] },
  { id: 'duplicates', name: 'Duplicate messages', enabledKey: 'automod_duplicates_enabled', pattern: { setting: 'automod_duplicate_threshold', kind: 'integer', min: 2, max: 20 }, aliases: [] },
  { id: 'fast_messages', name: 'Fast messages', enabledKey: 'automod_fast_messages_enabled', pattern: { setting: 'automod_fast_message_threshold', kind: 'integer', min: 2, max: 20 }, aliases: ['fast_message'] },
  { id: 'emoji_spam', name: 'Emoji spam', enabledKey: 'automod_emoji_spam_enabled', pattern: { setting: 'automod_emoji_spam_threshold', kind: 'integer', min: 2, max: 100 }, aliases: ['emoji'] },
  { id: 'wall_spam', name: 'Wall spam', enabledKey: 'automod_wall_spam_enabled', pattern: { setting: 'automod_wall_spam_max_lines', kind: 'integer', min: 2, max: 100 }, aliases: ['wall'] },
  { id: 'attachments', name: 'Attachment spam', enabledKey: 'automod_attachments_enabled', pattern: { setting: 'automod_attachment_threshold', kind: 'integer', min: 2, max: 20 }, aliases: ['attachment'] },
  { id: 'unicode_spam', name: 'Unicode spam', enabledKey: 'automod_unicode_spam_enabled', pattern: { setting: 'automod_unicode_symbol_ratio', kind: 'integer', min: 1, max: 100 }, aliases: ['unicode'] },
  { id: 'new_accounts', name: 'New accounts', enabledKey: 'automod_newaccount_enabled', pattern: { setting: 'automod_newaccount_days', kind: 'integer', min: 1, max: 365 }, aliases: ['new_account', 'identity'] },
  { id: 'raid', name: 'Raid protection', enabledKey: 'automod_raid_enabled', pattern: { setting: 'automod_raid_join_threshold', kind: 'integer', min: 2, max: 100 }, aliases: ['raids'] },
] as const

const DEFINITION_BY_ID = new Map<string, AutomodDefinition>()
for (const definition of AUTOMOD_DEFINITIONS) {
  DEFINITION_BY_ID.set(definition.id, definition)
  for (const alias of definition.aliases) DEFINITION_BY_ID.set(alias, definition)
}

export function automodDefinition(value: string): AutomodDefinition | null {
  return DEFINITION_BY_ID.get(value.trim().toLowerCase()) ?? null
}

export function normalizeAutomodRuleId(value: string): string | null {
  return automodDefinition(value)?.id ?? null
}

export function parseAutomodPolicy(value: unknown, fallbackAction = 'warn'): AutomodPolicy {
  const source = value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : { action: value }
  const rawAction = String(source.action ?? fallbackAction).trim().toLowerCase()
  const action = rawAction === 'mute' ? 'timeout' : rawAction === 'delete' ? 'log' : rawAction
  const normalized: AutomodPolicy['action'] = ['none', 'log', 'warn', 'timeout', 'kick', 'ban'].includes(action)
    ? action as AutomodPolicy['action']
    : 'warn'
  const durationValue = Number(source.duration)
  const policy: AutomodPolicy = {
    action: normalized,
    delete: source.delete === undefined ? rawAction !== 'none' : Boolean(source.delete),
  }
  if (normalized === 'timeout' && Number.isFinite(durationValue) && durationValue > 0) {
    policy.duration = Math.max(60, Math.min(2_419_200, Math.trunc(durationValue)))
  }
  return policy
}

export function displayAutomodAction(policy: AutomodPolicy): AutomodAction {
  if (policy.action === 'log' && policy.delete) return 'delete'
  return policy.action
}

export function serializeAutomodPattern(definition: AutomodDefinition, value: unknown): string | null {
  if (!definition.pattern) return null
  if (definition.pattern.kind === 'list') {
    return Array.isArray(value) ? value.map(String).join(', ') : value == null ? null : String(value)
  }
  return value == null ? null : String(value)
}

export function parseAutomodPattern(definition: AutomodDefinition, value: string | null | undefined): unknown {
  if (!definition.pattern || value == null) return undefined
  if (definition.pattern.kind === 'list') {
    const items = value.split(',').map((item) => item.trim()).filter(Boolean)
    if (items.length > 200) throw new Error('A rule can contain at most 200 entries')
    if (items.some((item) => item.length > 120)) throw new Error('Rule entries cannot exceed 120 characters')
    return items
  }
  if (!/^\d+$/.test(value.trim())) throw new Error(`${definition.name} threshold must be a whole number`)
  const parsed = Number(value)
  const min = definition.pattern.min ?? Number.MIN_SAFE_INTEGER
  const max = definition.pattern.max ?? Number.MAX_SAFE_INTEGER
  if (!Number.isSafeInteger(parsed) || parsed < min || parsed > max) {
    throw new Error(`${definition.name} threshold must be between ${min} and ${max}`)
  }
  return parsed
}

export function severityForAutomodAction(action: AutomodAction): string {
  if (action === 'ban') return 'critical'
  if (action === 'kick') return 'high'
  if (action === 'timeout' || action === 'mute') return 'medium'
  return 'low'
}
