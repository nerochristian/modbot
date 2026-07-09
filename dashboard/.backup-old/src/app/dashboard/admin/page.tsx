import type { Metadata } from 'next'
import Link from 'next/link'
import { Users2, ShieldCheck, ToggleRight, ScrollText, Blocks, Megaphone } from 'lucide-react'
import { prisma } from '@/lib/prisma'
import { Card, CardContent } from '@/components/ui/card'

export const metadata: Metadata = { title: 'Admin' }

export default async function AdminOverviewPage() {
  const [users, customers, features, enabledFeatures, widgets, auditCount] = await Promise.all([
    prisma.user.count(),
    prisma.customer.count(),
    prisma.featureToggle.count(),
    prisma.featureToggle.count({ where: { enabled: true } }),
    prisma.widget.count(),
    prisma.auditLog.count(),
  ])

  const stats = [
    { label: 'Team members', value: users, href: '/dashboard/users', icon: Users2 },
    { label: 'Customers', value: customers, href: '/dashboard/customers', icon: Users2 },
    { label: 'Features enabled', value: `${enabledFeatures}/${features}`, href: '/dashboard/admin/features', icon: ToggleRight },
    { label: 'Widgets', value: widgets, href: '/dashboard/admin/widgets', icon: Blocks },
    { label: 'Audit events', value: auditCount, href: '/dashboard/admin/audit', icon: ScrollText },
  ]

  const shortcuts = [
    { label: 'Roles & permissions', description: 'Edit what each role can access.', href: '/dashboard/admin/roles', icon: ShieldCheck },
    { label: 'Feature flags', description: 'Toggle features across the workspace.', href: '/dashboard/admin/features', icon: ToggleRight },
    { label: 'Global settings', description: 'App name, sign-ups, security policy.', href: '/dashboard/admin/settings', icon: Blocks },
    { label: 'Send broadcast', description: 'Notify all users of an announcement.', href: '/dashboard/admin/broadcast', icon: Megaphone },
  ]

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((s) => (
          <Link key={s.label} href={s.href}>
            <Card className="p-5 transition-colors hover:border-border-strong">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted">{s.label}</p>
                <s.icon className="size-4.5 text-muted-2" />
              </div>
              <p className="mt-2 text-2xl font-bold text-foreground">{s.value}</p>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {shortcuts.map((s) => (
          <Link key={s.label} href={s.href}>
            <Card className="transition-colors hover:border-border-strong">
              <CardContent className="flex items-start gap-4">
                <span className="flex size-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <s.icon className="size-5" />
                </span>
                <div>
                  <p className="font-medium text-foreground">{s.label}</p>
                  <p className="text-sm text-muted">{s.description}</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
