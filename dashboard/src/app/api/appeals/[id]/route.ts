import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { appealDecisionSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('appeals.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.appeal.findUnique({ where: { id }, include: { case: true } })
    if (!existing) return apiError('Appeal not found', 404)
    if (existing.status !== 'pending') return apiError('Appeal already reviewed', 409)

    const body = await request.json()
    const data = appealDecisionSchema.parse(body)

    const updated = await prisma.appeal.update({
      where: { id },
      data: {
        status: data.status,
        decision: data.decision ?? null,
        reviewedBy: user.name,
        reviewedAt: new Date(),
      },
    })

    // Closing the appeal resolves the linked case either way. An approved appeal
    // additionally restores the member's standing for enforcement-type cases.
    await prisma.case.update({ where: { id: existing.caseId }, data: { status: 'resolved' } })
    if (data.status === 'approved' && ['ban', 'mute', 'timeout'].includes(existing.case.type)) {
      await prisma.member.update({ where: { id: existing.memberId }, data: { standing: 'good' } })
    }

    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'reviewed_appeal',
      target: `#APL-${String(existing.ref).padStart(4, '0')}`,
    })
    return ok(updated)
  } catch (error) {
    return handleError(error)
  }
}
