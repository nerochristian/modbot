import { createHash, randomBytes } from 'node:crypto'
import { NextResponse, type NextRequest } from 'next/server'
import { safeReturnPath, secureCookies } from '@/lib/auth'
import { discordRedirectUri } from '@/lib/discord'

const DISCORD_SCOPES = ['identify', 'email', 'guilds'].join(' ')

export async function GET(request: NextRequest) {
  const clientId = process.env.DISCORD_CLIENT_ID?.trim()
  if (!clientId) return NextResponse.json({ error: 'Discord OAuth not configured' }, { status: 500 })

  const state = randomBytes(16).toString('hex')
  const codeVerifier = randomBytes(48).toString('base64url')
  const codeChallenge = createHash('sha256').update(codeVerifier).digest('base64url')
  const requestedNext = request.nextUrl.searchParams.get('next')
  const next = safeReturnPath(requestedNext)
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: discordRedirectUri(request.url),
    response_type: 'code',
    scope: DISCORD_SCOPES,
    state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
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
  response.cookies.set('discord_oauth_pkce', codeVerifier, {
    httpOnly: true,
    sameSite: 'lax',
    secure: secureCookies(),
    maxAge: 600,
    path: '/',
    priority: 'high',
  })
  return response
}
