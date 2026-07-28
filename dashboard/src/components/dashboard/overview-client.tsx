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
  Blocks,
  Users2,
  ScrollText,
  Megaphone,
  Settings,
  ArrowUpRight,
  BookOpenCheck,
} from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { WidgetCustomizer } from '@/components/dashboard/widget-customizer'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge, statusTone, severityTone, severityRail, TickMeter } from '@/components/ui/badge'
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
import { GuidedTour, type TourStep } from '@/components/dashboard/tour-engine'
import { RiskBreakdownModal } from '@/components/dashboard/risk-breakdown'

const OVERVIEW_TOUR_STEPS: readonly TourStep[] = [
  {
    eyebrow: 'Welcome to Docket',
    title: 'This is your moderation desk',
    description: 'Protection, cases, appeals, and activity all run from here. Ninety seconds now saves guesswork later.',
  },
  {
    target: 'server-switcher',
    eyebrow: 'Workspace',
    title: 'Your servers live here',
    description: 'Switch between the servers you manage. Every setting, case, and chart is scoped to the selected server.',
  },
  {
    target: 'modules',
    eyebrow: 'Features',
    title: 'Modules switch features on',
    description: 'Verification, AutoMod, Guardian, tickets, welcome cards — every switch applies to this server only.',
  },
  {
    target: 'overview-widgets',
    eyebrow: 'Signals',
    title: 'Your server at a glance',
    description: 'Live widgets for moderation load, member growth, the risk watchlist, and recent activity. Reorder or hide them from Customize.',
  },
  {
    target: 'activity',
    eyebrow: 'Records',
    title: 'Every action leaves a record',
    description: 'Activity keeps the full timeline — who was punished, what AutoMod blocked, who joined — so staff never dig through Discord.',
  },
  {
    eyebrow: 'First win',
    title: 'Start with AutoMod',
    description: 'The fastest protection upgrade: open AutoMod and apply a template. Every rule, word list, and link list stays editable afterwards.',
    action: { label: 'Open AutoMod', href: '/dashboard/automod' },
  },
]

type Kpi = { value: number; delta: number }
type OverviewData = {
  kpis: { actions: Kpi; openCases: Kpi; automod: Kpi; pendingAppeals: Kpi }
  actionsSeries: { label: string; value: number }[]
  automodSeries: { label: string; value: number }[]
  channels: { label: string; value: number }[]
  growth: { label: string; joined: number; left: number }[]
  infractions: { name: string; value: number; color: string }[]
  totalMembers: number
  watchlist: { id: string; displayName: string; username: string; avatarUrl: string | null; riskLevel: string; warnings: number; avatarColor: string }[]
  topRules: { id: string; name: string; trigger: string; action: string; severity: string; hits: number; enabled: boolean }[]
  recentActivity: { id: string; actorName: string; action: string; target: string | null; createdAt: string }[]
  systemStatus: { name: string; status: string; uptime: string }[]
}

type WorkspaceSummary = {
  dashboardAdministrators: number
  auditEvents: number
  serverMembers: number | null
}

const WORKSPACE_ACTIONS = [
  { label: 'Modules', description: 'Configure bot features', href: '/dashboard/modules', icon: Blocks },
  { label: 'Team', description: 'Review dashboard administrators', href: '/dashboard/users', icon: Users2 },
  { label: 'Audit history', description: 'Inspect sensitive changes', href: '/dashboard/activity/audit', icon: ScrollText },
  { label: 'Broadcast', description: 'Notify the dashboard team', href: '/dashboard/notifications/broadcast', icon: Megaphone },
  { label: 'Settings', description: 'Manage workspace preferences', href: '/dashboard/settings', icon: Settings },
]

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

export function OverviewClient({ workspaceSummary, guildId }: { workspaceSummary: WorkspaceSummary; guildId: string; guildName: string }) {
  const widgets = useConfigStore((s) => s.config.widgets)
  const dateRange = useConfigStore((s) => s.config.dateRange)
  const refreshInterval = useConfigStore((s) => s.config.refreshInterval)
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const setDateRange = useConfigStore((s) => s.setDateRange)
  const can = useConfigStore((s) => s.can)
  const [customizing, setCustomizing] = useState(false)
  const [walkthroughRun, setWalkthroughRun] = useState(0)
  const [riskMemberId, setRiskMemberId] = useState<string | null>(null)

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
        eyebrow="The desk"
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

      <WorkspaceControls summary={workspaceSummary} onStartWalkthrough={() => setWalkthroughRun((value) => value + 1)} />

      {error && !data ? (
        <Card>
          <ErrorState onRetry={refetch} description={error} />
        </Card>
      ) : loading && !data ? (
        <OverviewSkeleton />
      ) : data ? (
        <Stagger className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-12" data-tour="overview-widgets">
          {ordered.map((w) => (
            <StaggerItem key={w.key} className={SPAN[w.key] ?? 'lg:col-span-6'}>
              <Widget widgetKey={w.key} chartType={(w.chartType ?? 'area') as ChartType} data={data} onShowRisk={(memberId) => setRiskMemberId(memberId)} />
            </StaggerItem>
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
      <GuidedTour steps={OVERVIEW_TOUR_STEPS} storageKey={`docket:tour:v2:${guildId}`} restartToken={walkthroughRun} />
      {riskMemberId && <RiskBreakdownModal memberId={riskMemberId} onClose={() => setRiskMemberId(null)} />}
    </>
  )
}

function WorkspaceControls({ summary, onStartWalkthrough }: { summary: WorkspaceSummary; onStartWalkthrough: () => void }) {
  return (
    <Card className="mb-4 overflow-hidden">
      <div className="grid lg:grid-cols-[minmax(240px,0.8fr)_minmax(0,2.2fr)]">
        <div className="border-b border-border bg-surface-2/45 p-5 lg:border-b-0 lg:border-r">
          <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-accent">
            Workspace controls
          </p>
          <h2 className="mt-2 font-display text-lg font-semibold text-foreground">Everything in one place</h2>
          <p className="mt-1 text-sm leading-6 text-muted">
            Access follows your live Discord Administrator permission for this server.
          </p>
          <Button variant="ghost" size="sm" onClick={onStartWalkthrough} className="mt-3 -ml-2">
            <BookOpenCheck className="size-4" /> Walkthrough
          </Button>
          <dl className="mt-4 grid grid-cols-3 gap-3 border-t border-border pt-4">
            <div>
              <dt className="text-[0.6875rem] text-muted-2">Admins</dt>
              <dd className="mt-0.5 text-sm font-semibold tabular-nums text-foreground">{summary.dashboardAdministrators}</dd>
            </div>
            <div>
              <dt className="text-[0.6875rem] text-muted-2">Members</dt>
              <dd className="mt-0.5 text-sm font-semibold tabular-nums text-foreground">
                {summary.serverMembers?.toLocaleString() ?? 'Live'}
              </dd>
            </div>
            <div>
              <dt className="text-[0.6875rem] text-muted-2">Audit</dt>
              <dd className="mt-0.5 text-sm font-semibold tabular-nums text-foreground">{summary.auditEvents.toLocaleString()}</dd>
            </div>
          </dl>
        </div>
        <div className="grid gap-px bg-border sm:grid-cols-2 xl:grid-cols-3">
          {WORKSPACE_ACTIONS.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className="group flex min-h-24 items-start gap-3 bg-card p-4 transition-colors hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
            >
              <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
                <action.icon className="size-4.5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
                  {action.label}
                  <ArrowUpRight className="size-3.5 text-muted-2 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                </span>
                <span className="mt-1 block text-xs leading-5 text-muted">{action.description}</span>
              </span>
            </Link>
          ))}
        </div>
      </div>
    </Card>
  )
}

function Widget({
  widgetKey,
  chartType,
  data,
  onShowRisk,
}: {
  widgetKey: string
  chartType: ChartType
  data: OverviewData
  onShowRisk: (memberId: string) => void
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
        <ChartCard title="Active channels by message volume">
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
              <div key={r.id} className={`${severityRail(r.severity)} flex items-center gap-3 rounded-md py-1.5 pr-1`}>
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
                  <li key={m.id}>
                    <button
                      type="button"
                      onClick={() => onShowRisk(m.id)}
                      title="See why this member has this risk score"
                      className={`${severityRail(m.riskLevel)} flex w-full items-center gap-3 rounded-md py-1.5 pr-1 text-left transition-colors hover:bg-surface-2/70`}
                    >
                      <Avatar name={m.displayName} color={m.avatarColor} src={m.avatarUrl} size="sm" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{m.displayName}</p>
                        <p className="truncate text-xs text-muted">@{m.username}</p>
                      </div>
                      <TickMeter severity={m.riskLevel} />
                      <Badge tone={severityTone(m.riskLevel)}>{m.riskLevel}</Badge>
                      <span className="w-14 text-right text-sm font-medium tabular-nums text-foreground">
                        {m.warnings} warns
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )
    case 'status-system': {
      const statuses = data.systemStatus.map((service) => service.status.trim().toLowerCase())
      const overall = statuses.every((status) => status === 'operational')
        ? 'operational'
        : statuses.some((status) => status === 'down' || status === 'unavailable')
          ? 'down'
          : 'degraded'
      return (
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Bot status</CardTitle>
            <Badge tone={statusTone(overall)} dot>
              {overall === 'operational' ? 'Operational' : overall === 'degraded' ? 'Degraded' : 'Attention needed'}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2.5 pt-3">
            {data.systemStatus.map((service) => {
              const status = service.status.trim().toLowerCase()
              return (
                <div key={service.name} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2 text-foreground">
                    <span
                      className={`size-2 rounded-full ${
                        status === 'operational'
                          ? 'bg-success'
                          : status === 'degraded'
                            ? 'bg-warning'
                            : 'bg-danger'
                      }`}
                    />
                    {service.name}
                  </span>
                  <Badge tone={statusTone(status)}>{service.uptime}</Badge>
                </div>
              )
            })}
          </CardContent>
        </Card>
      )
    }
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
