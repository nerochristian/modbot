import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { logActivity } from '@/lib/log'

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('reports.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const report = await prisma.report.findUnique({ where: { id } })
    if (!report) return apiError('Report not found', 404)

    await prisma.report.delete({ where: { id } })
    await logActivity({ userId: user.id, actorName: user.name, action: 'deleted_report', target: report.name })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
