import { handleError, ok, paginate, parseListQuery, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'

type ActivityRow = {
  id: string
  actor_name: string
  action: string
  target: string | null
  created_at: Date
}

export async function GET(request: Request) {
  try {
    const guard = await requireUser('activity.read')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId!
    await ensureDashboardBackendSchema()
    const query = parseListQuery(new URL(request.url), { defaultSort: 'createdAt', maxPageSize: 50 })
    const base = `WITH activity AS (
      SELECT 'case-' || id::text AS id, 'Moderator ' || moderator_id::text AS actor_name,
        LOWER(action) AS action, user_id::text AS target, created_at
      FROM cases WHERE guild_id = $1::bigint
      UNION ALL
      SELECT 'automod-' || id::text, 'AutoMod', 'blocked_' || rule, user_id::text, created_at
      FROM automod_events WHERE guild_id = $1::bigint
      UNION ALL
      SELECT 'member-' || id::text, 'Discord', 'member_' || event_type, user_id::text, created_at
      FROM guild_member_events WHERE guild_id = $1::bigint
      UNION ALL
      SELECT 'dashboard-' || id::text, COALESCE(NULLIF(user_name, ''), 'Dashboard'), action, target, created_at
      FROM dashboard_audit WHERE guild_id = $1::bigint
    )`
    const conditions: string[] = []
    const baseValues: unknown[] = [guildId]
    if (query.q) {
      baseValues.push(`%${query.q}%`)
      conditions.push(`(actor_name ILIKE $${baseValues.length} OR action ILIKE $${baseValues.length} OR target ILIKE $${baseValues.length})`)
    }
    if (query.filters.actor) {
      baseValues.push(query.filters.actor)
      conditions.push(`actor_name = $${baseValues.length}`)
    }
    if (query.filters.action) {
      baseValues.push(query.filters.action)
      conditions.push(`action = $${baseValues.length}`)
    }
    const filter = conditions.length ? `WHERE ${conditions.join(' AND ')}` : ''
    const sorts: Record<string, string> = {
      actorName: 'actor_name',
      action: 'action',
      target: 'target',
      createdAt: 'created_at',
    }
    const sort = sorts[query.sort] ?? 'created_at'
    const direction = query.order === 'asc' ? 'ASC' : 'DESC'
    const rowsValues = [...baseValues, query.pageSize, (query.page - 1) * query.pageSize]
    const [rows, totals] = await Promise.all([
      botQuery<ActivityRow>(
        `${base} SELECT * FROM activity ${filter} ORDER BY ${sort} ${direction}
         LIMIT $${rowsValues.length - 1} OFFSET $${rowsValues.length}`,
        rowsValues,
      ),
      botQuery<{ value: string }>(`${base} SELECT COUNT(*) AS value FROM activity ${filter}`, baseValues),
    ])
    return ok(paginate(rows.map((row) => ({
      id: row.id,
      actorName: row.actor_name,
      action: row.action,
      target: row.target,
      createdAt: new Date(row.created_at).toISOString(),
      metadata: {},
    })), Number(totals[0]?.value || 0), query))
  } catch (error) {
    return handleError(error)
  }
}
