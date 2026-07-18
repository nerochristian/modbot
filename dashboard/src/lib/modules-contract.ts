/**
 * Module manifest — the single source of truth for the Modules page.
 *
 * Each definition maps a bot feature to (a) the flat `<id>_enabled` key the bot
 * reads in its per-guild `guild_settings` JSON blob and (b) a schema of
 * customizable fields. The dashboard reads/writes those keys through the
 * bot-settings bridge (see `modules-service.ts`), so what an operator toggles
 * here is exactly what the running bot honors on its next `get_settings()` call.
 *
 * Resolution of "is this module enabled?" mirrors the bot's
 * `utils/server_setup.py:module_enabled()` — flat key first, then a nested
 * `modules[id].enabled`, then the field default — so dashboard and bot agree.
 */

export type ModuleFieldType =
  | 'toggle'
  | 'select'
  | 'text'
  | 'url'
  | 'number'
  | 'channelId'
  | 'channelIds'
  | 'roleId'
  | 'roleIds'
  | 'multiSelect'
  | 'autopunishRules'
  | 'ticketOptions'
  | 'appealQuestions'

export type AutopunishAction = 'timeout' | 'kick' | 'ban'

export type AutopunishRule = {
  warnings: number
  action: AutopunishAction
  durationMinutes: number | null
}

export type TicketQuestion = {
  id: string
  label: string
  placeholder: string
  style: 'short' | 'paragraph'
  required: boolean
}

export const DEFAULT_APPEAL_QUESTIONS: TicketQuestion[] = [
  { id: 'why', label: 'Why should this punishment be reviewed?', placeholder: 'Explain what happened and why staff should reconsider the case.', style: 'paragraph', required: true },
  { id: 'context', label: 'Anything else staff should know?', placeholder: 'Add evidence, message links, or relevant context.', style: 'paragraph', required: false },
]

export type TicketOption = {
  id: string
  label: string
  description: string
  emoji: string
  questions: TicketQuestion[]
}

export const DEFAULT_TICKET_OPTIONS: TicketOption[] = [
  { id: 'general', label: 'Support', description: 'Help with an issue', emoji: '🛠️', questions: [{ id: 'details', label: 'How can we help you?', placeholder: 'Describe your issue…', style: 'paragraph', required: true }] },
  { id: 'report', label: 'Report', description: 'Report a user or problem', emoji: '🚨', questions: [{ id: 'reported', label: 'Who are you reporting?', placeholder: 'Name or Discord ID', style: 'short', required: true }, { id: 'reason', label: 'What happened?', placeholder: 'Explain the situation…', style: 'paragraph', required: true }, { id: 'evidence', label: 'Evidence (optional)', placeholder: 'Message or media links', style: 'paragraph', required: false }] },
  { id: 'appeal', label: 'Appeal', description: 'Appeal a punishment', emoji: '📝', questions: [{ id: 'punishment', label: 'What are you appealing?', placeholder: 'Ban, timeout, warning…', style: 'short', required: true }, { id: 'appeal', label: 'Why should it be lifted?', placeholder: 'Give staff the relevant context…', style: 'paragraph', required: true }] },
  { id: 'other', label: 'Other', description: 'Anything else', emoji: '💬', questions: [{ id: 'details', label: 'How can we help you?', placeholder: 'Describe what you need…', style: 'paragraph', required: true }] },
]

export type ModuleField = {
  /** Flat settings key written to the bot's guild_settings blob. */
  key: string
  label: string
  type: ModuleFieldType
  hint?: string
  placeholder?: string
  options?: { label: string; value: string }[]
  /** Allowed Discord channel types for channel pickers. Defaults to text and announcement channels. */
  channelTypes?: number[]
  min?: number
  max?: number
  maxLength?: number
  /** Default shown when the key is absent. */
  fallback?: string | number | boolean | string[] | AutopunishRule[] | TicketOption[] | TicketQuestion[]
}

export type ModuleBadge = 'new' | 'standard' | 'premium' | 'core'

export type ModuleSpecial =
  | 'moderation'
  | 'aimod'
  | 'antiraid'
  | 'verification'
  | 'whitelist'
  | 'tickets'
  | 'logging'
  | 'welcome_card'
  | 'autoroles'
  | 'appeals'

export type ModuleDefinition = {
  id: string
  name: string
  description: string
  /** Category label used for grouping/search. */
  category: string
  /** lucide-react icon name (kebab-case) resolved on the client. */
  icon: string
  badge?: ModuleBadge
  /**
   * Flat enable key in guild_settings. `null` = core/always-on module with no
   * toggle (the card shows a static "Core" state and only opens settings).
   */
  enableKey: string | null
  /** Runtime default when both the flat and nested enable flags are absent. */
  defaultEnabled?: boolean
  /** When enabling this module should also imply another flag is on. */
  enableAlso?: Record<string, boolean>
  /**
   * For modules whose bot-side default enable-state derives from a configured
   * value (e.g. welcome is "on" when a channel is set) rather than a flag.
   * Used only when neither the flat key nor the nested module flag is present.
   */
  defaultOnKey?: string
  /** Deep-link to a dedicated page instead of an in-card settings modal. */
  settingsHref?: string
  /** Special modal renderer for non–flat-field modules. */
  special?: ModuleSpecial
  /** Customizable fields shown in the settings modal. */
  fields: ModuleField[]
}

const MAX_SIGNED_BIGINT = BigInt('9223372036854775807')

export function isDiscordSnowflake(value: unknown): boolean {
  if (typeof value !== 'string' && typeof value !== 'bigint') return false
  const candidate = String(value).trim()
  if (!/^\d{15,19}$/.test(candidate)) return false
  try {
    const parsed = BigInt(candidate)
    return parsed > BigInt(0) && parsed <= MAX_SIGNED_BIGINT
  } catch {
    return false
  }
}

export const DEFAULT_AUTOPUNISH_RULES: AutopunishRule[] = [
  { warnings: 3, action: 'timeout', durationMinutes: 30 },
  { warnings: 5, action: 'kick', durationMinutes: null },
  { warnings: 7, action: 'ban', durationMinutes: null },
]

/** The complete moderation workspace: policy, access, responses, and escalation. */
export const MODERATION_FIELDS: ModuleField[] = [
  {
    key: 'moderation_dm_users',
    label: 'DM users on kick, ban, or mute',
    type: 'toggle',
    hint: 'Send the member a direct message before the action is applied.',
    fallback: true,
  },
  {
    key: 'moderation_use_timeouts',
    label: 'Use Discord timeouts for mute',
    type: 'toggle',
    hint: 'Required by the current moderation runtime.',
    fallback: true,
  },
  {
    key: 'moderation_delete_commands',
    label: 'Delete moderation commands after execution',
    type: 'toggle',
    hint: 'Remove successful prefix commands from public channels.',
    fallback: true,
  },
  {
    key: 'moderation_respond_with_reason',
    label: 'Respond with the reason',
    type: 'toggle',
    hint: 'Include the supplied reason in the public action response.',
    fallback: true,
  },
  {
    key: 'moderation_preserve_ban_messages',
    label: 'Preserve messages on ban',
    type: 'toggle',
    hint: 'Do not remove the banned member\'s recent message history.',
    fallback: true,
  },
  {
    key: 'mod_log_channel',
    label: 'Moderation log channel',
    type: 'channelId',
    hint: 'Moderator actions will be logged in this channel.',
  },
  {
    key: 'mod_roles',
    label: 'Moderator roles',
    type: 'roleIds',
    hint: 'Members in these roles can use moderator commands.',
  },
  {
    key: 'protected_roles',
    label: 'Protected roles',
    type: 'roleIds',
    hint: 'Members in these roles cannot be muted, kicked, or banned by moderators.',
  },
  {
    key: 'lockdown_channels',
    label: 'Lockdown channels',
    type: 'channelIds',
    hint: 'Only these channels are locked by the lockdown command.',
  },
  {
    key: 'moderation_ban_response',
    label: 'Ban message',
    type: 'text',
    fallback: '***{user} was banned***',
    maxLength: 500,
  },
  {
    key: 'moderation_unban_response',
    label: 'Unban message',
    type: 'text',
    fallback: '***{user} was unbanned***',
    maxLength: 500,
  },
  {
    key: 'moderation_softban_response',
    label: 'Softban message',
    type: 'text',
    fallback: '***{user} was softbanned***',
    maxLength: 500,
  },
  {
    key: 'moderation_kick_response',
    label: 'Kick message',
    type: 'text',
    fallback: '***{user} was kicked***',
    maxLength: 500,
  },
  {
    key: 'moderation_mute_response',
    label: 'Mute message',
    type: 'text',
    fallback: '***{user} was muted***',
    maxLength: 500,
  },
  {
    key: 'moderation_unmute_response',
    label: 'Unmute message',
    type: 'text',
    fallback: '***{user} was unmuted***',
    maxLength: 500,
  },
  {
    key: 'moderation_autopunish_rules',
    label: 'Autopunish rules',
    type: 'autopunishRules',
    fallback: DEFAULT_AUTOPUNISH_RULES,
  },
]

export const MODULE_DEFINITIONS: readonly ModuleDefinition[] = [
  {
    id: 'moderation',
    name: 'Moderation',
    description: 'Core moderation policy, staff access, action messages, case log, and automatic escalation.',
    category: 'Moderation',
    icon: 'gavel',
    badge: 'core',
    enableKey: null,
    special: 'moderation',
    fields: MODERATION_FIELDS,
  },
  {
    id: 'automod',
    name: 'Automod',
    description: 'Layered automatic moderation — spam, links, invites, mentions, raids, and more.',
    category: 'Moderation',
    icon: 'shield-alert',
    badge: 'standard',
    enableKey: 'automod_enabled',
    defaultEnabled: true,
    settingsHref: '/dashboard/automod',
    fields: [],
  },
  {
    id: 'aimod',
    name: 'AI Moderation',
    description: 'Natural-language moderation and chat — mention the bot to act, ask, or pull a member’s record.',
    category: 'Moderation',
    icon: 'bot',
    badge: 'new',
    enableKey: 'aimod_enabled',
    defaultEnabled: false,
    special: 'aimod',
    fields: [
      { key: 'aimod_chat_enabled', label: 'Conversational chat', type: 'toggle', hint: 'Let members chat with Docket instead of limiting AI to staff actions.', fallback: false },
      { key: 'aimod_confirm_enabled', label: 'Confirm destructive actions', type: 'toggle', hint: 'Require an explicit confirmation before selected high-impact actions run.', fallback: true },
      { key: 'aimod_confirm_timeout_seconds', label: 'Confirmation window', type: 'number', min: 5, max: 300, fallback: 25, hint: 'Seconds before a pending confirmation expires.' },
      {
        key: 'aimod_confirm_actions',
        label: 'Actions that require confirmation',
        type: 'multiSelect',
        fallback: ['ban_member', 'kick_member', 'purge_messages', 'delete_channel', 'delete_role', 'delete_emoji', 'edit_guild', 'execute_raw_api', 'execute_python'],
        options: [
          { label: 'Ban member', value: 'ban_member' },
          { label: 'Kick member', value: 'kick_member' },
          { label: 'Purge messages', value: 'purge_messages' },
          { label: 'Delete channel', value: 'delete_channel' },
          { label: 'Delete role', value: 'delete_role' },
          { label: 'Delete emoji', value: 'delete_emoji' },
          { label: 'Edit server', value: 'edit_guild' },
          { label: 'Raw Discord API', value: 'execute_raw_api' },
          { label: 'Generated Python', value: 'execute_python' },
        ],
      },
      { key: 'aimod_context_messages', label: 'Context window', type: 'number', min: 1, max: 200, fallback: 100, hint: 'Recent messages available to Galaxy. Newest messages are kept within a bounded input budget.' },
      { key: 'aimod_location_context', label: 'Server location context', type: 'text', maxLength: 120, placeholder: 'Global community, English speaking', hint: 'Optional regional or community context for better interpretation.' },
      { key: 'aimod_model', label: 'Model override', type: 'text', maxLength: 120, placeholder: 'Use provider default', hint: 'Advanced provider model ID. Leave blank to follow the server default.' },
    ],
  },
  {
    id: 'antiraid',
    name: 'Anti-Raid',
    description: 'Detects coordinated joins and mass activity, quarantining suspected raiders on the spot.',
    category: 'Moderation',
    icon: 'shield-x',
    badge: 'standard',
    enableKey: 'antiraid_enabled',
    defaultEnabled: false,
    special: 'antiraid',
    fields: [
      { key: 'antiraid_join_threshold', label: 'Join burst threshold', type: 'number', min: 3, max: 100, hint: 'Number of joins that trips the raid alarm.', fallback: 10 },
      { key: 'antiraid_join_seconds', label: 'Detection window', type: 'number', min: 5, max: 300, hint: 'Seconds in which the join threshold must be reached.', fallback: 10 },
      { key: 'antiraid_cooldown_seconds', label: 'Response cooldown', type: 'number', min: 10, max: 3600, hint: 'Seconds before another raid response can run.', fallback: 60 },
      {
        key: 'antiraid_action', label: 'Raid response', type: 'select', fallback: 'kick', options: [
          { label: 'Kick recent joiners', value: 'kick' },
          { label: 'Ban recent joiners', value: 'ban' },
          { label: 'Quarantine recent joiners', value: 'quarantine' },
          { label: 'Lock configured channels', value: 'lockdown' },
        ],
      },
      {
        key: 'antiraid_raidmode_action', label: 'New joins during raid mode', type: 'select', fallback: 'kick', options: [
          { label: 'Kick', value: 'kick' },
          { label: 'Ban', value: 'ban' },
          { label: 'Quarantine', value: 'quarantine' },
        ],
      },
      { key: 'antiraid_quarantine_role', label: 'Quarantine role', type: 'roleId', hint: 'Required when either response uses quarantine.' },
      { key: 'lockdown_channels', label: 'Lockdown channels', type: 'channelIds', channelTypes: [0, 5], hint: 'Only these channels are locked when the configured response is lockdown.' },
      { key: 'antiraid_log_channel', label: 'Anti-Raid log channel', type: 'channelId', channelTypes: [0, 5], hint: 'Detection details and finalized actions are recorded here. Falls back to the moderation log.' },
      { key: 'antiraid_ai_enabled', label: 'AI raid scoring', type: 'toggle', hint: 'Score coordinated join patterns before enforcement.', fallback: false },
      { key: 'antiraid_ai_min_confidence', label: 'Minimum AI confidence', type: 'number', min: 0, max: 100, fallback: 70, hint: 'Confidence percentage required to treat a pattern as a raid.' },
      { key: 'antiraid_override_ai_action', label: 'Always use configured response', type: 'toggle', fallback: false, hint: 'Ignore the AI action recommendation and use the configured raid response.' },
    ],
  },
  {
    id: 'appeals',
    name: 'Appeals',
    description: 'Give punished members a secure, one-time form and route submissions to your staff review queue.',
    category: 'Moderation',
    icon: 'scale',
    badge: 'new',
    enableKey: 'appeals_enabled',
    defaultEnabled: false,
    special: 'appeals',
    fields: [
      { key: 'appeals_open', label: 'Accept new appeals', type: 'toggle', fallback: true, hint: 'Closing submissions disables every unused appeal link without deleting pending appeals.' },
      { key: 'appeal_staff_channel', label: 'Staff review channel', type: 'channelId', channelTypes: [0, 5], hint: 'New appeals and decisions are posted here.' },
      { key: 'appeal_expiry_days', label: 'Appeal link lifetime', type: 'number', min: 1, max: 30, fallback: 7, hint: 'Days before a one-time appeal link expires.' },
      { key: 'appeal_questions', label: 'Appeal questions', type: 'appealQuestions', fallback: DEFAULT_APPEAL_QUESTIONS, hint: 'Members answer these questions on the secure appeal page.' },
    ],
  },
  {
    id: 'verification',
    name: 'Verification',
    description: 'Gate new members behind a verification step before they can access the server.',
    category: 'Access',
    icon: 'user-check',
    badge: 'standard',
    enableKey: 'verification_enabled',
    defaultEnabled: false,
    special: 'verification',
    fields: [
      { key: 'verification_method', label: 'Verification method', type: 'select', fallback: 'discord', hint: 'Use Docket inside Discord, or send members to the protected website check.', options: [{ label: 'Discord captcha', value: 'discord' }, { label: 'Website · hCaptcha', value: 'website' }] },
      { key: 'verified_role', label: 'Verified role', type: 'roleId', hint: 'Granted once a member verifies' },
      { key: 'unverified_role', label: 'Unverified role', type: 'roleId', hint: 'Applied while a member is waiting to verify' },
      { key: 'verify_channel', label: 'Verification channel', type: 'channelId', channelTypes: [0, 5], hint: 'Channel that hosts the verification panel.' },
      { key: 'verify_log_channel', label: 'Verification log channel', type: 'channelId', channelTypes: [0, 5], hint: 'Successful and failed verification events are recorded here.' },
      { key: 'voice_verification_enabled', label: 'Voice verification', type: 'toggle', fallback: false },
      { key: 'waiting_verify_voice_channel', label: 'Voice waiting room', type: 'channelId', channelTypes: [2, 13], hint: 'Voice or stage channel used while a member waits for staff verification.' },
      { key: 'vc_verify_bypass_roles', label: 'Voice bypass roles', type: 'roleIds', hint: 'Members in these roles skip voice verification.' },
      { key: 'vc_verify_session_ttl', label: 'Voice session timeout', type: 'number', min: 60, max: 86400, fallback: 900, hint: 'Seconds before an unfinished voice verification session expires.' },
    ],
  },
  {
    id: 'whitelist',
    name: 'Whitelist',
    description: 'Strict access control for new non-administrator members who are not on the allowlist.',
    category: 'Access',
    icon: 'lock',
    badge: 'standard',
    enableKey: 'whitelist_enabled',
    defaultEnabled: false,
    special: 'whitelist',
    fields: [
      { key: 'whitelist_immunity', label: 'Administrator immunity', type: 'toggle', fallback: true, hint: 'Server administrators bypass whitelist enforcement.' },
      { key: 'whitelist_dm_join', label: 'DM rejected members', type: 'toggle', fallback: true, hint: 'Tell non-whitelisted members why they were removed before kicking them.' },
    ],
  },
  {
    id: 'tickets',
    name: 'Tickets',
    description: 'Support tickets with a deployed panel, private channels, transcripts, and staff actions.',
    category: 'Engagement',
    icon: 'ticket',
    badge: 'standard',
    enableKey: 'tickets_enabled',
    defaultEnabled: false,
    special: 'tickets',
    fields: [
      { key: 'ticket_category', label: 'Ticket category', type: 'channelId', channelTypes: [4], hint: 'Discord category new private ticket channels open under.' },
      { key: 'ticket_support_role', label: 'Support role', type: 'roleId', hint: 'Granted access to every new ticket.' },
      { key: 'ticket_log_channel', label: 'Ticket log channel', type: 'channelId', channelTypes: [0, 5], hint: 'Closed-ticket transcripts and staff actions are posted here.' },
      { key: 'ticket_options', label: 'Panel options and questions', type: 'ticketOptions', fallback: DEFAULT_TICKET_OPTIONS, hint: 'Each dropdown option can ask up to five questions. Emoji are optional.' },
    ],
  },
  {
    id: 'logging',
    name: 'Action Log',
    description: 'Customizable log of everything that happens in the server, routed per event type.',
    category: 'Engagement',
    icon: 'scroll-text',
    badge: 'standard',
    enableKey: 'logging_enabled',
    defaultEnabled: true,
    special: 'logging',
    fields: [
      { key: 'audit_log_channel', label: 'Audit events', type: 'channelId', channelTypes: [0, 5], hint: 'Role, channel, server, invite, and webhook changes.' },
      { key: 'message_log_channel', label: 'Message events', type: 'channelId', channelTypes: [0, 5], hint: 'Message edits, deletes, and purge records.' },
      { key: 'voice_log_channel', label: 'Voice events', type: 'channelId', channelTypes: [0, 5], hint: 'Voice joins, moves, disconnects, and moderation.' },
      { key: 'automod_log_channel', label: 'Automod events', type: 'channelId', channelTypes: [0, 5], hint: 'Automatic rule hits and AI moderation activity.' },
      { key: 'report_log_channel', label: 'Report events', type: 'channelId', channelTypes: [0, 5], hint: 'Member reports and review activity.' },
      { key: 'ticket_log_channel', label: 'Ticket events', type: 'channelId', channelTypes: [0, 5], hint: 'Ticket creation, closure, and transcripts.' },
    ],
  },
  {
    id: 'welcome',
    name: 'Welcome Card',
    description: 'Greet new members with a customizable welcome image and message.',
    category: 'Engagement',
    icon: 'image-plus',
    badge: 'new',
    enableKey: 'welcome_enabled',
    defaultEnabled: false,
    defaultOnKey: 'welcome_channel',
    special: 'welcome_card',
    fields: [
      { key: 'welcome_channel', label: 'Welcome channel', type: 'channelId', channelTypes: [0, 5], hint: 'Where the welcome card is posted.' },
      { key: 'welcome_server_name', label: 'Server name on card', type: 'text', maxLength: 80, placeholder: 'Use the Discord server name' },
      { key: 'welcome_system_name', label: 'System / subtitle', type: 'text', maxLength: 80, placeholder: 'Welcome System' },
      { key: 'welcome_bg_url', label: 'Background image URL', type: 'url', placeholder: 'https://…/bg.png' },
    ],
  },
  {
    id: 'autoroles',
    name: 'Auto Roles',
    description: 'Assign a role to new human members when server verification is not enabled.',
    category: 'Access',
    icon: 'user-plus',
    badge: 'standard',
    enableKey: 'autoroles_enabled',
    defaultEnabled: false,
    defaultOnKey: 'auto_role',
    special: 'autoroles',
    fields: [
      { key: 'auto_role', label: 'Join role', type: 'roleId', hint: 'Assigned automatically on join' },
    ],
  },
] as const

const DEFINITION_BY_ID = new Map<string, ModuleDefinition>()
for (const def of MODULE_DEFINITIONS) DEFINITION_BY_ID.set(def.id, def)

export function moduleDefinition(id: string): ModuleDefinition | null {
  return DEFINITION_BY_ID.get(id.trim().toLowerCase()) ?? null
}

/** Truthiness coercion matching the bot's bool handling of stored settings. */
function asBool(value: unknown): boolean | null {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') {
    const v = value.trim().toLowerCase()
    if (['1', 'true', 'yes', 'on', 'enabled'].includes(v)) return true
    if (['0', 'false', 'no', 'off', 'disabled', ''].includes(v)) return false
  }
  return null
}

/**
 * Resolve whether a module is enabled for a settings blob — mirrors the bot's
 * `module_enabled()`: flat `<id>_enabled` key, then `modules[id].enabled`, then
 * a presence/field default heuristic for keyless modules (autoroles/welcome).
 */
export function moduleEnabled(settings: Record<string, unknown>, def: ModuleDefinition): boolean {
  if (def.enableKey) {
    const flat = asBool(settings[def.enableKey])
    if (flat !== null) return flat
    const modules = settings.modules
    if (modules && typeof modules === 'object' && !Array.isArray(modules)) {
      const mod = (modules as Record<string, unknown>)[def.id]
      if (mod && typeof mod === 'object') {
        const nested = asBool((mod as Record<string, unknown>).enabled)
        if (nested !== null) return nested
      }
    }
    // Bot-side default: some modules (welcome) are "on" when a value is set.
    if (def.defaultOnKey) {
      const v = settings[def.defaultOnKey]
      const field = def.fields.find((candidate) => candidate.key === def.defaultOnKey)
      if (field?.type === 'roleId' || field?.type === 'channelId') return isDiscordSnowflake(v)
      return v !== undefined && v !== null && v !== ''
    }
    return def.defaultEnabled ?? false
  }
  // Keyless modules are "on" when their primary config value is present.
  if (def.id === 'moderation') return true // core, always on
  const primary = def.fields[0]?.key
  if (primary) {
    const value = settings[primary]
    const field = def.fields[0]
    if (field.type === 'roleId' || field.type === 'channelId') return isDiscordSnowflake(value)
    return value !== undefined && value !== null && value !== ''
  }
  return true
}
