'use client'

import { Fragment, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Ban,
  ChevronDown,
  Clock3,
  Download,
  Gavel,
  Loader2,
  MessageSquareWarning,
  ShieldAlert,
  TimerReset,
  UserRoundX,
  Users2,
} from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, ColumnsMenu } from '@/components/dashboard/table-toolbar'
import { SavedViews } from '@/components/dashboard/saved-views'
import { Card } from '@/components/ui/card'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge, severityTone, TickMeter } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { Pagination } from '@/components/ui/pagination'
import { LoadingRows } from '@/components/ui/spinner'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { useListParams, type ListParams } from '@/lib/use-list-params'
import { exportRecords } from '@/lib/export-client'
import { cn, formatNumber } from '@/lib/utils'

type Member = {
  id: string
  username: string
  displayName: string
  discordId: string
  riskLevel: string
  warnings: number
  messages: number
  avatarColor: string
  avatarUrl: string
  joinedAt: string
  lastActiveAt: string
  timedOutUntil: string | null
}

type MemberRecord = {
  id: string
  ref: number
  action: string
  reason: string
  severity: string
  status: string
  moderatorId: string
  createdAt: string
}

type MemberDetail = {
  id: string
  discordId: string
  username: string
  displayName: string
  avatarUrl: string
  joinedAt: string
  lastActiveAt: string | null
  timedOutUntil: string | null
  warnings: number
  messages: number
  riskScore: number
  riskLevel: string
  roles: { id: string; name: string; color: number }[]
  records: MemberRecord[]
}

type Payload = {
  data: Member[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}

const ALL_COLUMNS = [
  { key: 'name', label: 'Member' },
  { key: 'discordId', label: 'Discord ID' },
  { key: 'status', label: 'Discord status' },
  { key: 'riskLevel', label: 'Risk' },
  { key: 'warnings', label: 'Warns' },
  { key: 'messages', label: 'Messages' },
  { key: 'joinedAt', label: 'Joined' },
  { key: 'lastActiveAt', label: 'Last seen' },
]

const ACTIONS = [
  { type: 'warn', label: 'Warn', icon: MessageSquareWarning, variant: 'outline' as const },
  { type: 'timeout', label: 'Timeout', icon: TimerReset, variant: 'outline' as const },
  { type: 'kick', label: 'Kick', icon: UserRoundX, variant: 'outline' as const },
  { type: 'ban', label: 'Ban', icon: Ban, variant: 'danger' as const },
]

function isTimedOut(until: string | null): boolean {
  return Boolean(until && new Date(until).getTime() > Date.now())
}

function cap(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function MembersClient() {
  const router = useRouter()
  const canCase = useConfigStore((s) => s.can('cases.write'))
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const visibleCols = useConfigStore((s) => s.config.tableColumns.members ?? ALL_COLUMNS.map((c) => c.key))
  const setTableColumns = useConfigStore((s) => s.setTableColumns)
  const list = useListParams({ sort: 'discord', order: 'asc' })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/members?${list.queryString}`)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [details, setDetails] = useState<Record<string, MemberDetail>>({})
  const [detailErrors, setDetailErrors] = useState<Record<string, string>>({})
  const [loadingDetailId, setLoadingDetailId] = useState<string | null>(null)
  const [riskMemberId, setRiskMemberId] = useState<string | null>(null)

  const columns = ALL_COLUMNS.filter((column) => visibleCols.includes(column.key))
  const profileColSpan = columns.length + (canCase ? 1 : 0)

  async function loadProfile(member: Member, force = false) {
    if (!force && details[member.id]) return
    setLoadingDetailId(member.id)
    setDetailErrors((current) => ({ ...current, [member.id]: '' }))
    try {
      const response = await fetch(`/api/members/${member.id}`)
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.error ?? 'Could not load this member')
      setDetails((current) => ({ ...current, [member.id]: body as MemberDetail }))
    } catch (reason) {
      setDetailErrors((current) => ({
        ...current,
        [member.id]: reason instanceof Error ? reason.message : 'Could not load this member',
      }))
    } finally {
      setLoadingDetailId((current) => current === member.id ? null : current)
    }
  }

  function toggleProfile(member: Member) {
    if (expandedId === member.id) {
      setExpandedId(null)
      return
    }
    setExpandedId(member.id)
    void loadProfile(member)
  }

  function openAction(member: Member, action: string) {
    router.push(`/dashboard/cases?member=${member.id}&new=1&type=${action}`)
  }

  function handleExport() {
    if (!data) return
    exportRecords(
      data.data.map((member) => ({
        username: member.username,
        displayName: member.displayName,
        discordId: member.discordId,
        discordStatus: isTimedOut(member.timedOutUntil) ? 'Timed out' : 'In server',
        riskLevel: member.riskLevel,
        warnings: member.warnings,
        messages: member.messages,
      })),
      exportFormat,
      'members',
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="Directory"
        title="Members"
        description={
          data
            ? `${formatNumber(data.total)} members synchronized from Discord`
            : 'A live member directory synchronized from your Discord server.'
        }
        actions={
          <Button variant="outline" size="sm" onClick={handleExport} disabled={!data?.data.length}>
            <Download className="size-4" />
            Export page
          </Button>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search members or Discord ID…" />
          <div className="flex flex-wrap items-center gap-2">
            <div className="ml-auto flex items-center gap-2">
              <SavedViews
                page="members"
                currentState={list.params as unknown as Record<string, unknown>}
                onApply={(state) => list.setState({
                  ...(state as Partial<ListParams>),
                  sort: 'discord',
                  order: 'asc',
                  filters: {},
                })}
              />
              <ColumnsMenu
                columns={ALL_COLUMNS}
                visible={visibleCols}
                onChange={(nextColumns) => setTableColumns('members', nextColumns)}
              />
            </div>
          </div>
        </div>

        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <LoadingRows rows={8} cols={profileColSpan} />
        ) : data && data.data.length === 0 ? (
          <EmptyState
            icon={Users2}
            title="No members found"
            description={
              list.activeFilterCount > 0
                ? 'Try adjusting your search or filters.'
                : 'Members will appear here as they join your server.'
            }
            action={
              list.activeFilterCount > 0 ? (
                <Button variant="outline" size="sm" onClick={list.clearFilters}>
                  Clear filters
                </Button>
              ) : undefined
            }
          />
        ) : data ? (
          <>
            <Table>
              <THead>
                <TR>
                  {columns.map((column) => (
                    <TH
                      key={column.key}
                      className={column.key === 'warnings' || column.key === 'messages' ? 'text-right' : undefined}
                    >
                      {column.label}
                    </TH>
                  ))}
                  {canCase && <TH className="w-10" />}
                </TR>
              </THead>
              <TBody>
                {data.data.map((member) => {
                  const expanded = expandedId === member.id
                  return (
                    <Fragment key={member.id}>
                      <TR className={cn('hover:bg-surface-2/50', expanded && 'bg-surface-2/40')}>
                        {columns.map((column) => (
                          <TD
                            key={column.key}
                            className={column.key === 'warnings' || column.key === 'messages' ? 'text-right' : undefined}
                          >
                            {renderCell(member, column.key, expanded, () => toggleProfile(member), () => setRiskMemberId(member.discordId))}
                          </TD>
                        ))}
                        {canCase && (
                          <TD>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label={`Open a moderation case for ${member.displayName}`}
                              onClick={() => openAction(member, 'warn')}
                            >
                              <Gavel className="size-4" />
                            </Button>
                          </TD>
                        )}
                      </TR>
                      {expanded && (
                        <TR>
                          <TD colSpan={profileColSpan} className="bg-surface-2/25 p-0">
                            <MemberCaseFile
                              member={member}
                              detail={details[member.id]}
                              loading={loadingDetailId === member.id}
                              error={detailErrors[member.id]}
                              canCase={canCase}
                              onRetry={() => void loadProfile(member, true)}
                              onAction={(action) => openAction(member, action)}
                              onViewCases={() => router.push(`/dashboard/cases?member=${member.id}`)}
                              onShowRisk={() => setRiskMemberId(member.discordId)}
                            />
                          </TD>
                        </TR>
                      )}
                    </Fragment>
                  )
                })}
              </TBody>
            </Table>
            <div className="border-t border-border">
              <Pagination
                page={data.page}
                totalPages={data.totalPages}
                total={data.total}
                pageSize={data.pageSize}
                onPageChange={list.setPage}
              />
            </div>
          </>
        ) : null}
      </Card>
      {riskMemberId && <RiskBreakdownModal memberId={riskMemberId} onClose={() => setRiskMemberId(null)} />}
    </>
  )
}

function renderCell(member: Member, key: string, expanded: boolean, onToggle: () => void, onShowRisk: () => void) {
  switch (key) {
    case 'name':
      return (
        <button
          type="button"
          className="focus-ring -m-1 flex max-w-full items-center gap-3 rounded-md p-1 text-left"
          aria-expanded={expanded}
          onClick={onToggle}
        >
          <Avatar name={member.displayName} color={member.avatarColor} src={member.avatarUrl} size="sm" />
          <span className="min-w-0">
            <span className="block truncate font-medium text-foreground">{member.displayName}</span>
            <span className="block truncate text-xs text-muted">@{member.username}</span>
          </span>
          <ChevronDown className={cn('ml-auto size-4 shrink-0 text-muted transition-transform', expanded && 'rotate-180')} />
        </button>
      )
    case 'discordId':
      return <span className="mono-id text-xs text-muted">{member.discordId}</span>
    case 'status':
      return isTimedOut(member.timedOutUntil)
        ? <Badge tone="warning" dot>Timed out</Badge>
        : <Badge tone="success" dot>In server</Badge>
    case 'riskLevel':
      return (
        <button
          type="button"
          onClick={onShowRisk}
          title="See why this member has this risk score"
          className="focus-ring -m-1 inline-flex items-center gap-2 rounded-md p-1 transition-colors hover:bg-surface-2"
        >
          <TickMeter severity={member.riskLevel} />
          <Badge tone={severityTone(member.riskLevel)}>{member.riskLevel}</Badge>
        </button>
      )
    case 'warnings':
      return <span className="font-medium tabular-nums">{member.warnings}</span>
    case 'messages':
      return <span className="tabular-nums text-muted">{formatNumber(member.messages)}</span>
    case 'joinedAt':
      return <span className="text-muted">{format(new Date(member.joinedAt), 'MMM d, yyyy')}</span>
    case 'lastActiveAt':
      return <span className="text-muted">{format(new Date(member.lastActiveAt), 'MMM d, yyyy')}</span>
    default:
      return null
  }
}

function MemberCaseFile({
  member,
  detail,
  loading,
  error,
  canCase,
  onRetry,
  onAction,
  onViewCases,
  onShowRisk,
}: {
  member: Member
  detail?: MemberDetail
  loading: boolean
  error?: string
  canCase: boolean
  onRetry: () => void
  onAction: (action: string) => void
  onViewCases: () => void
  onShowRisk: () => void
}) {
  if (loading && !detail) {
    return (
      <div className="flex items-center gap-2 px-5 py-8 text-sm text-muted">
        <Loader2 className="size-4 animate-spin" />
        Loading live Discord profile and moderation records…
      </div>
    )
  }

  if (error && !detail) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-6">
        <p className="text-sm text-danger">{error}</p>
        <Button variant="outline" size="sm" onClick={onRetry}>Try again</Button>
      </div>
    )
  }

  if (!detail) return null
  const timedOut = isTimedOut(detail.timedOutUntil)

  return (
    <section className="border-l-2 border-accent px-5 py-5" aria-label={`${member.displayName} moderation profile`}>
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <Avatar name={detail.displayName} src={detail.avatarUrl} size="lg" className="ring-2 ring-accent-line" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate font-display text-base font-semibold text-foreground">{detail.displayName}</h3>
              {timedOut ? <Badge tone="warning">Timed out</Badge> : <Badge tone="success">In server</Badge>}
            </div>
            <p className="truncate text-xs text-muted">@{detail.username} · {detail.discordId}</p>
          </div>
        </div>

        {canCase && (
          <div className="flex flex-wrap gap-2" aria-label="Moderation actions">
            {ACTIONS.map((action) => (
              <Button key={action.type} variant={action.variant} size="sm" onClick={() => onAction(action.type)}>
                <action.icon className="size-4" />
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>

      <div className="mt-5 grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 xl:grid-cols-4">
        <ProfileMetric label="Warnings" value={formatNumber(detail.warnings)} icon={ShieldAlert} />
        <ProfileMetric label="Messages tracked" value={formatNumber(detail.messages)} icon={MessageSquareWarning} />
        <ProfileMetric label="Joined" value={format(new Date(detail.joinedAt), 'MMM d, yyyy')} icon={Users2} />
        <ProfileMetric
          label="Last activity"
          value={detail.lastActiveAt
            ? formatDistanceToNow(new Date(detail.lastActiveAt), { addSuffix: true })
            : 'No tracked messages'}
          icon={Clock3}
        />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <div className="flex items-center justify-between gap-3">
            <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-muted-2">Server roles</p>
            <span className="text-xs text-muted">{detail.roles.length}</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {detail.roles.length ? detail.roles.map((role) => (
              <Badge key={role.id} tone="neutral">{role.name}</Badge>
            )) : <span className="text-sm text-muted">No assignable roles</span>}
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs text-muted">
            <button
              type="button"
              onClick={onShowRisk}
              title="See why this member has this risk score"
              className="focus-ring -m-1 flex items-center gap-2 rounded-md p-1 transition-colors hover:bg-surface-2"
            >
              <TickMeter severity={detail.riskLevel} />
              <span className="underline decoration-dotted underline-offset-2">{cap(detail.riskLevel)} risk telemetry · score {detail.riskScore}</span>
            </button>
          </div>
          {timedOut && detail.timedOutUntil && (
            <p className="mt-3 text-xs text-warning">
              Timeout ends {format(new Date(detail.timedOutUntil), 'MMM d, yyyy · h:mm a')}
            </p>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between gap-3">
            <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-muted-2">Past moderation records</p>
            <Button variant="ghost" size="sm" onClick={onViewCases}>View all</Button>
          </div>
          {detail.records.length ? (
            <div className="mt-2 divide-y divide-border rounded-lg border border-border bg-card">
              {detail.records.map((record) => (
                <div key={record.id} className="grid gap-2 px-3 py-2.5 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center">
                  <Badge tone={severityTone(record.severity)}>{cap(record.action)}</Badge>
                  <div className="min-w-0">
                    <p className="truncate text-sm text-foreground">{record.reason}</p>
                    <p className="text-xs text-muted">CASE-{String(record.ref).padStart(4, '0')} · Moderator {record.moderatorId}</p>
                  </div>
                  <div className="text-left text-xs text-muted sm:text-right">
                    <p>{format(new Date(record.createdAt), 'MMM d, yyyy')}</p>
                    <p>{cap(record.status)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-2 rounded-lg border border-dashed border-border px-4 py-5 text-sm text-muted">
              No moderation records for this member.
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function ProfileMetric({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Clock3 }) {
  return (
    <div className="flex items-center gap-3 bg-card px-3 py-3">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
        <Icon className="size-4" />
      </span>
      <div className="min-w-0">
        <p className="truncate text-[0.6875rem] text-muted-2">{label}</p>
        <p className="truncate text-sm font-medium text-foreground">{value}</p>
      </div>
    </div>
  )
}
