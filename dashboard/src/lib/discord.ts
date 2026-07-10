import 'server-only'

import { createCipheriv, createDecipheriv, createHash, randomBytes } from 'node:crypto'
import { prisma } from '@/lib/prisma'

const DISCORD_API = 'https://discord.com/api/v10'
const ADMINISTRATOR = BigInt(8)
const MANAGE_GUILD = BigInt(32)
const TOKEN_REFRESH_SKEW_MS = 60_000
const CACHE_TTL_MS = 30_000

export type DiscordUser = {
  id: string
  username: string
  global_name: string | null
  avatar: string | null
  email?: string | null
  verified?: boolean
}

type DiscordTokenResponse = {
  access_token: string
  refresh_token?: string
  expires_in: number
  token_type: 'Bearer'
  scope: string
}

type DiscordGuild = {
  id: string
  name: string
  icon: string | null
  owner?: boolean
  permissions?: string
  approximate_member_count?: number
  approximate_presence_count?: number
}

export type DiscordGuildMember = {
  user: {
    id: string
    username: string
    global_name: string | null
    avatar: string | null
  }
  nick: string | null
  avatar: string | null
  joined_at: string
  communication_disabled_until?: string | null
}

export type ManagedGuild = {
  id: string
  name: string
  iconUrl: string | null
  owner: boolean
  installed: boolean
  memberCount: number | null
  onlineCount: number | null
  inviteUrl: string
}

export class DiscordReauthRequiredError extends Error {
  constructor(message = 'Discord authorization has expired. Sign in again to continue.') {
    super(message)
    this.name = 'DiscordReauthRequiredError'
  }
}

function requiredEnv(name: 'DISCORD_CLIENT_ID' | 'DISCORD_CLIENT_SECRET'): string {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`${name} is not configured`)
  return value
}

export function dashboardBaseUrl(requestUrl?: string): string {
  if (process.env.NODE_ENV !== 'production' && requestUrl) return new URL(requestUrl).origin
  const configured =
    process.env.NEXT_PUBLIC_APP_URL ||
    process.env.DASHBOARD_PUBLIC_URL ||
    process.env.FRONTEND_PUBLIC_URL
  if (configured) return configured.replace(/\/$/, '')
  if (requestUrl) return new URL(requestUrl).origin
  return `http://localhost:${process.env.DASHBOARD_PORT || '3000'}`
}

export function discordRedirectUri(requestUrl?: string): string {
  return `${dashboardBaseUrl(requestUrl)}/api/auth/discord/callback`
}

function encryptionKey(): Buffer {
  const secret = process.env.AUTH_SECRET || process.env.SESSION_SECRET
  if (!secret) throw new Error('AUTH_SECRET or SESSION_SECRET is not configured')
  return createHash('sha256').update(secret).digest()
}

export function sealDiscordToken(token: string): string {
  const iv = randomBytes(12)
  const cipher = createCipheriv('aes-256-gcm', encryptionKey(), iv)
  const encrypted = Buffer.concat([cipher.update(token, 'utf8'), cipher.final()])
  const tag = cipher.getAuthTag()
  return ['v1', iv.toString('base64url'), tag.toString('base64url'), encrypted.toString('base64url')].join('.')
}

function openDiscordToken(value: string): string {
  const [version, iv, tag, encrypted] = value.split('.')
  if (version !== 'v1' || !iv || !tag || !encrypted) {
    throw new DiscordReauthRequiredError()
  }
  try {
    const decipher = createDecipheriv('aes-256-gcm', encryptionKey(), Buffer.from(iv, 'base64url'))
    decipher.setAuthTag(Buffer.from(tag, 'base64url'))
    return Buffer.concat([
      decipher.update(Buffer.from(encrypted, 'base64url')),
      decipher.final(),
    ]).toString('utf8')
  } catch {
    throw new DiscordReauthRequiredError()
  }
}

async function discordRequest<T>(path: string, authorization: string): Promise<T> {
  const response = await fetch(`${DISCORD_API}${path}`, {
    headers: { Authorization: authorization },
    cache: 'no-store',
  })
  if (response.status === 401) throw new DiscordReauthRequiredError()
  if (!response.ok) {
    throw new Error(`Discord API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

async function discordMutation(path: string, method: string, body?: unknown): Promise<void> {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  const response = await fetch(`${DISCORD_API}${path}`, {
    method,
    headers: {
      Authorization: `Bot ${token}`,
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
  })
  if (!response.ok) throw new Error(`Discord moderation request failed (${response.status})`)
}

export async function getBotGuildMembers(
  guildId: string,
  page: number,
  pageSize: number,
  query = '',
): Promise<DiscordGuildMember[]> {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  const offset = Math.max(0, page - 1) * pageSize
  if (query) {
    const params = new URLSearchParams({ query: query.slice(0, 100), limit: '1000' })
    const matches = await discordRequest<DiscordGuildMember[]>(
      `/guilds/${guildId}/members/search?${params}`,
      `Bot ${token}`,
    )
    return matches.slice(offset, offset + pageSize)
  }

  const collected: DiscordGuildMember[] = []
  let after = '0'
  const needed = offset + pageSize
  while (collected.length < needed) {
    const params = new URLSearchParams({ limit: String(Math.min(1000, needed - collected.length)), after })
    const batch = await discordRequest<DiscordGuildMember[]>(
      `/guilds/${guildId}/members?${params}`,
      `Bot ${token}`,
    )
    collected.push(...batch)
    if (batch.length === 0 || batch.length < Number(params.get('limit'))) break
    after = batch.at(-1)?.user.id ?? after
  }
  return collected.slice(offset, offset + pageSize)
}

export async function executeModerationAction(
  guildId: string,
  userId: string,
  action: string,
  durationHours = 0,
): Promise<void> {
  if (!/^\d{15,22}$/.test(guildId) || !/^\d{15,22}$/.test(userId)) {
    throw new Error('Invalid Discord ID')
  }
  if (action === 'timeout' || action === 'mute') {
    const hours = durationHours > 0 ? Math.min(durationHours, 24 * 28) : 1
    await discordMutation(`/guilds/${guildId}/members/${userId}`, 'PATCH', {
      communication_disabled_until: new Date(Date.now() + hours * 3_600_000).toISOString(),
    })
  } else if (action === 'kick') {
    await discordMutation(`/guilds/${guildId}/members/${userId}`, 'DELETE')
  } else if (action === 'ban') {
    await discordMutation(`/guilds/${guildId}/bans/${userId}`, 'PUT', { delete_message_seconds: 0 })
  } else if (action === 'unban') {
    await discordMutation(`/guilds/${guildId}/bans/${userId}`, 'DELETE')
  } else if (!['warn', 'note'].includes(action)) {
    throw new Error(`Unsupported moderation action: ${action}`)
  }
}

async function tokenRequest(params: URLSearchParams): Promise<DiscordTokenResponse> {
  const response = await fetch(`${DISCORD_API}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params,
    cache: 'no-store',
  })
  if (!response.ok) {
    throw new DiscordReauthRequiredError('Discord rejected the authorization request. Please try again.')
  }
  return response.json() as Promise<DiscordTokenResponse>
}

export async function exchangeDiscordCode(code: string, redirectUri: string): Promise<DiscordTokenResponse> {
  return tokenRequest(new URLSearchParams({
    client_id: requiredEnv('DISCORD_CLIENT_ID'),
    client_secret: requiredEnv('DISCORD_CLIENT_SECRET'),
    grant_type: 'authorization_code',
    code,
    redirect_uri: redirectUri,
  }))
}

export async function fetchDiscordUser(accessToken: string): Promise<DiscordUser> {
  return discordRequest<DiscordUser>('/users/@me', `Bearer ${accessToken}`)
}

async function refreshAccessToken(user: {
  id: string
  discordRefreshToken: string | null
}): Promise<string> {
  if (!user.discordRefreshToken) throw new DiscordReauthRequiredError()
  const refreshToken = openDiscordToken(user.discordRefreshToken)
  const tokens = await tokenRequest(new URLSearchParams({
    client_id: requiredEnv('DISCORD_CLIENT_ID'),
    client_secret: requiredEnv('DISCORD_CLIENT_SECRET'),
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
  }))
  const accessToken = tokens.access_token
  await prisma.user.update({
    where: { id: user.id },
    data: {
      discordAccessToken: sealDiscordToken(accessToken),
      discordRefreshToken: sealDiscordToken(tokens.refresh_token ?? refreshToken),
      discordTokenExpiresAt: new Date(Date.now() + tokens.expires_in * 1000),
    },
  })
  return accessToken
}

async function getAccessToken(userId: string): Promise<string> {
  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: {
      id: true,
      discordAccessToken: true,
      discordRefreshToken: true,
      discordTokenExpiresAt: true,
    },
  })
  if (!user?.discordAccessToken) throw new DiscordReauthRequiredError()
  if (!user.discordTokenExpiresAt || user.discordTokenExpiresAt.getTime() <= Date.now() + TOKEN_REFRESH_SKEW_MS) {
    return refreshAccessToken(user)
  }
  return openDiscordToken(user.discordAccessToken)
}

let botGuildCache: { expiresAt: number; ids: Set<string> } | null = null

async function getBotGuildIds(): Promise<Set<string>> {
  if (botGuildCache && botGuildCache.expiresAt > Date.now()) return botGuildCache.ids
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')

  const ids = new Set<string>()
  let after: string | undefined
  for (;;) {
    const query = new URLSearchParams({ limit: '200', ...(after ? { after } : {}) })
    const page = await discordRequest<DiscordGuild[]>(`/users/@me/guilds?${query}`, `Bot ${token}`)
    page.forEach((guild) => ids.add(guild.id))
    if (page.length < 200) break
    after = page.at(-1)?.id
    if (!after) break
  }
  botGuildCache = { ids, expiresAt: Date.now() + CACHE_TTL_MS }
  return ids
}

const userGuildCache = new Map<string, { expiresAt: number; guilds: ManagedGuild[] }>()

function canManageGuild(guild: DiscordGuild): boolean {
  if (guild.owner) return true
  try {
    const permissions = BigInt(guild.permissions ?? '0')
    return (permissions & ADMINISTRATOR) === ADMINISTRATOR || (permissions & MANAGE_GUILD) === MANAGE_GUILD
  } catch {
    return false
  }
}

function guildIconUrl(guild: DiscordGuild): string | null {
  if (!guild.icon) return null
  const extension = guild.icon.startsWith('a_') ? 'gif' : 'webp'
  return `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.${extension}?size=128`
}

export function botInviteUrl(guildId: string): string {
  const params = new URLSearchParams({
    client_id: requiredEnv('DISCORD_CLIENT_ID'),
    scope: 'bot applications.commands',
    permissions: process.env.DISCORD_BOT_PERMISSIONS?.trim() || '8',
    guild_id: guildId,
    disable_guild_select: 'true',
  })
  return `https://discord.com/oauth2/authorize?${params}`
}

export async function getManageableGuilds(userId: string, force = false): Promise<ManagedGuild[]> {
  const cached = userGuildCache.get(userId)
  if (!force && cached && cached.expiresAt > Date.now()) return cached.guilds

  const [accessToken, installedIds] = await Promise.all([getAccessToken(userId), getBotGuildIds()])
  const params = new URLSearchParams({ limit: '200', with_counts: 'true' })
  const guilds = await discordRequest<DiscordGuild[]>(`/users/@me/guilds?${params}`, `Bearer ${accessToken}`)
  const manageable = guilds
    .filter(canManageGuild)
    .map((guild): ManagedGuild => ({
      id: guild.id,
      name: guild.name,
      iconUrl: guildIconUrl(guild),
      owner: Boolean(guild.owner),
      installed: installedIds.has(guild.id),
      memberCount: guild.approximate_member_count ?? null,
      onlineCount: guild.approximate_presence_count ?? null,
      inviteUrl: botInviteUrl(guild.id),
    }))
    .sort((a, b) => Number(b.installed) - Number(a.installed) || a.name.localeCompare(b.name))

  userGuildCache.set(userId, { guilds: manageable, expiresAt: Date.now() + CACHE_TTL_MS })
  return manageable
}

export function discordAvatarUrl(user: Pick<DiscordUser, 'id' | 'avatar'>): string | null {
  if (!user.avatar) return null
  const extension = user.avatar.startsWith('a_') ? 'gif' : 'webp'
  return `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.${extension}?size=128`
}
