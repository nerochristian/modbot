import 'server-only'

import { createCipheriv, createDecipheriv, createHash, randomBytes } from 'node:crypto'
import { prisma } from '@/lib/prisma'

const DISCORD_API = 'https://discord.com/api/v10'
const ADMINISTRATOR = BigInt(8)
const TOKEN_REFRESH_SKEW_MS = 60_000
const CACHE_TTL_MS = 30_000
const TRANSIENT_AUTHORITY_GRACE_MS = 2 * 60_000

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
  roles: string[]
  communication_disabled_until?: string | null
}

export type DiscordGuildRoleResource = {
  id: string
  name: string
  position: number
  color: number
}

export type DiscordGuildChannelResource = {
  id: string
  name: string
  /** Discord channel type. Resources expose text, announcement, voice, stage, and category channels. */
  type: 0 | 2 | 4 | 5 | 13
  parentId: string | null
  position: number
}

type DiscordGuildRolePayload = DiscordGuildRoleResource & {
  managed: boolean
}

type DiscordGuildChannelPayload = {
  id: string
  name: string
  type: number
  parent_id?: string | null
  position?: number
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
  canManage: boolean
  membershipRole: 'admin' | 'manager' | 'viewer'
}

export class DiscordReauthRequiredError extends Error {
  constructor(message = 'Discord authorization has expired. Sign in again to continue.') {
    super(message)
    this.name = 'DiscordReauthRequiredError'
  }
}

export class DiscordTemporaryError extends Error {
  readonly status: number

  constructor(status: number) {
    super(`Discord API request failed (${status})`)
    this.name = 'DiscordTemporaryError'
    this.status = status
  }
}

function requiredEnv(name: 'DISCORD_CLIENT_ID' | 'DISCORD_CLIENT_SECRET'): string {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`${name} is not configured`)
  return value
}

export function dashboardBaseUrl(requestUrl?: string): string {
  const candidates = [
    process.env.DASHBOARD_PUBLIC_URL,
    process.env.FRONTEND_PUBLIC_URL,
    process.env.NEXT_PUBLIC_APP_URL,
    process.env.NEXT_PUBLIC_BASE_URL,
  ]
  for (const candidate of candidates) {
    if (!candidate) continue
    try {
      const url = new URL(candidate)
      if (
        ['http:', 'https:'].includes(url.protocol) &&
        !['0.0.0.0', '127.0.0.1', 'localhost', '::'].includes(url.hostname)
      ) {
        return url.origin
      }
    } catch {
      continue
    }
  }
  if (requestUrl) {
    const requestOrigin = new URL(requestUrl)
    if (!['0.0.0.0', '127.0.0.1', 'localhost', '::'].includes(requestOrigin.hostname)) {
      return requestOrigin.origin
    }
  }
  return `http://localhost:${process.env.DASHBOARD_PORT || '3000'}`
}

export function discordRedirectUri(requestUrl?: string): string {
  return `${dashboardBaseUrl(requestUrl)}/api/auth/discord/callback`
}

function encryptionKey(version: 'v1' | 'v2'): Buffer {
  const secret = version === 'v2'
    ? process.env.DISCORD_TOKEN_ENCRYPTION_KEY || process.env.AUTH_SECRET || process.env.SESSION_SECRET
    : process.env.AUTH_SECRET || process.env.SESSION_SECRET
  if (!secret) throw new Error('AUTH_SECRET or SESSION_SECRET is not configured')
  return createHash('sha256').update(secret).digest()
}

export function sealDiscordToken(token: string): string {
  const iv = randomBytes(12)
  const cipher = createCipheriv('aes-256-gcm', encryptionKey('v2'), iv)
  const encrypted = Buffer.concat([cipher.update(token, 'utf8'), cipher.final()])
  const tag = cipher.getAuthTag()
  return ['v2', iv.toString('base64url'), tag.toString('base64url'), encrypted.toString('base64url')].join('.')
}

function openDiscordToken(value: string): string {
  const [version, iv, tag, encrypted] = value.split('.')
  if ((version !== 'v1' && version !== 'v2') || !iv || !tag || !encrypted) {
    throw new DiscordReauthRequiredError()
  }
  try {
    const decipher = createDecipheriv('aes-256-gcm', encryptionKey(version), Buffer.from(iv, 'base64url'))
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
  if (response.status === 429 || response.status >= 500) throw new DiscordTemporaryError(response.status)
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

async function discordJsonMutation<T>(path: string, method: string, body: unknown): Promise<T> {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  const response = await fetch(`${DISCORD_API}${path}`, {
    method,
    headers: {
      Authorization: `Bot ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
  if (!response.ok) throw new Error(`Discord moderation request failed (${response.status})`)
  return response.json() as Promise<T>
}

async function sendBotDirectMessage(userId: string, content: string): Promise<void> {
  const channel = await discordJsonMutation<{ id: string }>('/users/@me/channels', 'POST', {
    recipient_id: userId,
  })
  await discordMutation(`/channels/${channel.id}/messages`, 'POST', {
    content: content.slice(0, 2000),
    allowed_mentions: { parse: [] },
  })
}

export async function sendBotChannelMessage(channelId: string, content: string): Promise<void> {
  if (!/^\d{15,22}$/.test(channelId)) throw new Error('Invalid Discord channel ID')
  await discordMutation(`/channels/${channelId}/messages`, 'POST', {
    content: content.slice(0, 2000),
    allowed_mentions: { parse: [] },
  })
}

const guildResourceCache = new Map<string, {
  expiresAt: number
  value: { roles: DiscordGuildRoleResource[]; channels: DiscordGuildChannelResource[] }
}>()

/**
 * Load the selectable moderation resources with the bot credential. The route
 * calling this function is already scoped to the authenticated user's selected
 * guild; accepting only a guild ID here keeps the bot token server-only.
 */
export async function getBotGuildResources(guildId: string): Promise<{
  roles: DiscordGuildRoleResource[]
  channels: DiscordGuildChannelResource[]
}> {
  if (!/^\d{15,22}$/.test(guildId)) throw new Error('Invalid Discord guild ID')
  const cached = guildResourceCache.get(guildId)
  if (cached && cached.expiresAt > Date.now()) return cached.value

  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  const [rolePayload, channelPayload] = await Promise.all([
    discordRequest<DiscordGuildRolePayload[]>(`/guilds/${guildId}/roles`, `Bot ${token}`),
    discordRequest<DiscordGuildChannelPayload[]>(`/guilds/${guildId}/channels`, `Bot ${token}`),
  ])
  const value = {
    roles: rolePayload
      .filter((role) => role.id !== guildId && !role.managed)
      .map(({ id, name, position, color }) => ({ id, name, position, color }))
      .sort((a, b) => b.position - a.position || a.name.localeCompare(b.name)),
    channels: channelPayload
      .filter((channel): channel is DiscordGuildChannelPayload & { type: 0 | 2 | 4 | 5 | 13 } => (
        channel.type === 0
        || channel.type === 2
        || channel.type === 4
        || channel.type === 5
        || channel.type === 13
      ))
      .map((channel) => ({
        id: channel.id,
        name: channel.name,
        type: channel.type,
        parentId: channel.parent_id ?? null,
        position: channel.position ?? 0,
      }))
      .sort((a, b) => a.position - b.position || a.name.localeCompare(b.name)),
  }
  guildResourceCache.set(guildId, { value, expiresAt: Date.now() + CACHE_TTL_MS })
  return value
}

export async function getBotGuildMembers(
  guildId: string,
  page: number,
  pageSize: number,
  query = '',
): Promise<{ data: DiscordGuildMember[]; total: number | null }> {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  const offset = Math.max(0, page - 1) * pageSize
  if (query) {
    if (/^\d{15,22}$/.test(query)) {
      try {
        const member = await getBotGuildMember(guildId, query)
        return { data: offset === 0 ? [member] : [], total: 1 }
      } catch (error) {
        if (error instanceof Error && error.message.includes('(404)')) return { data: [], total: 0 }
        throw error
      }
    }
    const params = new URLSearchParams({ query: query.slice(0, 100), limit: '1000' })
    const matches = await discordRequest<DiscordGuildMember[]>(
      `/guilds/${guildId}/members/search?${params}`,
      `Bot ${token}`,
    )
    return { data: matches.slice(offset, offset + pageSize), total: matches.length }
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
  return { data: collected.slice(offset, offset + pageSize), total: null }
}

export async function getBotGuildMember(guildId: string, userId: string): Promise<DiscordGuildMember> {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  return discordRequest<DiscordGuildMember>(`/guilds/${guildId}/members/${userId}`, `Bot ${token}`)
}

export async function executeModerationAction(
  guildId: string,
  userId: string,
  action: string,
  durationHours = 0,
  options: {
    reason?: string
    dmUser?: boolean
    preserveBanMessages?: boolean
  } = {},
): Promise<void> {
  if (!/^\d{15,22}$/.test(guildId) || !/^\d{15,22}$/.test(userId)) {
    throw new Error('Invalid Discord ID')
  }
  const normalizedAction = action === 'mute' ? 'timeout' : action
  if (options.dmUser && ['timeout', 'kick', 'ban'].includes(normalizedAction)) {
    const verb = normalizedAction === 'timeout'
      ? 'timed out'
      : normalizedAction === 'kick' ? 'kicked' : 'banned'
    const duration = normalizedAction === 'timeout'
      ? `\nDuration: ${durationHours > 0 ? durationHours : 1} hour(s)`
      : ''
    await sendBotDirectMessage(
      userId,
      `You were ${verb} by Docket.\nReason: ${options.reason || 'No reason provided'}${duration}`,
    ).catch(() => undefined)
  }

  if (normalizedAction === 'timeout') {
    const hours = durationHours > 0 ? Math.min(durationHours, 24 * 28) : 1
    await discordMutation(`/guilds/${guildId}/members/${userId}`, 'PATCH', {
      communication_disabled_until: new Date(Date.now() + hours * 3_600_000).toISOString(),
    })
  } else if (normalizedAction === 'kick') {
    await discordMutation(`/guilds/${guildId}/members/${userId}`, 'DELETE')
  } else if (normalizedAction === 'ban') {
    await discordMutation(`/guilds/${guildId}/bans/${userId}`, 'PUT', {
      delete_message_seconds: options.preserveBanMessages === false ? 86_400 : 0,
    })
  } else if (normalizedAction === 'unban') {
    await discordMutation(`/guilds/${guildId}/bans/${userId}`, 'DELETE')
  } else if (!['warn', 'note'].includes(normalizedAction)) {
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

export async function exchangeDiscordCode(
  code: string,
  redirectUri: string,
  codeVerifier: string,
): Promise<DiscordTokenResponse> {
  return tokenRequest(new URLSearchParams({
    client_id: requiredEnv('DISCORD_CLIENT_ID'),
    client_secret: requiredEnv('DISCORD_CLIENT_SECRET'),
    grant_type: 'authorization_code',
    code,
    redirect_uri: redirectUri,
    code_verifier: codeVerifier,
  }))
}

export async function fetchDiscordUser(accessToken: string): Promise<DiscordUser> {
  return discordRequest<DiscordUser>('/users/@me', `Bearer ${accessToken}`)
}

const refreshLocks = new Map<string, Promise<string>>()

async function performAccessTokenRefresh(user: {
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

async function refreshAccessToken(user: {
  id: string
  discordRefreshToken: string | null
}): Promise<string> {
  const inFlight = refreshLocks.get(user.id)
  if (inFlight) return inFlight
  const refresh = performAccessTokenRefresh(user)
  refreshLocks.set(user.id, refresh)
  try {
    return await refresh
  } finally {
    if (refreshLocks.get(user.id) === refresh) refreshLocks.delete(user.id)
  }
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

let botGuildCache: { expiresAt: number; guilds: Map<string, DiscordGuild> } | null = null

async function getBotGuilds(): Promise<Map<string, DiscordGuild>> {
  if (botGuildCache && botGuildCache.expiresAt > Date.now()) return botGuildCache.guilds
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')

  const guilds = new Map<string, DiscordGuild>()
  let after: string | undefined
  for (;;) {
    const query = new URLSearchParams({ limit: '200', with_counts: 'true', ...(after ? { after } : {}) })
    const page = await discordRequest<DiscordGuild[]>(`/users/@me/guilds?${query}`, `Bot ${token}`)
    page.forEach((guild) => guilds.set(guild.id, guild))
    if (page.length < 200) break
    after = page.at(-1)?.id
    if (!after) break
  }
  const installedIds = Array.from(guilds.keys())
  await prisma.$transaction([
    ...Array.from(guilds.values()).map((guild) => prisma.guild.upsert({
      where: { id: guild.id },
      create: { id: guild.id, name: guild.name, icon: guild.icon, installed: true },
      update: { name: guild.name, icon: guild.icon, installed: true },
    })),
    prisma.guild.updateMany({
      where: installedIds.length ? { installed: true, id: { notIn: installedIds } } : { installed: true },
      data: { installed: false },
    }),
  ])
  botGuildCache = { guilds, expiresAt: Date.now() + CACHE_TTL_MS }
  return guilds
}

const userGuildCache = new Map<string, { expiresAt: number; guilds: ManagedGuild[] }>()
const userGuildRefreshes = new Map<string, Promise<ManagedGuild[]>>()

function hasAdministratorAccess(guild: DiscordGuild): boolean {
  if (guild.owner) return true
  try {
    const permissions = BigInt(guild.permissions ?? '0')
    return (permissions & ADMINISTRATOR) === ADMINISTRATOR
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

async function fetchUserGuilds(accessToken: string): Promise<DiscordGuild[]> {
  const guilds: DiscordGuild[] = []
  let after: string | undefined
  for (;;) {
    const params = new URLSearchParams({
      limit: '200',
      with_counts: 'true',
      ...(after ? { after } : {}),
    })
    const page = await discordRequest<DiscordGuild[]>(`/users/@me/guilds?${params}`, `Bearer ${accessToken}`)
    guilds.push(...page)
    if (page.length < 200) break
    after = page.at(-1)?.id
    if (!after) break
  }
  return guilds
}

async function syncGuildMemberships(
  userId: string,
  userGuilds: DiscordGuild[],
  botGuilds: Map<string, DiscordGuild>,
): Promise<void> {
  const administrable = userGuilds.filter(hasAdministratorAccess)
  const administrableIds = administrable.map((guild) => guild.id)
  const now = new Date()

  const syncOperations = [
    ...administrable.map((guild) => prisma.guild.upsert({
      where: { id: guild.id },
      create: {
        id: guild.id,
        name: guild.name,
        icon: guild.icon,
        installed: botGuilds.has(guild.id),
      },
      update: { name: guild.name, icon: guild.icon, installed: botGuilds.has(guild.id) },
    })),
    ...administrable.map((guild) => {
      return prisma.guildMembership.upsert({
        where: { guildId_userId: { guildId: guild.id, userId } },
        create: {
          guildId: guild.id,
          userId,
          role: 'admin',
          status: botGuilds.has(guild.id) ? 'active' : 'revoked',
          source: 'discord',
          verifiedAt: botGuilds.has(guild.id) ? now : null,
        },
        update: {
          role: 'admin',
          status: botGuilds.has(guild.id) ? 'active' : 'revoked',
          source: 'discord',
          verifiedAt: botGuilds.has(guild.id) ? now : null,
        },
      })
    }),
  ]
  if (syncOperations.length) await prisma.$transaction(syncOperations)

  // Dashboard access is derived exclusively from live Discord Administrator
  // authority. An invitation may identify an expected person, but it never
  // activates or preserves access by itself.
  await prisma.guildMembership.updateMany({
    where: { userId, source: 'invite' },
    data: { status: 'revoked' },
  })
  await prisma.guildMembership.updateMany({
    where: {
      userId,
      source: 'discord',
      ...(administrableIds.length ? { guildId: { notIn: administrableIds } } : {}),
    },
    data: { status: 'revoked' },
  })
}

export function invalidateGuildCache(userId?: string): void {
  if (userId) userGuildCache.delete(userId)
  else userGuildCache.clear()
}

async function refreshManageableGuilds(userId: string): Promise<ManagedGuild[]> {
  const user = await prisma.user.findUnique({ where: { id: userId }, select: { discordId: true } })
  if (!user?.discordId) throw new DiscordReauthRequiredError()
  const [botGuilds, accessToken] = await Promise.all([getBotGuilds(), getAccessToken(userId)])
  const userGuilds = await fetchUserGuilds(accessToken)
  const liveAdministrable = userGuilds.filter(hasAdministratorAccess)
  const liveAdministratorIds = liveAdministrable.map((guild) => guild.id)

  await syncGuildMemberships(userId, userGuilds, botGuilds)

  const memberships = await prisma.guildMembership.findMany({
    where: {
      userId,
      role: 'admin',
      status: 'active',
      source: 'discord',
      guildId: { in: liveAdministratorIds },
      guild: { installed: true },
    },
    include: { guild: true },
  })
  const liveById = new Map(liveAdministrable.map((guild) => [guild.id, guild]))
  const manageableById = new Map(memberships.map((membership): [string, ManagedGuild] => {
    const live = liveById.get(membership.guildId) ?? botGuilds.get(membership.guildId)
    const stored = membership.guild
    const guild: DiscordGuild = live ?? {
      id: stored.id,
      name: stored.name,
      icon: stored.icon,
    }
    return [guild.id, {
      id: guild.id,
      name: guild.name,
      iconUrl: guildIconUrl(guild),
      owner: Boolean(guild.owner),
      installed: stored.installed,
      memberCount: guild.approximate_member_count ?? null,
      onlineCount: guild.approximate_presence_count ?? null,
      inviteUrl: botInviteUrl(guild.id),
      canManage: liveById.has(guild.id),
      membershipRole: 'admin',
    }]
  }))
  for (const guild of liveAdministrable) {
    if (botGuilds.has(guild.id) || manageableById.has(guild.id)) continue
    manageableById.set(guild.id, {
      id: guild.id,
      name: guild.name,
      iconUrl: guildIconUrl(guild),
      owner: Boolean(guild.owner),
      installed: false,
      memberCount: guild.approximate_member_count ?? null,
      onlineCount: guild.approximate_presence_count ?? null,
      inviteUrl: botInviteUrl(guild.id),
      canManage: true,
      membershipRole: 'admin',
    })
  }
  const manageable = Array.from(manageableById.values())
    .sort((a, b) => Number(b.installed) - Number(a.installed) || a.name.localeCompare(b.name))

  userGuildCache.set(userId, { guilds: manageable, expiresAt: Date.now() + CACHE_TTL_MS })
  return manageable
}

async function loadRecentlyVerifiedGuilds(userId: string): Promise<ManagedGuild[]> {
  const user = await prisma.user.findUnique({ where: { id: userId }, select: { discordId: true } })
  if (!user?.discordId) return []
  const memberships = await prisma.guildMembership.findMany({
    where: {
      userId,
      role: 'admin',
      source: 'discord',
      status: 'active',
      verifiedAt: { gte: new Date(Date.now() - TRANSIENT_AUTHORITY_GRACE_MS) },
      guild: { installed: true },
    },
    include: { guild: true },
  })
  return memberships
    .map((membership): ManagedGuild => {
      const guild = membership.guild
      return {
        id: guild.id,
        name: guild.name,
        iconUrl: guildIconUrl({ id: guild.id, name: guild.name, icon: guild.icon }),
        owner: false,
        installed: true,
        memberCount: null,
        onlineCount: null,
        inviteUrl: botInviteUrl(guild.id),
        canManage: true,
        membershipRole: 'admin',
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name))
}

export async function getManageableGuilds(userId: string, force = false): Promise<ManagedGuild[]> {
  const cached = userGuildCache.get(userId)
  if (!force && cached && cached.expiresAt > Date.now()) return cached.guilds

  const inFlight = userGuildRefreshes.get(userId)
  if (inFlight) return inFlight
  if (force) botGuildCache = null

  const refresh = refreshManageableGuilds(userId).catch(async (error) => {
    if (!(error instanceof DiscordTemporaryError)) throw error
    const recentlyVerified = await loadRecentlyVerifiedGuilds(userId)
    if (recentlyVerified.length === 0) throw error
    userGuildCache.set(userId, {
      guilds: recentlyVerified,
      expiresAt: Date.now() + CACHE_TTL_MS,
    })
    return recentlyVerified
  }).finally(() => {
    if (userGuildRefreshes.get(userId) === refresh) userGuildRefreshes.delete(userId)
  })
  userGuildRefreshes.set(userId, refresh)
  return refresh
}


export function discordAvatarUrl(user: Pick<DiscordUser, 'id' | 'avatar'>): string | null {
  if (!user.avatar) return null
  const extension = user.avatar.startsWith('a_') ? 'gif' : 'webp'
  return `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.${extension}?size=128`
}
