'use client'

import { useMemo } from 'react'
import { Gavel, Users, ShieldAlert, UserPlus, Download } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { SegmentedControl } from '@/components/ui/segmented'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/empty-state'
import { MultiLineChart, type MultiSeries } from '@/components/charts'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { exportRecords } from '@/lib/export-client'
import { formatCompact } from '@/lib/utils'
import { DATE_RANGES, type DateRange } from '@/lib/dashboard-config'

type Kpi = { value: number; delta: number }
type Point = { label: string; value: number }
type AnalyticsData = {
  kpis: Record<string, Kpi>
  series: Record<string, Point[]>
}

/** Fixed color per metric — bans are red, joins are green, and so on. */
const CHART_SERIES: MultiSeries[] = [
  { key: 'actions', label: 'Mod actions', color: 'var(--accent)' },
  { key: 'automodBlocks', label: 'Automod blocks', color: '#8b5cf6' },
  { key: 'joins', label: 'Joins', color: 'var(--success)' },
  { key: 'leaves', label: 'Leaves', color: 'var(--warning)' },
  { key: 'kicks', label: 'Kicks', color: '#f97316' },
  { key: 'bans', label: 'Bans', color: 'var(--danger)' },
  { key: 'warns', label: 'Warnings', color: '#eab308' },
]

export function AnalyticsClient() {
  const dateRange = useConfigStore((s) => s.config.dateRange)
  const refreshInterval = useConfigStore((s) => s.config.refreshInterval)
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const setDateRange = useConfigStore((s) => s.setDateRange)

  const { data, loading, error, refetch } = useApi<AnalyticsData>(
    `/api/analytics?range=${dateRange}`,
    { refreshInterval },
  )

  // Every metric on one canvas — merged by day label.
  const combined = useMemo(() => {
    if (!data) return []
    const base = data.series.actions ?? []
    return base.map((point, index) => {
      const row: Record<string, number | string> = { label: point.label }
      for (const series of CHART_SERIES) {
        row[series.key] = data.series[series.key]?.[index]?.value ?? 0
      }
      return row
    })
  }, [data])

  function handleExport() {
    if (!combined.length) return
    exportRecords(combined, exportFormat, `analytics-${dateRange}`)
  }

  return (
    <>
      <PageHeader
        eyebrow="Signals"
        title="Analytics"
        description="Every moderation and membership signal on one timeline — hover a day for the full picture."
        actions={
          <>
            <SegmentedControl
              size="sm"
              aria-label="Date range"
              value={dateRange}
              onChange={(v) => setDateRange(v as DateRange)}
              options={DATE_RANGES.map((r) => ({ label: r.value.toUpperCase(), value: r.value }))}
            />
            <Button variant="outline" size="sm" onClick={handleExport} disabled={!combined.length}>
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
              <CardTitle>Everything, one timeline</CardTitle>
              <span className="text-xs text-muted">Toggle metrics with the chips</span>
            </CardHeader>
            <CardContent className="pt-4">
              <MultiLineChart data={combined} series={CHART_SERIES} height={360} valueFormatter={(v) => formatCompact(v)} />
            </CardContent>
          </Card>
        </div>
      ) : null}
    </>
  )
}
