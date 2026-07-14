'use client'

import { useRef, useState } from 'react'
import { Plus, Download, MoreHorizontal, CheckCircle2, RotateCcw, Archive, Gavel } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, SortableTH, ColumnsMenu } from '@/components/dashboard/table-toolbar'
import { SavedViews } from '@/components/dashboard/saved-views'
import { Card } from '@/components/ui/card'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge, statusTone, severityTone, severityRail, TickMeter } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { Select } from '@/components/ui/select'
import { Field, Input } from '@/components/ui/input'
import { Modal, ConfirmDialog } from '@/components/ui/modal'
import { Pagination } from '@/components/ui/pagination'
import { LoadingRows } from '@/components/ui/spinner'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { Dropdown, DropdownTrigger, DropdownMenu, DropdownItem } from '@/components/ui/dropdown'
import { useToast } from '@/components/ui/toast'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { useListParams, type ListParams } from '@/lib/use-list-params'
import { exportRecords } from '@/lib/export-client'
import { createClientId } from '@/lib/client-id'
import { formatNumber } from '@/lib/utils'
import { useSearchParams } from 'next/navigation'
import { format } from 'date-fns'

type CaseMember = {
  id: string
  username: string
  displayName: string
  discordId: string
  avatarColor: string
}
type Case = {
  id: string
  ref: number
  memberId: string
  type: string
  severity: string
  status: string
  reason: string
  moderator: string
  channel: string | null
  expiresAt: string | null
  createdAt: string
  member: CaseMember
}
type Payload = {
  data: Case[]
  page: number
  pageSize: number
  total: number
  totalPages: number
  open: number
}

const ALL_COLUMNS = [
  { key: 'ref', label: 'Case' },
  { key: 'member', label: 'Member' },
  { key: 'type', label: 'Action' },
  { key: 'severity', label: 'Severity' },
  { key: 'status', label: 'Status' },
  { key: 'reason', label: 'Reason' },
  { key: 'moderator', label: 'Moderator' },
  { key: 'createdAt', label: 'Date' },
]
const SORTABLE = new Set(['ref', 'type', 'severity', 'status', 'createdAt'])

const TYPE_OPTIONS = [
  { label: 'All actions', value: '' },
  { label: 'Note', value: 'note' },
  { label: 'Warn', value: 'warn' },
  { label: 'Mute', value: 'mute' },
  { label: 'Timeout', value: 'timeout' },
  { label: 'Kick', value: 'kick' },
  { label: 'Ban', value: 'ban' },
  { label: 'Unban', value: 'unban' },
]
const SEVERITY_OPTIONS = [
  { label: 'All severities', value: '' },
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
  { label: 'Critical', value: 'critical' },
]
const STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Open', value: 'open' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Expired', value: 'expired' },
  { label: 'Appealed', value: 'appealed' },
]

const TYPE_TONE: Record<string, 'neutral' | 'info' | 'warning' | 'danger' | 'mint'> = {
  note: 'neutral',
  warn: 'info',
  mute: 'warning',
  timeout: 'warning',
  kick: 'warning',
  ban: 'danger',
  unban: 'mint',
}

function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export function CasesClient() {
  const toast = useToast()
  const searchParams = useSearchParams()
  const canWrite = useConfigStore((s) => s.can('cases.write'))
  const canDelete = useConfigStore((s) => s.can('cases.delete'))
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const visibleCols = useConfigStore((s) => s.config.tableColumns.cases ?? ALL_COLUMNS.map((c) => c.key))
  const setTableColumns = useConfigStore((s) => s.setTableColumns)

  const [presetMember] = useState(() => searchParams.get('member') ?? '')
  const [presetAction] = useState(() => {
    const action = searchParams.get('type') ?? ''
    return TYPE_OPTIONS.some((option) => option.value === action) ? action : ''
  })
  const list = useListParams({
    sort: 'createdAt',
    order: 'desc',
    filters: presetMember ? { memberId: presetMember } : {},
  })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/cases?${list.queryString}`)

  const [creating, setCreating] = useState(() => searchParams.get('new') === '1')
  const [deleting, setDeleting] = useState<Case | null>(null)
  const [delBusy, setDelBusy] = useState(false)

  const columns = ALL_COLUMNS.filter((c) => visibleCols.includes(c.key))

  async function patchStatus(c: Case, status: string) {
    try {
      const res = await fetch(`/api/cases/${c.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      if (!res.ok) throw new Error()
      toast.success(status === 'resolved' ? 'Case resolved' : 'Case reopened')
      refetch()
    } catch {
      toast.error('Failed to update case')
    }
  }

  async function handleDelete() {
    if (!deleting) return
    setDelBusy(true)
    try {
      const res = await fetch(`/api/cases/${deleting.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      toast.success('Case archived')
      setDeleting(null)
      refetch()
    } catch {
      toast.error('Failed to archive case')
    } finally {
      setDelBusy(false)
    }
  }

  function handleExport() {
    if (!data) return
    exportRecords(
      data.data.map((c) => ({
        ref: `#CASE-${String(c.ref).padStart(4, '0')}`,
        member: c.member.displayName,
        type: c.type,
        severity: c.severity,
        status: c.status,
        reason: c.reason,
        moderator: c.moderator,
      })),
      exportFormat,
      'cases',
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="Caseload"
        title="Cases"
        description={
          data
            ? `${formatNumber(data.total)} cases · ${formatNumber(data.open)} open`
            : 'Infractions and moderation actions.'
        }
        actions={
          <>
            <Button variant="outline" size="sm" onClick={handleExport} disabled={!data?.data.length}>
              <Download className="size-4" />
              Export
            </Button>
            {canWrite && (
              <Button size="sm" onClick={() => setCreating(true)}>
                <Plus className="size-4" />
                New case
              </Button>
            )}
          </>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search cases or #ref…" />
          <div className="flex flex-wrap items-center gap-2">
            <Select
              className="h-9 w-auto"
              options={TYPE_OPTIONS}
              value={list.params.filters.type ?? ''}
              onChange={(e) => list.setFilter('type', e.target.value)}
            />
            <Select
              className="h-9 w-auto"
              options={SEVERITY_OPTIONS}
              value={list.params.filters.severity ?? ''}
              onChange={(e) => list.setFilter('severity', e.target.value)}
            />
            <Select
              className="h-9 w-auto"
              options={STATUS_OPTIONS}
              value={list.params.filters.status ?? ''}
              onChange={(e) => list.setFilter('status', e.target.value)}
            />
            <div className="ml-auto flex items-center gap-2">
              <SavedViews
                page="cases"
                currentState={list.params as unknown as Record<string, unknown>}
                onApply={(state) => list.setState(state as Partial<ListParams>)}
              />
              <ColumnsMenu
                columns={ALL_COLUMNS}
                visible={visibleCols}
                onChange={(cols) => setTableColumns('cases', cols)}
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
            icon={Gavel}
            title="No cases found"
            description={
              list.activeFilterCount > 0
                ? 'Try adjusting your search or filters.'
                : 'Cases will appear here as moderation actions are logged.'
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
                  <TH className="w-10" />
                </TR>
              </THead>
              <TBody>
                {data.data.map((c) => (
                  <TR key={c.id} className="hover:bg-surface-2/50">
                    {columns.map((col) => (
                      <TD key={col.key}>{renderCell(c, col.key)}</TD>
                    ))}
                    <TD>
                      {canWrite || canDelete ? (
                        <Dropdown>
                          <DropdownTrigger>
                            <span className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-muted hover:bg-surface-2">
                              <MoreHorizontal className="size-4" />
                            </span>
                          </DropdownTrigger>
                          <DropdownMenu>
                            {canWrite && c.status !== 'resolved' && (
                              <DropdownItem icon={CheckCircle2} onClick={() => patchStatus(c, 'resolved')}>
                                Mark resolved
                              </DropdownItem>
                            )}
                            {canWrite && c.status !== 'open' && (
                              <DropdownItem icon={RotateCcw} onClick={() => patchStatus(c, 'open')}>
                                Reopen
                              </DropdownItem>
                            )}
                            {canDelete && (
                              <DropdownItem icon={Archive} onClick={() => setDeleting(c)}>
                                Archive
                              </DropdownItem>
                            )}
                          </DropdownMenu>
                        </Dropdown>
                      ) : null}
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

      {creating && (
        <CaseForm
          presetMember={presetMember}
          presetAction={presetAction}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            refetch()
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={handleDelete}
        title="Archive case"
        description={`Resolve and archive #CASE-${String(deleting?.ref ?? 0).padStart(4, '0')}? Its actions, appeals, and audit history will be preserved.`}
        confirmLabel="Archive"
        loading={delBusy}
      />
    </>
  )
}

function renderCell(c: Case, key: string) {
  switch (key) {
    case 'ref':
      return (
        <span className={severityRail(c.severity) + ' inline-flex items-center'}>
          <span className="mono-id text-xs font-medium">CASE-{String(c.ref).padStart(4, '0')}</span>
        </span>
      )
    case 'member':
      return (
        <div className="flex items-center gap-3">
          <Avatar name={c.member.displayName} color={c.member.avatarColor} size="sm" />
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{c.member.displayName}</p>
            <p className="truncate text-xs text-muted">@{c.member.username}</p>
          </div>
        </div>
      )
    case 'type':
      return <Badge tone={TYPE_TONE[c.type] ?? 'neutral'}>{cap(c.type)}</Badge>
    case 'severity':
      return (
        <span className="inline-flex items-center gap-2">
          <TickMeter severity={c.severity} />
          <Badge tone={severityTone(c.severity)}>{c.severity}</Badge>
        </span>
      )
    case 'status':
      return (
        <Badge tone={statusTone(c.status)} dot>
          {c.status}
        </Badge>
      )
    case 'reason':
      return <span className="block max-w-xs truncate text-muted">{c.reason}</span>
    case 'moderator':
      return <span className="text-muted">{c.moderator}</span>
    case 'createdAt':
      return <span className="text-muted">{format(new Date(c.createdAt), 'MMM d, yyyy')}</span>
    default:
      return null
  }
}

function CaseForm({
  presetMember,
  presetAction,
  onClose,
  onSaved,
}: {
  presetMember: string
  presetAction: string
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const idempotencyKey = useRef(createClientId('case'))
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({
    memberId: presetMember,
    type: presetAction || 'warn',
    severity: presetAction === 'ban'
      ? 'critical'
      : presetAction === 'kick'
        ? 'high'
        : presetAction === 'timeout' || presetAction === 'mute'
          ? 'medium'
          : 'low',
    reason: '',
    channel: '',
    duration: '',
  })

  async function submit() {
    setBusy(true)
    setErrors({})
    try {
      const payload = {
        memberId: form.memberId,
        type: form.type,
        severity: form.severity,
        reason: form.reason,
        channel: form.channel || null,
        durationHours: Number(form.duration) || 0,
      }
      const res = await fetch('/api/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey.current },
        body: JSON.stringify(payload),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (body.issues) {
          const fe: Record<string, string> = {}
          for (const i of body.issues) fe[i.path[0]] = i.message
          setErrors(fe)
        } else {
          setErrors({ form: body.error ?? 'Could not create case' })
        }
        return
      }
      toast.success('Case created')
      onSaved()
    } catch {
      setErrors({ form: 'Network error' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="New case"
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            Create
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {errors.form && (
          <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
            {errors.form}
          </div>
        )}
        <Field label="Discord member ID" error={errors.memberId} hint="Use the banned user's Discord ID when unbanning.">
          <Input
            value={form.memberId}
            onChange={(e) => setForm({ ...form, memberId: e.target.value.trim() })}
            placeholder="123456789012345678"
          />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Action" error={errors.type}>
            <Select
              options={TYPE_OPTIONS.slice(1)}
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
            />
          </Field>
          <Field label="Severity" error={errors.severity}>
            <Select
              options={SEVERITY_OPTIONS.slice(1)}
              value={form.severity}
              onChange={(e) => setForm({ ...form, severity: e.target.value })}
            />
          </Field>
        </div>
        <Field label="Reason" error={errors.reason}>
          <Input
            value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.target.value })}
            placeholder="What happened?"
          />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Channel" error={errors.channel}>
            <Input
              value={form.channel}
              onChange={(e) => setForm({ ...form, channel: e.target.value })}
              placeholder="#general"
            />
          </Field>
          <Field label="Duration (hours, 0 = permanent)" error={errors.durationHours}>
            <Input
              type="number"
              value={form.duration}
              onChange={(e) => setForm({ ...form, duration: e.target.value })}
              placeholder="0"
            />
          </Field>
        </div>
      </div>
    </Modal>
  )
}
