import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok } from '@/lib/api'
import { logAudit } from '@/lib/log'
import { z } from 'zod'

export async function GET() {
  try {
    const guard = await requireUser('admin.features.manage')
    if (guard instanceof Response) return guard
    const features = await prisma.featureToggle.findMany({ orderBy: { name: 'asc' } })
    return ok({ features })
  } catch (error) {
    return handleError(error)
  }
}

const patchSchema = z.object({ key: z.string(), enabled: z.boolean() })

export async function PATCH(request: Request) {
  try {
    const guard = await requireUser('admin.features.manage')
    if (guard instanceof Response) return guard
    const actor = guard

    const body = await request.json()
    const { key, enabled } = patchSchema.parse(body)

    const feature = await prisma.featureToggle.update({ where: { key }, data: { enabled } })
    await logAudit({
      userId: actor.id,
      actorName: actor.name,
      action: 'feature.toggle',
      entity: 'FeatureToggle',
      entityId: key,
      metadata: { enabled },
    })
    return ok(feature)
  } catch (error) {
    return handleError(error)
  }
}
