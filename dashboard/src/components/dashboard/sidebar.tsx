'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronsLeft, PanelLeft } from 'lucide-react'
import { Logo } from '@/components/logo'
import { NAV_ITEMS } from '@/lib/nav'
import { useConfigStore } from '@/lib/store'
import type { Permission } from '@/lib/rbac'
import { cn } from '@/lib/utils'

const SECTION_LABELS: Record<string, string> = {
  main: 'Moderation',
  account: 'Workspace',
  admin: 'Administration',
}

export function Sidebar({ permissions }: { permissions: Permission[] }) {
  const pathname = usePathname()
  const collapsed = useConfigStore((s) => s.config.sidebarCollapsed)
  const toggle = useConfigStore((s) => s.toggleSidebar)

  const visible = NAV_ITEMS.filter((item) => permissions.includes(item.permission))
  const sections = ['main', 'account', 'admin'] as const

  function isActive(href: string) {
    return href === '/dashboard' ? pathname === href : pathname.startsWith(href)
  }

  return (
    <aside
      className={cn(
        'sticky top-0 hidden h-screen shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200 lg:flex',
        collapsed ? 'w-[72px]' : 'w-64',
      )}
    >
      <div className={cn('flex h-16 items-center border-b border-border px-4', collapsed && 'justify-center px-0')}>
        <Link href="/dashboard" className="focus-ring rounded-lg">
          <Logo showWordmark={!collapsed} />
        </Link>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {sections.map((section) => {
          const items = visible.filter((i) => i.section === section)
          if (items.length === 0) return null
          return (
            <div key={section}>
              {!collapsed && (
                <p className="mb-1.5 px-2 text-xs font-medium uppercase tracking-wide text-muted-2">
                  {SECTION_LABELS[section]}
                </p>
              )}
              <ul className="space-y-0.5">
                {items.map((item) => {
                  const active = isActive(item.href)
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        title={collapsed ? item.label : undefined}
                        className={cn(
                          'focus-ring group flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors',
                          collapsed && 'justify-center px-0',
                          active
                            ? 'bg-accent-soft text-accent'
                            : 'text-muted hover:bg-surface-2 hover:text-foreground',
                        )}
                      >
                        <item.icon className="size-4.5 shrink-0" />
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          )
        })}
      </nav>

      <button
        onClick={toggle}
        className={cn(
          'focus-ring m-3 flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-foreground',
          collapsed && 'justify-center px-0',
        )}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <PanelLeft className="size-4.5" /> : <ChevronsLeft className="size-4.5" />}
        {!collapsed && <span>Collapse</span>}
      </button>
    </aside>
  )
}
