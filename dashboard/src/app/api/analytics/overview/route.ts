import { requireUser, handleError, ok } from '@/lib/api'
import { prisma } from '@/lib/prisma'
import { parseJson } from '@/lib/json'
import {
  getKpi,
  getMetricSeries,
  getGrowthByMonth,
  getInfractionDistribution,
  getWatchlist,
  getTopRules,
  getSystemStatus,
} from '@/lib/metrics'
import { rangeDays, type DateRange } from '@/lib/dashboard-config'

export async function GET(request: Request) {
  try {
    const guard = await requireUser('dashboard.view')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const range = (url.searchParams.get('range') as DateRange) || '30d'
    const days = rangeDays(range)

    const [
      actions,
      openCases,
      automod,
      pendingAppeals,
      actionsSeries,
      automodSeries,
      growth,
      infractions,
      watchlist,
      topRules,
      recentActivity,
      totals,
    ] = await Promise.all([
      getKpi('actions', days),
      getKpi('openCases', days),
      getKpi('automodBlocks', days),
      getKpi('pendingAppeals', days),
      getMetricSeries('actions', days),
      getMetricSeries('automodBlocks', days),
      getGrowthByMonth(6),
      getInfractionDistribution(),
      getWatchlist(5),
      getTopRules(6),
      prisma.activityLog.findMany({ orderBy: { createdAt: 'desc' }, take: 8 }),
      prisma.member.count(),
    ])

    return ok({
      range,
      kpis: { actions, openCases, automod, pendingAppeals },
      actionsSeries,
      automodSeries,
      growth,
      infractions,
      totalMembers: totals,
      watchlist: watchlist.map((m) => ({
        id: m.id,
        displayName: m.displayName,
        username: m.username,
        riskLevel: m.riskLevel,
        warnings: m.warnings,
        avatarColor: m.avatarColor,
      })),
      topRules: topRules.map((r) => ({
        id: r.id,
        name: r.name,
        trigger: r.trigger,
        action: r.action,
        severity: r.severity,
        hits: r.hits,
        enabled: r.enabled,
      })),
      recentActivity: recentActivity.map((a) => ({
        id: a.id,
        actorName: a.actorName,
        action: a.action,
        target: a.target,
        createdAt: a.createdAt.toISOString(),
        metadata: parseJson<Record<string, unknown>>(a.metadata, {}),
      })),
      systemStatus: getSystemStatus(),
    })
  } catch (error) {
    return handleError(error)
  }
}
