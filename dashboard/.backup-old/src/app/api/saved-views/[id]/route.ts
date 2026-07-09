import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('config.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const view = await prisma.savedView.findUnique({ where: { id } })
    if (!view || view.userId !== user.id) return apiError('Not found', 404)

    await prisma.savedView.delete({ where: { id } })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
