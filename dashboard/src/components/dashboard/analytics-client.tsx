'use client'

import { useState } from 'react'
import { Gavel, Users, ShieldAlert, UserPlus, Download, UserMinus, Ban } from 'lucide-react'
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
  actions: { label: 'Mod actions', format: (v) => formatCompact(v), invert: true },
  automodBlocks: { label: 'Automod blocks', format: (v) => formatCompact(v) },
  members: { label: 'Total members', format: (v) => formatCompact(v) },
  online: { label: 'Online now', format: (v) => formatCompact(v) },
  joins: { label: 'Joins', format: (v) => formatCompact(v) },
  leaves: { label: 'Leaves', format: (v) => formatCompact(v), invert: true },
  bans: { label: 'Bans', format: (v) => formatCompact(v), invert: true },
  warns: { label: 'Warnings', format: (v) => formatCompact(v), invert: true },
}

const SECONDARY = ['joins', 'leaves', 'bans', 'warns']

export function AnalyticsClient() {
  const dateRange = useConfigStore((s) => s.config.dateRange)
  const refreshInterval = useConfigStore((s) => s.config.refreshInterval)
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const setDateRange = useConfigStore((s) => s.setDateRange)

  const [metric, setMetric] = useState('actions')
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
        eyebrow="Signals"
        title="Analytics"
        description="Deep-dive into moderation load, membership, and automod performance."
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
            <StatCard label="Mod actions" value={formatCompact(data.kpis.actions.value)} delta={data.kpis.actions.delta} icon={Gavel} spark={data.series.actions} invertDelta />
            <StatCard label="Automod blocks" value={formatCompact(data.kpis.automodBlocks.value)} delta={data.kpis.automodBlocks.delta} icon={ShieldAlert} spark={data.series.automodBlocks} />
            <StatCard label="Total members" value={formatCompact(data.kpis.members.value)} delta={data.kpis.members.delta} icon={Users} spark={data.series.members} />
            <StatCard label="Joins" value={formatCompact(data.kpis.joins.value)} delta={data.kpis.joins.delta} icon={UserPlus} spark={data.series.joins} />
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
              const Icon = m === 'bans' ? Ban : m === 'leaves' ? UserMinus : m === 'joins' ? UserPlus : ShieldAlert
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
                      type={m === 'joins' ? 'area' : 'bar'}
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
