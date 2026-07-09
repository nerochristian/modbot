import { NextResponse } from 'next/server'
import { randomBytes } from 'crypto'

const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID!
const DISCORD_REDIRECT_URI = `${process.env.NEXT_PUBLIC_APP_URL}/api/auth/discord/callback`
const DISCORD_SCOPES = ['identify', 'guilds'].join(' ')

export async function GET() {
  if (!DISCORD_CLIENT_ID) {
    return NextResponse.json({ error: 'Discord OAuth not configured' }, { status: 500 })
  }

  const state = randomBytes(16).toString('hex')

  const params = new URLSearchParams({
    client_id: DISCORD_CLIENT_ID,
    redirect_uri: DISCORD_REDIRECT_URI,
    response_type: 'code',
    scope: DISCORD_SCOPES,
    state,
  })

  // Store state in a short-lived cookie for CSRF protection (production: use Redis or signed cookie)
  const response = NextResponse.redirect(
    `https://discord.com/api/oauth2/authorize?${params.toString()}`
  )

  response.cookies.set('discord_oauth_state', state, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 600, // 10 minutes
    path: '/',
  })

  return response
}
