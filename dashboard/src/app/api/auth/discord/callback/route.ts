import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { startSession } from '@/lib/auth-server'
import { signSession } from '@/lib/auth'

const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID!
const DISCORD_CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET!
const DISCORD_REDIRECT_URI = `${process.env.NEXT_PUBLIC_APP_URL}/api/auth/discord/callback`

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const code = searchParams.get('code')
  const state = searchParams.get('state')
  const storedState = request.headers.get('cookie')?.match(/discord_oauth_state=([^;]+)/)?.[1]

  if (!code || !state || state !== storedState) {
    return NextResponse.redirect(`${process.env.NEXT_PUBLIC_APP_URL}/login?error=invalid_state`)
  }

  // Exchange code for tokens
  const tokenRes = await fetch('https://discord.com/api/oauth2/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: DISCORD_CLIENT_ID,
      client_secret: DISCORD_CLIENT_SECRET,
      grant_type: 'authorization_code',
      code,
      redirect_uri: DISCORD_REDIRECT_URI,
    }),
  })

  if (!tokenRes.ok) {
    return NextResponse.redirect(`${process.env.NEXT_PUBLIC_APP_URL}/login?error=token_exchange`)
  }

  const tokens = await tokenRes.json()
  const accessToken = tokens.access_token
  const refreshToken = tokens.refresh_token
  const expiresIn = tokens.expires_in

  // Fetch user profile
  const userRes = await fetch('https://discord.com/api/users/@me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!userRes.ok) {
    return NextResponse.redirect(`${process.env.NEXT_PUBLIC_APP_URL}/login?error=user_fetch`)
  }
  const discordUser = await userRes.json()

  // Upsert user (Discord-first)
  const user = await prisma.user.upsert({
    where: { discordId: discordUser.id },
    update: {
      discordUsername: discordUser.username,
      discordAvatar: discordUser.avatar
        ? `https://cdn.discordapp.com/avatars/${discordUser.id}/${discordUser.avatar}.png`
        : null,
      discordAccessToken: accessToken,
      discordRefreshToken: refreshToken,
      discordTokenExpiresAt: new Date(Date.now() + expiresIn * 1000),
      lastLoginAt: new Date(),
    },
    create: {
      discordId: discordUser.id,
      discordUsername: discordUser.username,
      discordAvatar: discordUser.avatar
        ? `https://cdn.discordapp.com/avatars/${discordUser.id}/${discordUser.avatar}.png`
        : null,
      name: discordUser.global_name || discordUser.username,
      email: null,
      passwordHash: null,
      discordAccessToken: accessToken,
      discordRefreshToken: refreshToken,
      discordTokenExpiresAt: new Date(Date.now() + expiresIn * 1000),
      lastLoginAt: new Date(),
    },
  })

  // Start session
  await startSession({
    id: user.id,
    role: user.role,
    name: user.name,
    email: user.email || '',
  })

  // Clear state cookie
  const response = NextResponse.redirect(`${process.env.NEXT_PUBLIC_APP_URL}/dashboard/servers`)
  response.cookies.delete('discord_oauth_state')
  return response
}
