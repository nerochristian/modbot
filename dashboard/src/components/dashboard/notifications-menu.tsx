'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { Bell, CheckCheck, CreditCard, ShieldAlert, Info, FileText, AtSign } from 'lucide-react'
import { Dropdown, DropdownTrigger, DropdownMenu } from '@/components/ui/dropdown'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState } from '@/components/ui/empty-state'
import { cn } from '@/lib/utils'

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

export function NotificationsMenu() {
  const [items, setItems] = useState<Notification[] | null>(null)
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const res = await fetch('/api/notifications?limit=8')
      const data = await res.json()
      setItems(data.items)
      setUnread(data.unread)
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function markAll() {
    setItems((prev) => prev?.map((n) => ({ ...n, read: true })) ?? null)
    setUnread(0)
    await fetch('/api/notifications', { method: 'PATCH' }).catch(() => undefined)
  }

  return (
    <Dropdown>
      <DropdownTrigger>
        <span className="focus-ring relative inline-flex size-9 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface-2 hover:text-foreground">
          <Bell className="size-4.5" />
          {unread > 0 && (
            <span className="absolute right-1.5 top-1.5 flex min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </span>
      </DropdownTrigger>
      <DropdownMenu className="w-[22rem] p-0">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <p className="text-sm font-semibold text-foreground">Notifications</p>
          {unread > 0 && (
            <button
              onClick={markAll}
              className="focus-ring inline-flex items-center gap-1 rounded-md text-xs font-medium text-accent hover:underline"
            >
              <CheckCheck className="size-3.5" />
              Mark all read
            </button>
          )}
        </div>

        <div className="max-h-96 overflow-y-auto">
          {loading && !items ? (
            <div className="flex justify-center py-10">
              <Spinner />
            </div>
          ) : items && items.length > 0 ? (
            <ul className="divide-y divide-border">
              {items.map((n) => {
                const Icon = TYPE_ICON[n.type] ?? Info
                return (
                  <li key={n.id}>
                    <Link
                      href={n.href ?? '/dashboard/notifications'}
                      className={cn(
                        'flex gap-3 px-4 py-3 transition-colors hover:bg-surface-2',
                        !n.read && 'bg-accent-soft/40',
                      )}
                    >
                      <span
                        className={cn(
                          'flex size-8 shrink-0 items-center justify-center rounded-lg',
                          LEVEL_COLOR[n.level] ?? LEVEL_COLOR.info,
                        )}
                      >
                        <Icon className="size-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-foreground">{n.title}</p>
                        <p className="line-clamp-2 text-xs text-muted">{n.body}</p>
                        <p className="mt-0.5 text-[11px] text-muted-2">
                          {formatDistanceToNow(new Date(n.createdAt), { addSuffix: true })}
                        </p>
                      </div>
                      {!n.read && <span className="mt-1 size-2 shrink-0 rounded-full bg-accent" />}
                    </Link>
                  </li>
                )
              })}
            </ul>
          ) : (
            <EmptyState icon={Bell} title="You're all caught up" description="No notifications right now." />
          )}
        </div>

        <div className="border-t border-border p-2">
          <Link
            href="/dashboard/notifications"
            className="focus-ring block rounded-lg px-3 py-2 text-center text-sm font-medium text-accent hover:bg-surface-2"
          >
            View all notifications
          </Link>
        </div>
      </DropdownMenu>
    </Dropdown>
  )
}
