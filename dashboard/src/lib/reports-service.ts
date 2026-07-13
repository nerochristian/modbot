import 'server-only'

import { botQuery } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import { recordGuildAudit } from '@/lib/bot-audit'
import type { ListQuery } from '@/lib/api'
import type { ReportFormat, ReportRow } from '@/lib/report-formatters'

export type ReportType = 'actions' | 'members' | 'activity' | 'automod' | 'custom'

export type DashboardReport = {
  id: string
  guild_id: string
  requested_by_id: string
  requested_by_name: string
  name: string
  type: ReportType
  format: ReportFormat
  params: string | Record<string, unknown>
  status: string
  created_at: Date
}

const SORTS: Record<string, string> = {
  name: 'name',
  type: 'type',
  status: 'status',
  createdAt: 'created_at',
}

function present(report: DashboardReport) {
  return {
    id: report.id,
    name: report.name,
    type: report.type,
    status: report.status,
    format: report.format,
    createdAt: new Date(report.created_at).toISOString(),
    createdBy: report.requested_by_name,
  }
}

export async function listGuildReports(guildId: string, userId: string, query: ListQuery) {
  await ensureDashboardBackendSchema()
  const conditions = ['guild_id = $1::bigint', 'requested_by_id = $2']
  const values: unknown[] = [guildId, userId]
  if (query.q) {
    values.push(`%${query.q}%`)
    conditions.push(`name ILIKE $${values.length}`)
  }
  if (query.filters.type && ['actions', 'members', 'activity', 'automod', 'custom'].includes(query.filters.type)) {
    values.push(query.filters.type)
    conditions.push(`type = $${values.length}`)
  }
  if (query.filters.status && ['ready', 'failed'].includes(query.filters.status)) {
    values.push(query.filters.status)
    conditions.push(`status = $${values.length}`)
  }
  const where = conditions.join(' AND ')
  const sort = SORTS[query.sort] ?? 'created_at'
  const direction = query.order === 'asc' ? 'ASC' : 'DESC'
  const [rows, totals] = await Promise.all([
    botQuery<DashboardReport>(
      `SELECT id::text, guild_id::text, requested_by_id, requested_by_name, name, type, format,
         params, status, created_at FROM dashboard_reports WHERE ${where}
       ORDER BY ${sort} ${direction} LIMIT $${values.length + 1} OFFSET $${values.length + 2}`,
      [...values, query.pageSize, (query.page - 1) * query.pageSize],
    ),
    botQuery<{ value: string }>(`SELECT COUNT(*) AS value FROM dashboard_reports WHERE ${where}`, values),
  ])
  return { data: rows.map(present), total: Number(totals[0]?.value ?? 0) }
}

export async function createGuildReport(input: {
  guildId: string
  userId: string
  userName: string
  name: string
  type: ReportType
  format: ReportFormat
  params?: Record<string, unknown>
}) {
  await ensureDashboardBackendSchema()
  const rows = await botQuery<DashboardReport>(
    `INSERT INTO dashboard_reports (
       guild_id, requested_by_id, requested_by_name, name, type, format, params, status
     ) VALUES ($1::bigint, $2, $3, $4, $5, $6, $7, 'ready')
     RETURNING id::text, guild_id::text, requested_by_id, requested_by_name, name, type, format,
       params, status, created_at`,
    [input.guildId, input.userId, input.userName, input.name, input.type, input.format, JSON.stringify(input.params ?? {})],
  )
  await recordGuildAudit(input.guildId, { id: input.userId, name: input.userName }, 'report.created', rows[0].id, {
    type: input.type,
    format: input.format,
  })
  return present(rows[0])
}

export async function getGuildReport(guildId: string, userId: string, reportId: string): Promise<DashboardReport | null> {
  await ensureDashboardBackendSchema()
  const rows = await botQuery<DashboardReport>(
    `SELECT id::text, guild_id::text, requested_by_id, requested_by_name, name, type, format,
       params, status, created_at FROM dashboard_reports
     WHERE guild_id = $1::bigint AND requested_by_id = $2 AND id = $3::bigint`,
    [guildId, userId, reportId],
  )
  return rows[0] ?? null
}

export async function deleteGuildReport(guildId: string, userId: string, userName: string, reportId: string): Promise<boolean> {
  await ensureDashboardBackendSchema()
  const rows = await botQuery<{ id: string }>(
    `DELETE FROM dashboard_reports WHERE guild_id = $1::bigint AND requested_by_id = $2
     AND id = $3::bigint RETURNING id::text`,
    [guildId, userId, reportId],
  )
  if (!rows[0]) return false
  await recordGuildAudit(guildId, { id: userId, name: userName }, 'report.deleted', reportId)
  return true
}

function reportOptions(params: string | Record<string, unknown>): {
  days: number
  dataset: Exclude<ReportType, 'custom'>
} {
  let parsed: Record<string, unknown> = {}
  if (typeof params === 'string') {
    try {
      const value = JSON.parse(params)
      if (value && typeof value === 'object' && !Array.isArray(value)) parsed = value
    } catch {
      parsed = {}
    }
  } else {
    parsed = params
  }
  const requestedDays = Number(parsed.days)
  const days = Number.isFinite(requestedDays) ? Math.max(1, Math.min(365, Math.trunc(requestedDays))) : 90
  const dataset = ['actions', 'members', 'activity', 'automod'].includes(String(parsed.dataset))
    ? String(parsed.dataset) as Exclude<ReportType, 'custom'>
    : 'activity'
  return { days, dataset }
}

export async function getGuildReportRows(report: DashboardReport): Promise<ReportRow[]> {
  const options = reportOptions(report.params)
  const days = options.days
  const type = report.type === 'custom' ? options.dataset : report.type
  const rangeValues = [report.guild_id, days]
  if (type === 'actions') {
    return botQuery<ReportRow>(
      `SELECT case_number, user_id::text AS user_id, moderator_id::text AS moderator_id,
         LOWER(action) AS action, reason, severity, status, execution_status,
         created_at::text, expires_at::text
       FROM cases WHERE guild_id = $1::bigint
         AND created_at >= NOW() - ($2::int * INTERVAL '1 day')
       ORDER BY created_at DESC LIMIT 5000`,
      rangeValues,
    )
  }
  if (type === 'automod') {
    return botQuery<ReportRow>(
      `SELECT user_id::text AS user_id, channel_id::text AS channel_id, rule, category,
         severity, action, reason, message_deleted, created_at::text
       FROM automod_events WHERE guild_id = $1::bigint
         AND created_at >= NOW() - ($2::int * INTERVAL '1 day')
       ORDER BY created_at DESC LIMIT 5000`,
      rangeValues,
    )
  }
  if (type === 'activity') {
    return botQuery<ReportRow>(
      `WITH activity AS (
        SELECT 'case-' || id::text AS id, moderator_id::text AS actor, LOWER(action) AS action,
          user_id::text AS target, created_at FROM cases WHERE guild_id = $1::bigint
        UNION ALL
        SELECT 'automod-' || id::text, 'AutoMod', 'blocked_' || rule, user_id::text, created_at
          FROM automod_events WHERE guild_id = $1::bigint
        UNION ALL
        SELECT 'dashboard-' || id::text, COALESCE(NULLIF(user_name, ''), 'Dashboard'), action,
          target, created_at FROM dashboard_audit WHERE guild_id = $1::bigint
       ) SELECT id, actor, action, target, created_at::text FROM activity
       WHERE created_at >= NOW() - ($2::int * INTERVAL '1 day')
       ORDER BY created_at DESC LIMIT 5000`,
      rangeValues,
    )
  }
  return botQuery<ReportRow>(
    `SELECT members.user_id, COALESCE(warnings.count, 0)::int AS warnings,
       COALESCE(messages.count, 0)::int AS messages, COALESCE(risk.score, 0)::int AS risk_score,
       messages.last_active::text
     FROM (
       SELECT user_id::text FROM user_messages WHERE guild_id = $1::bigint
       UNION SELECT user_id::text FROM warnings WHERE guild_id = $1::bigint
       UNION SELECT user_id::text FROM user_risk_scores WHERE guild_id = $1::bigint
     ) members
     LEFT JOIN (SELECT user_id::text, COUNT(*) AS count FROM warnings WHERE guild_id = $1::bigint GROUP BY user_id) warnings USING (user_id)
     LEFT JOIN (SELECT user_id::text, COUNT(*) AS count, MAX(timestamp) AS last_active FROM user_messages WHERE guild_id = $1::bigint GROUP BY user_id) messages USING (user_id)
     LEFT JOIN user_risk_scores risk ON risk.guild_id = $1::bigint AND risk.user_id::text = members.user_id
     ORDER BY risk_score DESC, warnings DESC LIMIT 5000`,
    [report.guild_id],
  )
}
