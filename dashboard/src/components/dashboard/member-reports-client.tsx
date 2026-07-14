'use client'

import { useState } from 'react'
import { CheckCircle2, FileWarning, RotateCcw } from 'lucide-react'
import { format } from 'date-fns'
import { PageHeader } from '@/components/dashboard/page-header'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { SearchBox } from '@/components/dashboard/table-toolbar'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { LoadingRows } from '@/components/ui/spinner'
import { useApi } from '@/lib/use-api'
import { useConfigStore } from '@/lib/store'
import { useToast } from '@/components/ui/toast'

type Profile = { id: string; name: string; username: string; avatarUrl: string | null }
type MemberReport = {
  id: string
  reason: string
  resolved: boolean
  resolvedBy: string | null
  createdAt: string
  reporter: Profile
  target: Profile
}
type Payload = { data: MemberReport[] }

export function MemberReportsClient() {
  const canWrite = useConfigStore((state) => state.can('reports.write'))
  const toast = useToast()
  const [status, setStatus] = useState<'open' | 'resolved' | 'all'>('open')
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const params = new URLSearchParams({ status, q: query })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/member-reports?${params}`)

  async function setResolved(report: MemberReport, resolved: boolean) {
    setBusy(report.id)
    try {
      const response = await fetch(`/api/member-reports/${report.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved }),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.error || 'Could not update report')
      toast.success(resolved ? 'Report resolved' : 'Report reopened')
      refetch()
    } catch (reason) {
      toast.error('Report was not updated', reason instanceof Error ? reason.message : 'Try again.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Member safety"
        title="Reports"
        description="Private reports filed with /report. Review the member, evidence, and outcome here."
      />
      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center">
          <SearchBox value={query} onChange={setQuery} placeholder="Search report, member ID, or reason…" />
          <div className="flex gap-1 rounded-lg border border-border bg-surface-2 p-1">
            {(['open', 'resolved', 'all'] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatus(value)}
                className={`focus-ring rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors ${status === value ? 'bg-accent text-accent-foreground' : 'text-muted hover:text-foreground'}`}
              >
                {value === 'open' ? 'Needs review' : value}
              </button>
            ))}
          </div>
        </div>
        {error && !data ? <ErrorState description={error} onRetry={refetch} /> : null}
        {loading && !data ? <LoadingRows rows={5} cols={1} /> : null}
        {data?.data.length === 0 ? (
          <EmptyState icon={FileWarning} title="No matching reports" description="New /report submissions will appear here." />
        ) : null}
        {data?.data.length ? (
          <ul className="divide-y divide-border">
            {data.data.map((report) => (
              <li key={report.id} className="relative grid gap-4 p-5 transition-colors hover:bg-surface-2/50 lg:grid-cols-[minmax(15rem,0.7fr)_minmax(0,1.3fr)_auto] lg:items-center">
                <div className="flex items-center gap-3">
                  <Avatar name={report.target.name} src={report.target.avatarUrl} size="md" />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate font-medium text-foreground">{report.target.name}</p>
                      <Badge tone={report.resolved ? 'mint' : 'warning'} dot>{report.resolved ? 'Resolved' : 'Needs review'}</Badge>
                    </div>
                    <p className="mt-0.5 truncate font-mono text-[0.6875rem] text-muted">Report #{report.id} · {report.target.id}</p>
                  </div>
                </div>
                <div className="min-w-0 border-l-2 border-accent-line pl-4">
                  <p className="whitespace-pre-wrap text-sm leading-6 text-foreground">{report.reason}</p>
                  <p className="mt-2 text-xs text-muted">
                    Filed by {report.reporter.name} · {format(new Date(report.createdAt), 'MMM d, yyyy · h:mm a')}
                  </p>
                </div>
                {canWrite ? (
                  <Button
                    size="sm"
                    variant={report.resolved ? 'outline' : 'primary'}
                    loading={busy === report.id}
                    onClick={() => void setResolved(report, !report.resolved)}
                  >
                    {report.resolved ? <RotateCcw className="size-4" /> : <CheckCircle2 className="size-4" />}
                    {report.resolved ? 'Reopen' : 'Resolve'}
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
      </Card>
    </>
  )
}
