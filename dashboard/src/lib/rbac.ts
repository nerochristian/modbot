/**
 * Role-based access control.
 *
 * `ROLES` and `PERMISSIONS` are the canonical vocabulary. `DEFAULT_ROLE_MATRIX`
 * is the seed baseline — it is written into the RolePermission table so admins
 * can edit grants at runtime (see the Admin > Roles page). Server-side checks
 * read the live matrix via `getRolePermissions`; UI visibility uses the same
 * data passed down from the session.
 */

export const ROLES = ['admin', 'manager', 'viewer'] as const
export type Role = (typeof ROLES)[number]

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value)
}

export const PERMISSIONS = [
  'dashboard.view',
  'analytics.view',
  'customers.read',
  'customers.write',
  'users.read',
  'users.write',
  'users.delete',
  'reports.read',
  'reports.write',
  'billing.read',
  'billing.write',
  'notifications.read',
  'activity.read',
  'audit.read',
  'settings.read',
  'settings.write',
  'config.write',
  'admin.access',
  'admin.users.manage',
  'admin.roles.manage',
  'admin.features.manage',
  'admin.settings.manage',
  'admin.widgets.manage',
] as const
export type Permission = (typeof PERMISSIONS)[number]

export const PERMISSION_GROUPS: { label: string; permissions: Permission[] }[] = [
  { label: 'Dashboard', permissions: ['dashboard.view', 'analytics.view', 'config.write'] },
  { label: 'Customers', permissions: ['customers.read', 'customers.write'] },
  { label: 'Users', permissions: ['users.read', 'users.write', 'users.delete'] },
  { label: 'Reports', permissions: ['reports.read', 'reports.write'] },
  { label: 'Billing', permissions: ['billing.read', 'billing.write'] },
  { label: 'Activity & Audit', permissions: ['notifications.read', 'activity.read', 'audit.read'] },
  { label: 'Settings', permissions: ['settings.read', 'settings.write'] },
  {
    label: 'Administration',
    permissions: [
      'admin.access',
      'admin.users.manage',
      'admin.roles.manage',
      'admin.features.manage',
      'admin.settings.manage',
      'admin.widgets.manage',
    ],
  },
]

const READ_ONLY: Permission[] = [
  'dashboard.view',
  'analytics.view',
  'customers.read',
  'users.read',
  'reports.read',
  'billing.read',
  'notifications.read',
  'activity.read',
  'settings.read',
  'config.write',
]

export const DEFAULT_ROLE_MATRIX: Record<Role, Permission[]> = {
  admin: [...PERMISSIONS],
  manager: [
    'dashboard.view',
    'analytics.view',
    'customers.read',
    'customers.write',
    'users.read',
    'users.write',
    'reports.read',
    'reports.write',
    'billing.read',
    'notifications.read',
    'activity.read',
    'audit.read',
    'settings.read',
    'settings.write',
    'config.write',
  ],
  viewer: READ_ONLY,
}

export const ROLE_LABELS: Record<Role, string> = {
  admin: 'Admin',
  manager: 'Manager',
  viewer: 'Viewer',
}

export const ROLE_DESCRIPTIONS: Record<Role, string> = {
  admin: 'Full access, including user management, roles, and global configuration.',
  manager: 'Manage customers, users, reports, and team settings. No admin controls.',
  viewer: 'Read-only access to dashboards, analytics, and reports.',
}
