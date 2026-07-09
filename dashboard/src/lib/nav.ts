import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  LineChart,
  Users2,
  UserCog,
  FileBarChart,
  Activity,
  Bell,
  CreditCard,
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
  { label: 'Customers', href: '/dashboard/customers', icon: Users2, permission: 'customers.read', section: 'main' },
  { label: 'Users', href: '/dashboard/users', icon: UserCog, permission: 'users.read', section: 'main' },
  { label: 'Reports', href: '/dashboard/reports', icon: FileBarChart, permission: 'reports.read', section: 'main' },
  { label: 'Activity', href: '/dashboard/activity', icon: Activity, permission: 'activity.read', section: 'main' },
  { label: 'Notifications', href: '/dashboard/notifications', icon: Bell, permission: 'notifications.read', section: 'account' },
  { label: 'Billing', href: '/dashboard/billing', icon: CreditCard, permission: 'billing.read', section: 'account' },
  { label: 'Settings', href: '/dashboard/settings', icon: Settings, permission: 'settings.read', section: 'account' },
  { label: 'Admin', href: '/dashboard/admin', icon: ShieldCheck, permission: 'admin.access', section: 'admin' },
]

/** Human labels for the search command palette and breadcrumbs. */
export const NAV_LABEL_BY_HREF: Record<string, string> = Object.fromEntries(
  NAV_ITEMS.map((i) => [i.href, i.label]),
)
