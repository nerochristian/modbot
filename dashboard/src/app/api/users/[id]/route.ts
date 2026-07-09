import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { updateUserSchema } from '@/lib/validation'
import { logAudit } from '@/lib/log'

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('users.write')
    if (guard instanceof Response) return guard
    const actor = guard
    const { id } = await ctx.params

    const target = await prisma.user.findUnique({ where: { id } })
    if (!target) return apiError('User not found', 404)

    const body = await request.json()
    const data = updateUserSchema.parse(body)

    // Guard: prevent removing the last admin (by demotion or suspension).
    if ((data.role && data.role !== 'admin' && target.role === 'admin') ||
        (data.status === 'suspended' && target.role === 'admin')) {
      const activeAdmins = await prisma.user.count({ where: { role: 'admin', status: 'active' } })
      if (activeAdmins <= 1) return apiError('You cannot remove the last active admin.', 400)
    }
    // Guard: don't let an admin change their own role (avoid self-lockout).
    if (id === actor.id && data.role && data.role !== actor.role) {
      return apiError('You cannot change your own role.', 400)
    }

    const updated = await prisma.user.update({
      where: { id },
      data,
      select: { id: true, name: true, email: true, role: true, status: true, title: true, avatarColor: true, createdAt: true, lastLoginAt: true },
    })

    if (data.role && data.role !== target.role) {
      await logAudit({
        userId: actor.id,
        actorName: actor.name,
        action: 'user.role.update',
        entity: 'User',
        entityId: id,
        metadata: { before: target.role, after: data.role },
      })
    }
    if (data.status && data.status !== target.status) {
      await logAudit({
        userId: actor.id,
        actorName: actor.name,
        action: `user.${data.status}`,
        entity: 'User',
        entityId: id,
      })
    }

    return ok(updated)
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('users.delete')
    if (guard instanceof Response) return guard
    const actor = guard
    const { id } = await ctx.params

    if (id === actor.id) return apiError('You cannot delete your own account.', 400)

    const target = await prisma.user.findUnique({ where: { id } })
    if (!target) return apiError('User not found', 404)

    if (target.role === 'admin') {
      const activeAdmins = await prisma.user.count({ where: { role: 'admin', status: 'active' } })
      if (activeAdmins <= 1) return apiError('You cannot delete the last active admin.', 400)
    }

    await prisma.user.delete({ where: { id } })
    await logAudit({ userId: actor.id, actorName: actor.name, action: 'user.delete', entity: 'User', entityId: id })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
