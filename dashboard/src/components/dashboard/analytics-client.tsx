'use client'

import { useState } from 'react'
import { DollarSign, Users, Percent, Repeat, Download, Activity, TrendingDown } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { SegmentedControl } from '@/components/ui/segmented'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/empty-state'
import { TrendChart } from '@/components/charts'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { exportRecords } from '@/lib/export-client'
import { formatCompact } from '@/lib/utils'
import { DATE_RANGES, type ChartType, type DateRange } from '@/lib/dashboard-config'

type Kpi = { value: number; delta: number }
type Point = { label: string; value: number }
type AnalyticsData = {
  kpis: Record<string, Kpi>
  series: Record<string, Point[]>
}

const METRIC_META: Record<string, { label: string; format: (v: number) => string; invert?: boolean }> = {
  revenue: { label: 'Revenue', format: (v) => `$${formatCompact(v)}` },
  mrr: { label: 'MRR', format: (v) => `$${formatCompact(v)}` },
  active: { label: 'Active users', format: (v) => formatCompact(v) },
  users: { label: 'Total users', format: (v) => formatCompact(v) },
  sessions: { label: 'Sessions', format: (v) => formatCompact(v) },
  conversion: { label: 'Conversion', format: (v) => `${v.toFixed(1)}%` },
  retention: { label: 'Retention', format: (v) => `${v.toFixed(1)}%` },
  churn: { label: 'Churn', format: (v) => `${v.toFixed(1)}%`, invert: true },
}

const SECONDARY = ['retention', 'churn', 'sessions', 'conversion']

export function AnalyticsClient() {
  const dateRange = useConfigStore((s) => s.config.dateRange)
  const refreshInterval = useConfigStore((s) => s.config.refreshInterval)
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const setDateRange = useConfigStore((s) => s.setDateRange)

  const [metric, setMetric] = useState('revenue')
  const [chartType, setChartType] = useState<ChartType>('area')

  const { data, loading, error, refetch } = useApi<AnalyticsData>(
    `/api/analytics?range=${dateRange}`,
    { refreshInterval },
  )

  const meta = METRIC_META[metric]

  function handleExport() {
    if (!data) return
    const rows = data.series[metric].map((p) => ({ period: p.label, [metric]: p.value }))
    exportRecords(rows, exportFormat, `analytics-${metric}-${dateRange}`)
  }

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Deep-dive into revenue, growth, retention, and engagement."
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
          </>
        }
      />

      {error && !data ? (
        <Card>
          <ErrorState onRetry={refetch} description={error} />
        </Card>
      ) : loading && !data ? (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="p-5">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="mt-3 h-7 w-28" />
              </Card>
            ))}
          </div>
          <Card className="p-5">
            <Skeleton className="h-72 w-full" />
          </Card>
        </div>
      ) : data ? (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Revenue" value={`$${formatCompact(data.kpis.revenue.value)}`} delta={data.kpis.revenue.delta} icon={DollarSign} spark={data.series.revenue} />
            <StatCard label="MRR" value={`$${formatCompact(data.kpis.mrr.value)}`} delta={data.kpis.mrr.delta} icon={Repeat} spark={data.series.mrr} />
            <StatCard label="Active users" value={formatCompact(data.kpis.active.value)} delta={data.kpis.active.delta} icon={Users} spark={data.series.active} />
            <StatCard label="Conversion" value={`${data.kpis.conversion.value.toFixed(1)}%`} delta={data.kpis.conversion.delta} icon={Percent} spark={data.series.conversion} />
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Select
                  className="h-9 w-44"
                  options={Object.keys(METRIC_META).map((k) => ({ label: METRIC_META[k].label, value: k }))}
                  value={metric}
                  onChange={(e) => setMetric(e.target.value)}
                />
              </div>
              <SegmentedControl
                size="sm"
                aria-label="Chart type"
                value={chartType}
                onChange={setChartType}
                options={[
                  { label: 'Area', value: 'area' },
                  { label: 'Line', value: 'line' },
                  { label: 'Bar', value: 'bar' },
                ]}
              />
            </CardHeader>
            <CardContent className="pt-4">
              <TrendChart data={data.series[metric]} type={chartType} height={320} valueFormatter={meta.format} />
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            {SECONDARY.map((m) => {
              const mm = METRIC_META[m]
              const Icon = m === 'churn' ? TrendingDown : m === 'sessions' ? Activity : Percent
              return (
                <Card key={m}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Icon className="size-4 text-muted" />
                      {mm.label}
                    </CardTitle>
                    <span className="text-sm font-semibold text-foreground">{mm.format(data.kpis[m].value)}</span>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <TrendChart
                      data={data.series[m]}
                      type={m === 'sessions' ? 'bar' : 'line'}
                      height={200}
                      valueFormatter={mm.format}
                    />
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      ) : null}
    </>
  )
}
