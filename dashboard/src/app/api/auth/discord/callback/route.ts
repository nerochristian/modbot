import { randomBytes, timingSafeEqual } from 'node:crypto'
import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'
import { prisma } from '@/lib/prisma'
import { hashPassword } from '@/lib/auth'
import { startSession } from '@/lib/auth-server'
import { DEFAULT_DASHBOARD_CONFIG } from '@/lib/dashboard-config'
import {
  discordRedirectUri,
  exchangeDiscordCode,
  fetchDiscordUser,
  sealDiscordToken,
} from '@/lib/discord'

function sameState(actual: string | null, expected: string | undefined): boolean {
  if (!actual || !expected) return false
  const a = Buffer.from(actual)
  const b = Buffer.from(expected)
  return a.length === b.length && timingSafeEqual(a, b)
}

function authError(request: NextRequest, message: string) {
  const url = new URL('/login', request.url)
  url.searchParams.set('error', message)
  return NextResponse.redirect(url)
}

export async function GET(request: NextRequest) {
  const cookieStore = await cookies()
  const state = request.nextUrl.searchParams.get('state')
  const expectedState = cookieStore.get('discord_oauth_state')?.value
  const oauthError = request.nextUrl.searchParams.get('error')
  const code = request.nextUrl.searchParams.get('code')

  if (oauthError) return authError(request, 'Discord sign-in was cancelled.')
  if (!sameState(state, expectedState)) return authError(request, 'Discord sign-in expired. Please try again.')
  if (!code) return authError(request, 'Discord did not return an authorization code.')

  try {
    const tokens = await exchangeDiscordCode(code, discordRedirectUri(request.url))
    const profile = await fetchDiscordUser(tokens.access_token)
    const email = profile.email?.trim().toLowerCase() || `${profile.id}@discord.invalid`
    const displayName = profile.global_name?.trim() || profile.username
    const ownerIds = new Set(
      (process.env.OWNER_IDS || '').split(',').map((value) => value.trim()).filter(Boolean),
    )

    const existingByDiscord = await prisma.user.findUnique({ where: { discordId: profile.id } })
    const existingByEmail = existingByDiscord
      ? null
      : await prisma.user.findUnique({ where: { email } })
    const existing = existingByDiscord ?? existingByEmail
    const tokenData = {
      discordId: profile.id,
      discordUsername: profile.username,
      discordGlobalName: profile.global_name,
      discordAvatar: profile.avatar,
      discordAccessToken: sealDiscordToken(tokens.access_token),
      discordRefreshToken: tokens.refresh_token ? sealDiscordToken(tokens.refresh_token) : null,
      discordTokenExpiresAt: new Date(Date.now() + tokens.expires_in * 1000),
      email,
      emailVerified: Boolean(profile.verified),
      name: displayName,
      status: 'active',
      lastLoginAt: new Date(),
    }

    const user = existing
      ? await prisma.user.update({
          where: { id: existing.id },
          data: { ...tokenData, role: ownerIds.has(profile.id) ? 'admin' : existing.role },
        })
      : await prisma.user.create({
          data: {
            ...tokenData,
            passwordHash: await hashPassword(randomBytes(48).toString('base64url')),
            role: ownerIds.has(profile.id) ? 'admin' : 'manager',
            dashboardConfig: { create: { config: JSON.stringify(DEFAULT_DASHBOARD_CONFIG) } },
          },
        })

    await prisma.dashboardConfig.upsert({
      where: { userId: user.id },
      update: {},
      create: { userId: user.id, config: JSON.stringify(DEFAULT_DASHBOARD_CONFIG) },
    })
    await startSession({ id: user.id, role: user.role, name: user.name, email: user.email })

    const nextCookie = cookieStore.get('discord_oauth_next')?.value
    const next = nextCookie?.startsWith('/') && !nextCookie.startsWith('//') ? nextCookie : '/servers'
    cookieStore.delete('discord_oauth_state')
    cookieStore.delete('discord_oauth_next')
    cookieStore.delete('aegis_guild')
    return NextResponse.redirect(new URL(next, request.url))
  } catch (error) {
    console.error('[auth.discord.callback]', error instanceof Error ? error.message : error)
    return authError(request, 'Discord sign-in failed. Please try again.')
  }
}
