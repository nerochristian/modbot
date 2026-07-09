import { requireUser, handleError, ok } from '@/lib/api'
import { prisma } from '@/lib/prisma'
import { parseJson } from '@/lib/json'
import {
  getKpi,
  getMetricSeries,
  getGrowthByMonth,
  getPlanDistribution,
  getTopCustomers,
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
      revenue,
      active,
      conversion,
      churn,
      revenueSeries,
      retentionSeries,
      growth,
      plans,
      topCustomers,
      recentActivity,
      totals,
    ] = await Promise.all([
      getKpi('revenue', days),
      getKpi('active', days),
      getKpi('conversion', days),
      getKpi('churn', days),
      getMetricSeries('revenue', days),
      getMetricSeries('retention', days),
      getGrowthByMonth(6),
      getPlanDistribution(),
      getTopCustomers(5),
      prisma.activityLog.findMany({ orderBy: { createdAt: 'desc' }, take: 8 }),
      prisma.customer.count(),
    ])

    return ok({
      range,
      kpis: { revenue, active, conversion, churn },
      revenueSeries,
      retentionSeries,
      growth,
      plans,
      totalCustomers: totals,
      topCustomers: topCustomers.map((c) => ({
        id: c.id,
        name: c.name,
        company: c.company,
        plan: c.plan,
        mrr: c.mrr,
        avatarColor: c.avatarColor,
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
