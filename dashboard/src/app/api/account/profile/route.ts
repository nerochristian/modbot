import { prisma } from '@/lib/prisma'
import { requireMutation, requireUser, handleError, ok } from '@/lib/api'
import { updateProfileSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'

const PROFILE_SELECT = {
  id: true,
  name: true,
  email: true,
  role: true,
  title: true,
  phone: true,
  timezone: true,
  bio: true,
  avatarColor: true,
  createdAt: true,
} as const

export async function GET() {
  const guard = await requireUser()
  if (guard instanceof Response) return guard
  const profile = await prisma.user.findUnique({
    where: { id: guard.id },
    select: PROFILE_SELECT,
  })
  return ok({ profile: profile ? { ...profile, role: guard.role } : null })
}

export async function PATCH(request: Request) {
  try {
    const guard = await requireMutation(request)
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
    await logActivity({
      guildId: user.selectedGuildId ?? undefined,
      userId: user.id,
      actorName: updated.name,
      action: 'updated_profile',
    })
    return ok(updated)
  } catch (error) {
    return handleError(error)
  }
}
