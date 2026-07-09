import { cookies } from 'next/headers'
import { SESSION_COOKIE, verifySession } from '@/lib/auth'
import { endSession } from '@/lib/auth-server'
import { ok } from '@/lib/api'

export async function POST() {
  const cookieStore = await cookies()
  const token = cookieStore.get(SESSION_COOKIE)?.value
  if (token) {
    const payload = await verifySession(token)
    if (payload) await endSession(payload.jti)
    else cookieStore.delete(SESSION_COOKIE)
  }
  return ok({ success: true })
}
