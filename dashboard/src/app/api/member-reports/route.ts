import { handleError, ok, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { discordMemberAvatarUrl, getBotGuildMember } from '@/lib/discord'

type ReportRow = {
  id: string
  reporter_id: string
  reported_id: string
  reason: string
  resolved: boolean | number | string
  resolved_by: string | null
  created_at: Date
}

type Profile = { id: string; name: string; username: string; avatarUrl: string | null }

export async function GET(request: Request) {
  try {
    const guard = await requireUser('reports.read')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId!
    const url = new URL(request.url)
    const status = url.searchParams.get('status') || 'open'
    const q = (url.searchParams.get('q') || '').trim()
    const values: unknown[] = [guildId]
    const conditions = ['guild_id = $1::bigint']
    if (status === 'open') conditions.push('resolved = FALSE')
    if (status === 'resolved') conditions.push('resolved = TRUE')
    if (q) {
      values.push(`%${q}%`)
      conditions.push(`(reason ILIKE $${values.length} OR reported_id::text ILIKE $${values.length} OR reporter_id::text ILIKE $${values.length} OR id::text ILIKE $${values.length})`)
    }
    const rows = await botQuery<ReportRow>(
      `SELECT id::text, reporter_id::text, reported_id::text, reason, resolved,
         resolved_by::text, created_at
       FROM reports WHERE ${conditions.join(' AND ')}
       ORDER BY resolved ASC, created_at DESC LIMIT 200`,
      values,
    )
    const userIds = [...new Set(rows.flatMap((row) => [row.reporter_id, row.reported_id]))]
    const profiles = new Map<string, Profile>()
    await Promise.all(userIds.map(async (userId) => {
      try {
        const member = await getBotGuildMember(guildId, userId)
        profiles.set(userId, {
          id: userId,
          name: member.nick || member.user.global_name || member.user.username,
          username: member.user.username,
          avatarUrl: discordMemberAvatarUrl(guildId, member),
        })
      } catch {
        profiles.set(userId, { id: userId, name: `Discord user ${userId}`, username: userId, avatarUrl: null })
      }
    }))
    return ok({
      data: rows.map((row) => ({
        id: row.id,
        reason: row.reason,
        resolved: row.resolved === true || row.resolved === 1 || row.resolved === '1' || row.resolved === 'true',
        resolvedBy: row.resolved_by,
        createdAt: new Date(row.created_at).toISOString(),
        reporter: profiles.get(row.reporter_id),
        target: profiles.get(row.reported_id),
      })),
    })
  } catch (error) {
    return handleError(error)
  }
}
