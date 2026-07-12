'use client'

import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox } from '@/components/dashboard/table-toolbar'
import { Card, CardContent } from '@/components/ui/card'
import { Avatar } from '@/components/ui/avatar'
import { Pagination } from '@/components/ui/pagination'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { useApi } from '@/lib/use-api'
import { useListParams } from '@/lib/use-list-params'
import { Activity } from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'

type Item = {
  id: string
  actorName: string
  action: string
  target: string | null
  createdAt: string
  metadata: Record<string, unknown>
}
type Payload = { data: Item[]; page: number; pageSize: number; total: number; totalPages: number }

function humanAction(action: string) {
  return action.replace(/_/g, ' ')
}

export function ActivityClient() {
  const list = useListParams({ pageSize: 20 })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/activity?${list.queryString}`)

  return (
    <>
      <PageHeader eyebrow="Ledger" title="Activity" description="A chronological log of everything happening across your workspace." />

      <Card>
        <div className="border-b border-border p-4">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search activity…" />
        </div>

        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : data && data.data.length === 0 ? (
          <EmptyState icon={Activity} title="No activity found" description="Nothing matches your search." />
        ) : data ? (
          <>
            <CardContent>
              <ol className="relative space-y-5 before:absolute before:left-[1.05rem] before:top-2 before:h-[calc(100%-1rem)] before:w-px before:bg-border">
                {data.data.map((item) => (
                  <li key={item.id} className="relative flex gap-4">
                    <Avatar name={item.actorName} size="sm" className="z-10 ring-4 ring-card" />
                    <div className="min-w-0 flex-1 pt-1">
                      <p className="text-sm text-foreground">
                        <span className="font-medium">{item.actorName}</span>{' '}
                        <span className="text-muted">{humanAction(item.action)}</span>
                        {item.target && <span className="font-medium"> {item.target}</span>}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-2" title={format(new Date(item.createdAt), 'PPpp')}>
                        {formatDistanceToNow(new Date(item.createdAt), { addSuffix: true })}
                        {typeof item.metadata.ip === 'string' && <span> · {item.metadata.ip}</span>}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
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
