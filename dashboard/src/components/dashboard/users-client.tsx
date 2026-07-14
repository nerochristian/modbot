'use client'

import { formatDistanceToNow } from 'date-fns'
import { ShieldCheck } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, SortableTH } from '@/components/dashboard/table-toolbar'
import { Avatar } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { Pagination } from '@/components/ui/pagination'
import { LoadingRows } from '@/components/ui/spinner'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { useApi } from '@/lib/use-api'
import { useListParams } from '@/lib/use-list-params'

type Administrator = {
  id: string
  name: string
  email: string
  role: 'admin'
  status: 'active'
  title: string | null
  avatarColor: string
  avatarUrl: string | null
  createdAt: string
  lastLoginAt: string | null
}

type Payload = {
  data: Administrator[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export function UsersClient() {
  const list = useListParams({ sort: 'createdAt', order: 'desc' })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/users?${list.queryString}`)

  return (
    <>
      <PageHeader
        eyebrow="Discord authority"
        title="Administrators"
        description="People who have signed in with live Discord Administrator permission for this server."
      />

      <Card>
        <div className="border-b border-border p-4">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search administrators…" />
        </div>

        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <LoadingRows rows={8} cols={4} />
        ) : data && data.data.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="No administrators found"
            description={list.params.q ? 'No administrator matches your search.' : 'Administrators appear after signing in with Discord.'}
          />
        ) : data ? (
          <>
            <Table>
              <THead>
                <TR>
                  <SortableTH column="name" label="Administrator" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <TH>Access source</TH>
                  <SortableTH column="lastLoginAt" label="Last active" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                  <SortableTH column="createdAt" label="First verified" sort={list.params.sort} order={list.params.order} onToggle={list.toggleSort} />
                </TR>
              </THead>
              <TBody>
                {data.data.map((administrator) => (
                  <TR key={administrator.id} className="hover:bg-surface-2/50">
                    <TD>
                      <div className="flex items-center gap-3">
                        <Avatar name={administrator.name} color={administrator.avatarColor} src={administrator.avatarUrl} size="sm" />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-foreground">{administrator.name}</p>
                          <p className="truncate text-xs text-muted">{administrator.email}</p>
                        </div>
                      </div>
                    </TD>
                    <TD><Badge tone="accent">Discord Administrator</Badge></TD>
                    <TD className="text-muted">
                      {administrator.lastLoginAt
                        ? formatDistanceToNow(new Date(administrator.lastLoginAt), { addSuffix: true })
                        : 'Never'}
                    </TD>
                    <TD className="text-muted">
                      {formatDistanceToNow(new Date(administrator.createdAt), { addSuffix: true })}
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
    </>
  )
}
