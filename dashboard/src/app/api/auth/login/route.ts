import { prisma } from '@/lib/prisma'
import { verifyPassword } from '@/lib/auth'
import { startSession } from '@/lib/auth-server'
import { loginSchema } from '@/lib/validation'
import { apiError, handleError, ok } from '@/lib/api'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { email, password } = loginSchema.parse(body)

    const user = await prisma.user.findUnique({ where: { email: email.toLowerCase() } })
    // Constant-ish response to avoid leaking which emails exist.
    if (!user) return apiError('Invalid email or password.', 401)

    const valid = await verifyPassword(password, user.passwordHash)
    if (!valid) return apiError('Invalid email or password.', 401)

    if (user.status === 'suspended') {
      return apiError('Your account has been suspended. Contact an administrator.', 403)
    }

    await prisma.user.update({ where: { id: user.id }, data: { lastLoginAt: new Date() } })
    await startSession({ id: user.id, role: user.role, name: user.name, email: user.email })

    return ok({ id: user.id, name: user.name, email: user.email, role: user.role })
  } catch (error) {
    return handleError(error)
  }
}
