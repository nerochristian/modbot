import { requireUser, handleError, ok } from '@/lib/api'
import { getKpi, getMetricSeries } from '@/lib/metrics'
import { rangeDays, type DateRange } from '@/lib/dashboard-config'

const METRICS = ['actions', 'automodBlocks', 'members', 'online', 'joins', 'leaves', 'bans', 'warns']

export async function GET(request: Request) {
  try {
    const guard = await requireUser('analytics.view')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const range = (url.searchParams.get('range') as DateRange) || '30d'
    const days = rangeDays(range)

    const [kpiEntries, seriesEntries] = await Promise.all([
      Promise.all(METRICS.map(async (m) => [m, await getKpi(m, days)] as const)),
      Promise.all(METRICS.map(async (m) => [m, await getMetricSeries(m, days)] as const)),
    ])

    return ok({
      range,
      kpis: Object.fromEntries(kpiEntries),
      series: Object.fromEntries(seriesEntries),
    })
  } catch (error) {
    return handleError(error)
  }
}
