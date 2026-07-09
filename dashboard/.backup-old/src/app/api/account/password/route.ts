import { cookies } from 'next/headers'
import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, apiError } from '@/lib/api'
import { changePasswordSchema } from '@/lib/validation'
import { hashPassword, verifyPassword, SESSION_COOKIE, verifySession } from '@/lib/auth'
import { revokeAllSessions } from '@/lib/auth-server'
import { logAudit } from '@/lib/log'

export async function PATCH(request: Request) {
  try {
    const guard = await requireUser()
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const { currentPassword, newPassword } = changePasswordSchema.parse(body)

    const record = await prisma.user.findUnique({ where: { id: user.id } })
    if (!record) return apiError('User not found', 404)

    const valid = await verifyPassword(currentPassword, record.passwordHash)
    if (!valid) return apiError('Your current password is incorrect.', 400)

    await prisma.user.update({
      where: { id: user.id },
      data: { passwordHash: await hashPassword(newPassword) },
    })

    // Revoke all other sessions after a password change; keep the current one.
    const token = (await cookies()).get(SESSION_COOKIE)?.value
    const payload = token ? await verifySession(token) : null
    await revokeAllSessions(user.id, payload?.jti)

    await logAudit({ userId: user.id, actorName: user.name, action: 'password.change', entity: 'User', entityId: user.id })
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
