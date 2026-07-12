'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { User, ShieldCheck, Palette, Bell, LayoutDashboard } from 'lucide-react'
import { cn } from '@/lib/utils'

const ITEMS = [
  { label: 'Profile', href: '/dashboard/settings/profile', icon: User },
  { label: 'Security', href: '/dashboard/settings/security', icon: ShieldCheck },
  { label: 'Appearance', href: '/dashboard/settings/appearance', icon: Palette },
  { label: 'Notifications', href: '/dashboard/settings/notifications', icon: Bell },
  { label: 'Dashboard', href: '/dashboard/settings/dashboard', icon: LayoutDashboard },
]

export function SettingsNav() {
  const pathname = usePathname()

  return (
    <nav className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
      {ITEMS.map((item) => {
        const active = pathname === item.href
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
