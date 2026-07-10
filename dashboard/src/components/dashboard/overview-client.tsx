'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  Gavel,
  FolderOpen,
  ShieldAlert,
  Scale,
  SlidersHorizontal,
  Download,
} from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { WidgetCustomizer } from '@/components/dashboard/widget-customizer'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge, statusTone, severityTone, severitySpine } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { SegmentedControl } from '@/components/ui/segmented'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState, EmptyState } from '@/components/ui/empty-state'
import { TrendChart, GroupedBarChart, DonutChart } from '@/components/charts'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { exportRecords } from '@/lib/export-client'
import { formatCompact, formatNumber } from '@/lib/utils'
import { DATE_RANGES, type ChartType, type DateRange } from '@/lib/dashboard-config'
import { formatDistanceToNow } from 'date-fns'

type Kpi = { value: number; delta: number }
type OverviewData = {
  kpis: { actions: Kpi; openCases: Kpi; automod: Kpi; pendingAppeals: Kpi }
  actionsSeries: { label: string; value: number }[]
  automodSeries: { label: string; value: number }[]
  channels: { label: string; value: number }[]
  growth: { label: string; joined: number; left: number }[]
  infractions: { name: string; value: number; color: string }[]
  totalMembers: number
  watchlist: { id: string; displayName: string; username: string; riskLevel: string; warnings: number; avatarColor: string }[]
  topRules: { id: string; name: string; trigger: string; action: string; severity: string; hits: number; enabled: boolean }[]
  recentActivity: { id: string; actorName: string; action: string; target: string | null; createdAt: string }[]
  systemStatus: { name: string; status: string; uptime: string }[]
}

const SPAN: Record<string, string> = {
  'kpi-actions': 'lg:col-span-3',
  'kpi-openCases': 'lg:col-span-3',
  'kpi-automod': 'lg:col-span-3',
  'kpi-appeals': 'lg:col-span-3',
  'chart-actions': 'lg:col-span-8',
  'chart-infractions': 'lg:col-span-4',
  'chart-joins': 'lg:col-span-6',
  'chart-rules': 'lg:col-span-6',
  'list-activity': 'lg:col-span-6',
  'list-members': 'lg:col-span-6',
  'status-system': 'lg:col-span-4',
  'chart-channels': 'lg:col-span-8',
}

const TRIGGER_LABELS: Record<string, string> = {
  keyword: 'Keyword',
  regex: 'Regex',
  spam: 'Spam',
  mention_spam: 'Mentions',
  invite: 'Invites',
  link: 'Links',
  caps: 'Caps',
  attachment: 'Files',
}

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
      data.actionsSeries.map((p) => ({ period: p.label, actions: p.value })),
      exportFormat,
      `mod-actions-${dateRange}`,
    )
  }

  return (
    <>
      <PageHeader
        title="Overview"
        description="A real-time snapshot of your server's health and moderation load."
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
    case 'kpi-actions':
      return (
        <StatCard
          label="Mod actions"
          value={formatCompact(data.kpis.actions.value)}
          delta={data.kpis.actions.delta}
          icon={Gavel}
          spark={data.actionsSeries}
          invertDelta
        />
      )
    case 'kpi-openCases':
      return (
        <StatCard
          label="Open cases"
          value={formatNumber(data.kpis.openCases.value)}
          delta={data.kpis.openCases.delta}
          icon={FolderOpen}
          invertDelta
        />
      )
    case 'kpi-automod':
      return (
        <StatCard
          label="Automod blocks"
          value={formatCompact(data.kpis.automod.value)}
          delta={data.kpis.automod.delta}
          icon={ShieldAlert}
        />
      )
    case 'kpi-appeals':
      return (
        <StatCard
          label="Pending appeals"
          value={formatNumber(data.kpis.pendingAppeals.value)}
          delta={data.kpis.pendingAppeals.delta}
          icon={Scale}
          invertDelta
        />
      )
    case 'chart-actions':
      return (
        <ChartCard title="Moderation actions over time">
          <TrendChart
            data={data.actionsSeries}
            type={chartType}
            valueFormatter={(v) => formatCompact(v)}
          />
        </ChartCard>
      )
    case 'chart-channels':
      return (
        <ChartCard title="Flagged channels">
          <TrendChart data={data.channels} type="bar" showAxes valueFormatter={(v) => formatCompact(v)} />
        </ChartCard>
      )
    case 'chart-joins':
      return (
        <ChartCard title="Member growth">
          <GroupedBarChart
            data={data.growth as unknown as Record<string, number | string>[]}
            keys={[
              { key: 'joined', color: 'var(--mint)', label: 'Joined' },
              { key: 'left', color: '#f0476b', label: 'Left' },
            ]}
          />
        </ChartCard>
      )
    case 'chart-infractions':
      return (
        <ChartCard title="Infractions by type">
          <div className="flex flex-col items-center">
            <DonutChart data={data.infractions} valueFormatter={(v) => formatNumber(v)} />
            <div className="mt-3 grid w-full grid-cols-2 gap-2">
              {data.infractions.map((p) => (
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
    case 'chart-rules':
      return (
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Top automod rules</CardTitle>
            <Link href="/dashboard/automod" className="text-xs font-medium text-accent hover:underline">
              Manage
            </Link>
          </CardHeader>
          <CardContent className="space-y-2 pt-3">
            {data.topRules.map((r) => (
              <div key={r.id} className={`${severitySpine(r.severity)} flex items-center gap-3 rounded-lg py-1.5 pl-3 pr-1`}>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{r.name}</p>
                  <p className="text-xs text-muted">{TRIGGER_LABELS[r.trigger] ?? r.trigger} · {r.action}</p>
                </div>
                <span className="text-sm font-medium tabular-nums text-foreground">{formatCompact(r.hits)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
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
                      {a.target && <span className="mono-id text-xs font-medium"> {a.target}</span>}
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
    case 'list-members':
      return (
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Watchlist</CardTitle>
            <Link href="/dashboard/members" className="text-xs font-medium text-accent hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="pt-3">
            {data.watchlist.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted">No flagged members. All quiet.</p>
            ) : (
              <ul className="space-y-1">
                {data.watchlist.map((m) => (
                  <li key={m.id} className={`${severitySpine(m.riskLevel)} flex items-center gap-3 rounded-lg py-1.5 pl-3 pr-1`}>
                    <Avatar name={m.displayName} color={m.avatarColor} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">{m.displayName}</p>
                      <p className="truncate text-xs text-muted">@{m.username}</p>
                    </div>
                    <Badge tone={severityTone(m.riskLevel)}>{m.riskLevel}</Badge>
                    <span className="w-14 text-right text-sm font-medium tabular-nums text-foreground">
                      {m.warnings} warns
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )
    case 'status-system':
      return (
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Bot status</CardTitle>
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
                <Badge tone={statusTone(s.status)}>{s.uptime}</Badge>
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
