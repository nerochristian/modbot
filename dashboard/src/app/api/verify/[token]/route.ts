import { createHash, randomUUID } from 'node:crypto'
import { apiError, ok } from '@/lib/api'
import { getBotGuildSettings } from '@/lib/bot-settings'
import { botQuery } from '@/lib/bot-db'
import {
  dashboardBaseUrl,
  discordMemberAvatarUrl,
  sendBotChannelEmbed,
  type DiscordGuildMember,
} from '@/lib/discord'
import { verifyVerificationCapability } from '@/lib/web-verification'

const DISCORD_API = 'https://discord.com/api/v10'
const attempts = new Map<string, { count: number; resetAt: number }>()

type TurnstileResponse = { success: boolean; action?: string; hostname?: string; 'error-codes'?: string[] }

const TURNSTILE_ACTION = 'verify'
const MAX_TURNSTILE_TOKEN_LENGTH = 2_048
const MAX_REQUEST_BYTES = 16_384
function clientAddress(request: Request): string {
  return request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown'
}

function rateLimit(request: Request): boolean {
  const key = createHash('sha256').update(clientAddress(request)).digest('hex')
  const now = Date.now()
  const current = attempts.get(key)
  if (!current || current.resetAt <= now) {
    attempts.set(key, { count: 1, resetAt: now + 10 * 60_000 })
    return false
  }
  current.count += 1
  return current.count > 10
}

async function discord(path: string, init: RequestInit = {}): Promise<Response> {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  return fetch(`${DISCORD_API}${path}`, {
    ...init,
    headers: { Authorization: `Bot ${token}`, ...init.headers },
    cache: 'no-store',
  })
}

export async function POST(request: Request, context: { params: Promise<{ token: string }> }) {
  let nonce = ''
  try {
    if (rateLimit(request)) return apiError('Too many verification attempts. Wait a few minutes and try again.', 429)
    const expectedOrigin = new URL(dashboardBaseUrl(request.url)).origin
    if (request.headers.get('origin') !== expectedOrigin) return apiError('Verification request rejected.', 403)
    if (Number(request.headers.get('content-length') || 0) > MAX_REQUEST_BYTES) return apiError('Request is too large.', 413)

    const { token } = await context.params
    const capability = verifyVerificationCapability(token)
    nonce = capability.n
    const body = await request.json() as { challenge?: unknown }
    if (
      typeof body.challenge !== 'string'
      || body.challenge.length < 10
      || body.challenge.length > MAX_TURNSTILE_TOKEN_LENGTH
    ) {
      return apiError('Complete the human check before continuing.', 400)
    }

    const settings = await getBotGuildSettings(capability.g)
    if (!settings.verification_enabled || settings.verification_method !== 'website') {
      return apiError('Website verification is not active for this server.', 409)
    }
    const secret = process.env.TURNSTILE_SECRET_KEY?.trim()
    if (!secret) return apiError('Website verification is not configured.', 503)
    const form = new URLSearchParams({
      secret,
      response: body.challenge,
      idempotency_key: randomUUID(),
    })
    const remoteAddress = clientAddress(request)
    if (remoteAddress !== 'unknown') form.set('remoteip', remoteAddress)
    const turnstileResponse = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
      cache: 'no-store',
      signal: AbortSignal.timeout(8_000),
    })
    if (!turnstileResponse.ok) throw new Error(`Turnstile validation failed (${turnstileResponse.status})`)
    const turnstile = await turnstileResponse.json() as TurnstileResponse
    const expectedHostname = new URL(dashboardBaseUrl(request.url)).hostname
    const actionOk = turnstile.action === TURNSTILE_ACTION
    const hostOk = turnstile.hostname === expectedHostname
    if (!turnstile.success || !actionOk || !hostOk) {
      return apiError('The human check was not accepted. Refresh the page and try again.', 400)
    }

    await botQuery(`CREATE TABLE IF NOT EXISTS web_verification_consumptions (
      nonce text PRIMARY KEY,
      guild_id bigint NOT NULL,
      user_id bigint NOT NULL,
      completed_at timestamptz NOT NULL DEFAULT now()
    )`)
    const reserved = await botQuery<{ nonce: string }>(
      `INSERT INTO web_verification_consumptions (nonce, guild_id, user_id)
       VALUES ($1, $2::bigint, $3::bigint)
       ON CONFLICT (nonce) DO NOTHING RETURNING nonce`,
      [nonce, capability.g, capability.u],
    )
    if (reserved.length === 0) return apiError('This verification link has already been used.', 409)

    const memberResponse = await discord(`/guilds/${capability.g}/members/${capability.u}`)
    if (!memberResponse.ok) throw new Error(`Discord member lookup failed (${memberResponse.status})`)
    const member = await memberResponse.json() as DiscordGuildMember
    if (member.user.bot) return apiError('Bot accounts cannot complete member verification.', 403)
    const verifiedRole = String(settings.verified_role ?? settings.verification_role ?? '')
    const unverifiedRole = String(settings.unverified_role ?? '')
    if (!/^\d{15,22}$/.test(verifiedRole) || !/^\d{15,22}$/.test(unverifiedRole)) {
      throw new Error('Verification roles are not configured')
    }

    const finalRoles = [...new Set([
      ...(member.roles ?? []).filter((roleId) => roleId !== unverifiedRole),
      verifiedRole,
    ])]
    const roleUpdate = await discord(`/guilds/${capability.g}/members/${capability.u}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-Audit-Log-Reason': encodeURIComponent('Website verification passed'),
      },
      body: JSON.stringify({ roles: finalRoles }),
    })
    if (!roleUpdate.ok) throw new Error(`Discord rejected the verification role update (${roleUpdate.status})`)
    const updatedMember = await roleUpdate.json() as DiscordGuildMember
    const updatedRoles = new Set(updatedMember.roles ?? [])
    if (!updatedRoles.has(verifiedRole) || updatedRoles.has(unverifiedRole)) {
      throw new Error('Discord did not persist the final verification role state')
    }

    const createdAt = Number((BigInt(capability.u) >> BigInt(22)) + BigInt(1420070400000))
    const accountAgeDays = Math.max(0, Math.floor((Date.now() - createdAt) / 86_400_000))
    const logChannel = String(settings.verify_log_channel ?? settings.verification_log_channel ?? '')
    if (/^\d{15,22}$/.test(logChannel)) {
      const avatarUrl = discordMemberAvatarUrl(capability.g, updatedMember)
      const username = updatedMember.user.username
      await sendBotChannelEmbed(logChannel, {
        title: 'Verification complete',
        description: [
          `> **User:** ${username} (<@${capability.u}>)`,
          `> **Account created:** <t:${Math.floor(createdAt / 1000)}:R>`,
          `> **Method:** Website`,
          `> **Status:** Verified`,
          `> **Account age:** ${accountAgeDays} day(s)`,
          `> **Roles:** Added <@&${verifiedRole}>, removed <@&${unverifiedRole}>`,
        ].join('\n'),
        color: 0x22c55e,
        timestamp: new Date().toISOString(),
        thumbnail: { url: avatarUrl },
        footer: { text: `@${username}`, icon_url: avatarUrl },
      }).catch((error) => console.error('Failed to send website verification log', error))
    }
    return ok({ verified: true })
  } catch (error) {
    if (nonce) await botQuery('DELETE FROM web_verification_consumptions WHERE nonce = $1', [nonce]).catch(() => undefined)
    if (error instanceof SyntaxError) return apiError('Request body must be valid JSON.', 400)
    const message = error instanceof Error ? error.message : 'Verification failed'
    if (/link|expired|malformed/i.test(message)) return apiError(message, 400)
    console.error(error)
    return apiError('Docket could not finish verification. Return to Discord and try again.', 500)
  }
}
