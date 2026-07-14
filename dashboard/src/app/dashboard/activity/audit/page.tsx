'use client'

import { format } from 'date-fns'
import { ScrollText } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { SearchBox } from '@/components/dashboard/table-toolbar'
import { Avatar } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { Pagination } from '@/components/ui/pagination'
import { LoadingRows } from '@/components/ui/spinner'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { useApi } from '@/lib/use-api'
import { useListParams } from '@/lib/use-list-params'

type AuditEntry = {
  id: string
  actorName: string
  action: string
  entity: string
  entityId: string | null
  ip: string | null
  createdAt: string
}

type Payload = { data: AuditEntry[]; page: number; pageSize: number; total: number; totalPages: number }

export default function AuditHistoryPage() {
  const list = useListParams({ pageSize: 15 })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/admin/audit?${list.queryString}`)

  return (
    <>
      <PageHeader
        eyebrow="Ledger"
        title="Audit history"
        description="Sensitive dashboard changes for this server workspace."
      />
      <SettingsCard title="Dashboard changes" description="An immutable record of configuration and access changes.">
        <div className="mb-4">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search audit history…" />
        </div>
        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <LoadingRows rows={8} cols={4} />
        ) : data && data.data.length === 0 ? (
          <EmptyState icon={ScrollText} title="No audit entries" description="Sensitive dashboard changes will appear here." />
        ) : data ? (
          <>
            <Table>
              <THead>
                <TR><TH>Actor</TH><TH>Action</TH><TH>Entity</TH><TH>IP</TH><TH>Time</TH></TR>
              </THead>
              <TBody>
                {data.data.map((entry) => (
                  <TR key={entry.id} className="hover:bg-surface-2/50">
                    <TD>
                      <div className="flex items-center gap-2.5">
                        <Avatar name={entry.actorName} size="xs" />
                        <span className="font-medium text-foreground">{entry.actorName}</span>
                      </div>
                    </TD>
                    <TD><code className="rounded bg-surface-2 px-1.5 py-0.5 text-xs text-foreground">{entry.action}</code></TD>
                    <TD><Badge tone="neutral">{entry.entity}</Badge></TD>
                    <TD className="font-mono text-xs text-muted">{entry.ip ?? '—'}</TD>
                    <TD className="whitespace-nowrap text-muted">{format(new Date(entry.createdAt), 'MMM d, HH:mm')}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
            <div className="border-t border-border">
              <Pagination page={data.page} totalPages={data.totalPages} total={data.total} pageSize={data.pageSize} onPageChange={list.setPage} />
            </div>
          </>
        ) : null}
      </SettingsCard>
    </>
  )
}
