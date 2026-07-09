import { prisma } from '@/lib/prisma'
import { rangeDays, type DateRange } from '@/lib/dashboard-config'

export type SeriesPoint = { label: string; value: number; date: string }
export type Kpi = { value: number; delta: number }

function shortLabel(date: Date, days: number): string {
  // Use month labels for long ranges, day labels for short ones.
  if (days > 120) {
    return date.toLocaleDateString('en-US', { month: 'short' })
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

/** Daily series for a metric over the last N days, oldest → newest. */
export async function getMetricSeries(metric: string, days: number): Promise<SeriesPoint[]> {
  const since = new Date(Date.now() - days * 86_400_000)
  const points = await prisma.metricPoint.findMany({
    where: { metric, date: { gte: since } },
    orderBy: { date: 'asc' },
  })

  // Downsample long ranges to keep charts legible.
  const step = days > 180 ? 7 : days > 60 ? 2 : 1
  return points
    .filter((_, i) => i % step === 0)
    .map((p) => ({ label: shortLabel(p.date, days), value: p.value, date: p.date.toISOString() }))
}

/** Current value + percent change vs. the preceding window of equal length. */
export async function getKpi(metric: string, days: number): Promise<Kpi> {
  const now = Date.now()
  const currentSince = new Date(now - days * 86_400_000)
  const prevSince = new Date(now - days * 2 * 86_400_000)

  const [current, previous] = await Promise.all([
    prisma.metricPoint.findMany({
      where: { metric, date: { gte: currentSince } },
      orderBy: { date: 'desc' },
    }),
    prisma.metricPoint.findMany({
      where: { metric, date: { gte: prevSince, lt: currentSince } },
    }),
  ])

  if (current.length === 0) return { value: 0, delta: 0 }

  // Point-in-time metrics use the latest value; flow metrics compare summed volume.
  const pointInTime = ['members', 'online', 'openCases', 'pendingAppeals'].includes(metric)
  const currentValue = pointInTime ? current[0].value : sum(current.map((p) => p.value))
  const prevValue = pointInTime
    ? previous[0]?.value ?? currentValue
    : sum(previous.map((p) => p.value))

  const delta = prevValue === 0 ? 0 : ((currentValue - prevValue) / prevValue) * 100
  return { value: currentValue, delta }
}

function sum(nums: number[]): number {
  return nums.reduce((s, n) => s + n, 0)
}

/** Distribution of cases by infraction type — powers the donut/bar. */
export type TypeDistribution = { name: string; value: number; color: string }
const TYPE_COLORS: Record<string, string> = {
  note: '#626c7d',
  warn: '#38bdf8',
  mute: '#f5a524',
  timeout: '#fb923c',
  kick: '#f97316',
  ban: '#f0476b',
  unban: '#3ddc97',
}

export async function getInfractionDistribution(): Promise<TypeDistribution[]> {
  const grouped = await prisma.case.groupBy({
    by: ['type'],
    _count: { type: true },
  })
  const order = ['note', 'warn', 'mute', 'timeout', 'kick', 'ban', 'unban']
  return grouped
    .map((g) => ({
      name: g.type.charAt(0).toUpperCase() + g.type.slice(1),
      value: g._count.type,
      color: TYPE_COLORS[g.type] ?? '#626c7d',
      _type: g.type,
    }))
    .sort((a, b) => order.indexOf(a._type) - order.indexOf(b._type))
    .map(({ name, value, color }) => ({ name, value, color }))
}

/** Member joins vs. leaves per month for the growth chart. */
export async function getGrowthByMonth(months = 6) {
  const [joins, leaves] = await Promise.all([
    prisma.metricPoint.findMany({ where: { metric: 'joins' }, orderBy: { date: 'asc' } }),
    prisma.metricPoint.findMany({ where: { metric: 'leaves' }, orderBy: { date: 'asc' } }),
  ])
  const buckets: { label: string; joined: number; left: number }[] = []
  const now = new Date()
  for (let m = months - 1; m >= 0; m--) {
    const d = new Date(now.getFullYear(), now.getMonth() - m, 1)
    const next = new Date(now.getFullYear(), now.getMonth() - m + 1, 1)
    const label = d.toLocaleDateString('en-US', { month: 'short' })
    const joined = joins.filter((p) => p.date >= d && p.date < next).reduce((s, p) => s + p.value, 0)
    const left = leaves.filter((p) => p.date >= d && p.date < next).reduce((s, p) => s + p.value, 0)
    buckets.push({ label, joined: Math.round(joined), left: Math.round(left) })
  }
  return buckets
}

/** Highest-risk flagged members for the watchlist widget. */
export async function getWatchlist(limit = 5) {
  const RISK_RANK: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }
  const members = await prisma.member.findMany({
    where: { standing: { in: ['watchlist', 'muted'] } },
    take: 40,
  })
  return members
    .sort(
      (a, b) =>
        (RISK_RANK[a.riskLevel] ?? 3) - (RISK_RANK[b.riskLevel] ?? 3) || b.warnings - a.warnings,
    )
    .slice(0, limit)
}

/** Top automod rules by hit count. */
export async function getTopRules(limit = 6) {
  return prisma.automodRule.findMany({
    orderBy: { hits: 'desc' },
    take: limit,
  })
}

export type ServiceStatus = { name: string; status: 'operational' | 'degraded' | 'down'; uptime: string }
export function getSystemStatus(): ServiceStatus[] {
  return [
    { name: 'Gateway', status: 'operational', uptime: '99.99%' },
    { name: 'Shard 0', status: 'operational', uptime: '99.98%' },
    { name: 'Shard 1', status: 'operational', uptime: '99.96%' },
    { name: 'Automod engine', status: 'operational', uptime: '99.95%' },
    { name: 'Audit webhook', status: 'degraded', uptime: '99.21%' },
  ]
}

export { rangeDays }
export type { DateRange }
