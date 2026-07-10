import { cookies, headers } from 'next/headers'
import { prisma } from '@/lib/prisma'
import {
  SESSION_COOKIE,
  signSession,
  sessionExpiryDate,
  sessionMaxAge,
  secureCookies,
} from '@/lib/auth'

/**
 * Server-only session lifecycle helpers. Used by the auth route handlers to
 * create a persisted, revocable session and set the httpOnly cookie, or tear it
 * down on logout.
 */

export async function startSession(user: {
  id: string
  role: string
  name: string
  email: string
}): Promise<void> {
  const jti = crypto.randomUUID()
  const hdrs = await headers()

  await prisma.session.create({
    data: {
      userId: user.id,
      jti,
      expiresAt: sessionExpiryDate(),
      userAgent: hdrs.get('user-agent')?.slice(0, 300) ?? null,
      ip: hdrs.get('x-forwarded-for')?.split(',')[0]?.trim() ?? null,
    },
  })

  const token = await signSession({
    sub: user.id,
    role: user.role,
    jti,
    name: user.name,
    email: user.email,
  })

  const cookieStore = await cookies()
  cookieStore.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: secureCookies(),
    path: '/',
    maxAge: sessionMaxAge(),
  })
}

export async function endSession(jti: string): Promise<void> {
  await prisma.session
    .update({ where: { jti }, data: { revokedAt: new Date() } })
    .catch(() => undefined)
  const cookieStore = await cookies()
  cookieStore.delete(SESSION_COOKIE)
}

/** Revoke every active session for a user (logout everywhere). */
export async function revokeAllSessions(userId: string, exceptJti?: string): Promise<void> {
  await prisma.session.updateMany({
    where: { userId, revokedAt: null, ...(exceptJti ? { jti: { not: exceptJti } } : {}) },
    data: { revokedAt: new Date() },
  })
}
