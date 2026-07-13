'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Logo } from '@/components/logo'
import { NAV_ITEMS, type NavItem } from '@/lib/nav'
import type { Permission } from '@/lib/rbac'
import { cn } from '@/lib/utils'

const SECTION_LABELS: Record<string, string> = {
  main: 'Moderation',
  account: 'Workspace',
  admin: 'Administration',
}

const SECTIONS = ['main', 'account', 'admin'] as const

const BADGE_STYLES: Record<NonNullable<NavItem['badge']>, string> = {
  NEW: 'bg-success-soft text-success',
  UPDATE: 'bg-info-soft text-info',
  PLUS: 'bg-accent-soft text-accent',
}

function NavBadge({ badge }: { badge: NonNullable<NavItem['badge']> }) {
  return (
    <span
      className={cn(
        'ml-auto rounded-full px-1.5 py-0.5 font-mono text-[0.5625rem] font-bold uppercase tracking-[0.08em]',
        BADGE_STYLES[badge],
      )}
    >
      {badge}
    </span>
  )
}

function NavigationLink({ item }: { item: NavItem }) {
  const pathname = usePathname()
  const Icon = item.icon
  const isActive =
    item.href === '/dashboard'
      ? pathname === item.href
      : pathname.startsWith(item.href)

  return (
    <Link
      href={item.href}
      className={cn(
        'group flex h-9 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-all duration-200',
        isActive
          ? 'bg-accent text-accent-foreground shadow-[0_8px_25px_-8px_var(--accent)]'
          : 'text-muted hover:bg-surface-2 hover:text-foreground',
      )}
    >
      <Icon
        size={16}
        strokeWidth={1.8}
        className={cn(
          'shrink-0 transition-colors',
          isActive ? 'text-accent-foreground' : 'text-muted-2 group-hover:text-foreground',
        )}
      />
      <span className="truncate">{item.label}</span>
      {item.badge && !isActive && <NavBadge badge={item.badge} />}
    </Link>
  )
}

export function Sidebar({ permissions = [] }: { permissions?: readonly Permission[] }) {
  const visible = NAV_ITEMS.filter((i) => permissions.includes(i.permission))

  return (
    <aside className="hidden h-screen w-[250px] shrink-0 flex-col border-r border-border bg-surface lg:flex">
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-border px-5">
        <Link href="/dashboard" aria-label="Dashboard home" className="flex items-center">
          <Logo />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {SECTIONS.map((section) => {
          const items = visible.filter((i) => i.section === section)
          if (!items.length) return null
          return (
            <div key={section}>
              <p className="mb-2 px-3 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-muted-2">
                {SECTION_LABELS[section]}
              </p>
              <div className="space-y-1">
                {items.map((item) => (
                  <NavigationLink key={item.href} item={item} />
                ))}
              </div>
            </div>
          )
        })}
      </nav>

      {/* Footer signal — live/online marker echoing Nova's green pip */}
      <div className="flex h-12 items-center gap-2 border-t border-border px-5">
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-60" />
          <span className="relative inline-flex size-2 rounded-full bg-success" />
        </span>
        <span className="text-xs font-medium text-muted">All systems online</span>
      </div>
    </aside>
  )
}

export default Sidebar
