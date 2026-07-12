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
  'members.read',
  'members.write',
  'cases.read',
  'cases.write',
  'cases.delete',
  'automod.read',
  'automod.write',
  'appeals.read',
  'appeals.write',
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
  'config.write',
  'admin.access',
  'admin.roles.manage',
] as const
export type Permission = (typeof PERMISSIONS)[number]

export function isPermission(value: string): value is Permission {
  return (PERMISSIONS as readonly string[]).includes(value)
}

export const PERMISSION_GROUPS: { label: string; permissions: Permission[] }[] = [
  { label: 'Dashboard', permissions: ['dashboard.view', 'analytics.view', 'config.write'] },
  { label: 'Members', permissions: ['members.read', 'members.write'] },
  { label: 'Cases', permissions: ['cases.read', 'cases.write', 'cases.delete'] },
  { label: 'Automod', permissions: ['automod.read', 'automod.write'] },
  { label: 'Appeals', permissions: ['appeals.read', 'appeals.write'] },
  { label: 'Team', permissions: ['users.read', 'users.write', 'users.delete'] },
  { label: 'Reports', permissions: ['reports.read', 'reports.write'] },
  { label: 'Premium', permissions: ['billing.read', 'billing.write'] },
  { label: 'Activity & Audit', permissions: ['notifications.read', 'activity.read', 'audit.read'] },
  { label: 'Settings', permissions: ['settings.read'] },
  {
    label: 'Administration',
    permissions: [
      'admin.access',
      'admin.roles.manage',
    ],
  },
]

const READ_ONLY: Permission[] = [
  'dashboard.view',
  'analytics.view',
  'members.read',
  'cases.read',
  'automod.read',
  'appeals.read',
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
    'members.read',
    'members.write',
    'cases.read',
    'cases.write',
    'automod.read',
    'automod.write',
    'appeals.read',
    'appeals.write',
    'users.read',
    'users.write',
    'reports.read',
    'reports.write',
    'billing.read',
    'notifications.read',
    'activity.read',
    'audit.read',
    'settings.read',
    'config.write',
  ],
  viewer: READ_ONLY,
}

export const ROLE_LABELS: Record<Role, string> = {
  admin: 'Admin',
  manager: 'Moderator',
  viewer: 'Helper',
}

export const ROLE_DESCRIPTIONS: Record<Role, string> = {
  admin: 'Full access to this server workspace, including team roles and moderation configuration.',
  manager: 'Take moderation actions, manage cases, automod, appeals, and members. No admin controls.',
  viewer: 'Read-only access to the queue, cases, members, and analytics.',
}
