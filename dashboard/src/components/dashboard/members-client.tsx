'use client'

import { useRouter } from 'next/navigation'
import { Download, MoreHorizontal, Gavel, Users2 } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SearchBox, ColumnsMenu } from '@/components/dashboard/table-toolbar'
import { SavedViews } from '@/components/dashboard/saved-views'
import { Card } from '@/components/ui/card'
import { Table, THead, TBody, TR, TH, TD } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge, statusTone, severityTone, TickMeter } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { Pagination } from '@/components/ui/pagination'
import { LoadingRows } from '@/components/ui/spinner'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { Dropdown, DropdownTrigger, DropdownMenu, DropdownItem } from '@/components/ui/dropdown'
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
const STANDING_LABELS: Record<string, string> = {
  good: 'Good standing',
  watchlist: 'Watchlist',
  muted: 'Muted',
  banned: 'Banned',
  left: 'Left',
}

export function MembersClient() {
  const router = useRouter()
  const canCase = useConfigStore((s) => s.can('cases.write'))
  const exportFormat = useConfigStore((s) => s.config.exportFormat)
  const visibleCols = useConfigStore((s) => s.config.tableColumns.members ?? ALL_COLUMNS.map((c) => c.key))
  const setTableColumns = useConfigStore((s) => s.setTableColumns)

  const list = useListParams({ sort: 'discord', order: 'asc' })
  const { data, loading, error, refetch } = useApi<Payload>(`/api/members?${list.queryString}`)

  const columns = ALL_COLUMNS.filter((c) => visibleCols.includes(c.key))

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
        eyebrow="Directory"
        title="Members"
        description={
          data
            ? `${formatNumber(data.total)} members synchronized from Discord`
            : 'A read-only directory synchronized from your Discord server.'
        }
        actions={
          <Button variant="outline" size="sm" onClick={handleExport} disabled={!data?.data.length}>
            <Download className="size-4" />
            Export page
          </Button>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <SearchBox value={list.params.q} onChange={list.setQuery} placeholder="Search members or Discord ID…" />
          <div className="flex flex-wrap items-center gap-2">
            <div className="ml-auto flex items-center gap-2">
              <SavedViews
                page="members"
                currentState={list.params as unknown as Record<string, unknown>}
                onApply={(state) => list.setState({
                  ...(state as Partial<ListParams>),
                  sort: 'discord',
                  order: 'asc',
                  filters: {},
                })}
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
                  {columns.map((c) => (
                    <TH key={c.key} className={c.key === 'warnings' || c.key === 'messages' ? 'text-right' : undefined}>
                      {c.label}
                    </TH>
                  ))}
                  {canCase && <TH className="w-10" />}
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
                    {canCase && <TD>
                      <Dropdown>
                        <DropdownTrigger>
                          <span className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-muted hover:bg-surface-2">
                            <MoreHorizontal className="size-4" />
                          </span>
                        </DropdownTrigger>
                        <DropdownMenu>
                          <DropdownItem
                            icon={Gavel}
                            onClick={() => router.push(`/dashboard/cases?member=${m.id}&new=1`)}
                          >
                            Open case
                          </DropdownItem>
                        </DropdownMenu>
                      </Dropdown>
                    </TD>}
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
        <span className="inline-flex items-center gap-2">
          <TickMeter severity={m.riskLevel} />
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
