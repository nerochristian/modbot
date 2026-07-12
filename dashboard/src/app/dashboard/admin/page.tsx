import type { Metadata } from 'next'
import Link from 'next/link'
import { Users2, ShieldCheck, ToggleRight, ScrollText, Blocks, Megaphone } from 'lucide-react'
import { prisma } from '@/lib/prisma'
import { Card, CardContent } from '@/components/ui/card'

export const metadata: Metadata = { title: 'Admin' }

export default async function AdminOverviewPage() {
  const [users, members, features, enabledFeatures, rules, auditCount] = await Promise.all([
    prisma.user.count(),
    prisma.member.count(),
    prisma.featureToggle.count(),
    prisma.featureToggle.count({ where: { enabled: true } }),
    prisma.automodRule.count(),
    prisma.auditLog.count(),
  ])

  const stats = [
    { label: 'Team members', value: users, href: '/dashboard/users', icon: Users2 },
    { label: 'Server members', value: members, href: '/dashboard/members', icon: Users2 },
    { label: 'Features enabled', value: `${enabledFeatures}/${features}`, href: '/dashboard/admin/features', icon: ToggleRight },
    { label: 'Automod rules', value: rules, href: '/dashboard/automod', icon: Blocks },
    { label: 'Audit events', value: auditCount, href: '/dashboard/admin/audit', icon: ScrollText },
  ]

  const shortcuts = [
    { label: 'Roles & permissions', description: 'Edit what each mod role can access.', href: '/dashboard/admin/roles', icon: ShieldCheck },
    { label: 'Feature flags', description: 'Toggle features across the server.', href: '/dashboard/admin/features', icon: ToggleRight },
    { label: 'Global settings', description: 'Bot name, sign-ups, security policy.', href: '/dashboard/admin/settings', icon: Blocks },
    { label: 'Send broadcast', description: 'Notify the whole mod team of an announcement.', href: '/dashboard/admin/broadcast', icon: Megaphone },
  ]

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((s) => (
          <Link key={s.label} href={s.href}>
            <Card className="p-5 transition-colors hover:border-border-strong">
              <div className="flex items-center justify-between">
                <p className="font-mono text-[0.6875rem] font-medium uppercase tracking-[0.1em] text-muted">{s.label}</p>
                <s.icon className="size-4.5 text-muted-2" />
              </div>
              <p className="mt-2 font-display text-2xl font-semibold text-foreground">{s.value}</p>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {shortcuts.map((s) => (
          <Link key={s.label} href={s.href}>
            <Card className="transition-colors hover:border-border-strong">
              <CardContent className="flex items-start gap-4">
                <span className="flex size-10 items-center justify-center rounded-md bg-accent-soft text-accent">
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
