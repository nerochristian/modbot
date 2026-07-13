import { apiError, handleError, ok, requireMutation } from '@/lib/api'
import { deleteGuildReport } from '@/lib/reports-service'

export async function DELETE(request: Request, ctx: RouteContext<'/api/reports/[id]'>) {
  try {
    const guard = await requireMutation(request, 'reports.write')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params
    if (!/^\d+$/.test(id)) return apiError('Report not found', 404)
    const deleted = await deleteGuildReport(guard.selectedGuildId!, guard.id, guard.name, id)
    if (!deleted) return apiError('Report not found', 404)
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
