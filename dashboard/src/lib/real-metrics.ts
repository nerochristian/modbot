import 'server-only'

import { botDatabaseHealthy, botQuery } from '@/lib/bot-db'
import type { ManagedGuild } from '@/lib/discord'

type Kpi = { value: number; delta: number }
type Point = { label: string; value: number }

function number(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function trend(current: number, previous: number): number {
  if (previous === 0) return current === 0 ? 0 : 100
  return Math.round(((current - previous) / previous) * 1000) / 10
}

function clampDays(days: number): number {
  return Math.max(1, Math.min(365, Math.trunc(days) || 30))
}

async function periodCount(
  guildId: string,
  days: number,
  table: 'cases' | 'automod_events' | 'guild_member_events',
  extra = '',
): Promise<Kpi> {
  const safeDays = clampDays(days)
  const rows = await botQuery<{ current: string; previous: string }>(
    `SELECT
       COUNT(*) FILTER (WHERE created_at >= NOW() - ($2::int * INTERVAL '1 day')) AS current,
       COUNT(*) FILTER (
         WHERE created_at >= NOW() - ($2::int * 2 * INTERVAL '1 day')
           AND created_at < NOW() - ($2::int * INTERVAL '1 day')
       ) AS previous
     FROM ${table}
     WHERE guild_id = $1::bigint ${extra}`,
    [guildId, safeDays],
  )
  const current = number(rows[0]?.current)
  const previous = number(rows[0]?.previous)
  return { value: current, delta: trend(current, previous) }
}

async function dailySeries(
  guildId: string,
  days: number,
  table: 'cases' | 'automod_events' | 'guild_member_events',
  extra = '',
): Promise<Point[]> {
  const safeDays = clampDays(days)
  const rows = await botQuery<{ label: string; value: string }>(
    `WITH dates AS (
       SELECT generate_series(CURRENT_DATE - ($2::int - 1), CURRENT_DATE, INTERVAL '1 day')::date AS day
     )
     SELECT TO_CHAR(dates.day, 'Mon DD') AS label, COUNT(events.id)::int AS value
     FROM dates
     LEFT JOIN ${table} events
       ON events.guild_id = $1::bigint
      AND events.created_at >= dates.day
      AND events.created_at < dates.day + INTERVAL '1 day'
      ${extra}
     GROUP BY dates.day
     ORDER BY dates.day`,
    [guildId, safeDays],
  )
  return rows.map((row) => ({ label: row.label, value: number(row.value) }))
}

function snapshotSeries(days: number, value: number): Point[] {
  const safeDays = clampDays(days)
  const formatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: '2-digit', timeZone: 'UTC' })
  return Array.from({ length: safeDays }, (_, index) => {
    const date = new Date()
    date.setUTCHours(0, 0, 0, 0)
    date.setUTCDate(date.getUTCDate() - (safeDays - index - 1))
    return { label: formatter.format(date), value }
  })
}

export async function getRealAnalytics(guild: ManagedGuild, days: number) {
  const [
    actions,
    automodBlocks,
    joins,
    leaves,
    bans,
    warns,
    actionsSeries,
    automodSeries,
    joinsSeries,
    leavesSeries,
    bansSeries,
    warnsSeries,
  ] = await Promise.all([
    periodCount(guild.id, days, 'cases'),
    periodCount(guild.id, days, 'automod_events'),
    periodCount(guild.id, days, 'guild_member_events', "AND event_type = 'join'"),
    periodCount(guild.id, days, 'guild_member_events', "AND event_type = 'leave'"),
    periodCount(guild.id, days, 'cases', "AND LOWER(action) = 'ban'"),
    periodCount(guild.id, days, 'cases', "AND LOWER(action) = 'warn'"),
    dailySeries(guild.id, days, 'cases'),
    dailySeries(guild.id, days, 'automod_events'),
    dailySeries(guild.id, days, 'guild_member_events', "AND events.event_type = 'join'"),
    dailySeries(guild.id, days, 'guild_member_events', "AND events.event_type = 'leave'"),
    dailySeries(guild.id, days, 'cases', "AND LOWER(events.action) = 'ban'"),
    dailySeries(guild.id, days, 'cases', "AND LOWER(events.action) = 'warn'"),
  ])
  const memberCount = guild.memberCount ?? 0
  const onlineCount = guild.onlineCount ?? 0
  return {
    kpis: {
      actions,
      automodBlocks,
      members: { value: memberCount, delta: 0 },
      online: { value: onlineCount, delta: 0 },
      joins,
      leaves,
      bans,
      warns,
    },
    series: {
      actions: actionsSeries,
      automodBlocks: automodSeries,
      members: snapshotSeries(days, memberCount),
      online: snapshotSeries(days, onlineCount),
      joins: joinsSeries,
      leaves: leavesSeries,
      bans: bansSeries,
      warns: warnsSeries,
    },
  }
}

export async function getRealOverview(guild: ManagedGuild, days: number) {
  const analyticsPromise = getRealAnalytics(guild, days)
  const [
    analytics,
    openCasesRows,
    growthRows,
    infractionRows,
    watchlistRows,
    ruleRows,
    activityRows,
    channelRows,
    databaseOk,
  ] = await Promise.all([
    analyticsPromise,
    botQuery<{ value: string }>(
      'SELECT COUNT(*) AS value FROM cases WHERE guild_id = $1::bigint AND active = TRUE',
      [guild.id],
    ),
    botQuery<{ label: string; joined: string; left: string }>(
      `WITH months AS (
         SELECT generate_series(
           DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months',
           DATE_TRUNC('month', CURRENT_DATE),
           INTERVAL '1 month'
         ) AS month
       )
       SELECT TO_CHAR(months.month, 'Mon') AS label,
         COUNT(events.id) FILTER (WHERE events.event_type = 'join')::int AS joined,
         COUNT(events.id) FILTER (WHERE events.event_type = 'leave')::int AS left
       FROM months
       LEFT JOIN guild_member_events events
         ON events.guild_id = $1::bigint
        AND events.created_at >= months.month
        AND events.created_at < months.month + INTERVAL '1 month'
       GROUP BY months.month ORDER BY months.month`,
      [guild.id],
    ),
    botQuery<{ name: string; value: string }>(
      `SELECT COALESCE(NULLIF(LOWER(action), ''), 'other') AS name, COUNT(*)::int AS value
       FROM cases WHERE guild_id = $1::bigint GROUP BY 1 ORDER BY value DESC`,
      [guild.id],
    ),
    botQuery<{ id: string; score: number; warnings: string; messages: string; username: string }>(
      `SELECT risk.user_id::text AS id, risk.score,
         COALESCE(warnings.count, 0)::int AS warnings,
         COALESCE(messages.count, 0)::int AS messages,
         COALESCE(NULLIF(profiles.username, ''), 'Discord user ' || risk.user_id::text) AS username
       FROM user_risk_scores risk
       LEFT JOIN (
         SELECT user_id, COUNT(*) AS count FROM warnings WHERE guild_id = $1::bigint GROUP BY user_id
       ) warnings ON warnings.user_id = risk.user_id
       LEFT JOIN (
         SELECT user_id, COUNT(*) AS count FROM user_messages WHERE guild_id = $1::bigint GROUP BY user_id
       ) messages ON messages.user_id = risk.user_id
       LEFT JOIN banned_user_profiles profiles ON profiles.user_id = risk.user_id
       WHERE risk.guild_id = $1::bigint AND risk.score > 0
       ORDER BY risk.score DESC LIMIT 5`,
      [guild.id],
    ),
    botQuery<{ rule: string; action: string; severity: string; hits: string }>(
      `SELECT rule, MODE() WITHIN GROUP (ORDER BY action) AS action,
         MODE() WITHIN GROUP (ORDER BY severity) AS severity, COUNT(*)::int AS hits
       FROM automod_events WHERE guild_id = $1::bigint
       GROUP BY rule ORDER BY hits DESC LIMIT 6`,
      [guild.id],
    ),
    botQuery<{ id: string; actor_name: string; action: string; target: string; created_at: Date }>(
      `SELECT 'case-' || id::text AS id, moderator_id::text AS actor_name,
         action, user_id::text AS target, created_at
       FROM cases WHERE guild_id = $1::bigint
       ORDER BY created_at DESC LIMIT 8`,
      [guild.id],
    ),
    botQuery<{ channel_id: string; value: string }>(
      `SELECT channel_id::text, COUNT(*)::int AS value FROM user_messages
       WHERE guild_id = $1::bigint AND timestamp >= NOW() - INTERVAL '30 days'
       GROUP BY channel_id ORDER BY value DESC LIMIT 6`,
      [guild.id],
    ),
    botDatabaseHealthy(),
  ])

  const colors: Record<string, string> = {
    warn: 'var(--sev-low)',
    mute: 'var(--sev-medium)',
    timeout: 'var(--sev-medium)',
    kick: 'var(--sev-high)',
    ban: 'var(--sev-critical)',
  }
  const openCases = number(openCasesRows[0]?.value)

  return {
    kpis: {
      actions: analytics.kpis.actions,
      openCases: { value: openCases, delta: 0 },
      automod: analytics.kpis.automodBlocks,
      pendingAppeals: { value: 0, delta: 0 },
    },
    actionsSeries: analytics.series.actions,
    automodSeries: analytics.series.automodBlocks,
    channels: channelRows.map((row) => ({ label: `#${row.channel_id}`, value: number(row.value) })),
    growth: growthRows.map((row) => ({ label: row.label, joined: number(row.joined), left: number(row.left) })),
    infractions: infractionRows.map((row) => ({
      name: row.name.charAt(0).toUpperCase() + row.name.slice(1),
      value: number(row.value),
      color: colors[row.name] ?? 'var(--sev-none)',
    })),
    totalMembers: guild.memberCount ?? 0,
    watchlist: watchlistRows.map((row) => {
      const score = number(row.score)
      const riskLevel = score >= 80 ? 'critical' : score >= 60 ? 'high' : score >= 35 ? 'medium' : 'low'
      return {
        id: row.id,
        displayName: row.username,
        username: row.id,
        riskLevel,
        warnings: number(row.warnings),
        avatarColor: score >= 60 ? '#dc2f55' : '#c77700',
      }
    }),
    topRules: ruleRows.map((row) => ({
      id: row.rule,
      name: row.rule.replace(/_/g, ' ').replace(/^\w/, (letter) => letter.toUpperCase()),
      trigger: row.rule,
      action: row.action,
      severity: row.severity,
      hits: number(row.hits),
      enabled: true,
    })),
    recentActivity: activityRows.map((row) => ({
      id: row.id,
      actorName: `Moderator ${row.actor_name}`,
      action: row.action,
      target: row.target,
      createdAt: new Date(row.created_at).toISOString(),
    })),
    systemStatus: [
      { name: 'Bot connection', status: guild.installed ? 'Operational' : 'Unavailable', uptime: 'Live' },
      { name: 'Moderation database', status: databaseOk ? 'Operational' : 'Unavailable', uptime: databaseOk ? 'Live' : 'Check service' },
      { name: 'Discord guild data', status: 'Operational', uptime: 'Live' },
    ],
  }
}
