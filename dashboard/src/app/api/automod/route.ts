import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, created, parseListQuery } from '@/lib/api'
import { automodRuleSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'
import type { Prisma } from '@prisma/client'

export async function GET(request: Request) {
  try {
    const guard = await requireUser('automod.read')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const query = parseListQuery(url)

    const where: Prisma.AutomodRuleWhereInput = {}
    if (query.filters.trigger) where.trigger = query.filters.trigger
    if (query.filters.enabled) where.enabled = query.filters.enabled === 'true'

    const rows = await prisma.automodRule.findMany({
      where,
      orderBy: [{ enabled: 'desc' }, { hits: 'desc' }],
    })

    const rules = rows.map((rule) => ({
      ...rule,
      exemptRoles: JSON.parse(rule.exemptRoles || '[]') as string[],
    }))
    const totalHits = rules.reduce((sum, r) => sum + r.hits, 0)
    const activeCount = rules.filter((r) => r.enabled).length

    return ok({ data: rules, totalHits, activeCount })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireUser('automod.write')
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const data = automodRuleSchema.parse(body)

    const rule = await prisma.automodRule.create({
      data: {
        name: data.name,
        description: data.description ?? null,
        trigger: data.trigger,
        pattern: data.pattern ?? null,
        action: data.action,
        severity: data.severity,
        exemptRoles: JSON.stringify(data.exemptRoles ?? []),
        enabled: data.enabled ?? true,
      },
    })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'created_automod_rule',
      target: data.name,
    })
    return created(rule)
  } catch (error) {
    return handleError(error)
  }
}
