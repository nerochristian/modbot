import { NextResponse } from 'next/server'

import { botDatabaseHealthy } from '@/lib/bot-db'
import { prisma } from '@/lib/prisma'

export const dynamic = 'force-dynamic'

/**
 * Health check for both data sources the dashboard depends on:
 * - `bot`: the live bot PostgreSQL database (settings, cases, members, automod)
 * - `dashboard`: the dashboard's own store (accounts, sessions, workspace preferences)
 *
 * Returns 200 only when both are reachable, so uptime checks fail loudly if the
 * bot database connection is misconfigured rather than silently showing gaps.
 */
export async function GET() {
  const [botOk, dashboardOk] = await Promise.all([
    botDatabaseHealthy(),
    prisma.$queryRaw`SELECT 1`.then(() => true).catch(() => false),
  ])

  const healthy = botOk && dashboardOk
  return NextResponse.json(
    {
      status: healthy ? 'ok' : 'degraded',
      sources: {
        bot: botOk ? 'connected' : 'unreachable',
        dashboard: dashboardOk ? 'connected' : 'unreachable',
      },
    },
    { status: healthy ? 200 : 503 },
  )
}
