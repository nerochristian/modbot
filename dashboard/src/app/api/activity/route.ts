import { handleError, ok, paginate, parseListQuery, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import { resolveDiscordProfiles } from '@/lib/discord'

type ActivityRow = {
  id: string
  category: string
  actor_label: string | null
  actor_id: string | null
  action: string
  target_id: string | null
  severity: string | null
  detail: string | null
  rule: string | null
  message_deleted: boolean | null
  case_number: number | null
  created_at: Date
}

const CATEGORIES = new Set(['moderation', 'automod', 'members', 'dashboard'])

export async function GET(request: Request) {
  try {
    const guard = await requireUser('activity.read')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId!
    await ensureDashboardBackendSchema()
    const query = parseListQuery(new URL(request.url), { defaultSort: 'createdAt', maxPageSize: 50 })
    const base = `WITH activity AS (
      SELECT 'case-' || id::text AS id, 'moderation' AS category,
        'Moderator ' || moderator_id::text AS actor_label, moderator_id::text AS actor_id,
        LOWER(action) AS action, user_id::text AS target_id,
        severity, reason AS detail, NULL AS rule, NULL::boolean AS message_deleted, case_number, created_at
      FROM cases WHERE guild_id = $1::bigint
      UNION ALL
      SELECT 'automod-' || id::text, 'automod', 'AutoMod', NULL,
        'blocked_' || rule, user_id::text,
        severity, reason, rule, message_deleted::boolean, NULL, created_at
      FROM automod_events WHERE guild_id = $1::bigint
      UNION ALL
      SELECT 'member-' || id::text, 'members', 'Discord', NULL,
        'member_' || event_type, user_id::text,
        NULL, NULL, NULL, NULL, NULL, created_at
      FROM guild_member_events WHERE guild_id = $1::bigint
      UNION ALL
      SELECT 'dashboard-' || id::text, 'dashboard', COALESCE(NULLIF(user_name, ''), 'Dashboard'), NULL,
        action, target,
        NULL, NULL, NULL, NULL, NULL, created_at
      FROM dashboard_audit WHERE guild_id = $1::bigint
    )`
    const conditions: string[] = []
    const baseValues: unknown[] = [guildId]
    if (query.q) {
      baseValues.push(`%${query.q}%`)
      conditions.push(`(actor_label ILIKE $${baseValues.length} OR action ILIKE $${baseValues.length} OR target_id ILIKE $${baseValues.length} OR detail ILIKE $${baseValues.length})`)
    }
    if (query.filters.category && CATEGORIES.has(query.filters.category)) {
      baseValues.push(query.filters.category)
      conditions.push(`category = $${baseValues.length}`)
    }
    if (query.filters.action) {
      baseValues.push(query.filters.action)
      conditions.push(`action = $${baseValues.length}`)
    }
    const filter = conditions.length ? `WHERE ${conditions.join(' AND ')}` : ''
    const sort = 'created_at'
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

    // Resolve real Discord identities for actors and targets on this page.
    const profileIds = rows.flatMap((row) => [row.actor_id, row.target_id].filter((id): id is string => !!id))
    const profiles = await resolveDiscordProfiles(guildId, profileIds).catch(() => new Map())

    return ok(paginate(rows.map((row) => {
      const actorProfile = row.actor_id ? profiles.get(row.actor_id) : undefined
      const targetProfile = row.target_id ? profiles.get(row.target_id) : undefined
      return {
        id: row.id,
        category: row.category,
        action: row.action,
        createdAt: new Date(row.created_at).toISOString(),
        actor: {
          name: actorProfile?.displayName ?? row.actor_label ?? 'System',
          avatarUrl: actorProfile?.avatarUrl ?? null,
        },
        target: row.target_id
          ? { id: row.target_id, name: targetProfile?.displayName ?? null, avatarUrl: targetProfile?.avatarUrl ?? null }
          : null,
        detail: {
          severity: row.severity,
          reason: row.detail,
          rule: row.rule,
          deleted: row.message_deleted === true,
          caseNumber: row.case_number,
        },
      }
    }), Number(totals[0]?.value || 0), query))
  } catch (error) {
    return handleError(error)
  }
}
