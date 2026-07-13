import { NextResponse } from 'next/server'
import { ZodError } from 'zod'
import { getCurrentUser, refreshSelectedGuildAuthority, type CurrentUser } from '@/lib/session'
import { DiscordReauthRequiredError, getManageableGuilds } from '@/lib/discord'
import type { Permission } from '@/lib/rbac'

export { paginate, parseListQuery } from '@/lib/list-query'
export type { ListQuery, Paginated } from '@/lib/list-query'

export function ok<T>(data: T, init?: ResponseInit) {
  return NextResponse.json(data, init)
}

export function created<T>(data: T) {
  return NextResponse.json(data, { status: 201 })
}

export function apiError(message: string, status = 400, extra?: Record<string, unknown>) {
  return NextResponse.json({ error: message, ...extra }, { status })
}

function discordAuthorityError(error: unknown): NextResponse {
  return error instanceof DiscordReauthRequiredError
    ? apiError('Discord authorization must be refreshed', 401)
    : apiError('Discord is temporarily unavailable; try again shortly', 503)
}

/**
 * Guard for route handlers. Returns the authenticated user, or a Response to
 * return immediately. Optionally enforces a permission.
 *
 *   const guard = await requireUser('users.write')
 *   if (guard instanceof NextResponse) return guard
 *   const user = guard
 */
export async function requireUser(
  permission?: Permission,
): Promise<CurrentUser | NextResponse> {
  let user = await getCurrentUser()
  if (!user) return apiError('Unauthorized', 401)
  if (permission) {
    if (!user.selectedGuildId) return apiError('Choose an authorized server workspace first', 409)
    try {
      // getManageableGuilds uses a short server-side cache and synchronizes
      // Discord removals, role changes, OAuth revocation, and bot uninstalls.
      await getManageableGuilds(user.id)
    } catch (error) {
      return discordAuthorityError(error)
    }
    user = await refreshSelectedGuildAuthority(user)
    if (!user.selectedGuildId) return apiError('Server workspace access is no longer valid', 403)
    if (!user.permissions.includes(permission)) return apiError('Forbidden', 403)
  }
  return user
}

/** Require a same-origin browser mutation before applying the normal auth/RBAC guard. */
export async function requireMutation(
  request: Request,
  permission?: Permission,
): Promise<CurrentUser | NextResponse> {
  const method = request.method.toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const origin = request.headers.get('origin')
    let sameOrigin = false
    try {
      const allowedOrigins = new Set([new URL(request.url).origin])
      for (const candidate of [
        process.env.DASHBOARD_PUBLIC_URL,
        process.env.FRONTEND_PUBLIC_URL,
        process.env.NEXT_PUBLIC_APP_URL,
        process.env.NEXT_PUBLIC_BASE_URL,
      ]) {
        if (!candidate) continue
        try {
          allowedOrigins.add(new URL(candidate).origin)
        } catch {
          // Invalid deployment URLs are ignored rather than weakening the check.
        }
      }
      sameOrigin = Boolean(origin) && allowedOrigins.has(new URL(origin as string).origin)
    } catch {
      sameOrigin = false
    }
    const fetchSite = request.headers.get('sec-fetch-site')
    if (!sameOrigin || (fetchSite && fetchSite !== 'same-origin' && fetchSite !== 'none')) {
      return apiError('Cross-origin mutation rejected', 403)
    }
  }
  const initial = await requireUser()
  if (initial instanceof NextResponse || !permission) return initial
  if (!initial.selectedGuildId) return apiError('Choose an authorized server workspace first', 409)
  try {
    await getManageableGuilds(initial.id, true)
  } catch (error) {
    return discordAuthorityError(error)
  }
  const user = await refreshSelectedGuildAuthority(initial)
  if (!user.selectedGuildId) return apiError('Server workspace access is no longer valid', 403)
  if (!user.permissions.includes(permission)) return apiError('Forbidden', 403)
  return user
}

/** Translate common thrown errors into clean JSON responses. */
export function handleError(error: unknown) {
  if (error instanceof ZodError) {
    return NextResponse.json(
      { error: 'Validation failed', issues: error.issues },
      { status: 422 },
    )
  }
  console.error(error)
  return apiError('Internal server error', 500)
}
