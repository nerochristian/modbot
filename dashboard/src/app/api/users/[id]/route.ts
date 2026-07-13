import { prisma } from '@/lib/prisma'
import { requireMutation, handleError, ok, apiError } from '@/lib/api'
import { updateUserSchema } from '@/lib/validation'
import { invalidateGuildCache } from '@/lib/discord'
import { logAudit } from '@/lib/log'

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireMutation(request, 'users.write')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId as string
    const { id } = await ctx.params
    const target = await prisma.guildMembership.findUnique({
      where: { guildId_userId: { guildId, userId: id } },
      include: { user: true },
    })
    if (!target) return apiError('Workspace member not found', 404)
    const data = updateUserSchema.parse(await request.json())

    if (guard.role !== 'admin' && (data.role === 'admin' || target.role === 'admin')) {
      return apiError('Only a workspace admin can modify an admin.', 403)
    }
    const nextStatus = data.status === 'suspended' ? 'revoked' : data.status
    if (nextStatus === 'active' && target.status !== 'active') {
      return apiError('Discord verification is required before this invitation can be activated.', 409)
    }
    if (target.role === 'admin' && ((data.role && data.role !== 'admin') || nextStatus === 'revoked')) {
      const activeAdmins = await prisma.guildMembership.count({
        where: { guildId, role: 'admin', status: 'active' },
      })
      if (activeAdmins <= 1) return apiError('You cannot remove the last active workspace admin.', 400)
    }
    if (id === guard.id && data.role && data.role !== target.role) {
      return apiError('You cannot change your own workspace role.', 400)
    }

    const updatedMembership = await prisma.guildMembership.update({
      where: { guildId_userId: { guildId, userId: id } },
      data: {
        ...(data.role ? { role: data.role } : {}),
        ...(nextStatus ? { status: nextStatus } : {}),
      },
    })
    invalidateGuildCache(id)

    if (data.role && data.role !== target.role) {
      await logAudit({
        guildId,
        userId: guard.id,
        actorName: guard.name,
        action: 'membership.role.update',
        entity: 'GuildMembership',
        entityId: updatedMembership.id,
        metadata: { before: target.role, after: data.role },
      })
    }
    if (nextStatus && nextStatus !== target.status) {
      await logAudit({
        guildId,
        userId: guard.id,
        actorName: guard.name,
        action: `membership.${nextStatus}`,
        entity: 'GuildMembership',
        entityId: updatedMembership.id,
      })
    }
    return ok({
      id: target.user.id,
      name: target.user.name,
      email: target.user.email,
      role: updatedMembership.role,
      status: updatedMembership.status === 'revoked' ? 'suspended' : updatedMembership.status,
      title: target.user.title,
      avatarColor: target.user.avatarColor,
      createdAt: updatedMembership.createdAt,
      lastLoginAt: target.user.lastLoginAt,
    })
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireMutation(request, 'users.delete')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId as string
    const { id } = await ctx.params
    if (id === guard.id) return apiError('You cannot remove yourself from the workspace.', 400)
    const target = await prisma.guildMembership.findUnique({
      where: { guildId_userId: { guildId, userId: id } },
    })
    if (!target) return apiError('Workspace member not found', 404)
    if (target.role === 'admin') {
      const activeAdmins = await prisma.guildMembership.count({
        where: { guildId, role: 'admin', status: 'active' },
      })
      if (activeAdmins <= 1) return apiError('You cannot remove the last active workspace admin.', 400)
    }
    await prisma.guildMembership.delete({ where: { guildId_userId: { guildId, userId: id } } })
    invalidateGuildCache(id)
    await logAudit({ guildId, userId: guard.id, actorName: guard.name, action: 'membership.delete', entity: 'GuildMembership', entityId: target.id })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
