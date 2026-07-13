import { prisma } from '@/lib/prisma'
import { requireMutation, handleError, ok } from '@/lib/api'
import { logActivity, logAudit } from '@/lib/log'
import { parseJson } from '@/lib/json'
import type { DashboardConfig } from '@/lib/dashboard-config'
import { z } from 'zod'

const schema = z.object({
  title: z.string().min(2).max(120),
  body: z.string().min(2).max(500),
  level: z.enum(['info', 'success', 'warning', 'error']).default('info'),
  audience: z.enum(['all', 'admin', 'manager', 'viewer']).default('all'),
})

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'admin.access')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId as string
    const data = schema.parse(await request.json())
    const memberships = await prisma.guildMembership.findMany({
      where: {
        guildId,
        status: 'active',
        ...(data.audience === 'all' ? {} : { role: data.audience }),
      },
      select: { userId: true, user: { select: { dashboardConfig: { select: { config: true } } } } },
    })
    const recipients = memberships.filter((membership) => {
      const config = parseJson<Partial<DashboardConfig>>(membership.user.dashboardConfig?.config, {})
      return config.notifications?.product?.inApp !== false
    })
    if (recipients.length) {
      await prisma.notification.createMany({
        data: recipients.map((membership) => ({
          guildId,
          userId: membership.userId,
          type: 'product',
          level: data.level,
          title: data.title,
          body: data.body,
        })),
      })
    }
    await logActivity({ guildId, userId: guard.id, actorName: guard.name, action: 'sent_broadcast', target: data.title })
    await logAudit({
      guildId,
      userId: guard.id,
      actorName: guard.name,
      action: 'notification.broadcast',
      entity: 'Notification',
      metadata: { audience: data.audience, recipients: recipients.length },
    })
    return ok({ success: true, recipients: recipients.length })
  } catch (error) {
    return handleError(error)
  }
}
