import { apiError, handleError, ok, requireMutation } from '@/lib/api'
import { reviewGuildAppeal } from '@/lib/appeals-service'
import { appealDecisionSchema } from '@/lib/validation'

export async function PATCH(request: Request, ctx: RouteContext<'/api/appeals/[id]'>) {
  try {
    const guard = await requireMutation(request, 'appeals.write')
    if (guard instanceof Response) return guard
    if (!guard.discordId) return apiError('Reconnect your Discord account', 401)
    const { id } = await ctx.params
    if (!/^\d+$/.test(id)) return apiError('Appeal not found', 404)
    const data = appealDecisionSchema.parse(await request.json())
    const result = await reviewGuildAppeal({
      guildId: guard.selectedGuildId!,
      appealId: id,
      status: data.status,
      decision: data.decision,
      actor: { id: guard.id, discordId: guard.discordId, name: guard.name },
    })
    if (result.kind === 'not_found') return apiError('Appeal not found', 404)
    if (result.kind === 'reviewed') return apiError('Appeal already reviewed', 409)
    return ok(result.appeal)
  } catch (error) {
    if (error instanceof Error && /Discord reversal failed/i.test(error.message)) {
      return apiError('The punishment could not be reversed on Discord. The appeal remains pending.', 502)
    }
    return handleError(error)
  }
}
