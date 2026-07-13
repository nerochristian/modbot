import { prisma } from '@/lib/prisma'
import { requireMutation, handleError, ok, apiError } from '@/lib/api'

// PATCH /api/notifications/[id] — toggle/mark read state for one notification.
export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireMutation(request, 'notifications.read')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.notification.findUnique({ where: { id } })
    if (!existing || existing.userId !== user.id || existing.guildId !== user.selectedGuildId) {
      return apiError('Not found', 404)
    }

    const body = (await request.json().catch(() => ({}))) as { read?: boolean }
    const updated = await prisma.notification.update({
      where: { id },
      data: { read: body.read ?? true },
    })
    return ok(updated)
  } catch (error) {
    return handleError(error)
  }
}

// DELETE /api/notifications/[id]
export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireMutation(_request, 'notifications.read')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.notification.findUnique({ where: { id } })
    if (!existing || existing.userId !== user.id || existing.guildId !== user.selectedGuildId) {
      return apiError('Not found', 404)
    }

    await prisma.notification.delete({ where: { id } })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
