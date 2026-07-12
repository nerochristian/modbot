import { cookies } from 'next/headers'
import { cache } from 'react'
import { prisma } from '@/lib/prisma'
import { isSystemOwner, SELECTED_GUILD_COOKIE, SESSION_COOKIE, verifySession } from '@/lib/auth'
import {
  DEFAULT_ROLE_MATRIX,
  PERMISSIONS,
  isPermission,
  isRole,
  type Permission,
  type Role,
} from '@/lib/rbac'

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
  selectedGuildId: string | null
  systemAdmin: boolean
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
  if (!session || session.userId !== payload.sub || session.revokedAt || session.expiresAt < new Date()) return null

  const user = await prisma.user.findUnique({ where: { id: payload.sub } })
  if (!user || user.status === 'suspended') return null

  const systemAdmin = isSystemOwner(user.discordId)
  const selectedId = cookieStore.get(SELECTED_GUILD_COOKIE)?.value
  const selectedGuildId = selectedId && /^\d{15,22}$/.test(selectedId) ? selectedId : null
  const membership = selectedGuildId
    ? await prisma.guildMembership.findUnique({
        where: { guildId_userId: { guildId: selectedGuildId, userId: user.id } },
        include: { guild: { select: { installed: true } } },
      })
    : null
  const membershipActive = membership
    && membership.guild.installed
    && (membership.status === 'active' || membership.status === 'invited')
  const role: Role = systemAdmin
    ? 'admin'
    : membershipActive && isRole(membership.role)
      ? membership.role
      : 'viewer'
  const authorizedGuildId = systemAdmin && selectedGuildId
    ? (await prisma.guild.findFirst({ where: { id: selectedGuildId, installed: true }, select: { id: true } }))?.id ?? null
    : membershipActive
      ? selectedGuildId
      : null
  const permissions = authorizedGuildId
    ? await getRolePermissions(role, authorizedGuildId, systemAdmin)
    : []

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
    selectedGuildId: authorizedGuildId,
    systemAdmin,
  }
})

/** Effective permissions for a role, from the live (admin-editable) matrix. */
export async function getRolePermissions(
  role: Role,
  guildId: string,
  systemAdmin = false,
): Promise<Permission[]> {
  if (systemAdmin) return [...PERMISSIONS]
  const rows = await prisma.rolePermission.findMany({
    where: { guildId, role },
  })
  if (rows.length === 0) {
    // Fall back to the code default if the matrix hasn't been seeded.
    return DEFAULT_ROLE_MATRIX[role]
  }
  return rows.filter((row) => row.allowed && isPermission(row.permission)).map((row) => row.permission as Permission)
}

export function userCan(user: CurrentUser | null, permission: Permission): boolean {
  return !!user && user.permissions.includes(permission)
}
