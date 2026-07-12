'use client'

import { useState } from 'react'
import { Download, Scale } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, SortableTH, ColumnsMenu } from '@/components/dashboard/table-toolbar'
import { SavedViews } from '@/components/dashboard/saved-views'
import { Card } from '@/components/ui/card'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge, statusTone, severityTone, severityRail, TickMeter } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { Select } from '@/components/ui/select'
import { Field, Textarea } from '@/components/ui/input'
import { Modal } from '@/components/ui/modal'
import { Pagination } from '@/components/ui/pagination'
import { LoadingRows } from '@/components/ui/spinner'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { useToast } from '@/components/ui/toast'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { useListParams, type ListParams } from '@/lib/use-list-params'
import { exportRecords } from '@/lib/export-client'
import { formatNumber } from '@/lib/utils'
import { format } from 'date-fns'

type Appeal = {
  id: string
  ref: number
  memberId: string
  caseId: string
  status: string
  message: string
  decision: string | null
  reviewedBy: string | null
  submittedAt: string
  reviewedAt: string | null
  member: {
    id: string
    username: string
    displayName: string
    discordId: string
    avatarColor: string
  }
  case: {
    id: string
    ref: number
    type: string
    severity: string
    reason: string
  }
}
type Payload = {
  data: Appeal[]
  page: number
  pageSize: number
  total: number
  totalPages: number
  pending: number
}

const ALL_COLUMNS = [
  { key: 'ref', label: 'Appeal' },
  { key: 'member', label: 'Member' },
  { key: 'caseRef', label: 'Case' },
  { key: 'status', label: 'Status' },
  { key: 'submittedAt', label: 'Submitted' },
]
const SORTABLE = new Set(['ref', 'status', 'submittedAt'])

const STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Denied', value: 'denied' },
]

const aplRef = (ref: number) => `#APL-${String(ref).padStart(4, '0')}`
const caseRefLabel = (ref: number) => `#CASE-${String(ref).padStart(4, '0')}`

export function AppealsClient() {
  const canWrite = useConfigStore((s) => s.can('appeals.write'))
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const visibleCols = useConfigStore((s) => s.config.tableColumns.appeals ?? ALL_COLUMNS.map((c) => c.key))
  const setTableColumns = useConfigStore((s) => s.setTableColumns)

  const list = useListParams({ sort: 'submittedAt', order: 'desc' })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/appeals?${list.queryString}`)

  const [reviewing, setReviewing] = useState<Appeal | null>(null)

  const columns = ALL_COLUMNS.filter((c) => visibleCols.includes(c.key))

  function handleExport() {
    if (!data) return
    exportRecords(
      data.data.map((a) => ({
        ref: aplRef(a.ref),
        member: a.member.displayName,
        caseRef: caseRefLabel(a.case.ref),
        status: a.status,
        submittedAt: a.submittedAt,
      })),
      exportFormat,
      'appeals',
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="Review queue"
        title="Appeals"
        description={
          data
            ? `${formatNumber(data.total)} appeals · ${formatNumber(data.pending)} pending`
            : 'Member requests to overturn a case.'
        }
        actions={
          <Button variant="outline" size="sm" onClick={handleExport} disabled={!data?.data.length}>
            <Download className="size-4" />
            Export
          </Button>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search appeals or #ref…" />
          <div className="flex flex-wrap items-center gap-2">
            <Select
              className="h-9 w-auto"
              options={STATUS_OPTIONS}
              value={list.params.filters.status ?? ''}
              onChange={(e) => list.setFilter('status', e.target.value)}
            />
            <div className="ml-auto flex items-center gap-2">
              <SavedViews
                page="appeals"
                currentState={list.params as unknown as Record<string, unknown>}
                onApply={(state) => list.setState(state as Partial<ListParams>)}
              />
              <ColumnsMenu
                columns={ALL_COLUMNS}
                visible={visibleCols}
                onChange={(cols) => setTableColumns('appeals', cols)}
              />
            </div>
          </div>
        </div>

        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <LoadingRows rows={8} cols={columns.length + 1} />
        ) : data && data.data.length === 0 ? (
          <EmptyState
            icon={Scale}
            title="No appeals found"
            description={
              list.activeFilterCount > 0
                ? 'Try adjusting your search or filters.'
                : 'Appeals will appear here as members submit them.'
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
                  {columns.map((c) =>
                    SORTABLE.has(c.key) ? (
                      <SortableTH
                        key={c.key}
                        column={c.key}
                        label={c.label}
                        sort={list.params.sort}
                        order={list.params.order}
                        onToggle={list.toggleSort}
                      />
                    ) : (
                      <TH key={c.key}>{c.label}</TH>
                    ),
                  )}
                  <TH className="w-24" />
                </TR>
              </THead>
              <TBody>
                {data.data.map((a) => (
                  <TR
                    key={a.id}
                    className="cursor-pointer hover:bg-surface-2/50"
                    onClick={() => setReviewing(a)}
                  >
                    {columns.map((col) => (
                      <TD key={col.key}>{renderCell(a, col.key)}</TD>
                    ))}
                    <TD>
                      <Button
                        variant={a.status === 'pending' ? 'primary' : 'outline'}
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          setReviewing(a)
                        }}
                      >
                        {a.status === 'pending' ? 'Review' : 'View'}
                      </Button>
                    </TD>
                  </TR>
                ))}
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

      {reviewing && (
        <AppealReview
          appeal={reviewing}
          canWrite={canWrite}
          onClose={() => setReviewing(null)}
          onReviewed={() => {
            setReviewing(null)
            refetch()
          }}
        />
      )}
    </>
  )
}

function renderCell(a: Appeal, key: string) {
  switch (key) {
    case 'ref':
      return (
        <span className={severityRail(a.case.severity) + ' inline-flex items-center'}>
          <span className="mono-id text-xs font-medium">{aplRef(a.ref)}</span>
        </span>
      )
    case 'member':
      return (
        <div className="flex items-center gap-3">
          <Avatar name={a.member.displayName} color={a.member.avatarColor} size="sm" />
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{a.member.displayName}</p>
            <p className="truncate text-xs text-muted">@{a.member.username}</p>
          </div>
        </div>
      )
    case 'caseRef':
      return (
        <div className="min-w-0">
          <span className="mono-id text-xs text-muted">{caseRefLabel(a.case.ref)}</span>
          <p className="truncate text-xs text-muted-2">{a.case.type}</p>
        </div>
      )
    case 'status':
      return (
        <Badge tone={statusTone(a.status)} dot>
          {a.status}
        </Badge>
      )
    case 'submittedAt':
      return <span className="text-muted">{format(new Date(a.submittedAt), 'MMM d, yyyy')}</span>
    default:
      return null
  }
}

function AppealReview({
  appeal,
  canWrite,
  onClose,
  onReviewed,
}: {
  appeal: Appeal
  canWrite: boolean
  onClose: () => void
  onReviewed: () => void
}) {
  const toast = useToast()
  const [decision, setDecision] = useState('')
  const [busy, setBusy] = useState<'approved' | 'denied' | null>(null)

  const isPending = appeal.status === 'pending'
  const canReview = isPending && canWrite

  async function submit(status: 'approved' | 'denied') {
    setBusy(status)
    try {
      const res = await fetch(`/api/appeals/${appeal.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, decision: decision || null }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        if (res.status === 409) {
          toast.error('This appeal has already been reviewed')
        } else {
          toast.error(body.error ?? 'Could not save decision')
        }
        return
      }
      toast.success(status === 'approved' ? 'Appeal approved' : 'Appeal denied')
      onReviewed()
    } catch {
      toast.error('Network error')
    } finally {
      setBusy(null)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Appeal ${aplRef(appeal.ref)}`}
      size="lg"
      footer={
        canReview ? (
          <>
            <Button variant="outline" onClick={() => submit('denied')} loading={busy === 'denied'} disabled={!!busy}>
              Deny
            </Button>
            <Button onClick={() => submit('approved')} loading={busy === 'approved'} disabled={!!busy}>
              Approve appeal
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        )
      }
    >
      <div className="space-y-4">
        {/* Member */}
        <div className="flex items-center gap-3">
          <Avatar name={appeal.member.displayName} color={appeal.member.avatarColor} size="md" />
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{appeal.member.displayName}</p>
            <p className="mono-id truncate text-xs text-muted">{appeal.member.discordId}</p>
          </div>
        </div>

        {/* Linked case */}
        <div className="rounded-lg border border-border p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="mono-id text-xs font-medium text-muted">{caseRefLabel(appeal.case.ref)}</span>
            <Badge tone={statusTone(appeal.case.type)}>{appeal.case.type}</Badge>
            <TickMeter severity={appeal.case.severity} />
            <Badge tone={severityTone(appeal.case.severity)}>{appeal.case.severity}</Badge>
          </div>
          <p className="mt-2 text-sm text-muted">{appeal.case.reason}</p>
        </div>

        {/* Member's appeal message */}
        <div>
          <p className="mb-1.5 text-sm font-medium text-foreground">Appeal message</p>
          <div className="rounded-lg border border-border bg-surface-2 p-3 text-sm">{appeal.message}</div>
        </div>

        {canReview ? (
          <Field label="Decision note (optional)">
            <Textarea
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              placeholder="Add context for this decision…"
            />
          </Field>
        ) : (
          !isPending && (
            <div className="space-y-3 rounded-lg border border-border p-3">
              <div className="flex items-center gap-2">
                <Badge tone={statusTone(appeal.status)} dot>
                  {appeal.status}
                </Badge>
                {appeal.reviewedBy && (
                  <span className="text-sm text-muted">
                    by {appeal.reviewedBy}
                    {appeal.reviewedAt && ` · ${format(new Date(appeal.reviewedAt), 'MMM d, yyyy')}`}
                  </span>
                )}
              </div>
              {appeal.decision && <p className="text-sm text-muted">{appeal.decision}</p>}
            </div>
          )
        )}
      </div>
    </Modal>
  )
}
