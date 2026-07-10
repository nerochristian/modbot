import { apiError, handleError, ok, paginate, parseListQuery, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { getBotGuildMembers } from '@/lib/discord'
import { getSelectedGuild } from '@/lib/guild-context'

type MemberStats = {
  user_id: string
  warnings: string
  messages: string
  risk_score: number
  last_active: Date | null
}

function riskLevel(score: number): string {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'high'
  if (score >= 35) return 'medium'
  return 'low'
}

function avatarColor(id: string): string {
  const colors = ['#5865f2', '#3ddc97', '#f5a524', '#f0476b', '#38bdf8', '#8b5cf6']
  return colors[Number(BigInt(id) % BigInt(colors.length))]
}

export async function GET(request: Request) {
  try {
    const guard = await requireUser('members.read')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const query = parseListQuery(new URL(request.url), { defaultSort: 'joinedAt', maxPageSize: 100 })
    const discordMembers = await getBotGuildMembers(guild.id, query.page, query.pageSize, query.q)
    const ids = discordMembers.map((member) => member.user.id)
    const stats = ids.length
      ? await botQuery<MemberStats>(
          `SELECT ids.user_id,
             COALESCE(warnings.count, 0)::int AS warnings,
             COALESCE(messages.count, 0)::int AS messages,
             COALESCE(risk.score, 0)::int AS risk_score,
             messages.last_active
           FROM UNNEST($2::text[]) AS ids(user_id)
           LEFT JOIN (
             SELECT user_id::text, COUNT(*) AS count FROM warnings WHERE guild_id = $1::bigint GROUP BY user_id
           ) warnings ON warnings.user_id = ids.user_id
           LEFT JOIN (
             SELECT user_id::text, COUNT(*) AS count, MAX(timestamp) AS last_active
             FROM user_messages WHERE guild_id = $1::bigint GROUP BY user_id
           ) messages ON messages.user_id = ids.user_id
           LEFT JOIN user_risk_scores risk
             ON risk.guild_id = $1::bigint AND risk.user_id::text = ids.user_id`,
          [guild.id, ids],
        )
      : []
    const byId = new Map(stats.map((row) => [row.user_id, row]))
    let rows = discordMembers.map((member) => {
      const row = byId.get(member.user.id)
      const score = Number(row?.risk_score || 0)
      const timedOut = member.communication_disabled_until
        ? new Date(member.communication_disabled_until).getTime() > Date.now()
        : false
      const standing = timedOut ? 'muted' : score >= 35 ? 'watchlist' : 'good'
      return {
        id: member.user.id,
        username: member.user.username,
        displayName: member.nick || member.user.global_name || member.user.username,
        discordId: member.user.id,
        standing,
        riskLevel: riskLevel(score),
        warnings: Number(row?.warnings || 0),
        messages: Number(row?.messages || 0),
        note: null,
        avatarColor: avatarColor(member.user.id),
        joinedAt: member.joined_at,
        lastActiveAt: row?.last_active ? new Date(row.last_active).toISOString() : member.joined_at,
      }
    })
    if (query.filters.standing) rows = rows.filter((row) => row.standing === query.filters.standing)
    if (query.filters.riskLevel) rows = rows.filter((row) => row.riskLevel === query.filters.riskLevel)

    const sort = query.sort as keyof (typeof rows)[number]
    if (rows[0] && sort in rows[0]) {
      rows.sort((a, b) => {
        const av = a[sort]
        const bv = b[sort]
        const result = typeof av === 'number' && typeof bv === 'number'
          ? av - bv
          : String(av ?? '').localeCompare(String(bv ?? ''))
        return query.order === 'asc' ? result : -result
      })
    }
    const filtered = Boolean(query.q || query.filters.standing || query.filters.riskLevel)
    const total = filtered ? rows.length : guild.memberCount ?? rows.length
    const flagged = rows.filter((row) => row.standing !== 'good').length
    return ok({ ...paginate(rows, total, query), flagged })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST() {
  return apiError('Members are synchronized from Discord and cannot be created manually.', 405)
}
