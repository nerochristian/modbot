'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutGrid, ShieldCheck, ToggleRight, Blocks, SlidersHorizontal, ScrollText, Megaphone, Users2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const ITEMS = [
  { label: 'Overview', href: '/dashboard/admin', icon: LayoutGrid, exact: true },
  { label: 'Roles & permissions', href: '/dashboard/admin/roles', icon: ShieldCheck },
  { label: 'Feature flags', href: '/dashboard/admin/features', icon: ToggleRight },
  { label: 'Widgets', href: '/dashboard/admin/widgets', icon: Blocks },
  { label: 'Global settings', href: '/dashboard/admin/settings', icon: SlidersHorizontal },
  { label: 'Audit log', href: '/dashboard/admin/audit', icon: ScrollText },
  { label: 'Broadcast', href: '/dashboard/admin/broadcast', icon: Megaphone },
  { label: 'Users', href: '/dashboard/users', icon: Users2 },
]

export function AdminNav() {
  const pathname = usePathname()
  return (
    <nav className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
      {ITEMS.map((item) => {
        const active = item.exact ? pathname === item.href : pathname.startsWith(item.href)
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'focus-ring flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              active ? 'bg-accent-soft text-accent' : 'text-muted hover:bg-surface-2 hover:text-foreground',
            )}
          >
            <item.icon className="size-4.5" />
            {item.label}
          </Link>
        )
      })}
    </nav>
  )
}
