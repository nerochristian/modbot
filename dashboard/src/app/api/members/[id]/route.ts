import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { memberSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'

export async function GET(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('members.read')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params

    const member = await prisma.member.findUnique({
      where: { id },
      include: {
        cases: { orderBy: { createdAt: 'desc' }, take: 20 },
        appeals: { orderBy: { submittedAt: 'desc' }, take: 10 },
      },
    })
    if (!member) return apiError('Member not found', 404)
    return ok(member)
  } catch (error) {
    return handleError(error)
  }
}

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('members.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.member.findUnique({ where: { id } })
    if (!existing) return apiError('Member not found', 404)

    const body = await request.json()
    const data = memberSchema.partial().parse(body)

    const member = await prisma.member.update({ where: { id }, data })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'updated_member',
      target: member.displayName,
    })
    return ok(member)
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('members.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.member.findUnique({ where: { id } })
    if (!existing) return apiError('Member not found', 404)

    await prisma.member.delete({ where: { id } })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'removed_member',
      target: existing.displayName,
    })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
