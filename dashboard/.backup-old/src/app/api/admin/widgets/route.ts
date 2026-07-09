import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok } from '@/lib/api'
import { logAudit } from '@/lib/log'
import { z } from 'zod'

export async function GET() {
  try {
    const guard = await requireUser('admin.widgets.manage')
    if (guard instanceof Response) return guard
    const widgets = await prisma.widget.findMany({ orderBy: { order: 'asc' } })
    return ok({ widgets })
  } catch (error) {
    return handleError(error)
  }
}

const patchSchema = z.object({ key: z.string(), enabled: z.boolean() })

// PATCH — admin kill-switch for a widget across the whole app.
export async function PATCH(request: Request) {
  try {
    const guard = await requireUser('admin.widgets.manage')
    if (guard instanceof Response) return guard
    const actor = guard

    const body = await request.json()
    const { key, enabled } = patchSchema.parse(body)

    const widget = await prisma.widget.update({ where: { key }, data: { enabled } })
    await logAudit({
      userId: actor.id,
      actorName: actor.name,
      action: enabled ? 'widget.enable' : 'widget.disable',
      entity: 'Widget',
      entityId: key,
    })
    return ok(widget)
  } catch (error) {
    return handleError(error)
  }
}
