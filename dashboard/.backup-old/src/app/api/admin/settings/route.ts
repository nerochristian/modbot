import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok } from '@/lib/api'
import { parseJson } from '@/lib/json'
import { logAudit } from '@/lib/log'
import { z } from 'zod'

export async function GET() {
  try {
    const guard = await requireUser('admin.settings.manage')
    if (guard instanceof Response) return guard

    const rows = await prisma.appSetting.findMany()
    const settings: Record<string, unknown> = {}
    for (const row of rows) settings[row.key] = parseJson<unknown>(row.value, null)
    return ok({ settings })
  } catch (error) {
    return handleError(error)
  }
}

const patchSchema = z.object({ key: z.string(), value: z.unknown() })

export async function PATCH(request: Request) {
  try {
    const guard = await requireUser('admin.settings.manage')
    if (guard instanceof Response) return guard
    const actor = guard

    const body = await request.json()
    const { key, value } = patchSchema.parse(body)

    await prisma.appSetting.upsert({
      where: { key },
      create: { key, value: JSON.stringify(value) },
      update: { value: JSON.stringify(value) },
    })
    await logAudit({
      userId: actor.id,
      actorName: actor.name,
      action: 'setting.update',
      entity: 'AppSetting',
      entityId: key,
      metadata: { value },
    })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
