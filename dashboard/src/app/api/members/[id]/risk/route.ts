import { handleError, ok, requireUser } from '@/lib/api'
import { getRiskBreakdown, explainRisk } from '@/lib/risk-service'

export async function GET(_request: Request, ctx: RouteContext<'/api/members/[id]/risk'>) {
  try {
    const guard = await requireUser('members.read')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params
    const breakdown = await getRiskBreakdown(guard.selectedGuildId!, id)
    return ok(breakdown)
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(_request: Request, ctx: RouteContext<'/api/members/[id]/risk'>) {
  try {
    const guard = await requireUser('members.read')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params
    const breakdown = await getRiskBreakdown(guard.selectedGuildId!, id)
    const explanation = await explainRisk(breakdown)
    return ok({ ...breakdown, explanation })
  } catch (error) {
    return handleError(error)
  }
}
