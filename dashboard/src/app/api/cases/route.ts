import { apiError, created, handleError, ok, paginate, parseListQuery, requireMutation, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import {
  createModerationCase,
  isValidIdempotencyKey,
  ProtectedModerationTargetError,
} from '@/lib/moderation-service'
import { issueAppealToken } from '@/lib/appeal-portal-service'
import { dashboardBaseUrl } from '@/lib/discord'
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
  active: number | string
  severity: string
  status: string
  channel: string | null
  expires_at: Date | null
  updated_at: Date
  execution_status: string
  command_id: string | null
  error_message: string | null
}

const SORTS: Record<string, string> = {
  ref: 'cases.case_number',
  type: 'cases.action',
  status: 'cases.status',
  createdAt: 'cases.created_at',
  expiresAt: 'cases.expires_at',
  severity: `CASE cases.severity WHEN 'low' THEN 1 WHEN 'medium' THEN 2 WHEN 'high' THEN 3 WHEN 'critical' THEN 4 ELSE 0 END`,
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
    severity: row.severity || severity(row.action),
    status: row.status || (Number(row.active) !== 0 ? 'open' : 'resolved'),
    reason: row.reason || 'No reason provided',
    moderator: `Moderator ${row.moderator_id}`,
    channel: row.channel,
    expiresAt: row.expires_at ? new Date(row.expires_at).toISOString() : null,
    executionStatus: row.execution_status,
    commandId: row.command_id,
    error: row.error_message,
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
    const guildId = guard.selectedGuildId!
    await ensureDashboardBackendSchema()

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'createdAt', maxPageSize: 100 })
    const conditions = ['cases.guild_id = $1::bigint']
    const values: unknown[] = [guildId]
    const add = (sql: string, value: unknown) => {
      values.push(value)
      conditions.push(sql.replace('?', `$${values.length}`))
    }
    if (query.q) {
      values.push(`%${query.q}%`)
      const index = values.length
      conditions.push(`(cases.reason ILIKE $${index} OR cases.action ILIKE $${index} OR cases.user_id::text ILIKE $${index} OR cases.case_number::text ILIKE $${index})`)
    }
    if (query.filters.type) add('LOWER(cases.action) = LOWER(?)', query.filters.type)
    if (query.filters.status && ['open', 'resolved', 'expired', 'appealed', 'failed', 'pending'].includes(query.filters.status)) {
      add('cases.status = ?', query.filters.status)
    }
    const memberId = query.filters.memberId || url.searchParams.get('member')
    if (memberId) {
      if (!/^\d{15,22}$/.test(memberId)) return apiError('Invalid Discord member ID', 400)
      add('cases.user_id = ?::bigint', memberId)
    }
    if (query.filters.severity) {
      if (['low', 'medium', 'high', 'critical'].includes(query.filters.severity)) {
        add('LOWER(cases.severity) = LOWER(?)', query.filters.severity)
      }
    }

    const where = conditions.join(' AND ')
    const sort = SORTS[query.sort] || 'cases.created_at'
    const direction = query.order === 'asc' ? 'ASC' : 'DESC'
    values.push(query.pageSize, (query.page - 1) * query.pageSize)
    const limitIndex = values.length - 1
    const offsetIndex = values.length
    const [rows, totals, opens] = await Promise.all([
      botQuery<BotCase>(
         `SELECT cases.id::text, cases.case_number, cases.user_id::text, cases.moderator_id::text,
            LOWER(cases.action) AS action, cases.reason, cases.duration, cases.created_at,
            cases.updated_at, cases.active, cases.severity, cases.status, cases.channel,
            cases.expires_at, cases.execution_status, commands.id::text AS command_id, commands.error_message
          FROM cases LEFT JOIN dashboard_moderation_commands commands ON commands.id = cases.dashboard_command_id
          WHERE ${where}
         ORDER BY ${sort} ${direction} LIMIT $${limitIndex} OFFSET $${offsetIndex}`,
        values,
      ),
      botQuery<{ value: string }>(`SELECT COUNT(*) AS value FROM cases WHERE ${where}`, values.slice(0, -2)),
      botQuery<{ value: string }>(`SELECT COUNT(*) AS value FROM cases WHERE ${where} AND cases.active = 1`, values.slice(0, -2)),
    ])
    const total = Number(totals[0]?.value || 0)
    return ok({ ...paginate(rows.map(present), total, query), open: Number(opens[0]?.value || 0) })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'cases.write')
    if (guard instanceof Response) return guard
    if (!guard.discordId) return apiError('Reconnect your Discord account', 401)

    const data = caseSchema.parse(await request.json())
    if (data.durationHours && !['mute', 'timeout'].includes(data.type)) {
      return apiError('A duration is only supported for mute or timeout actions', 400)
    }
    const durationHours = ['mute', 'timeout'].includes(data.type) ? data.durationHours || 1 : null
    const headerKey = request.headers.get('idempotency-key')?.trim()
    const idempotencyKey = data.idempotencyKey || headerKey || crypto.randomUUID()
    if (!isValidIdempotencyKey(idempotencyKey)) return apiError('Invalid idempotency key', 400)
    const result = await createModerationCase({
      guildId: guard.selectedGuildId!,
      actor: { id: guard.id, discordId: guard.discordId, name: guard.name },
      targetUserId: data.memberId,
      action: data.type,
      reason: data.reason,
      severity: data.severity,
      durationHours,
      idempotencyKey,
    })
    const response = present(result.row)
    if (result.row.execution_status === 'pending') {
      return ok(
        { ...response, replayed: result.replayed, idempotencyKey, pending: true },
        { status: 202 },
      )
    }
    if (result.row.execution_status === 'failed') {
      return apiError(
        result.row.error_message || 'Discord rejected this moderation action. The failed attempt was recorded.',
        502,
        { case: response },
      )
    }
    const appeal = result.replayed
      ? { eligible: false as const, replayed: true as const }
      : await issueAppealToken({
          guildId: guard.selectedGuildId!,
          caseId: result.row.id,
          caseNumber: result.row.case_number,
          targetUserId: data.memberId,
          action: data.type,
          reason: data.reason,
          duration: durationHours ? `${durationHours} hour(s)` : null,
          publicBaseUrl: dashboardBaseUrl(request.url),
        }).catch((error) => ({
          eligible: true as const,
          deliveryStatus: 'failed',
          error: error instanceof Error ? error.message : String(error),
        }))
    return created({ ...response, replayed: result.replayed, idempotencyKey, appeal })
  } catch (error) {
    if (error instanceof ProtectedModerationTargetError) return apiError(error.message, 409)
    return handleError(error)
  }
}
