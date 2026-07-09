import { prisma } from '@/lib/prisma'
import { hashPassword } from '@/lib/auth'
import { startSession } from '@/lib/auth-server'
import { registerSchema } from '@/lib/validation'
import { apiError, created, handleError } from '@/lib/api'
import { parseJson } from '@/lib/json'
import { logActivity } from '@/lib/log'
import { DEFAULT_DASHBOARD_CONFIG } from '@/lib/dashboard-config'
import { isRole } from '@/lib/rbac'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { name, email, password } = registerSchema.parse(body)

    const signupsSetting = await prisma.appSetting.findUnique({ where: { key: 'app.signupsEnabled' } })
    if (signupsSetting && parseJson<boolean>(signupsSetting.value, true) === false) {
      return apiError('Sign-ups are currently disabled.', 403)
    }

    const existing = await prisma.user.findUnique({ where: { email: email.toLowerCase() } })
    if (existing) {
      return apiError('An account with that email already exists.', 409)
    }

    const defaultRoleSetting = await prisma.appSetting.findUnique({ where: { key: 'app.defaultRole' } })
    const defaultRole = parseJson<string>(defaultRoleSetting?.value, 'viewer')
    const role = isRole(defaultRole) ? defaultRole : 'viewer'

    const user = await prisma.user.create({
      data: {
        name,
        email: email.toLowerCase(),
        passwordHash: await hashPassword(password),
        role,
        status: 'active',
        dashboardConfig: {
          create: { config: JSON.stringify(DEFAULT_DASHBOARD_CONFIG) },
        },
      },
    })

    await startSession({ id: user.id, role: user.role, name: user.name, email: user.email })
    await logActivity({ userId: user.id, actorName: user.name, action: 'account_created' })

    return created({ id: user.id, name: user.name, email: user.email, role: user.role })
  } catch (error) {
    return handleError(error)
  }
}
