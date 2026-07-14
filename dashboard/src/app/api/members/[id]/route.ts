import { apiError, handleError, ok, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import {
  discordMemberAvatarUrl,
  getBotGuildMember,
  getBotGuildMemberRoles,
} from '@/lib/discord'
import { getSelectedGuild } from '@/lib/guild-context'

type MemberStats = {
  warnings: string
  messages: string
  risk_score: number
  last_active: Date | null
}

type MemberCase = {
  id: string
  case_number: number
  action: string
  reason: string
  severity: string
  status: string
  moderator_id: string
  created_at: Date
}

function riskLevel(score: number): string {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'high'
  if (score >= 35) return 'medium'
  return 'low'
}

export async function GET(_request: Request, ctx: RouteContext<'/api/members/[id]'>) {
  try {
    const guard = await requireUser('members.read')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const { id } = await ctx.params
    if (!/^\d{15,22}$/.test(id)) return apiError('Member not found', 404)
    await ensureDashboardBackendSchema()
    const [member, resources, stats, cases] = await Promise.all([
      getBotGuildMember(guild.id, id),
      getBotGuildMemberRoles(guild.id),
      botQuery<MemberStats>(
        `SELECT
           (SELECT COUNT(*) FROM warnings WHERE guild_id = $1::bigint AND user_id = $2::bigint)::int AS warnings,
           (SELECT COUNT(*) FROM user_messages WHERE guild_id = $1::bigint AND user_id = $2::bigint)::int AS messages,
           COALESCE((SELECT score FROM user_risk_scores WHERE guild_id = $1::bigint AND user_id = $2::bigint), 0)::int AS risk_score,
           (SELECT MAX(timestamp) FROM user_messages WHERE guild_id = $1::bigint AND user_id = $2::bigint) AS last_active`,
        [guild.id, id],
      ),
      botQuery<MemberCase>(
        `SELECT id::text, case_number, LOWER(action) AS action, reason,
           COALESCE(severity, 'low') AS severity,
           COALESCE(status, CASE WHEN active = 1 THEN 'open' ELSE 'resolved' END) AS status,
           moderator_id::text, created_at
         FROM cases
         WHERE guild_id = $1::bigint AND user_id = $2::bigint
         ORDER BY created_at DESC
         LIMIT 8`,
        [guild.id, id],
      ),
    ])
    const row = stats[0]
    const score = Number(row?.risk_score || 0)
    const rolesById = new Map(resources.map((role) => [role.id, role]))
    return ok({
      id,
      discordId: id,
      username: member.user.username,
      displayName: member.nick || member.user.global_name || member.user.username,
      avatarUrl: discordMemberAvatarUrl(guild.id, member),
      joinedAt: member.joined_at,
      lastActiveAt: row?.last_active ? new Date(row.last_active).toISOString() : null,
      timedOutUntil: member.communication_disabled_until ?? null,
      warnings: Number(row?.warnings || 0),
      messages: Number(row?.messages || 0),
      riskScore: score,
      riskLevel: riskLevel(score),
      roles: member.roles
        .map((roleId) => rolesById.get(roleId))
        .filter((role): role is NonNullable<typeof role> => Boolean(role))
        .map((role) => ({ id: role.id, name: role.name, color: role.color })),
      records: cases.map((record) => ({
        id: record.id,
        ref: Number(record.case_number),
        action: record.action,
        reason: record.reason || 'No reason provided',
        severity: record.severity,
        status: record.status,
        moderatorId: record.moderator_id,
        createdAt: new Date(record.created_at).toISOString(),
      })),
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
