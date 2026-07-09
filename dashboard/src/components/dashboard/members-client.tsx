'use client'

import { useState } from 'react'
import { Plus, Download, MoreHorizontal, Pencil, Trash2, Gavel, Users2, ShieldAlert } from 'lucide-react'
import Link from 'next/link'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, SortableTH, ColumnsMenu } from '@/components/dashboard/table-toolbar'
import { SavedViews } from '@/components/dashboard/saved-views'
import { Card } from '@/components/ui/card'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge, statusTone, severityTone } from '@/components/ui/badge'
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
import { formatNumber } from '@/lib/utils'
import { format } from 'date-fns'

type Member = {
  id: string
  username: string
  displayName: string
  discordId: string
  standing: string
  riskLevel: string
  warnings: number
  messages: number
  note: string | null
  avatarColor: string
  joinedAt: string
  lastActiveAt: string
}
type Payload = {
  data: Member[]
  page: number
  pageSize: number
  total: number
  totalPages: number
  flagged: number
}

const ALL_COLUMNS = [
  { key: 'name', label: 'Member' },
  { key: 'discordId', label: 'Discord ID' },
  { key: 'standing', label: 'Standing' },
  { key: 'riskLevel', label: 'Risk' },
  { key: 'warnings', label: 'Warns' },
  { key: 'messages', label: 'Messages' },
  { key: 'joinedAt', label: 'Joined' },
  { key: 'lastActiveAt', label: 'Last seen' },
]
const SORTABLE = new Set(['warnings', 'messages', 'joinedAt', 'lastActiveAt', 'standing', 'riskLevel'])

const STANDING_OPTIONS = [
  { label: 'All standings', value: '' },
  { label: 'Good standing', value: 'good' },
  { label: 'Watchlist', value: 'watchlist' },
  { label: 'Muted', value: 'muted' },
  { label: 'Banned', value: 'banned' },
  { label: 'Left server', value: 'left' },
]
const RISK_OPTIONS = [
  { label: 'All risk levels', value: '' },
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
  { label: 'Critical', value: 'critical' },
]

const STANDING_LABELS: Record<string, string> = {
  good: 'Good standing',
  watchlist: 'Watchlist',
  muted: 'Muted',
  banned: 'Banned',
  left: 'Left',
}

export function MembersClient() {
  const toast = useToast()
  const canWrite = useConfigStore((s) => s.can('members.write'))
  const canCase = useConfigStore((s) => s.can('cases.write'))
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const visibleCols = useConfigStore((s) => s.config.tableColumns.members ?? ALL_COLUMNS.map((c) => c.key))
  const setTableColumns = useConfigStore((s) => s.setTableColumns)

  const list = useListParams({ sort: 'joinedAt', order: 'desc' })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/members?${list.queryString}`)

  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Member | null>(null)
  const [deleting, setDeleting] = useState<Member | null>(null)
  const [delBusy, setDelBusy] = useState(false)

  const columns = ALL_COLUMNS.filter((c) => visibleCols.includes(c.key))

  async function handleDelete() {
    if (!deleting) return
    setDelBusy(true)
    try {
      const res = await fetch(`/api/members/${deleting.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      toast.success('Member removed')
      setDeleting(null)
      refetch()
    } catch {
      toast.error('Failed to remove member')
    } finally {
      setDelBusy(false)
    }
  }

  function handleExport() {
    if (!data) return
    exportRecords(
      data.data.map((m) => ({
        username: m.username,
        displayName: m.displayName,
        discordId: m.discordId,
        standing: m.standing,
        riskLevel: m.riskLevel,
        warnings: m.warnings,
        messages: m.messages,
      })),
      exportFormat,
      'members',
    )
  }

  return (
    <>
      <PageHeader
        title="Members"
        description={
          data
            ? `${formatNumber(data.total)} members · ${formatNumber(data.flagged)} flagged`
            : 'The people in your community.'
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
                Add member
              </Button>
            )}
          </>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search members or Discord ID…" />
          <div className="flex flex-wrap items-center gap-2">
            <Select
              className="h-9 w-auto"
              options={STANDING_OPTIONS}
              value={list.params.filters.standing ?? ''}
              onChange={(e) => list.setFilter('standing', e.target.value)}
            />
            <Select
              className="h-9 w-auto"
              options={RISK_OPTIONS}
              value={list.params.filters.riskLevel ?? ''}
              onChange={(e) => list.setFilter('riskLevel', e.target.value)}
            />
            <div className="ml-auto flex items-center gap-2">
              <SavedViews
                page="members"
                currentState={list.params as unknown as Record<string, unknown>}
                onApply={(state) => list.setState(state as Partial<ListParams>)}
              />
              <ColumnsMenu
                columns={ALL_COLUMNS}
                visible={visibleCols}
                onChange={(cols) => setTableColumns('members', cols)}
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
                  {columns.map((c) =>
                    SORTABLE.has(c.key) ? (
                      <SortableTH
                        key={c.key}
                        column={c.key}
                        label={c.label}
                        sort={list.params.sort}
                        order={list.params.order}
                        onToggle={list.toggleSort}
                        className={c.key === 'warnings' || c.key === 'messages' ? 'text-right' : undefined}
                      />
                    ) : (
                      <TH key={c.key}>{c.label}</TH>
                    ),
                  )}
                  <TH className="w-10" />
                </TR>
              </THead>
              <TBody>
                {data.data.map((m) => (
                  <TR key={m.id} className="hover:bg-surface-2/50">
                    {columns.map((col) => (
                      <TD
                        key={col.key}
                        className={col.key === 'warnings' || col.key === 'messages' ? 'text-right' : undefined}
                      >
                        {renderCell(m, col.key)}
                      </TD>
                    ))}
                    <TD>
                      <Dropdown>
                        <DropdownTrigger>
                          <span className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-muted hover:bg-surface-2">
                            <MoreHorizontal className="size-4" />
                          </span>
                        </DropdownTrigger>
                        <DropdownMenu>
                          {canCase && (
                            <DropdownItem icon={Gavel} asChild>
                              <Link href={`/dashboard/cases?member=${m.id}&new=1`}>Open case</Link>
                            </DropdownItem>
                          )}
                          {canWrite && (
                            <DropdownItem icon={Pencil} onClick={() => setEditing(m)}>
                              Edit
                            </DropdownItem>
                          )}
                          {canWrite && (
                            <DropdownItem icon={Trash2} destructive onClick={() => setDeleting(m)}>
                              Remove
                            </DropdownItem>
                          )}
                        </DropdownMenu>
                      </Dropdown>
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

      {(creating || editing) && (
        <MemberForm
          member={editing}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
          onSaved={() => {
            setCreating(false)
            setEditing(null)
            refetch()
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={handleDelete}
        title="Remove member"
        description={`Remove ${deleting?.displayName} from the member index? Their case history will be deleted. This cannot be undone.`}
        confirmLabel="Remove"
        destructive
        loading={delBusy}
      />
    </>
  )
}

function renderCell(m: Member, key: string) {
  switch (key) {
    case 'name':
      return (
        <div className="flex items-center gap-3">
          <Avatar name={m.displayName} color={m.avatarColor} size="sm" />
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{m.displayName}</p>
            <p className="truncate text-xs text-muted">@{m.username}</p>
          </div>
        </div>
      )
    case 'discordId':
      return <span className="mono-id text-xs text-muted">{m.discordId}</span>
    case 'standing':
      return (
        <Badge tone={statusTone(m.standing)} dot>
          {STANDING_LABELS[m.standing] ?? m.standing}
        </Badge>
      )
    case 'riskLevel':
      return (
        <span className={`spine spine-${m.riskLevel} inline-flex pl-2.5`}>
          <Badge tone={severityTone(m.riskLevel)}>{m.riskLevel}</Badge>
        </span>
      )
    case 'warnings':
      return <span className="font-medium tabular-nums">{m.warnings}</span>
    case 'messages':
      return <span className="tabular-nums text-muted">{formatNumber(m.messages)}</span>
    case 'joinedAt':
      return <span className="text-muted">{format(new Date(m.joinedAt), 'MMM d, yyyy')}</span>
    case 'lastActiveAt':
      return <span className="text-muted">{format(new Date(m.lastActiveAt), 'MMM d, yyyy')}</span>
    default:
      return null
  }
}

function MemberForm({
  member,
  onClose,
  onSaved,
}: {
  member: Member | null
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({
    username: member?.username ?? '',
    displayName: member?.displayName ?? '',
    discordId: member?.discordId ?? '',
    standing: member?.standing ?? 'good',
    riskLevel: member?.riskLevel ?? 'low',
    note: member?.note ?? '',
  })

  async function submit() {
    setBusy(true)
    setErrors({})
    try {
      const payload = { ...form, note: form.note || null }
      const res = await fetch(member ? `/api/members/${member.id}` : '/api/members', {
        method: member ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (body.issues) {
          const fe: Record<string, string> = {}
          for (const i of body.issues) fe[i.path[0]] = i.message
          setErrors(fe)
        } else {
          setErrors({ form: body.error === 'duplicate' ? 'A member with that Discord ID already exists' : body.error ?? 'Could not save member' })
        }
        return
      }
      toast.success(member ? 'Member updated' : 'Member added')
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
      title={member ? 'Edit member' : 'Add member'}
      icon={ShieldAlert}
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            {member ? 'Save changes' : 'Add member'}
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
        <div className="grid grid-cols-2 gap-4">
          <Field label="Username" error={errors.username}>
            <Input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="shadowfox" />
          </Field>
          <Field label="Display name" error={errors.displayName}>
            <Input value={form.displayName} onChange={(e) => setForm({ ...form, displayName: e.target.value })} placeholder="Shadow" />
          </Field>
        </div>
        <Field label="Discord ID" error={errors.discordId}>
          <Input
            className="font-mono"
            value={form.discordId}
            onChange={(e) => setForm({ ...form, discordId: e.target.value.replace(/\D/g, '') })}
            placeholder="112233445566778899"
            disabled={!!member}
          />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Standing">
            <Select
              options={STANDING_OPTIONS.slice(1)}
              value={form.standing}
              onChange={(e) => setForm({ ...form, standing: e.target.value })}
            />
          </Field>
          <Field label="Risk level">
            <Select
              options={RISK_OPTIONS.slice(1)}
              value={form.riskLevel}
              onChange={(e) => setForm({ ...form, riskLevel: e.target.value })}
            />
          </Field>
        </div>
        <Field label="Moderator note" error={errors.note}>
          <Input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="Optional context for the team" />
        </Field>
      </div>
    </Modal>
  )
}
