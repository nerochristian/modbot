import { apiError, handleError, ok, requireMutation } from '@/lib/api'
import { disableAutomodRule, updateAutomodRule } from '@/lib/automod-service'
import { recordGuildAudit } from '@/lib/bot-audit'
import { automodRuleSchema } from '@/lib/validation'

export async function PATCH(request: Request, ctx: RouteContext<'/api/automod/[id]'>) {
  try {
    const guard = await requireMutation(request, 'automod.write')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params
    const data = automodRuleSchema.partial().parse(await request.json())
    const updated = await updateAutomodRule(guard.selectedGuildId!, id, data)
    await recordGuildAudit(guard.selectedGuildId!, guard, 'automod.rule.updated', updated.id, data)
    return ok(updated)
  } catch (error) {
    if (error instanceof Error && /not found/i.test(error.message)) return apiError(error.message, 404)
    if (error instanceof Error && /threshold|entries|role IDs|exempt roles/i.test(error.message)) return apiError(error.message, 400)
    return handleError(error)
  }
}

export async function DELETE(request: Request, ctx: RouteContext<'/api/automod/[id]'>) {
  try {
    const guard = await requireMutation(request, 'automod.write')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params
    const canonicalId = await disableAutomodRule(guard.selectedGuildId!, id)
    await recordGuildAudit(guard.selectedGuildId!, guard, 'automod.rule.disabled', canonicalId)
    return ok({ success: true, id: canonicalId })
  } catch (error) {
    if (error instanceof Error && /not found/i.test(error.message)) return apiError(error.message, 404)
    return handleError(error)
  }
}
