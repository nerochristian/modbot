import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok } from '@/lib/api'
import { logAudit } from '@/lib/log'

// PATCH — toggle two-factor authentication for the current user.
export async function PATCH(request: Request) {
  try {
    const guard = await requireUser()
    if (guard instanceof Response) return guard
    const user = guard

    const body = (await request.json()) as { enabled?: boolean }
    const enabled = !!body.enabled

    await prisma.user.update({ where: { id: user.id }, data: { twoFactorEnabled: enabled } })
    await logAudit({
      userId: user.id,
      actorName: user.name,
      action: enabled ? '2fa.enable' : '2fa.disable',
      entity: 'User',
      entityId: user.id,
    })
    return ok({ twoFactorEnabled: enabled })
  } catch (error) {
    return handleError(error)
  }
}
