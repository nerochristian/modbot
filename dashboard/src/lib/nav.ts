import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  LineChart,
  Users2,
  Gavel,
  ShieldAlert,
  Scale,
  UserCog,
  FileBarChart,
  Activity,
  Bell,
  Sparkles,
  Settings,
  ShieldCheck,
} from 'lucide-react'
import type { Permission } from '@/lib/rbac'

export type NavItem = {
  label: string
  href: string
  icon: LucideIcon
  permission: Permission
  section: 'main' | 'account' | 'admin'
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', href: '/dashboard', icon: LayoutDashboard, permission: 'dashboard.view', section: 'main' },
  { label: 'Analytics', href: '/dashboard/analytics', icon: LineChart, permission: 'analytics.view', section: 'main' },
  { label: 'Members', href: '/dashboard/members', icon: Users2, permission: 'members.read', section: 'main' },
  { label: 'Cases', href: '/dashboard/cases', icon: Gavel, permission: 'cases.read', section: 'main' },
  { label: 'Automod', href: '/dashboard/automod', icon: ShieldAlert, permission: 'automod.read', section: 'main' },
  { label: 'Appeals', href: '/dashboard/appeals', icon: Scale, permission: 'appeals.read', section: 'main' },
  { label: 'Reports', href: '/dashboard/reports', icon: FileBarChart, permission: 'reports.read', section: 'main' },
  { label: 'Activity', href: '/dashboard/activity', icon: Activity, permission: 'activity.read', section: 'main' },
  { label: 'Team', href: '/dashboard/users', icon: UserCog, permission: 'users.read', section: 'account' },
  { label: 'Notifications', href: '/dashboard/notifications', icon: Bell, permission: 'notifications.read', section: 'account' },
  { label: 'Premium', href: '/dashboard/billing', icon: Sparkles, permission: 'billing.read', section: 'account' },
  { label: 'Settings', href: '/dashboard/settings', icon: Settings, permission: 'settings.read', section: 'account' },
  { label: 'Admin', href: '/dashboard/admin', icon: ShieldCheck, permission: 'admin.access', section: 'admin' },
]

/** Human labels for the search command palette and breadcrumbs. */
export const NAV_LABEL_BY_HREF: Record<string, string> = Object.fromEntries(
  NAV_ITEMS.map((i) => [i.href, i.label]),
)
