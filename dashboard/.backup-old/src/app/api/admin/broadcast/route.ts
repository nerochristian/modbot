import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok } from '@/lib/api'
import { logActivity, logAudit } from '@/lib/log'
import { z } from 'zod'

const schema = z.object({
  title: z.string().min(2).max(120),
  body: z.string().min(2).max(500),
  level: z.enum(['info', 'success', 'warning', 'error']).default('info'),
  audience: z.enum(['all', 'admin', 'manager', 'viewer']).default('all'),
})

// POST — broadcast a system notification to every targeted user.
export async function POST(request: Request) {
  try {
    const guard = await requireUser('admin.settings.manage')
    if (guard instanceof Response) return guard
    const actor = guard

    const body = await request.json()
    const data = schema.parse(body)

    const users = await prisma.user.findMany({
      where: data.audience === 'all' ? {} : { role: data.audience },
      select: { id: true },
    })

    if (users.length > 0) {
      await prisma.notification.createMany({
        data: users.map((u) => ({
          userId: u.id,
          type: 'system',
          level: data.level,
          title: data.title,
          body: data.body,
        })),
      })
    }

    await logActivity({ userId: actor.id, actorName: actor.name, action: 'sent_broadcast', target: data.title })
    await logAudit({
      userId: actor.id,
      actorName: actor.name,
      action: 'notification.broadcast',
      entity: 'Notification',
      metadata: { audience: data.audience, recipients: users.length },
    })

    return ok({ success: true, recipients: users.length })
  } catch (error) {
    return handleError(error)
  }
}
