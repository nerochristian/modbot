import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { logAudit } from '@/lib/log'
import {
  DEFAULT_ROLE_MATRIX,
  PERMISSION_GROUPS,
  PERMISSIONS,
  ROLES,
  isRole,
  type Permission,
  type Role,
} from '@/lib/rbac'
import { z } from 'zod'

// GET — the full role/permission matrix from the live table.
export async function GET() {
  try {
    const guard = await requireUser('admin.roles.manage')
    if (guard instanceof Response) return guard

    const rows = await prisma.rolePermission.findMany()
    const matrix: Record<string, string[]> = {}
    for (const role of ROLES) {
      const granted = rows.filter((r) => r.role === role && r.allowed).map((r) => r.permission)
      matrix[role] = granted.length ? granted : DEFAULT_ROLE_MATRIX[role]
    }

    return ok({ roles: ROLES, permissions: PERMISSIONS, groups: PERMISSION_GROUPS, matrix })
  } catch (error) {
    return handleError(error)
  }
}

const patchSchema = z.object({
  role: z.enum(ROLES),
  permission: z.enum(PERMISSIONS),
  allowed: z.boolean(),
})

// PATCH — grant or revoke a single permission for a role.
export async function PATCH(request: Request) {
  try {
    const guard = await requireUser('admin.roles.manage')
    if (guard instanceof Response) return guard
    const actor = guard

    const body = await request.json()
    const { role, permission, allowed } = patchSchema.parse(body)

    if (!isRole(role)) return apiError('Invalid role', 400)
    // The admin role is immutable to prevent self-lockout.
    if (role === 'admin') return apiError('The admin role cannot be modified.', 400)

    await prisma.rolePermission.upsert({
      where: { role_permission: { role, permission } },
      create: { role, permission, allowed },
      update: { allowed },
    })

    await logAudit({
      userId: actor.id,
      actorName: actor.name,
      action: 'permission.update',
      entity: 'RolePermission',
      metadata: { role, permission, allowed },
    })

    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}

export type { Role, Permission }
