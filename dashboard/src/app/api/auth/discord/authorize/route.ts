import { randomBytes } from 'node:crypto'
import { NextResponse, type NextRequest } from 'next/server'
import { secureCookies } from '@/lib/auth'
import { discordRedirectUri } from '@/lib/discord'

const DISCORD_SCOPES = ['identify', 'email', 'guilds'].join(' ')

export async function GET(request: NextRequest) {
  const clientId = process.env.DISCORD_CLIENT_ID?.trim()
  if (!clientId) return NextResponse.json({ error: 'Discord OAuth not configured' }, { status: 500 })

  const state = randomBytes(16).toString('hex')
  const requestedNext = request.nextUrl.searchParams.get('next')
  const next = requestedNext?.startsWith('/') && !requestedNext.startsWith('//')
    ? requestedNext
    : '/servers'
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: discordRedirectUri(request.url),
    response_type: 'code',
    scope: DISCORD_SCOPES,
    state,
  })
  const response = NextResponse.redirect(`https://discord.com/oauth2/authorize?${params}`)
  response.cookies.set('discord_oauth_state', state, {
    httpOnly: true,
    sameSite: 'lax',
    secure: secureCookies(),
    maxAge: 600,
    path: '/',
    priority: 'high',
  })
  response.cookies.set('discord_oauth_next', next, {
    httpOnly: true,
    sameSite: 'lax',
    secure: secureCookies(),
    maxAge: 600,
    path: '/',
  })
  return response
}
