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

  // Point-in-time metrics use the latest value; flow metrics compare averages.
  const pointInTime = ['users', 'active', 'mrr', 'retention', 'churn', 'conversion'].includes(metric)
  const currentValue = pointInTime ? current[0].value : average(current.map((p) => p.value))
  const prevValue = pointInTime
    ? previous[0]?.value ?? currentValue
    : average(previous.map((p) => p.value))

  const delta = prevValue === 0 ? 0 : ((currentValue - prevValue) / prevValue) * 100
  return { value: currentValue, delta }
}

function average(nums: number[]): number {
  if (nums.length === 0) return 0
  return nums.reduce((s, n) => s + n, 0) / nums.length
}

export type PlanDistribution = { name: string; value: number; color: string }
const PLAN_COLORS: Record<string, string> = {
  free: '#94a3b8',
  starter: '#0ea5e9',
  pro: '#6366f1',
  enterprise: '#8b5cf6',
}

export async function getPlanDistribution(): Promise<PlanDistribution[]> {
  const grouped = await prisma.customer.groupBy({
    by: ['plan'],
    _count: { plan: true },
  })
  const order = ['free', 'starter', 'pro', 'enterprise']
  return grouped
    .map((g) => ({
      name: g.plan.charAt(0).toUpperCase() + g.plan.slice(1),
      value: g._count.plan,
      color: PLAN_COLORS[g.plan] ?? '#94a3b8',
      _plan: g.plan,
    }))
    .sort((a, b) => order.indexOf(a._plan) - order.indexOf(b._plan))
    .map(({ name, value, color }) => ({ name, value, color }))
}

/** New vs. churned customers per month for the growth chart. */
export async function getGrowthByMonth(months = 6) {
  const customers = await prisma.customer.findMany({ select: { createdAt: true, status: true, lastActiveAt: true } })
  const buckets: { label: string; new: number; churned: number }[] = []
  const now = new Date()
  for (let m = months - 1; m >= 0; m--) {
    const d = new Date(now.getFullYear(), now.getMonth() - m, 1)
    const next = new Date(now.getFullYear(), now.getMonth() - m + 1, 1)
    const label = d.toLocaleDateString('en-US', { month: 'short' })
    const created = customers.filter((c) => c.createdAt >= d && c.createdAt < next).length
    const churned = customers.filter(
      (c) => c.status === 'churned' && c.lastActiveAt >= d && c.lastActiveAt < next,
    ).length
    buckets.push({ label, new: created, churned })
  }
  return buckets
}

export async function getTopCustomers(limit = 5) {
  return prisma.customer.findMany({
    where: { status: { in: ['active', 'trialing'] } },
    orderBy: { mrr: 'desc' },
    take: limit,
  })
}

export type ServiceStatus = { name: string; status: 'operational' | 'degraded' | 'down'; uptime: string }
export function getSystemStatus(): ServiceStatus[] {
  return [
    { name: 'API', status: 'operational', uptime: '99.99%' },
    { name: 'Dashboard', status: 'operational', uptime: '99.98%' },
    { name: 'Ingestion pipeline', status: 'operational', uptime: '99.95%' },
    { name: 'Webhooks', status: 'degraded', uptime: '99.21%' },
    { name: 'Exports', status: 'operational', uptime: '99.97%' },
  ]
}

export { rangeDays }
export type { DateRange }
