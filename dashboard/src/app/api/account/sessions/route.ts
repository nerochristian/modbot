import { cookies } from 'next/headers'
import { prisma } from '@/lib/prisma'
import { requireMutation, requireUser, handleError, ok } from '@/lib/api'
import { SESSION_COOKIE, verifySession } from '@/lib/auth'
import { revokeAllSessions } from '@/lib/auth-server'

// GET — active sessions for the current user (marks the current device).
export async function GET() {
  const guard = await requireUser()
  if (guard instanceof Response) return guard
  const user = guard

  const token = (await cookies()).get(SESSION_COOKIE)?.value
  const payload = token ? await verifySession(token) : null

  const sessions = await prisma.session.findMany({
    where: { userId: user.id, revokedAt: null, expiresAt: { gt: new Date() } },
    orderBy: { createdAt: 'desc' },
  })

  return ok({
    sessions: sessions.map((s) => ({
      id: s.id,
      userAgent: s.userAgent,
      ip: s.ip,
      createdAt: s.createdAt.toISOString(),
      current: s.jti === payload?.jti,
    })),
  })
}

// DELETE — sign out of all other devices.
export async function DELETE(request: Request) {
  try {
    const guard = await requireMutation(request)
    if (guard instanceof Response) return guard
    const user = guard

    const token = (await cookies()).get(SESSION_COOKIE)?.value
    const payload = token ? await verifySession(token) : null
    await revokeAllSessions(user.id, payload?.jti)
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
