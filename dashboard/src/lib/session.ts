import { cookies } from 'next/headers'
import { cache } from 'react'
import { prisma } from '@/lib/prisma'
import { SESSION_COOKIE, verifySession } from '@/lib/auth'
import { DEFAULT_ROLE_MATRIX, isRole, type Permission, type Role } from '@/lib/rbac'

export type CurrentUser = {
  id: string
  discordId: string | null
  name: string
  email: string
  role: Role
  status: string
  avatarColor: string
  title: string | null
  timezone: string
  twoFactorEnabled: boolean
  permissions: Permission[]
}

/**
 * Resolve the authenticated user for the current request, or null.
 *
 * Wrapped in React `cache` so multiple calls within one request (layout, page,
 * components) hit the DB once. Verifies the JWT signature, confirms the backing
 * Session row is live (not revoked / expired), then loads the user and their
 * effective permissions from the live role matrix.
 */
export const getCurrentUser = cache(async (): Promise<CurrentUser | null> => {
  const cookieStore = await cookies()
  const token = cookieStore.get(SESSION_COOKIE)?.value
  if (!token) return null

  const payload = await verifySession(token)
  if (!payload) return null

  const session = await prisma.session.findUnique({ where: { jti: payload.jti } })
  if (!session || session.revokedAt || session.expiresAt < new Date()) return null

  const user = await prisma.user.findUnique({ where: { id: payload.sub } })
  if (!user || user.status === 'suspended') return null

  const role: Role = isRole(user.role) ? user.role : 'viewer'
  const permissions = await getRolePermissions(role)

  return {
    id: user.id,
    discordId: user.discordId,
    name: user.name,
    email: user.email,
    role,
    status: user.status,
    avatarColor: user.avatarColor,
    title: user.title,
    timezone: user.timezone,
    twoFactorEnabled: user.twoFactorEnabled,
    permissions,
  }
})

/** Effective permissions for a role, from the live (admin-editable) matrix. */
export async function getRolePermissions(role: Role): Promise<Permission[]> {
  const rows = await prisma.rolePermission.findMany({
    where: { role, allowed: true },
  })
  if (rows.length === 0) {
    // Fall back to the code default if the matrix hasn't been seeded.
    return DEFAULT_ROLE_MATRIX[role]
  }
  return rows.map((r) => r.permission as Permission)
}

export function userCan(user: CurrentUser | null, permission: Permission): boolean {
  return !!user && user.permissions.includes(permission)
}
