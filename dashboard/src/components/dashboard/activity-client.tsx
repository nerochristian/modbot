'use client'

import { useMemo, useState } from 'react'
import { Activity, ChevronDown, Gavel, LayoutDashboard, ShieldAlert, UserPlus } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox } from '@/components/dashboard/table-toolbar'
import { Card, CardContent } from '@/components/ui/card'
import { Avatar } from '@/components/ui/avatar'
import { Badge, severityTone } from '@/components/ui/badge'
import { Pagination } from '@/components/ui/pagination'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { useApi } from '@/lib/use-api'
import { useListParams } from '@/lib/use-list-params'
import { cn } from '@/lib/utils'
import { format, formatDistanceToNow, isSameDay, isToday, isYesterday } from 'date-fns'

type Item = {
  id: string
  category: 'moderation' | 'automod' | 'members' | 'dashboard'
  action: string
  createdAt: string
  actor: { name: string; avatarUrl: string | null }
  target: { id: string; name: string | null; avatarUrl: string | null } | null
  detail: {
    severity: string | null
    reason: string | null
    rule: string | null
    deleted: boolean
    caseNumber: number | null
  }
}
type Payload = { data: Item[]; page: number; pageSize: number; total: number; totalPages: number }

const CATEGORY_META: Record<Item['category'], { label: string; icon: typeof Gavel; chip: string }> = {
  moderation: { label: 'Moderation', icon: Gavel, chip: 'border-danger/30 bg-danger-soft text-danger' },
  automod: { label: 'AutoMod', icon: ShieldAlert, chip: 'border-[#8b5cf6]/30 bg-[#8b5cf6]/10 text-[#8b5cf6]' },
  members: { label: 'Members', icon: UserPlus, chip: 'border-success/30 bg-success-soft text-success' },
  dashboard: { label: 'Dashboard', icon: LayoutDashboard, chip: 'border-accent-line bg-accent-soft text-accent' },
}

const CATEGORY_FILTERS = [
  { value: '', label: 'All activity' },
  { value: 'moderation', label: 'Moderation' },
  { value: 'automod', label: 'AutoMod' },
  { value: 'members', label: 'Members' },
  { value: 'dashboard', label: 'Dashboard' },
]

function humanAction(action: string) {
  return action.replace(/_/g, ' ')
}

function dayLabel(date: Date) {
  if (isToday(date)) return 'Today'
  if (isYesterday(date)) return 'Yesterday'
  return format(date, 'EEEE, MMM d')
}

export function ActivityClient() {
  const list = useListParams({ pageSize: 20 })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/activity?${list.queryString}`)
  const [expanded, setExpanded] = useState<string | null>(null)

  const groups = useMemo(() => {
    if (!data) return []
    const out: { label: string; items: Item[] }[] = []
    for (const item of data.data) {
      const date = new Date(item.createdAt)
      const label = dayLabel(date)
      const group = out[out.length - 1]
      if (group && isSameDay(new Date(group.items[0].createdAt), date)) group.items.push(item)
      else out.push({ label, items: [item] })
    }
    return out
  }, [data])

  return (
    <>
      <PageHeader eyebrow="Ledger" title="Activity" description="The full timeline of moderation, AutoMod blocks, membership, and staff changes." />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search actors, actions, reasons…" />
          <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Activity category">
            {CATEGORY_FILTERS.map((filter) => {
              const active = (list.params.filters.category ?? '') === filter.value
              return (
                <button
                  key={filter.value}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => list.setFilter('category', filter.value)}
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-xs font-medium transition-all',
                    active
                      ? 'border-accent bg-accent text-accent-foreground shadow-sm'
                      : 'border-border bg-surface-2/50 text-muted hover:border-accent-line hover:text-foreground',
                  )}
                >
                  {filter.label}
                </button>
              )
            })}
          </div>
        </div>

        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : data && data.data.length === 0 ? (
          <EmptyState icon={Activity} title="No activity found" description="Nothing matches your search or filters yet." />
        ) : data ? (
          <>
            <CardContent className="space-y-8">
              {groups.map((group) => (
                <section key={group.label}>
                  <div className="mb-3 flex items-center gap-3">
                    <h2 className="font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-muted-2">{group.label}</h2>
                    <span className="h-px flex-1 bg-border" />
                  </div>
                  <ol className="relative space-y-1">
                    {group.items.map((item) => {
                      const meta = CATEGORY_META[item.category] ?? CATEGORY_META.dashboard
                      const Icon = meta.icon
                      const isOpen = expanded === item.id
                      const hasDetail = !!(item.detail.reason || item.detail.rule || item.detail.caseNumber)
                      return (
                        <li key={item.id}>
                          <button
                            type="button"
                            disabled={!hasDetail}
                            onClick={() => setExpanded(isOpen ? null : item.id)}
                            className={cn(
                              'flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors',
                              hasDetail && 'cursor-pointer hover:bg-surface-2/60',
                              isOpen && 'bg-surface-2/60',
                            )}
                          >
                            <span className={cn('mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border', meta.chip)}>
                              <Icon className="size-4" />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                                <span className="text-sm text-foreground">
                                  <span className="font-medium">{item.actor.name}</span>{' '}
                                  <span className="text-muted">{humanAction(item.action)}</span>
                                  {item.target && (
                                    <>
                                      {' '}
                                      <span className="inline-flex items-center gap-1.5 font-medium">
                                        {item.target.avatarUrl && (
                                          <Avatar name={item.target.name ?? item.target.id} src={item.target.avatarUrl} size="xs" />
                                        )}
                                        {item.target.name ?? `user ${item.target.id}`}
                                      </span>
                                    </>
                                  )}
                                </span>
                                {item.detail.severity && (
                                  <Badge tone={severityTone(item.detail.severity)}>{item.detail.severity}</Badge>
                                )}
                                {item.detail.deleted && <Badge tone="neutral">deleted</Badge>}
                                {item.detail.caseNumber != null && (
                                  <span className="mono-id text-xs text-muted-2">#CASE-{String(item.detail.caseNumber).padStart(4, '0')}</span>
                                )}
                              </span>
                              <span className="mt-0.5 block text-xs text-muted-2" title={format(new Date(item.createdAt), 'PPpp')}>
                                {formatDistanceToNow(new Date(item.createdAt), { addSuffix: true })}
                                {' · '}
                                {meta.label}
                                {item.detail.rule && ` · ${item.detail.rule.replace(/_/g, ' ')}`}
                              </span>
                              {isOpen && item.detail.reason && (
                                <span className="animate-fade-in mt-2 block rounded-lg border border-border bg-surface-2/50 px-3 py-2 text-sm text-muted">
                                  {item.detail.reason}
                                </span>
                              )}
                            </span>
                            {hasDetail && (
                              <ChevronDown className={cn('mt-2 size-4 shrink-0 text-muted-2 transition-transform', isOpen && 'rotate-180')} />
                            )}
                          </button>
                        </li>
                      )
                    })}
                  </ol>
                </section>
              ))}
            </CardContent>
            <div className="border-t border-border">
              <Pagination page={data.page} totalPages={data.totalPages} total={data.total} pageSize={data.pageSize} onPageChange={list.setPage} />
            </div>
          </>
        ) : null}
      </Card>
    </>
  )
}
