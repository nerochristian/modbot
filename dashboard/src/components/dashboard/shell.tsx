'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { Logo } from '@/components/logo'
import { Topbar } from './topbar'
import { Sidebar } from './sidebar'
import { NAV_ITEMS } from '@/lib/nav'
import type { Permission } from '@/lib/rbac'
import { cn } from '@/lib/utils'

const SECTION_LABELS: Record<string, string> = {
  main: 'Workspace',
  account: 'Account',
  admin: 'Administration',
}

function MobileDrawer({
  open,
  onClose,
  permissions,
}: {
  open: boolean
  onClose: () => void
  permissions: Permission[]
}) {
  const pathname = usePathname()
  if (!open || typeof document === 'undefined') return null
  const visible = NAV_ITEMS.filter((i) => permissions.includes(i.permission))
  const sections = ['main', 'account', 'admin'] as const

  return createPortal(
    <div className="fixed inset-0 z-[80] lg:hidden">
      <div className="absolute inset-0" style={{ background: 'var(--overlay)' }} onClick={onClose} />
      <div className="animate-fade-in absolute inset-y-0 left-0 flex w-72 flex-col border-r border-border bg-surface">
        <div className="flex h-16 items-center justify-between border-b border-border px-4">
          <Logo />
          <button
            onClick={onClose}
            className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-muted hover:bg-surface-2"
            aria-label="Close menu"
          >
            <X className="size-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-6 overflow-y-auto p-3">
          {sections.map((section) => {
            const items = visible.filter((i) => i.section === section)
            if (!items.length) return null
            return (
              <div key={section}>
                <p className="mb-1.5 px-2 text-xs font-medium uppercase tracking-wide text-muted-2">
                  {SECTION_LABELS[section]}
                </p>
                <ul className="space-y-0.5">
                  {items.map((item) => {
                    const active =
                      item.href === '/dashboard'
                        ? pathname === item.href
                        : pathname.startsWith(item.href)
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          onClick={onClose}
                          className={cn(
                            'flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium',
                            active
                              ? 'bg-accent-soft text-accent'
                              : 'text-muted hover:bg-surface-2 hover:text-foreground',
                          )}
                        >
                          <item.icon className="size-4.5" />
                          {item.label}
                        </Link>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )
          })}
        </nav>
      </div>
    </div>,
    document.body,
  )
}

export function DashboardShell({
  permissions,
  children,
}: {
  permissions: Permission[]
  children: React.ReactNode
}) {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <div className="flex min-h-full">
      <Sidebar permissions={permissions} />
      <MobileDrawer open={mobileOpen} onClose={() => setMobileOpen(false)} permissions={permissions} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenMobile={() => setMobileOpen(true)} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
