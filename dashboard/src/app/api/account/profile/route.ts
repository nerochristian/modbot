import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok } from '@/lib/api'
import { updateProfileSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'

export async function PATCH(request: Request) {
  try {
    const guard = await requireUser()
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const data = updateProfileSchema.parse(body)

    const updated = await prisma.user.update({
      where: { id: user.id },
      data,
      select: {
        id: true,
        name: true,
        email: true,
        title: true,
        phone: true,
        timezone: true,
        bio: true,
        avatarColor: true,
      },
    })
    await logActivity({ userId: user.id, actorName: updated.name, action: 'updated_profile' })
    return ok(updated)
  } catch (error) {
    return handleError(error)
  }
}
