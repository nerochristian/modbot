import { NextResponse, type NextRequest } from 'next/server'
import { SESSION_COOKIE, verifySession } from '@/lib/auth'

// Next.js 16 renamed `middleware` to `proxy` (nodejs runtime). This is a
// lightweight gate: it checks the session JWT signature only — no database —
// and redirects unauthenticated users away from /dashboard, and authenticated
// users away from the auth pages. Full, revocation-aware checks happen in
// getCurrentUser() inside the protected pages and API routes.

const AUTH_PAGES = ['/login', '/register']

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get(SESSION_COOKIE)?.value
  const session = token ? await verifySession(token) : null

  const isProtected = pathname.startsWith('/dashboard') || pathname.startsWith('/servers')
  const isAuthPage = AUTH_PAGES.some((p) => pathname === p || pathname.startsWith(`${p}/`))

  if (isProtected && !session) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    url.searchParams.set('next', pathname)
    return NextResponse.redirect(url)
  }

  if (isAuthPage && session) {
    const url = request.nextUrl.clone()
    url.pathname = '/servers'
    url.search = ''
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/servers/:path*', '/login', '/register'],
}
