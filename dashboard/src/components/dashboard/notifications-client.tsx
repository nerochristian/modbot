'use client'

import { useState } from 'react'
import { PageHeader } from '@/components/dashboard/page-header'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { SegmentedControl } from '@/components/ui/segmented'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { useApi } from '@/lib/use-api'
import { useToast } from '@/components/ui/toast'
import { cn } from '@/lib/utils'
import {
  Bell,
  CheckCheck,
  CreditCard,
  ShieldAlert,
  Info,
  FileText,
  AtSign,
  Trash2,
  Circle,
} from 'lucide-react'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'

type Notification = {
  id: string
  type: string
  level: string
  title: string
  body: string
  read: boolean
  href: string | null
  createdAt: string
}
type Payload = { items: Notification[]; unread: number }

const TYPE_ICON: Record<string, typeof Bell> = {
  billing: CreditCard,
  security: ShieldAlert,
  system: Info,
  report: FileText,
  mention: AtSign,
}
const LEVEL_COLOR: Record<string, string> = {
  info: 'text-info bg-info-soft',
  success: 'text-success bg-success-soft',
  warning: 'text-warning bg-warning-soft',
  error: 'text-danger bg-danger-soft',
}

export function NotificationsClient() {
  const toast = useToast()
  const { data, loading, error, refetch } = useApi<Payload>('/api/notifications?limit=50')
  const [tab, setTab] = useState<'all' | 'unread'>('all')

  const items = data?.items ?? []
  const filtered = tab === 'unread' ? items.filter((n) => !n.read) : items

  async function markAll() {
    await fetch('/api/notifications', { method: 'PATCH' }).catch(() => undefined)
    toast.success('All caught up')
    refetch()
  }
  async function toggleRead(n: Notification) {
    await fetch(`/api/notifications/${n.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ read: !n.read }),
    }).catch(() => undefined)
    refetch()
  }
  async function remove(id: string) {
    await fetch(`/api/notifications/${id}`, { method: 'DELETE' }).catch(() => undefined)
    refetch()
  }

  return (
    <>
      <PageHeader
        eyebrow="Inbox"
        title="Notifications"
        description={data ? `${data.unread} unread` : 'Stay on top of what matters.'}
        actions={
          <>
            <SegmentedControl
              size="sm"
              aria-label="Filter"
              value={tab}
              onChange={setTab}
              options={[
                { label: 'All', value: 'all' },
                { label: 'Unread', value: 'unread' },
              ]}
            />
            <Button variant="outline" size="sm" onClick={markAll} disabled={!data?.unread}>
              <CheckCheck className="size-4" />
              Mark all read
            </Button>
          </>
        }
      />

      <Card>
        {error && !data ? (
          <ErrorState onRetry={refetch} description={error} />
        ) : loading && !data ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={Bell} title="You're all caught up" description="No notifications to show." />
        ) : (
          <ul className="divide-y divide-border">
            {filtered.map((n) => {
              const Icon = TYPE_ICON[n.type] ?? Info
              return (
                <li
                  key={n.id}
                  className={cn('group flex items-start gap-4 p-4', !n.read && 'bg-accent-soft/30')}
                >
                  <span className={cn('flex size-9 shrink-0 items-center justify-center rounded-xl', LEVEL_COLOR[n.level] ?? LEVEL_COLOR.info)}>
                    <Icon className="size-4.5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-foreground">{n.title}</p>
                      {!n.read && <span className="size-2 rounded-full bg-accent" />}
                    </div>
                    <p className="mt-0.5 text-sm text-muted">{n.body}</p>
                    <div className="mt-1 flex items-center gap-3 text-xs text-muted-2">
                      <span>{formatDistanceToNow(new Date(n.createdAt), { addSuffix: true })}</span>
                      {n.href && (
                        <Link href={n.href} className="font-medium text-accent hover:underline">
                          View
                        </Link>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      onClick={() => toggleRead(n)}
                      title={n.read ? 'Mark as unread' : 'Mark as read'}
                      className="focus-ring rounded-md p-1.5 text-muted-2 hover:text-foreground"
                    >
                      {n.read ? <Circle className="size-4" /> : <CheckCheck className="size-4" />}
                    </button>
                    <button
                      onClick={() => remove(n.id)}
                      title="Delete"
                      className="focus-ring rounded-md p-1.5 text-muted-2 hover:text-danger"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </Card>
    </>
  )
}
