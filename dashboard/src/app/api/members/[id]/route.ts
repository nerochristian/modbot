import { apiError, handleError, ok, requireUser } from '@/lib/api'
import { getBotGuildMember } from '@/lib/discord'
import { getSelectedGuild } from '@/lib/guild-context'

export async function GET(_request: Request, ctx: RouteContext<'/api/members/[id]'>) {
  try {
    const guard = await requireUser('members.read')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const { id } = await ctx.params
    if (!/^\d{15,22}$/.test(id)) return apiError('Member not found', 404)
    const member = await getBotGuildMember(guild.id, id)
    return ok({
      id,
      discordId: id,
      username: member.user.username,
      displayName: member.nick || member.user.global_name || member.user.username,
      joinedAt: member.joined_at,
    })
  } catch (error) {
    return handleError(error)
  }
}

export async function PATCH() {
  return apiError('Member profiles are synchronized from Discord.', 405)
}

export async function DELETE() {
  return apiError('Use a moderation case to kick or ban a Discord member.', 405)
}
