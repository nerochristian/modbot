import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok } from '@/lib/api'
import { mergeConfig, type DashboardConfig } from '@/lib/dashboard-config'
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
    const guard = await requireUser('config.write')
    if (guard instanceof Response) return guard
    const user = guard

    const body = (await request.json()) as Partial<DashboardConfig>
    const merged = mergeConfig(body)

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
