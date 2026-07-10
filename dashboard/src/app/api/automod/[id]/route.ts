import { apiError, handleError, ok, requireUser } from '@/lib/api'
import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'
import { getSelectedGuild } from '@/lib/guild-context'
import { automodRuleSchema } from '@/lib/validation'

const RULE_KEYS: Record<string, { enabled: string; pattern?: string }> = {
  keyword: { enabled: 'automod_badwords_enabled', pattern: 'automod_badwords' },
  spam: { enabled: 'automod_spam_enabled', pattern: 'automod_spam_threshold' },
  mention_spam: { enabled: 'automod_mentions_enabled', pattern: 'automod_max_mentions' },
  invite: { enabled: 'automod_invites_enabled' },
  link: { enabled: 'automod_links_enabled' },
  caps: { enabled: 'automod_caps_enabled', pattern: 'automod_caps_percentage' },
  attachment: { enabled: 'automod_attachments_enabled', pattern: 'automod_attachment_threshold' },
}

export async function PATCH(request: Request, ctx: RouteContext<'/api/automod/[id]'>) {
  try {
    const guard = await requireUser('automod.write')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const { id } = await ctx.params
    const definition = RULE_KEYS[id]
    if (!definition) return apiError('AutoMod rule not found', 404)
    const data = automodRuleSchema.partial().parse(await request.json())
    const settings = await getBotGuildSettings(guild.id)
    const changes: Record<string, unknown> = {}
    if (data.enabled !== undefined) changes[definition.enabled] = data.enabled
    if (data.action) {
      const actions = typeof settings.automod_rule_actions === 'object' && settings.automod_rule_actions
        ? { ...(settings.automod_rule_actions as Record<string, string>) }
        : {}
      actions[id] = data.action
      changes.automod_rule_actions = actions
    }
    if (data.exemptRoles) changes.automod_bypass_roles = data.exemptRoles
    if (definition.pattern && data.pattern != null) {
      changes[definition.pattern] = id === 'keyword'
        ? data.pattern.split(',').map((word) => word.trim()).filter(Boolean)
        : Number(data.pattern)
    }
    await patchBotGuildSettings(guild.id, changes)
    return ok({ id, ...data })
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(_request: Request, ctx: RouteContext<'/api/automod/[id]'>) {
  try {
    const guard = await requireUser('automod.write')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const { id } = await ctx.params
    const definition = RULE_KEYS[id]
    if (!definition) return apiError('AutoMod rule not found', 404)
    await patchBotGuildSettings(guild.id, { [definition.enabled]: false })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
