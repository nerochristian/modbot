'use client'

import { useState } from 'react'
import { UserPlus, MoreHorizontal, Pencil, Trash2, UserCog } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, SortableTH } from '@/components/dashboard/table-toolbar'
import { Card } from '@/components/ui/card'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge, statusTone } from '@/components/ui/badge'
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
import { useListParams } from '@/lib/use-list-params'
import { ROLE_LABELS, ROLES, type Role } from '@/lib/rbac'
import { formatDistanceToNow, format } from 'date-fns'

type User = {
  id: string
  name: string
  email: string
  role: string
  status: string
  title: string | null
  avatarColor: string
  createdAt: string
  lastLoginAt: string | null
}
type Payload = { data: User[]; page: number; pageSize: number; total: number; totalPages: number }

const ROLE_OPTIONS = [{ label: 'All roles', value: '' }, ...ROLES.map((r) => ({ label: ROLE_LABELS[r], value: r }))]
const STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Invited', value: 'invited' },
  { label: 'Suspended', value: 'suspended' },
]
const roleTone = (role: string) => (role === 'admin' ? 'accent' : role === 'manager' ? 'info' : 'neutral')

export function UsersClient() {
  const toast = useToast()
  const canWrite = useConfigStore((s) => s.can('users.write'))
  const canDelete = useConfigStore((s) => s.can('users.delete'))
  const selfId = useConfigStore((s) => s.user?.id)

  const list = useListParams({ sort: 'createdAt', order: 'desc' })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/users?${list.queryString}`)

  const [inviting, setInviting] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [deleting, setDeleting] = useState<User | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleDelete() {
    if (!deleting) return
    setBusy(true)
    try {
      const res = await fetch(`/api/users/${deleting.id}`, { method: 'DELETE' })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error)
      toast.success('User removed')
      setDeleting(null)
      refetch()
    } catch (e) {
      toast.error((e as Error).message || 'Failed to remove user')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Users"
        description="Manage your team members, roles, and access."
        actions={
          canWrite && (
            <Button size="sm" onClick={() => setInviting(true)}>
              <UserPlus className="size-4" />
              Invite user
            </Button>
          )
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search users…" />
          <div className="flex flex-wrap items-center gap-2 lg:ml-auto">
            <Select
              className="h-9 w-auto"
              options={ROLE_OPTIONS}
              value={list.params.filters.role ?? ''}
              onChange={(e) => list.setFilter('role', e.target.value)}
            />
            <Select
              className="h-9 w-auto"
              options={STATUS_OPTIONS}
              value={list.params.filters.status ?? ''}
              onChange={(e) => list.setFilter('status', e.target.value)}
            />
          </div>
        </div>

        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <LoadingRows rows={8} cols={5} />
        ) : data && data.data.length === 0 ? (
          <EmptyState
            icon={UserCog}
            title="No users found"
            description={list.activeFilterCount > 0 ? 'Try adjusting your filters.' : 'Invite your first team member.'}
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
                  <SortableTH column="name" label="User" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <SortableTH column="role" label="Role" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <SortableTH column="status" label="Status" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <SortableTH column="lastLoginAt" label="Last active" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  {canWrite && <TH className="w-10" />}
                </TR>
              </THead>
              <TBody>
                {data.data.map((u) => (
                  <TR key={u.id} className="hover:bg-surface-2/50">
                    <TD>
                      <div className="flex items-center gap-3">
                        <Avatar name={u.name} color={u.avatarColor} size="sm" />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-foreground">
                            {u.name}
                            {u.id === selfId && <span className="ml-1.5 text-xs text-muted-2">(you)</span>}
                          </p>
                          <p className="truncate text-xs text-muted">{u.email}</p>
                        </div>
                      </div>
                    </TD>
                    <TD>
                      <Badge tone={roleTone(u.role)}>{ROLE_LABELS[u.role as Role] ?? u.role}</Badge>
                    </TD>
                    <TD>
                      <Badge tone={statusTone(u.status)} dot>
                        {u.status}
                      </Badge>
                    </TD>
                    <TD className="text-muted">
                      {u.lastLoginAt
                        ? formatDistanceToNow(new Date(u.lastLoginAt), { addSuffix: true })
                        : 'Never'}
                    </TD>
                    {canWrite && (
                      <TD>
                        <Dropdown>
                          <DropdownTrigger>
                            <span className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-muted hover:bg-surface-2">
                              <MoreHorizontal className="size-4" />
                            </span>
                          </DropdownTrigger>
                          <DropdownMenu>
                            <DropdownItem icon={Pencil} onClick={() => setEditing(u)}>
                              Edit
                            </DropdownItem>
                            {canDelete && (
                              <DropdownItem
                                icon={Trash2}
                                destructive
                                disabled={u.id === selfId}
                                onClick={() => setDeleting(u)}
                              >
                                Remove
                              </DropdownItem>
                            )}
                          </DropdownMenu>
                        </Dropdown>
                      </TD>
                    )}
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

      {inviting && (
        <InviteForm
          onClose={() => setInviting(false)}
          onSaved={() => {
            setInviting(false)
            refetch()
          }}
        />
      )}
      {editing && (
        <EditUserForm
          user={editing}
          isSelf={editing.id === selfId}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            refetch()
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={handleDelete}
        title="Remove user"
        description={`Remove ${deleting?.name} from your team? They will lose all access immediately.`}
        confirmLabel="Remove"
        destructive
        loading={busy}
      />
    </>
  )
}

function InviteForm({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({ name: '', email: '', role: 'viewer' })

  async function submit() {
    setBusy(true)
    setErrors({})
    try {
      const res = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (body.issues) {
          const fe: Record<string, string> = {}
          for (const i of body.issues) fe[i.path[0]] = i.message
          setErrors(fe)
        } else setErrors({ form: body.error ?? 'Could not invite user' })
        return
      }
      toast.success('Invitation sent')
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
      title="Invite user"
      description="Send an invitation and assign a role."
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            Send invite
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
        <Field label="Full name" error={errors.name}>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Email" error={errors.email}>
          <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Role">
          <Select
            options={ROLES.map((r) => ({ label: ROLE_LABELS[r], value: r }))}
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          />
        </Field>
      </div>
    </Modal>
  )
}

function EditUserForm({
  user,
  isSelf,
  onClose,
  onSaved,
}: {
  user: User
  isSelf: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [form, setForm] = useState({ name: user.name, role: user.role, status: user.status })

  async function submit() {
    setBusy(true)
    setErrorMsg('')
    try {
      const res = await fetch(`/api/users/${user.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        setErrorMsg(body.error ?? 'Could not update user')
        return
      }
      toast.success('User updated')
      onSaved()
    } catch {
      setErrorMsg('Network error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Edit user"
      description={`Member since ${format(new Date(user.createdAt), 'MMM d, yyyy')}`}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            Save changes
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {errorMsg && (
          <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
            {errorMsg}
          </div>
        )}
        <Field label="Name">
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Role" hint={isSelf ? 'You cannot change your own role.' : undefined}>
          <Select
            options={ROLES.map((r) => ({ label: ROLE_LABELS[r], value: r }))}
            value={form.role}
            disabled={isSelf}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          />
        </Field>
        <Field label="Status">
          <Select
            options={STATUS_OPTIONS.slice(1)}
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
          />
        </Field>
      </div>
    </Modal>
  )
}
