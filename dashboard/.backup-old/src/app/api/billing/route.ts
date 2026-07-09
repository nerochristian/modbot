import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok } from '@/lib/api'
import { logActivity, logAudit } from '@/lib/log'
import { z } from 'zod'

const PLAN_PRICES: Record<string, number> = { starter: 2900, pro: 9900, enterprise: 49900 }

export async function GET() {
  try {
    const guard = await requireUser('billing.read')
    if (guard instanceof Response) return guard
    const user = guard

    const [subscription, invoices] = await Promise.all([
      prisma.subscription.findUnique({ where: { userId: user.id } }),
      prisma.invoice.findMany({ where: { userId: user.id }, orderBy: { issuedAt: 'desc' }, take: 24 }),
    ])

    return ok({
      subscription: subscription
        ? {
            plan: subscription.plan,
            status: subscription.status,
            seats: subscription.seats,
            interval: subscription.interval,
            amount: subscription.amount,
            currentPeriodEnd: subscription.currentPeriodEnd.toISOString(),
            cancelAtPeriodEnd: subscription.cancelAtPeriodEnd,
          }
        : null,
      invoices: invoices.map((i) => ({
        id: i.id,
        number: i.number,
        amount: i.amount,
        status: i.status,
        issuedAt: i.issuedAt.toISOString(),
      })),
    })
  } catch (error) {
    return handleError(error)
  }
}

const patchSchema = z.object({
  plan: z.enum(['starter', 'pro', 'enterprise']).optional(),
  interval: z.enum(['month', 'year']).optional(),
  cancelAtPeriodEnd: z.boolean().optional(),
})

export async function PATCH(request: Request) {
  try {
    const guard = await requireUser('billing.write')
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const data = patchSchema.parse(body)

    const existing = await prisma.subscription.findUnique({ where: { userId: user.id } })
    const nextPlan = data.plan ?? existing?.plan ?? 'pro'
    const nextInterval = data.interval ?? existing?.interval ?? 'month'

    const subscription = await prisma.subscription.upsert({
      where: { userId: user.id },
      create: {
        userId: user.id,
        plan: nextPlan,
        interval: nextInterval,
        amount: PLAN_PRICES[nextPlan],
        status: 'active',
        currentPeriodEnd: new Date(Date.now() + 30 * 86_400_000),
      },
      update: {
        plan: nextPlan,
        interval: nextInterval,
        amount: PLAN_PRICES[nextPlan],
        cancelAtPeriodEnd: data.cancelAtPeriodEnd ?? existing?.cancelAtPeriodEnd ?? false,
        status: data.cancelAtPeriodEnd ? existing?.status ?? 'active' : 'active',
      },
    })

    const action = data.cancelAtPeriodEnd !== undefined
      ? data.cancelAtPeriodEnd ? 'canceled_subscription' : 'reactivated_subscription'
      : 'changed_plan'
    await logActivity({ userId: user.id, actorName: user.name, action, target: nextPlan })
    await logAudit({ userId: user.id, actorName: user.name, action: `billing.${action}`, entity: 'Subscription', entityId: subscription.id })

    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
