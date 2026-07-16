import 'server-only'

import { botQuery, withBotTransaction } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import { recordGuildAudit } from '@/lib/bot-audit'
import { executeModerationReversal, type ModerationActor } from '@/lib/moderation-service'
import { notifyAppealDecision } from '@/lib/appeal-portal-service'
import type { ListQuery } from '@/lib/api'

type AppealRow = {
  id: string
  appeal_number: number
  case_id: string
  case_number: number
  user_id: string
  action: string
  reason: string
  message: string
  answers_json: string
  status: string
  decision: string | null
  reviewed_by_name: string | null
  submitted_at: Date
  reviewed_at: Date | null
  severity: string
  staff_channel_id: string | null
}

const SORTS: Record<string, string> = {
  ref: 'appeal_number',
  caseRef: 'case_number',
  status: 'appeal_status',
  submittedAt: 'submitted_at',
}

function present(row: AppealRow) {
  let answers: Record<string, string> = {}
  try { answers = JSON.parse(row.answers_json || '{}') as Record<string, string> } catch { answers = {} }
  return {
    id: row.id,
    ref: Number(row.appeal_number),
    memberId: row.user_id,
    caseId: row.case_id,
    status: row.status,
    message: row.message,
    answers,
    decision: row.decision,
    reviewedBy: row.reviewed_by_name,
    submittedAt: new Date(row.submitted_at).toISOString(),
    reviewedAt: row.reviewed_at ? new Date(row.reviewed_at).toISOString() : null,
    member: {
      id: row.user_id,
      discordId: row.user_id,
      username: row.user_id,
      displayName: `Discord user ${row.user_id}`,
      avatarColor: '#5865f2',
    },
    case: {
      id: row.case_id,
      ref: Number(row.case_number),
      type: row.action,
      reason: row.reason,
      severity: row.severity || 'low',
    },
  }
}

export async function listGuildAppeals(guildId: string, query: ListQuery) {
  await ensureDashboardBackendSchema()
  const conditions = ['appeals.guild_id = $1::bigint']
  const values: unknown[] = [guildId]
  if (query.q) {
    values.push(`%${query.q}%`)
    conditions.push(`(appeals.message ILIKE $${values.length} OR appeals.decision ILIKE $${values.length}
      OR appeals.user_id::text ILIKE $${values.length} OR appeals.appeal_number::text ILIKE $${values.length})`)
  }
  if (query.filters.status && ['pending', 'approved', 'denied'].includes(query.filters.status)) {
    values.push(query.filters.status)
    conditions.push(`appeals.status = $${values.length}`)
  }
  const where = conditions.join(' AND ')
  const sort = SORTS[query.sort] ?? 'submitted_at'
  const direction = query.order === 'asc' ? 'ASC' : 'DESC'
  const base = `FROM dashboard_appeals appeals
    JOIN cases ON cases.guild_id = appeals.guild_id AND cases.id = appeals.case_id`
  const [rows, totals, pending] = await Promise.all([
    botQuery<AppealRow>(
      `SELECT appeals.id::text, appeals.appeal_number, appeals.case_id::text, cases.case_number,
        appeals.user_id::text, LOWER(cases.action) AS action, cases.reason, cases.severity, appeals.message, appeals.answers_json,
        appeals.status AS appeal_status, appeals.status, appeals.decision, appeals.reviewed_by_name,
        appeals.submitted_at, appeals.reviewed_at, appeals.staff_channel_id::text ${base} WHERE ${where}
       ORDER BY ${sort} ${direction} LIMIT $${values.length + 1} OFFSET $${values.length + 2}`,
      [...values, query.pageSize, (query.page - 1) * query.pageSize],
    ),
    botQuery<{ value: string }>(`SELECT COUNT(*) AS value ${base} WHERE ${where}`, values),
    botQuery<{ value: string }>(
      `SELECT COUNT(*) AS value FROM dashboard_appeals WHERE guild_id = $1::bigint AND status = 'pending'`,
      [guildId],
    ),
  ])
  return {
    data: rows.map(present),
    total: Number(totals[0]?.value ?? 0),
    pending: Number(pending[0]?.value ?? 0),
  }
}

export async function reviewGuildAppeal(input: {
  guildId: string
  appealId: string
  status: 'approved' | 'denied'
  decision?: string | null
  actor: ModerationActor
}) {
  await ensureDashboardBackendSchema()
  const outcome = await withBotTransaction(async (client) => {
    const locked = await client.query<AppealRow>(
      `SELECT appeals.id::text, appeals.appeal_number, appeals.case_id::text, cases.case_number,
         appeals.user_id::text, LOWER(cases.action) AS action, cases.reason, cases.severity, appeals.message,
         appeals.answers_json, appeals.status, appeals.decision, appeals.reviewed_by_name, appeals.submitted_at,
         appeals.reviewed_at, appeals.staff_channel_id::text
       FROM dashboard_appeals appeals
       JOIN cases ON cases.guild_id = appeals.guild_id AND cases.id = appeals.case_id
       WHERE appeals.guild_id = $1::bigint AND appeals.id = $2::bigint
       FOR UPDATE OF appeals`,
      [input.guildId, input.appealId],
    )
    const existing = locked.rows[0]
    if (!existing) return { kind: 'not_found' as const }
    if (existing.status !== 'pending') return { kind: 'reviewed' as const }

    if (input.status === 'approved') {
      await executeModerationReversal({
        guildId: input.guildId,
        caseId: existing.case_id,
        targetUserId: existing.user_id,
        originalAction: existing.action,
        reason: input.decision || `Appeal #${existing.appeal_number} approved`,
        actor: input.actor,
        idempotencyKey: `appeal-${existing.id}-approval`,
      })
    }

    const result = await client.query<AppealRow>(
      `UPDATE dashboard_appeals SET status = $3, decision = $4, reviewed_by_id = $5,
         reviewed_by_name = $6, reviewed_at = CURRENT_TIMESTAMP
       WHERE guild_id = $1::bigint AND id = $2::bigint AND status = 'pending'
       RETURNING id::text, appeal_number, case_id::text, user_id::text, message, answers_json, status, decision,
         reviewed_by_name, submitted_at, reviewed_at, staff_channel_id::text`,
      [input.guildId, input.appealId, input.status, input.decision ?? null, input.actor.id, input.actor.name],
    )
    if (!result.rows[0]) return { kind: 'reviewed' as const }
    if (input.status === 'approved') {
      await client.query(
        `UPDATE cases SET status = 'resolved', active = 0, updated_at = CURRENT_TIMESTAMP
         WHERE guild_id = $1::bigint AND id = $2::bigint`,
        [input.guildId, existing.case_id],
      )
    }
    await recordGuildAudit(
      input.guildId,
      input.actor,
      `appeal.${input.status}`,
      existing.id,
      { caseId: existing.case_id, userId: existing.user_id, decision: input.decision ?? null },
      client,
    )
    return {
      kind: 'ok' as const,
      appeal: { ...present({ ...existing, ...result.rows[0] }), status: input.status },
      notification: { userId: existing.user_id, appealNumber: existing.appeal_number, caseNumber: existing.case_number, status: input.status, decision: input.decision, staffChannelId: existing.staff_channel_id },
    }
  })
  if (outcome.kind === 'ok') await notifyAppealDecision(outcome.notification)
  return outcome.kind === 'ok' ? { kind: 'ok' as const, appeal: outcome.appeal } : outcome
}
