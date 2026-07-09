import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { updateCaseSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('cases.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.case.findUnique({ where: { id } })
    if (!existing) return apiError('Case not found', 404)

    const body = await request.json()
    const data = updateCaseSchema.parse(body)

    const updated = await prisma.case.update({ where: { id }, data })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'updated_case',
      target: `#CASE-${String(existing.ref).padStart(4, '0')}`,
    })
    return ok(updated)
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('cases.delete')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.case.findUnique({ where: { id } })
    if (!existing) return apiError('Case not found', 404)

    await prisma.case.delete({ where: { id } })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'deleted_case',
      target: `#CASE-${String(existing.ref).padStart(4, '0')}`,
    })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
