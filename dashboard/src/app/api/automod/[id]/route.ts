import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { automodRuleSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'
import type { Prisma } from '@prisma/client'

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('automod.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.automodRule.findUnique({ where: { id } })
    if (!existing) return apiError('Automod rule not found', 404)

    const body = await request.json()
    const data = automodRuleSchema.partial().parse(body)

    const update: Prisma.AutomodRuleUpdateInput = { ...data }
    if (data.exemptRoles !== undefined) {
      update.exemptRoles = JSON.stringify(data.exemptRoles)
    }

    const rule = await prisma.automodRule.update({ where: { id }, data: update })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'updated_automod_rule',
      target: rule.name,
    })
    return ok(rule)
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('automod.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.automodRule.findUnique({ where: { id } })
    if (!existing) return apiError('Automod rule not found', 404)

    await prisma.automodRule.delete({ where: { id } })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'deleted_automod_rule',
      target: existing.name,
    })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
