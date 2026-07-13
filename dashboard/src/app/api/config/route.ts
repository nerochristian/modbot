import { prisma } from '@/lib/prisma'
import { requireMutation, requireUser, handleError, ok } from '@/lib/api'
import { dashboardConfigPatchSchema, mergeConfig, type DashboardConfig } from '@/lib/dashboard-config'
import { parseJson } from '@/lib/json'

export async function GET() {
  const guard = await requireUser()
  if (guard instanceof Response) return guard
  const user = guard

  const row = await prisma.dashboardConfig.findUnique({ where: { userId: user.id } })
  const config = mergeConfig(row ? parseJson<Partial<DashboardConfig>>(row.config, {}) : null)
  return ok({ config })
}

export async function PATCH(request: Request) {
  try {
    const guard = await requireMutation(request)
    if (guard instanceof Response) return guard
    const user = guard

    const patch = dashboardConfigPatchSchema.parse(await request.json())
    const existing = await prisma.dashboardConfig.findUnique({ where: { userId: user.id } })
    const current = existing
      ? parseJson<Partial<DashboardConfig>>(existing.config, {})
      : {}
    const merged = mergeConfig({
      ...current,
      ...patch,
      notifications: {
        billing: { ...current.notifications?.billing, ...patch.notifications?.billing },
        security: { ...current.notifications?.security, ...patch.notifications?.security },
        product: { ...current.notifications?.product, ...patch.notifications?.product },
        mentions: { ...current.notifications?.mentions, ...patch.notifications?.mentions },
      } as DashboardConfig['notifications'],
    })

    await prisma.dashboardConfig.upsert({
      where: { userId: user.id },
      create: { userId: user.id, config: JSON.stringify(merged) },
      update: { config: JSON.stringify(merged) },
    })

    return ok({ config: merged })
  } catch (error) {
    return handleError(error)
  }
}
