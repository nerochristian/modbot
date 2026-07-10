import { apiError, created, handleError, ok, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'
import { getSelectedGuild } from '@/lib/guild-context'
import { automodRuleSchema } from '@/lib/validation'

const RULES = [
  { id: 'keyword', name: 'Blocked words', enabledKey: 'automod_badwords_enabled', patternKey: 'automod_badwords' },
  { id: 'spam', name: 'Spam protection', enabledKey: 'automod_spam_enabled', patternKey: 'automod_spam_threshold' },
  { id: 'mention_spam', name: 'Mention spam', enabledKey: 'automod_mentions_enabled', patternKey: 'automod_max_mentions' },
  { id: 'invite', name: 'Discord invites', enabledKey: 'automod_invites_enabled' },
  { id: 'link', name: 'Dangerous links', enabledKey: 'automod_links_enabled' },
  { id: 'caps', name: 'Excessive caps', enabledKey: 'automod_caps_enabled', patternKey: 'automod_caps_percentage' },
  { id: 'attachment', name: 'Attachment spam', enabledKey: 'automod_attachments_enabled', patternKey: 'automod_attachment_threshold' },
] as const

function severity(action: string): string {
  if (action === 'ban') return 'critical'
  if (action === 'kick') return 'high'
  if (action === 'timeout' || action === 'mute') return 'medium'
  return 'low'
}

function pattern(settings: Record<string, unknown>, key?: string): string | null {
  if (!key) return null
  const value = settings[key]
  return Array.isArray(value) ? value.join(', ') : value == null ? null : String(value)
}

export async function GET() {
  try {
    const guard = await requireUser('automod.read')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const [settings, hits] = await Promise.all([
      getBotGuildSettings(guild.id),
      botQuery<{ rule: string; hits: string; last_triggered: Date | null }>(
        `SELECT rule, COUNT(*)::int AS hits, MAX(created_at) AS last_triggered
         FROM automod_events WHERE guild_id = $1::bigint GROUP BY rule`,
        [guild.id],
      ),
    ])
    const byRule = new Map(hits.map((row) => [row.rule, row]))
    const actions = typeof settings.automod_rule_actions === 'object' && settings.automod_rule_actions
      ? settings.automod_rule_actions as Record<string, string>
      : {}
    const fallbackAction = String(settings.automod_punishment || 'warn')
    const bypassRoles = Array.isArray(settings.automod_bypass_roles)
      ? settings.automod_bypass_roles.map(String)
      : []
    const now = new Date().toISOString()
    const rows = RULES.map((definition) => {
      const action = String(actions[definition.id] || fallbackAction)
      const telemetry = byRule.get(definition.id)
      return {
        id: definition.id,
        name: definition.name,
        description: `Live ${definition.name.toLowerCase()} configuration from Discord bot settings.`,
        trigger: definition.id,
        pattern: pattern(settings, 'patternKey' in definition ? definition.patternKey : undefined),
        action,
        severity: severity(action),
        exemptRoles: bypassRoles,
        enabled: settings[definition.enabledKey] !== false && settings.automod_enabled !== false,
        hits: Number(telemetry?.hits || 0),
        lastTriggeredAt: telemetry?.last_triggered ? new Date(telemetry.last_triggered).toISOString() : null,
        createdAt: now,
        updatedAt: now,
      }
    })
    return ok({
      data: rows,
      totalHits: rows.reduce((sum, row) => sum + row.hits, 0),
      activeCount: rows.filter((row) => row.enabled).length,
    })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireUser('automod.write')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const data = automodRuleSchema.parse(await request.json())
    const definition = RULES.find((rule) => rule.id === data.trigger)
    if (!definition) return apiError('This trigger is not supported by the bot runtime', 400)
    const settings = await getBotGuildSettings(guild.id)
    const actions = typeof settings.automod_rule_actions === 'object' && settings.automod_rule_actions
      ? { ...(settings.automod_rule_actions as Record<string, string>) }
      : {}
    actions[definition.id] = data.action
    const changes: Record<string, unknown> = {
      [definition.enabledKey]: data.enabled ?? true,
      automod_rule_actions: actions,
    }
    if ('patternKey' in definition && definition.patternKey && data.pattern != null) {
      changes[definition.patternKey] = definition.id === 'keyword'
        ? data.pattern.split(',').map((word) => word.trim()).filter(Boolean)
        : Number(data.pattern)
    }
    await patchBotGuildSettings(guild.id, changes)
    return created({ id: definition.id, ...data })
  } catch (error) {
    return handleError(error)
  }
}
