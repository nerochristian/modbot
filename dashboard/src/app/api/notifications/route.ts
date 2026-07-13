import { prisma } from '@/lib/prisma'
import { requireMutation, requireUser, handleError, ok } from '@/lib/api'

// GET /api/notifications?limit=8 — recent notifications + unread count.
export async function GET(request: Request) {
  const guard = await requireUser('notifications.read')
  if (guard instanceof Response) return guard
  const user = guard
  const guildId = user.selectedGuildId as string

  const url = new URL(request.url)
  const limit = Math.min(50, Math.max(1, Number(url.searchParams.get('limit')) || 20))
  const onlyUnread = url.searchParams.get('unread') === '1'

  const [items, unread] = await Promise.all([
    prisma.notification.findMany({
      where: { userId: user.id, guildId, ...(onlyUnread ? { read: false } : {}) },
      orderBy: { createdAt: 'desc' },
      take: limit,
    }),
    prisma.notification.count({ where: { userId: user.id, guildId, read: false } }),
  ])

  return ok({ items, unread })
}

// PATCH /api/notifications — mark all as read.
export async function PATCH(request: Request) {
  try {
    const guard = await requireMutation(request, 'notifications.read')
    if (guard instanceof Response) return guard
    const user = guard

    await prisma.notification.updateMany({
      where: { userId: user.id, guildId: user.selectedGuildId as string, read: false },
      data: { read: true },
    })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
