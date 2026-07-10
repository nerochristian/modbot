import { apiError, created, handleError, ok, paginate, parseListQuery, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { executeModerationAction } from '@/lib/discord'
import { getSelectedGuild } from '@/lib/guild-context'
import { caseSchema } from '@/lib/validation'

type BotCase = {
  id: string
  case_number: number
  user_id: string
  moderator_id: string
  action: string
  reason: string
  duration: string | null
  created_at: Date
  active: boolean
}

const SORTS: Record<string, string> = {
  ref: 'case_number',
  type: 'action',
  status: 'active',
  createdAt: 'created_at',
  expiresAt: 'created_at',
  severity: 'action',
}

function severity(action: string): string {
  if (action === 'ban') return 'critical'
  if (action === 'kick') return 'high'
  if (action === 'timeout' || action === 'mute') return 'medium'
  return 'low'
}

function present(row: BotCase) {
  const userId = String(row.user_id)
  return {
    id: String(row.id),
    ref: Number(row.case_number),
    memberId: userId,
    type: row.action,
    severity: severity(row.action),
    status: row.active ? 'open' : 'resolved',
    reason: row.reason || 'No reason provided',
    moderator: `Moderator ${row.moderator_id}`,
    channel: null,
    expiresAt: null,
    createdAt: new Date(row.created_at).toISOString(),
    member: {
      id: userId,
      username: userId,
      displayName: `Discord user ${userId}`,
      discordId: userId,
      avatarColor: '#5865f2',
    },
  }
}

export async function GET(request: Request) {
  try {
    const guard = await requireUser('cases.read')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'createdAt', maxPageSize: 100 })
    const conditions = ['guild_id = $1::bigint']
    const values: unknown[] = [guild.id]
    const add = (sql: string, value: unknown) => {
      values.push(value)
      conditions.push(sql.replace('?', `$${values.length}`))
    }
    if (query.q) {
      values.push(`%${query.q}%`)
      const index = values.length
      conditions.push(`(reason ILIKE $${index} OR action ILIKE $${index} OR user_id::text ILIKE $${index} OR case_number::text ILIKE $${index})`)
    }
    if (query.filters.type) add('LOWER(action) = LOWER(?)', query.filters.type)
    if (query.filters.status === 'open') conditions.push('active = TRUE')
    if (query.filters.status === 'resolved') conditions.push('active = FALSE')
    const memberId = query.filters.memberId || url.searchParams.get('member')
    if (memberId) add('user_id = ?::bigint', memberId)
    if (query.filters.severity) {
      const actions: Record<string, string[]> = {
        low: ['note', 'warn', 'unban'],
        medium: ['mute', 'timeout'],
        high: ['kick'],
        critical: ['ban'],
      }
      const selected = actions[query.filters.severity]
      if (selected) {
        values.push(selected)
        conditions.push(`LOWER(action) = ANY($${values.length}::text[])`)
      }
    }

    const where = conditions.join(' AND ')
    const sort = SORTS[query.sort] || 'created_at'
    const direction = query.order === 'asc' ? 'ASC' : 'DESC'
    values.push(query.pageSize, (query.page - 1) * query.pageSize)
    const limitIndex = values.length - 1
    const offsetIndex = values.length
    const [rows, totals, opens] = await Promise.all([
      botQuery<BotCase>(
        `SELECT id::text, case_number, user_id::text, moderator_id::text, LOWER(action) AS action,
           reason, duration, created_at, active
         FROM cases WHERE ${where}
         ORDER BY ${sort} ${direction} LIMIT $${limitIndex} OFFSET $${offsetIndex}`,
        values,
      ),
      botQuery<{ value: string }>(`SELECT COUNT(*) AS value FROM cases WHERE ${where}`, values.slice(0, -2)),
      botQuery<{ value: string }>(`SELECT COUNT(*) AS value FROM cases WHERE ${where} AND active = TRUE`, values.slice(0, -2)),
    ])
    const total = Number(totals[0]?.value || 0)
    return ok({ ...paginate(rows.map(present), total, query), open: Number(opens[0]?.value || 0) })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireUser('cases.write')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    if (!guard.discordId) return apiError('Reconnect your Discord account', 401)

    const data = caseSchema.parse(await request.json())
    if (!/^\d{15,22}$/.test(data.memberId)) return apiError('Invalid Discord member ID', 400)
    await executeModerationAction(guild.id, data.memberId, data.type, data.durationHours ?? 0)

    const rows = await botQuery<BotCase>(
      `WITH lock AS (
         SELECT pg_advisory_xact_lock(hashtext($1))
       ), next_case AS (
         SELECT COALESCE(MAX(case_number), 0) + 1 AS case_number FROM cases, lock WHERE guild_id = $2::bigint
       )
       INSERT INTO cases (guild_id, case_number, user_id, moderator_id, action, reason, duration, active)
       SELECT $2::bigint, next_case.case_number, $3::bigint, $4::bigint, $5, $6, $7, TRUE FROM next_case
       RETURNING id::text, case_number, user_id::text, moderator_id::text, LOWER(action) AS action,
         reason, duration, created_at, active`,
      [`dashboard-case-${guild.id}`, guild.id, data.memberId, guard.discordId, data.type, data.reason, data.durationHours ? `${data.durationHours}h` : null],
    )
    return created(present(rows[0]))
  } catch (error) {
    return handleError(error)
  }
}
