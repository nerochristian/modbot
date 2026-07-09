'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  DollarSign,
  Users,
  Percent,
  TrendingDown,
  SlidersHorizontal,
  Download,
} from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { WidgetCustomizer } from '@/components/dashboard/widget-customizer'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge, statusTone } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { SegmentedControl } from '@/components/ui/segmented'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState, EmptyState } from '@/components/ui/empty-state'
import { TrendChart, GroupedBarChart, DonutChart } from '@/components/charts'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { exportRecords } from '@/lib/export-client'
import { formatCompact, formatCurrency, formatNumber } from '@/lib/utils'
import { DATE_RANGES, type ChartType, type DateRange } from '@/lib/dashboard-config'
import { formatDistanceToNow } from 'date-fns'

type Kpi = { value: number; delta: number }
type OverviewData = {
  kpis: { revenue: Kpi; active: Kpi; conversion: Kpi; churn: Kpi }
  revenueSeries: { label: string; value: number }[]
  retentionSeries: { label: string; value: number }[]
  growth: { label: string; new: number; churned: number }[]
  plans: { name: string; value: number; color: string }[]
  totalCustomers: number
  topCustomers: { id: string; name: string; company: string | null; plan: string; mrr: number; avatarColor: string }[]
  recentActivity: { id: string; actorName: string; action: string; target: string | null; createdAt: string }[]
  systemStatus: { name: string; status: string; uptime: string }[]
}

const SPAN: Record<string, string> = {
  'kpi-revenue': 'lg:col-span-3',
  'kpi-users': 'lg:col-span-3',
  'kpi-conversion': 'lg:col-span-3',
  'kpi-churn': 'lg:col-span-3',
  'chart-revenue': 'lg:col-span-8',
  'chart-plans': 'lg:col-span-4',
  'chart-growth': 'lg:col-span-6',
  'chart-retention': 'lg:col-span-6',
  'list-activity': 'lg:col-span-6',
  'list-customers': 'lg:col-span-6',
  'status-system': 'lg:col-span-4',
  'chart-traffic': 'lg:col-span-8',
}

const TRAFFIC = [
  { label: 'Organic', value: 4200 },
  { label: 'Direct', value: 3100 },
  { label: 'Referral', value: 2200 },
  { label: 'Social', value: 1800 },
  { label: 'Email', value: 1400 },
  { label: 'Paid', value: 900 },
]

function humanAction(action: string) {
  return action.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}

export function OverviewClient() {
  const widgets = useConfigStore((s) => s.config.widgets)
  const dateRange = useConfigStore((s) => s.config.dateRange)
  const refreshInterval = useConfigStore((s) => s.config.refreshInterval)
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const setDateRange = useConfigStore((s) => s.setDateRange)
  const can = useConfigStore((s) => s.can)
  const [customizing, setCustomizing] = useState(false)

  const { data, error, loading, refetch } = useApi<OverviewData>(
    `/api/analytics/overview?range=${dateRange}`,
    { refreshInterval },
  )

  const ordered = [...widgets].sort((a, b) => a.order - b.order).filter((w) => w.visible)

  function handleExport() {
    if (!data) return
    exportRecords(
      data.revenueSeries.map((p) => ({ period: p.label, revenue: p.value })),
      exportFormat,
      `revenue-${dateRange}`,
    )
  }

  return (
    <>
      <PageHeader
        title="Overview"
        description="A real-time snapshot of your business performance."
        actions={
          <>
            <SegmentedControl
              size="sm"
              aria-label="Date range"
              value={dateRange}
              onChange={(v) => setDateRange(v as DateRange)}
              options={DATE_RANGES.map((r) => ({ label: r.value.toUpperCase(), value: r.value }))}
            />
            <Button variant="outline" size="sm" onClick={handleExport} disabled={!data}>
              <Download className="size-4" />
              Export
            </Button>
            {can('config.write') && (
              <Button variant="secondary" size="sm" onClick={() => setCustomizing(true)}>
                <SlidersHorizontal className="size-4" />
                Customize
              </Button>
            )}
          </>
        }
      />

      {error && !data ? (
        <Card>
          <ErrorState onRetry={refetch} description={error} />
        </Card>
      ) : loading && !data ? (
        <OverviewSkeleton />
      ) : data ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-12">
          {ordered.map((w) => (
            <div key={w.key} className={SPAN[w.key] ?? 'lg:col-span-6'}>
              <Widget widgetKey={w.key} chartType={(w.chartType ?? 'area') as ChartType} data={data} />
            </div>
          ))}
          {ordered.length === 0 && (
            <div className="lg:col-span-12">
              <Card>
                <EmptyState
                  icon={SlidersHorizontal}
                  title="No widgets visible"
                  description="All widgets are hidden. Open Customize to add some back."
                  action={
                    can('config.write') ? (
                      <Button size="sm" onClick={() => setCustomizing(true)}>
                        Customize dashboard
                      </Button>
                    ) : undefined
                  }
                />
              </Card>
            </div>
          )}
        </div>
      ) : null}

      <WidgetCustomizer open={customizing} onClose={() => setCustomizing(false)} />
    </>
  )
}

function Widget({
  widgetKey,
  chartType,
  data,
}: {
  widgetKey: string
  chartType: ChartType
  data: OverviewData
}) {
  switch (widgetKey) {
    case 'kpi-revenue':
      return (
        <StatCard
          label="Revenue"
          value={`$${formatCompact(data.kpis.revenue.value)}`}
          delta={data.kpis.revenue.delta}
          icon={DollarSign}
          spark={data.revenueSeries}
        />
      )
    case 'kpi-users':
      return (
        <StatCard
          label="Active users"
          value={formatCompact(data.kpis.active.value)}
          delta={data.kpis.active.delta}
          icon={Users}
        />
      )
    case 'kpi-conversion':
      return (
        <StatCard
          label="Conversion rate"
          value={`${data.kpis.conversion.value.toFixed(1)}%`}
          delta={data.kpis.conversion.delta}
          icon={Percent}
        />
      )
    case 'kpi-churn':
      return (
        <StatCard
          label="Churn rate"
          value={`${data.kpis.churn.value.toFixed(1)}%`}
          delta={data.kpis.churn.delta}
          icon={TrendingDown}
          invertDelta
        />
      )
    case 'chart-revenue':
      return (
        <ChartCard title="Revenue over time">
          <TrendChart
            data={data.revenueSeries}
            type={chartType}
            valueFormatter={(v) => `$${formatCompact(v)}`}
          />
        </ChartCard>
      )
    case 'chart-retention':
      return (
        <ChartCard title="Retention">
          <TrendChart data={data.retentionSeries} type={chartType} valueFormatter={(v) => `${v.toFixed(0)}%`} />
        </ChartCard>
      )
    case 'chart-growth':
      return (
        <ChartCard title="User growth">
          <GroupedBarChart
            data={data.growth as unknown as Record<string, number | string>[]}
            keys={[
              { key: 'new', color: 'var(--accent)', label: 'New' },
              { key: 'churned', color: '#f43f5e', label: 'Churned' },
            ]}
          />
        </ChartCard>
      )
    case 'chart-plans':
      return (
        <ChartCard title="Customers by plan">
          <div className="flex flex-col items-center">
            <DonutChart data={data.plans} valueFormatter={(v) => formatNumber(v)} />
            <div className="mt-3 grid w-full grid-cols-2 gap-2">
              {data.plans.map((p) => (
                <div key={p.name} className="flex items-center gap-2 text-xs">
                  <span className="size-2.5 rounded-full" style={{ background: p.color }} />
                  <span className="text-muted">{p.name}</span>
                  <span className="ml-auto font-medium text-foreground">{formatNumber(p.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      )
    case 'chart-traffic':
      return (
        <ChartCard title="Traffic sources">
          <TrendChart data={TRAFFIC} type="bar" showAxes valueFormatter={(v) => formatCompact(v)} />
        </ChartCard>
      )
    case 'list-activity':
      return (
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <Link href="/dashboard/activity" className="text-xs font-medium text-accent hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="pt-3">
            <ul className="space-y-3">
              {data.recentActivity.map((a) => (
                <li key={a.id} className="flex items-start gap-3">
                  <Avatar name={a.actorName} size="sm" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-foreground">
                      <span className="font-medium">{a.actorName}</span>{' '}
                      <span className="text-muted">{humanAction(a.action).toLowerCase()}</span>
                      {a.target && <span className="font-medium"> {a.target}</span>}
                    </p>
                    <p className="text-xs text-muted-2">
                      {formatDistanceToNow(new Date(a.createdAt), { addSuffix: true })}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )
    case 'list-customers':
      return (
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Top customers</CardTitle>
            <Link href="/dashboard/customers" className="text-xs font-medium text-accent hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="pt-3">
            <ul className="space-y-1">
              {data.topCustomers.map((c) => (
                <li key={c.id} className="flex items-center gap-3 rounded-lg px-1 py-1.5">
                  <Avatar name={c.name} color={c.avatarColor} size="sm" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">{c.name}</p>
                    <p className="truncate text-xs text-muted">{c.company ?? '—'}</p>
                  </div>
                  <Badge tone="accent">{c.plan}</Badge>
                  <span className="w-20 text-right text-sm font-medium text-foreground">
                    {formatCurrency(c.mrr)}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )
    case 'status-system':
      return (
        <Card className="h-full">
          <CardHeader>
            <CardTitle>System status</CardTitle>
            <Badge tone="success" dot>
              Operational
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2.5 pt-3">
            {data.systemStatus.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-foreground">
                  <span
                    className={`size-2 rounded-full ${
                      s.status === 'operational'
                        ? 'bg-success'
                        : s.status === 'degraded'
                          ? 'bg-warning'
                          : 'bg-danger'
                    }`}
                  />
                  {s.name}
                </span>
                <Badge tone={statusTone(s.status === 'operational' ? 'active' : s.status === 'degraded' ? 'warning' : 'failed')}>
                  {s.uptime}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )
    default:
      return null
  }
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="pt-4">{children}</CardContent>
    </Card>
  )
}

function OverviewSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-12">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="lg:col-span-3">
          <Card className="p-5">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="mt-3 h-7 w-32" />
            <Skeleton className="mt-3 h-4 w-16" />
          </Card>
        </div>
      ))}
      <div className="lg:col-span-8">
        <Card className="p-5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="mt-4 h-64 w-full" />
        </Card>
      </div>
      <div className="lg:col-span-4">
        <Card className="p-5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="mt-4 h-64 w-full" />
        </Card>
      </div>
    </div>
  )
}
