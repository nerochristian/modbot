'use client'

import { useState } from 'react'
import { Plus, Download, MoreHorizontal, Pencil, Trash2, Users2 } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, SortableTH, ColumnsMenu } from '@/components/dashboard/table-toolbar'
import { SavedViews } from '@/components/dashboard/saved-views'
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
import { useListParams, type ListParams } from '@/lib/use-list-params'
import { exportRecords } from '@/lib/export-client'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { format } from 'date-fns'

type Customer = {
  id: string
  name: string
  email: string
  company: string | null
  plan: string
  status: string
  country: string
  mrr: number
  avatarColor: string
  createdAt: string
  lastActiveAt: string
}
type Payload = {
  data: Customer[]
  page: number
  pageSize: number
  total: number
  totalPages: number
  totalMrr: number
}

const ALL_COLUMNS = [
  { key: 'name', label: 'Customer' },
  { key: 'company', label: 'Company' },
  { key: 'plan', label: 'Plan' },
  { key: 'status', label: 'Status' },
  { key: 'mrr', label: 'MRR' },
  { key: 'country', label: 'Country' },
  { key: 'lastActiveAt', label: 'Last active' },
  { key: 'createdAt', label: 'Created' },
]
const SORTABLE = new Set(['name', 'plan', 'status', 'mrr', 'createdAt', 'lastActiveAt'])

const STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Trialing', value: 'trialing' },
  { label: 'Past due', value: 'past_due' },
  { label: 'Churned', value: 'churned' },
]
const PLAN_OPTIONS = [
  { label: 'All plans', value: '' },
  { label: 'Free', value: 'free' },
  { label: 'Starter', value: 'starter' },
  { label: 'Pro', value: 'pro' },
  { label: 'Enterprise', value: 'enterprise' },
]

export function CustomersClient() {
  const toast = useToast()
  const canWrite = useConfigStore((s) => s.can('customers.write'))
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const visibleCols = useConfigStore((s) => s.config.tableColumns.customers ?? ALL_COLUMNS.map((c) => c.key))
  const setTableColumns = useConfigStore((s) => s.setTableColumns)

  const list = useListParams({ sort: 'mrr', order: 'desc' })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/customers?${list.queryString}`)

  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Customer | null>(null)
  const [deleting, setDeleting] = useState<Customer | null>(null)
  const [deletBusy, setDelBusy] = useState(false)

  const columns = ALL_COLUMNS.filter((c) => visibleCols.includes(c.key))

  async function handleDelete() {
    if (!deleting) return
    setDelBusy(true)
    try {
      const res = await fetch(`/api/customers/${deleting.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      toast.success('Customer deleted')
      setDeleting(null)
      refetch()
    } catch {
      toast.error('Failed to delete customer')
    } finally {
      setDelBusy(false)
    }
  }

  function handleExport() {
    if (!data) return
    exportRecords(
      data.data.map((c) => ({
        name: c.name,
        email: c.email,
        company: c.company ?? '',
        plan: c.plan,
        status: c.status,
        country: c.country,
        mrr: (c.mrr / 100).toFixed(2),
      })),
      exportFormat,
      'customers',
    )
  }

  return (
    <>
      <PageHeader
        title="Customers"
        description={
          data
            ? `${formatNumber(data.total)} customers · ${formatCurrency(data.totalMrr)} total MRR`
            : 'Manage your customer accounts.'
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
                Add customer
              </Button>
            )}
          </>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search customers…" />
          <div className="flex flex-wrap items-center gap-2">
            <Select
              className="h-9 w-auto"
              options={STATUS_OPTIONS}
              value={list.params.filters.status ?? ''}
              onChange={(e) => list.setFilter('status', e.target.value)}
            />
            <Select
              className="h-9 w-auto"
              options={PLAN_OPTIONS}
              value={list.params.filters.plan ?? ''}
              onChange={(e) => list.setFilter('plan', e.target.value)}
            />
            <div className="ml-auto flex items-center gap-2">
              <SavedViews
                page="customers"
                currentState={list.params as unknown as Record<string, unknown>}
                onApply={(state) => list.setState(state as Partial<ListParams>)}
              />
              <ColumnsMenu
                columns={ALL_COLUMNS}
                visible={visibleCols}
                onChange={(cols) => setTableColumns('customers', cols)}
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
            title="No customers found"
            description={
              list.activeFilterCount > 0
                ? 'Try adjusting your search or filters.'
                : 'Add your first customer to get started.'
            }
            action={
              list.activeFilterCount > 0 ? (
                <Button variant="outline" size="sm" onClick={list.clearFilters}>
                  Clear filters
                </Button>
              ) : canWrite ? (
                <Button size="sm" onClick={() => setCreating(true)}>
                  Add customer
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
                        className={c.key === 'mrr' ? 'text-right' : undefined}
                      />
                    ) : (
                      <TH key={c.key}>{c.label}</TH>
                    ),
                  )}
                  {canWrite && <TH className="w-10" />}
                </TR>
              </THead>
              <TBody>
                {data.data.map((c) => (
                  <TR key={c.id} className="hover:bg-surface-2/50">
                    {columns.map((col) => (
                      <TD key={col.key} className={col.key === 'mrr' ? 'text-right' : undefined}>
                        {renderCell(c, col.key)}
                      </TD>
                    ))}
                    {canWrite && (
                      <TD>
                        <Dropdown>
                          <DropdownTrigger>
                            <span className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-muted hover:bg-surface-2">
                              <MoreHorizontal className="size-4" />
                            </span>
                          </DropdownTrigger>
                          <DropdownMenu>
                            <DropdownItem icon={Pencil} onClick={() => setEditing(c)}>
                              Edit
                            </DropdownItem>
                            <DropdownItem icon={Trash2} destructive onClick={() => setDeleting(c)}>
                              Delete
                            </DropdownItem>
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

      {(creating || editing) && (
        <CustomerForm
          customer={editing}
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
        title="Delete customer"
        description={`Are you sure you want to delete ${deleting?.name}? This action cannot be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deletBusy}
      />
    </>
  )
}

function renderCell(c: Customer, key: string) {
  switch (key) {
    case 'name':
      return (
        <div className="flex items-center gap-3">
          <Avatar name={c.name} color={c.avatarColor} size="sm" />
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{c.name}</p>
            <p className="truncate text-xs text-muted">{c.email}</p>
          </div>
        </div>
      )
    case 'company':
      return <span className="text-muted">{c.company ?? '—'}</span>
    case 'plan':
      return <Badge tone="accent">{c.plan}</Badge>
    case 'status':
      return (
        <Badge tone={statusTone(c.status)} dot>
          {c.status.replace('_', ' ')}
        </Badge>
      )
    case 'mrr':
      return <span className="font-medium tabular-nums">{formatCurrency(c.mrr)}</span>
    case 'country':
      return <span className="text-muted">{c.country}</span>
    case 'lastActiveAt':
      return <span className="text-muted">{format(new Date(c.lastActiveAt), 'MMM d, yyyy')}</span>
    case 'createdAt':
      return <span className="text-muted">{format(new Date(c.createdAt), 'MMM d, yyyy')}</span>
    default:
      return null
  }
}

function CustomerForm({
  customer,
  onClose,
  onSaved,
}: {
  customer: Customer | null
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({
    name: customer?.name ?? '',
    email: customer?.email ?? '',
    company: customer?.company ?? '',
    plan: customer?.plan ?? 'starter',
    status: customer?.status ?? 'active',
    country: customer?.country ?? 'US',
    mrr: customer ? String(customer.mrr / 100) : '0',
  })

  async function submit() {
    setBusy(true)
    setErrors({})
    try {
      const payload = {
        name: form.name,
        email: form.email,
        company: form.company || null,
        plan: form.plan,
        status: form.status,
        country: form.country,
        mrr: Math.round(Number(form.mrr) * 100) || 0,
      }
      const res = await fetch(customer ? `/api/customers/${customer.id}` : '/api/customers', {
        method: customer ? 'PATCH' : 'POST',
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
          setErrors({ form: body.error ?? 'Could not save customer' })
        }
        return
      }
      toast.success(customer ? 'Customer updated' : 'Customer created')
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
      title={customer ? 'Edit customer' : 'Add customer'}
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            {customer ? 'Save changes' : 'Create customer'}
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
          <Field label="Name" error={errors.name}>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="Email" error={errors.email}>
            <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
        </div>
        <Field label="Company" error={errors.company}>
          <Input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Plan">
            <Select
              options={PLAN_OPTIONS.slice(1)}
              value={form.plan}
              onChange={(e) => setForm({ ...form, plan: e.target.value })}
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
        <div className="grid grid-cols-2 gap-4">
          <Field label="Country (2-letter)" error={errors.country}>
            <Input
              maxLength={2}
              value={form.country}
              onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase() })}
            />
          </Field>
          <Field label="MRR (USD)" error={errors.mrr}>
            <Input
              type="number"
              value={form.mrr}
              onChange={(e) => setForm({ ...form, mrr: e.target.value })}
            />
          </Field>
        </div>
      </div>
    </Modal>
  )
}
