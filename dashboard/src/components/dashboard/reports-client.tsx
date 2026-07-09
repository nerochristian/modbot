'use client'

import { useState } from 'react'
import { Plus, MoreHorizontal, Download, Trash2, FileBarChart } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, SortableTH } from '@/components/dashboard/table-toolbar'
import { Card } from '@/components/ui/card'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge, statusTone } from '@/components/ui/badge'
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
import { format } from 'date-fns'

type Report = {
  id: string
  name: string
  type: string
  status: string
  format: string
  createdAt: string
  createdBy: string
}
type Payload = { data: Report[]; page: number; pageSize: number; total: number; totalPages: number }

const TYPE_OPTIONS = [
  { label: 'All types', value: '' },
  { label: 'Mod actions', value: 'actions' },
  { label: 'Members', value: 'members' },
  { label: 'Activity', value: 'activity' },
  { label: 'Automod', value: 'automod' },
  { label: 'Custom', value: 'custom' },
]
const STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Ready', value: 'ready' },
  { label: 'Generating', value: 'generating' },
  { label: 'Scheduled', value: 'scheduled' },
  { label: 'Failed', value: 'failed' },
]
const FORMAT_OPTIONS = [
  { label: 'CSV', value: 'csv' },
  { label: 'JSON', value: 'json' },
  { label: 'PDF', value: 'pdf' },
  { label: 'XLSX', value: 'xlsx' },
]

export function ReportsClient() {
  const toast = useToast()
  const canWrite = useConfigStore((s) => s.can('reports.write'))
  const list = useListParams({ sort: 'createdAt', order: 'desc' })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/reports?${list.queryString}`)

  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<Report | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleDelete() {
    if (!deleting) return
    setBusy(true)
    try {
      const res = await fetch(`/api/reports/${deleting.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      toast.success('Report deleted')
      setDeleting(null)
      refetch()
    } catch {
      toast.error('Failed to delete report')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Reports"
        description="Generate, schedule, and export detailed reports."
        actions={
          canWrite && (
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="size-4" />
              New report
            </Button>
          )
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search reports…" />
          <div className="flex flex-wrap items-center gap-2 lg:ml-auto">
            <Select className="h-9 w-auto" options={TYPE_OPTIONS} value={list.params.filters.type ?? ''} onChange={(e) => list.setFilter('type', e.target.value)} />
            <Select className="h-9 w-auto" options={STATUS_OPTIONS} value={list.params.filters.status ?? ''} onChange={(e) => list.setFilter('status', e.target.value)} />
          </div>
        </div>

        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <LoadingRows rows={8} cols={5} />
        ) : data && data.data.length === 0 ? (
          <EmptyState
            icon={FileBarChart}
            title="No reports yet"
            description={list.activeFilterCount > 0 ? 'Try adjusting your filters.' : 'Create your first report to get started.'}
            action={
              canWrite && list.activeFilterCount === 0 ? (
                <Button size="sm" onClick={() => setCreating(true)}>
                  New report
                </Button>
              ) : undefined
            }
          />
        ) : data ? (
          <>
            <Table>
              <THead>
                <TR>
                  <SortableTH column="name" label="Report" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <SortableTH column="type" label="Type" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <SortableTH column="status" label="Status" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <TH>Format</TH>
                  <TH>Created by</TH>
                  <SortableTH column="createdAt" label="Created" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <TH className="w-10" />
                </TR>
              </THead>
              <TBody>
                {data.data.map((r) => (
                  <TR key={r.id} className="hover:bg-surface-2/50">
                    <TD className="font-medium text-foreground">{r.name}</TD>
                    <TD className="capitalize text-muted">{r.type}</TD>
                    <TD>
                      <Badge tone={statusTone(r.status)} dot>
                        {r.status}
                      </Badge>
                    </TD>
                    <TD className="uppercase text-muted">{r.format}</TD>
                    <TD className="text-muted">{r.createdBy}</TD>
                    <TD className="text-muted">{format(new Date(r.createdAt), 'MMM d, yyyy')}</TD>
                    <TD>
                      <Dropdown>
                        <DropdownTrigger>
                          <span className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-muted hover:bg-surface-2">
                            <MoreHorizontal className="size-4" />
                          </span>
                        </DropdownTrigger>
                        <DropdownMenu>
                          <DropdownItem
                            icon={Download}
                            disabled={r.status !== 'ready'}
                            onClick={() => window.open(`/api/reports/${r.id}/download`, '_blank')}
                          >
                            Download
                          </DropdownItem>
                          {canWrite && (
                            <DropdownItem icon={Trash2} destructive onClick={() => setDeleting(r)}>
                              Delete
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
              <Pagination page={data.page} totalPages={data.totalPages} total={data.total} pageSize={data.pageSize} onPageChange={list.setPage} />
            </div>
          </>
        ) : null}
      </Card>

      {creating && (
        <ReportForm
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
        title="Delete report"
        description={`Delete "${deleting?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        loading={busy}
      />
    </>
  )
}

function ReportForm({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const toast = useToast()
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({ name: '', type: 'actions', format: exportFormat })

  async function submit() {
    setBusy(true)
    setErrors({})
    try {
      const res = await fetch('/api/reports', {
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
        } else setErrors({ form: body.error ?? 'Could not create report' })
        return
      }
      toast.success('Report created')
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
      title="New report"
      description="Generate a report from your live data."
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            Generate report
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {errors.form && (
          <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{errors.form}</div>
        )}
        <Field label="Report name" error={errors.name}>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Weekly Moderation Digest" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Type">
            <Select options={TYPE_OPTIONS.slice(1)} value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} />
          </Field>
          <Field label="Format">
            <Select options={FORMAT_OPTIONS} value={form.format} onChange={(e) => setForm({ ...form, format: e.target.value as typeof form.format })} />
          </Field>
        </div>
      </div>
    </Modal>
  )
}
