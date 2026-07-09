import { getCurrentUser } from '@/lib/session'
import { ok } from '@/lib/api'

export async function GET() {
  const user = await getCurrentUser()
  return ok({ user })
}
