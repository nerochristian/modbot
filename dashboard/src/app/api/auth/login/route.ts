import { prisma } from '@/lib/prisma'
import { verifyPassword } from '@/lib/auth'
import { startSession } from '@/lib/auth-server'
import { loginSchema } from '@/lib/validation'
import { apiError, handleError, ok } from '@/lib/api'
import { parseJson } from '@/lib/json'
import type { DashboardConfig } from '@/lib/dashboard-config'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { email, password } = loginSchema.parse(body)

    const user = await prisma.user.findUnique({
      where: { email: email.toLowerCase() },
      include: { dashboardConfig: true },
    })
    // Constant-ish response to avoid leaking which emails exist.
    if (!user) return apiError('Invalid email or password.', 401)

    const valid = await verifyPassword(password, user.passwordHash)
    if (!valid) return apiError('Invalid email or password.', 401)

    if (user.status === 'suspended') {
      return apiError('Your account has been suspended. Contact an administrator.', 403)
    }

    await prisma.user.update({ where: { id: user.id }, data: { lastLoginAt: new Date() } })
    await startSession({ id: user.id, role: user.role, name: user.name, email: user.email })

    const config = user.dashboardConfig
      ? parseJson<Partial<DashboardConfig>>(user.dashboardConfig.config, {})
      : {}
    const landingPage =
      typeof config.defaultLandingPage === 'string' && config.defaultLandingPage.startsWith('/dashboard')
        ? config.defaultLandingPage
        : '/dashboard'

    return ok({ id: user.id, name: user.name, email: user.email, role: user.role, landingPage })
  } catch (error) {
    return handleError(error)
  }
}
