import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { customerSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('customers.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.customer.findUnique({ where: { id } })
    if (!existing) return apiError('Customer not found', 404)

    const body = await request.json()
    const data = customerSchema.partial().parse(body)

    const customer = await prisma.customer.update({
      where: { id },
      data: {
        ...data,
        email: data.email ? data.email.toLowerCase() : undefined,
      },
    })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'updated_customer',
      target: customer.name,
    })
    return ok(customer)
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireUser('customers.write')
    if (guard instanceof Response) return guard
    const user = guard
    const { id } = await ctx.params

    const existing = await prisma.customer.findUnique({ where: { id } })
    if (!existing) return apiError('Customer not found', 404)

    await prisma.customer.delete({ where: { id } })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'deleted_customer',
      target: existing.name,
    })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
