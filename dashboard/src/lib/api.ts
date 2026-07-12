import { NextResponse } from 'next/server'
import { ZodError } from 'zod'
import { getCurrentUser, type CurrentUser } from '@/lib/session'
import type { Permission } from '@/lib/rbac'

export function ok<T>(data: T, init?: ResponseInit) {
  return NextResponse.json(data, init)
}

export function created<T>(data: T) {
  return NextResponse.json(data, { status: 201 })
}

export function apiError(message: string, status = 400, extra?: Record<string, unknown>) {
  return NextResponse.json({ error: message, ...extra }, { status })
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
  const user = await getCurrentUser()
  if (!user) return apiError('Unauthorized', 401)
  if (permission && !user.selectedGuildId) {
    return apiError('Choose an authorized server workspace first', 409)
  }
  if (permission && !user.permissions.includes(permission)) {
    return apiError('Forbidden', 403)
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
      sameOrigin = Boolean(origin) && new URL(origin as string).origin === new URL(request.url).origin
    } catch {
      sameOrigin = false
    }
    const fetchSite = request.headers.get('sec-fetch-site')
    if (!sameOrigin || (fetchSite && fetchSite !== 'same-origin' && fetchSite !== 'none')) {
      return apiError('Cross-origin mutation rejected', 403)
    }
  }
  return requireUser(permission)
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

export type ListQuery = {
  page: number
  pageSize: number
  sort: string
  order: 'asc' | 'desc'
  q: string
  filters: Record<string, string>
}

/**
 * Parse standard list query params for server-side pagination/sort/filter.
 * Recognized: page, pageSize, sort, order, q. Any `filter.<field>=value` pair
 * is collected into `filters`.
 */
export function parseListQuery(
  url: URL,
  opts?: { defaultSort?: string; maxPageSize?: number },
): ListQuery {
  const sp = url.searchParams
  const page = Math.max(1, Number(sp.get('page')) || 1)
  const maxPageSize = opts?.maxPageSize ?? 100
  const pageSize = Math.min(maxPageSize, Math.max(1, Number(sp.get('pageSize')) || 10))
  const sort = sp.get('sort') || opts?.defaultSort || 'createdAt'
  const order = sp.get('order') === 'asc' ? 'asc' : 'desc'
  const q = (sp.get('q') || '').trim()

  const filters: Record<string, string> = {}
  for (const [key, value] of sp.entries()) {
    if (key.startsWith('filter.') && value) {
      filters[key.slice('filter.'.length)] = value
    }
  }

  return { page, pageSize, sort, order, q, filters }
}

export type Paginated<T> = {
  data: T[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export function paginate<T>(data: T[], total: number, query: ListQuery): Paginated<T> {
  return {
    data,
    page: query.page,
    pageSize: query.pageSize,
    total,
    totalPages: Math.max(1, Math.ceil(total / query.pageSize)),
  }
}
