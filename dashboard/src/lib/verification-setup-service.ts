import 'server-only'

import { withBotAdvisoryLock } from '@/lib/bot-db'
import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'

const DISCORD_API = 'https://discord.com/api/v10'
const VIEW_CHANNEL = BigInt(1 << 10)
const SEND_MESSAGES = BigInt(1 << 11)
const ADMINISTRATOR = BigInt(1 << 3)
const READ_MESSAGE_HISTORY = BigInt(1 << 16)
const IS_COMPONENTS_V2 = 1 << 15
const MAX_DISCORD_ATTEMPTS = 5
const DISCORD_WRITE_CONCURRENCY = 3
const BULK_VERIFICATION_AUDIT_REASON = 'Docket verification setup - queue existing member'

export type VerificationMethod = 'website' | 'discord'

const STAFF_ROLE_SETTING_KEYS = [
  'owner_role',
  'manager_role',
  'admin_role',
  'supervisor_role',
  'senior_mod_role',
  'mod_role',
  'trial_mod_role',
  'staff_role',
] as const

type DiscordRole = { id: string; name: string; managed: boolean; permissions: string }
type DiscordChannel = { id: string; name: string; type: number; parent_id?: string | null }
type DiscordMessage = {
  id: string
  author?: { id?: string }
  components?: unknown[]
}
type DiscordGuild = { id: string; name: string; icon: string | null; owner_id: string }
type DiscordUser = { id: string; bot?: boolean }
type DiscordMember = { user: DiscordUser; roles: string[] }

function botToken(): string {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  return token
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

async function discord<T>(path: string, init: RequestInit = {}): Promise<T> {
  for (let attempt = 1; attempt <= MAX_DISCORD_ATTEMPTS; attempt += 1) {
    const response = await fetch(`${DISCORD_API}${path}`, {
      ...init,
      headers: {
        Authorization: `Bot ${botToken()}`,
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...init.headers,
      },
      cache: 'no-store',
    })

    if (response.status === 429 && attempt < MAX_DISCORD_ATTEMPTS) {
      const detail = await response.json().catch(() => null) as { retry_after?: number } | null
      const retryAfter = Math.max(250, Math.ceil(Number(detail?.retry_after ?? 1) * 1_000))
      await wait(retryAfter)
      continue
    }

    if (!response.ok) {
      const detail = await response.json().catch(() => null) as { message?: string; code?: number } | null
      throw new Error(`Discord setup failed (${response.status}${detail?.code ? ` / ${detail.code}` : ''})${detail?.message ? `: ${detail.message}` : ''}`)
    }
    if (response.status === 204) return undefined as T
    return response.json() as Promise<T>
  }

  throw new Error('Discord setup failed after repeated rate limits')
}

async function mapConcurrent<T>(
  items: T[],
  concurrency: number,
  task: (item: T) => Promise<void>,
): Promise<void> {
  let nextIndex = 0
  async function worker() {
    while (nextIndex < items.length) {
      const item = items[nextIndex]
      nextIndex += 1
      await task(item)
    }
  }
  const workerCount = Math.min(Math.max(1, concurrency), items.length)
  await Promise.all(Array.from({ length: workerCount }, () => worker()))
}

async function createRole(guildId: string, name: string, color: number): Promise<DiscordRole> {
  return discord<DiscordRole>(`/guilds/${guildId}/roles`, {
    method: 'POST',
    body: JSON.stringify({ name, color, permissions: '0', hoist: false, mentionable: false }),
  })
}

async function createChannel(
  guildId: string,
  name: string,
  type: 0 | 4,
  parentId?: string,
): Promise<DiscordChannel> {
  return discord<DiscordChannel>(`/guilds/${guildId}/channels`, {
    method: 'POST',
    body: JSON.stringify({
      name,
      type,
      ...(parentId ? { parent_id: parentId } : {}),
      ...(type === 0 ? { topic: 'Docket member verification' } : {}),
    }),
  })
}

async function setOverwrite(
  channelId: string,
  targetId: string,
  type: 0 | 1,
  allow: bigint,
  deny: bigint,
): Promise<void> {
  await discord<void>(`/channels/${channelId}/permissions/${targetId}`, {
    method: 'PUT',
    body: JSON.stringify({ type, allow: allow.toString(), deny: deny.toString() }),
  })
}

function guildIconUrl(guild: DiscordGuild): string | null {
  if (!guild.icon) return null
  const extension = guild.icon.startsWith('a_') ? 'gif' : 'png'
  return `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.${extension}?size=256`
}

function escapeDiscordMarkdown(value: string): string {
  return value.replace(/[\\*_~`>|]/g, '\\$&')
}

function componentHasCustomId(value: unknown, customId: string): boolean {
  if (Array.isArray(value)) return value.some((item) => componentHasCustomId(item, customId))
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  if (record.custom_id === customId) return true
  return Object.values(record).some((item) => componentHasCustomId(item, customId))
}

function panelPayload(guild: DiscordGuild, editing = false) {
  const iconUrl = guildIconUrl(guild)
  const header = {
    type: 10,
    content: `## Unlock ${escapeDiscordMarkdown(guild.name)}\nComplete one private security check to enter. Docket grants your access automatically.`,
  }
  return {
    ...(editing ? { content: null, embeds: [] } : {}),
    flags: IS_COMPONENTS_V2,
    allowed_mentions: { parse: [] },
    components: [{
      type: 17,
      accent_color: 0x2b7fff,
      components: [
        ...(iconUrl ? [{
          type: 9,
          components: [header],
          accessory: { type: 11, media: { url: iconUrl }, description: `${guild.name} icon` },
        }] : [header]),
        { type: 14, divider: true, spacing: 1 },
        {
          type: 1,
          components: [{
            type: 2,
            style: 1,
            label: 'Verify now',
            custom_id: 'verification:start',
          }, {
            type: 2,
            style: 2,
            label: 'How it works',
            custom_id: 'verification:tutorial',
          }],
        },
        { type: 14, divider: true, spacing: 1 },
        { type: 10, content: '-# Private  •  No password  •  Usually under a minute' },
      ],
    }],
  }
}

function configuredStaffRoleIds(settings: Record<string, unknown>): Set<string> {
  return new Set(
    STAFF_ROLE_SETTING_KEYS
      .map((key) => String(settings[key] ?? ''))
      .filter((roleId) => /^\d{15,22}$/.test(roleId)),
  )
}

function roleHasAdministrator(role: DiscordRole | undefined): boolean {
  if (!role) return false
  try {
    return (BigInt(role.permissions || '0') & ADMINISTRATOR) === ADMINISTRATOR
  } catch {
    return false
  }
}

async function queueExistingMembers(
  guild: DiscordGuild,
  roles: DiscordRole[],
  settings: Record<string, unknown>,
  verifiedRoleId: string,
  unverifiedRoleId: string,
): Promise<{ assigned: number; skipped: number }> {
  const rolesById = new Map(roles.map((role) => [role.id, role]))
  const staffRoleIds = configuredStaffRoleIds(settings)
  let assigned = 0
  let skipped = 0
  let after = '0'

  while (true) {
    const page = await discord<DiscordMember[]>(`/guilds/${guild.id}/members?limit=1000&after=${after}`)
    const candidates = page.filter((member) => {
      const memberRoles = new Set(member.roles)
      const exempt = Boolean(member.user.bot)
        || member.user.id === guild.owner_id
        || memberRoles.has(verifiedRoleId)
        || memberRoles.has(unverifiedRoleId)
        || member.roles.some((roleId) => staffRoleIds.has(roleId) || roleHasAdministrator(rolesById.get(roleId)))
      if (exempt) skipped += 1
      return !exempt
    })

    await mapConcurrent(candidates, DISCORD_WRITE_CONCURRENCY, async (member) => {
      await discord<void>(`/guilds/${guild.id}/members/${member.user.id}/roles/${unverifiedRoleId}`, {
        method: 'PUT',
        headers: { 'X-Audit-Log-Reason': encodeURIComponent(BULK_VERIFICATION_AUDIT_REASON) },
      })
      assigned += 1
    })

    if (page.length < 1000) break
    after = page[page.length - 1].user.id
  }

  return { assigned, skipped }
}

async function removeDuplicateVerificationPanels(
  channelId: string,
  botUserId: string,
  canonicalMessageId: string,
): Promise<number> {
  try {
    const messages = await discord<DiscordMessage[]>(`/channels/${channelId}/messages?limit=100`)
    const duplicates = messages.filter((message) => (
      message.id !== canonicalMessageId
      && message.author?.id === botUserId
      && componentHasCustomId(message.components, 'verification:start')
    ))
    let removed = 0
    await mapConcurrent(duplicates, 2, async (message) => {
      try {
        await discord<void>(`/channels/${channelId}/messages/${message.id}`, { method: 'DELETE' })
        removed += 1
      } catch {
        // A stale panel is harmless; never fail an otherwise valid setup over cleanup.
      }
    })
    return removed
  } catch {
    return 0
  }
}

function assertPersistedSetup(
  persisted: Record<string, unknown>,
  expected: Record<string, string | boolean>,
): void {
  const mismatches = Object.entries(expected).filter(([key, value]) => {
    const stored = persisted[key]
    return typeof value === 'boolean' ? stored !== value : String(stored ?? '') !== value
  })
  if (mismatches.length > 0) {
    throw new Error(`Verification setup was not persisted: ${mismatches.map(([key]) => key).join(', ')}`)
  }
}

function assertVerificationMethodReady(method: VerificationMethod): void {
  if (method === 'website' && (
    !process.env.TURNSTILE_SITE_KEY?.trim()
    || !process.env.TURNSTILE_SECRET_KEY?.trim()
  )) {
    throw new Error('Website verification needs Cloudflare Turnstile keys on the dashboard server')
  }
}

async function automaticallySetupVerificationLocked(
  guildId: string,
  method: VerificationMethod,
) {
  assertVerificationMethodReady(method)
  const settings = await getBotGuildSettings(guildId)
  const [guild, botUser, roles, channels] = await Promise.all([
    discord<DiscordGuild>(`/guilds/${guildId}`),
    discord<DiscordUser>('/users/@me'),
    discord<DiscordRole[]>(`/guilds/${guildId}/roles`),
    discord<DiscordChannel[]>(`/guilds/${guildId}/channels`),
  ])

  const configuredVerified = roles.find((role) => role.id === String(settings.verified_role ?? settings.verification_role ?? ''))
  const configuredUnverified = roles.find((role) => role.id === String(settings.unverified_role ?? ''))
  const verified = configuredVerified
    ?? roles.find((role) => !role.managed && role.name.toLowerCase() === 'verified')
    ?? await createRole(guildId, 'Verified', 0x57f287)
  const unverified = configuredUnverified
    ?? roles.find((role) => !role.managed && role.name.toLowerCase() === 'unverified')
    ?? await createRole(guildId, 'Unverified', 0x747f8d)
  const resolvedRoles = roles.some((role) => role.id === verified.id) && roles.some((role) => role.id === unverified.id)
    ? roles
    : await discord<DiscordRole[]>(`/guilds/${guildId}/roles`)

  const configuredVerify = channels.find((channel) => channel.id === String(settings.verify_channel ?? settings.verification_channel ?? ''))
  const configuredLog = channels.find((channel) => channel.id === String(settings.verify_log_channel ?? settings.verification_log_channel ?? ''))
  const category = channels.find((channel) => channel.type === 4 && channel.name.toLowerCase() === 'start here')
    ?? await createChannel(guildId, 'START HERE', 4)
  const verifyChannel = configuredVerify
    ?? channels.find((channel) => channel.type === 0 && ['verify', 'verification'].includes(channel.name.toLowerCase()))
    ?? await createChannel(guildId, 'verify', 0, category.id)
  const logChannel = configuredLog
    ?? channels.find((channel) => channel.type === 0 && channel.name.toLowerCase() === 'verify-logs')
    ?? await createChannel(guildId, 'verify-logs', 0, category.id)

  const allChannels = await discord<DiscordChannel[]>(`/guilds/${guildId}/channels`)
  const protectedChannels = allChannels.filter((channel) => channel.id !== verifyChannel.id && channel.id !== logChannel.id)
  await mapConcurrent(protectedChannels, DISCORD_WRITE_CONCURRENCY, async (channel) => {
    await setOverwrite(channel.id, unverified.id, 0, BigInt(0), VIEW_CHANNEL)
  })
  await setOverwrite(verifyChannel.id, unverified.id, 0, VIEW_CHANNEL | READ_MESSAGE_HISTORY, SEND_MESSAGES)
  await setOverwrite(verifyChannel.id, verified.id, 0, BigInt(0), VIEW_CHANNEL)
  await setOverwrite(logChannel.id, guildId, 0, BigInt(0), VIEW_CHANNEL)
  await setOverwrite(logChannel.id, botUser.id, 1, VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY, BigInt(0))
  await mapConcurrent(
    [...configuredStaffRoleIds(settings)],
    DISCORD_WRITE_CONCURRENCY,
    async (roleId) => setOverwrite(logChannel.id, roleId, 0, VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY, BigInt(0)),
  )

  const setupChanges = {
    verification_enabled: true,
    autoroles_enabled: false,
    verification_method: method,
    verified_role: verified.id,
    verification_role: verified.id,
    unverified_role: unverified.id,
    verify_channel: verifyChannel.id,
    verification_channel: verifyChannel.id,
    verify_log_channel: logChannel.id,
    verification_log_channel: logChannel.id,
  }
  const persistedSetup = await patchBotGuildSettings(guildId, setupChanges)
  assertPersistedSetup(persistedSetup, setupChanges)

  const memberQueue = await queueExistingMembers(
    guild,
    resolvedRoles,
    persistedSetup,
    verified.id,
    unverified.id,
  )

  const existingPanelId = typeof settings.verification_panel_message_id === 'string'
    ? settings.verification_panel_message_id
    : String(settings.verification_panel_message_id ?? '')
  let panel: DiscordMessage | null = null
  if (/^\d{15,22}$/.test(existingPanelId)) {
    try {
      panel = await discord<DiscordMessage>(`/channels/${verifyChannel.id}/messages/${existingPanelId}`, {
        method: 'PATCH',
        body: JSON.stringify(panelPayload(guild, true)),
      })
    } catch {
      panel = null
    }
  }
  if (!panel) {
    panel = await discord<DiscordMessage>(`/channels/${verifyChannel.id}/messages`, {
      method: 'POST',
      body: JSON.stringify(panelPayload(guild)),
    })
  }

  const persistedPanel = await patchBotGuildSettings(guildId, {
    verification_panel_message_id: panel.id,
  })
  assertPersistedSetup(persistedPanel, { verification_panel_message_id: panel.id })
  const duplicatePanelsRemoved = await removeDuplicateVerificationPanels(
    verifyChannel.id,
    botUser.id,
    panel.id,
  )

  return {
    verifiedRoleId: verified.id,
    unverifiedRoleId: unverified.id,
    verifyChannelId: verifyChannel.id,
    logChannelId: logChannel.id,
    panelMessageId: panel.id,
    restrictedChannels: protectedChannels.length,
    existingMembersAssigned: memberQueue.assigned,
    exemptMembersSkipped: memberQueue.skipped,
    duplicatePanelsRemoved,
    verificationMethod: method,
    autoRolesDisabled: true,
  }
}

export async function automaticallySetupVerification(
  guildId: string,
  method: VerificationMethod,
) {
  if (!/^\d{15,22}$/.test(guildId)) throw new Error('Invalid Discord guild ID')
  if (method !== 'website' && method !== 'discord') throw new Error('Choose website or Discord verification')
  return withBotAdvisoryLock(
    `verification-setup:${guildId}`,
    () => automaticallySetupVerificationLocked(guildId, method),
  )
}
