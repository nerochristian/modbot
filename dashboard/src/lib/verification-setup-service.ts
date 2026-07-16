import 'server-only'

import { getBotGuildSettings, patchBotGuildSettings } from '@/lib/bot-settings'

const DISCORD_API = 'https://discord.com/api/v10'
const VIEW_CHANNEL = BigInt(1 << 10)
const SEND_MESSAGES = BigInt(1 << 11)
const READ_MESSAGE_HISTORY = BigInt(1 << 16)

type DiscordRole = { id: string; name: string; managed: boolean }
type DiscordChannel = { id: string; name: string; type: number; parent_id?: string | null }
type DiscordMessage = { id: string }

function botToken(): string {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  return token
}

async function discord<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${DISCORD_API}${path}`, {
    ...init,
    headers: {
      Authorization: `Bot ${botToken()}`,
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
    cache: 'no-store',
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => null) as { message?: string; code?: number } | null
    throw new Error(`Discord setup failed (${response.status}${detail?.code ? ` / ${detail.code}` : ''})${detail?.message ? `: ${detail.message}` : ''}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
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

async function setRoleOverwrite(
  channelId: string,
  roleId: string,
  allow: bigint,
  deny: bigint,
): Promise<void> {
  await discord<void>(`/channels/${channelId}/permissions/${roleId}`, {
    method: 'PUT',
    body: JSON.stringify({ type: 0, allow: allow.toString(), deny: deny.toString() }),
  })
}

function panelPayload() {
  return {
    content: '## ✅ Verify to enter\nPress **Start Verification** below. Docket will guide you through a private human check and unlock the server when you pass.',
    allowed_mentions: { parse: [] },
    components: [{
      type: 1,
      components: [{
        type: 2,
        style: 3,
        label: 'Start Verification',
        emoji: { name: '✅' },
        custom_id: 'verification:start',
      }],
    }],
  }
}

export async function automaticallySetupVerification(guildId: string) {
  if (!/^\d{15,22}$/.test(guildId)) throw new Error('Invalid Discord guild ID')
  const settings = await getBotGuildSettings(guildId)
  const [roles, channels] = await Promise.all([
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
  await Promise.all(protectedChannels.map((channel) => setRoleOverwrite(channel.id, unverified.id, BigInt(0), VIEW_CHANNEL)))
  await setRoleOverwrite(verifyChannel.id, unverified.id, VIEW_CHANNEL | READ_MESSAGE_HISTORY, SEND_MESSAGES)
  await setRoleOverwrite(logChannel.id, guildId, BigInt(0), VIEW_CHANNEL)

  const existingPanelId = typeof settings.verification_panel_message_id === 'string'
    ? settings.verification_panel_message_id
    : String(settings.verification_panel_message_id ?? '')
  let panel: DiscordMessage | null = null
  if (/^\d{15,22}$/.test(existingPanelId)) {
    try {
      panel = await discord<DiscordMessage>(`/channels/${verifyChannel.id}/messages/${existingPanelId}`, {
        method: 'PATCH',
        body: JSON.stringify(panelPayload()),
      })
    } catch {
      panel = null
    }
  }
  if (!panel) {
    panel = await discord<DiscordMessage>(`/channels/${verifyChannel.id}/messages`, {
      method: 'POST',
      body: JSON.stringify(panelPayload()),
    })
  }

  const method = settings.verification_method === 'website' ? 'website' : 'discord'
  await patchBotGuildSettings(guildId, {
    verification_enabled: true,
    verification_method: method,
    verified_role: verified.id,
    verification_role: verified.id,
    unverified_role: unverified.id,
    verify_channel: verifyChannel.id,
    verification_channel: verifyChannel.id,
    verify_log_channel: logChannel.id,
    verification_log_channel: logChannel.id,
    verification_panel_message_id: panel.id,
  })

  return {
    verifiedRoleId: verified.id,
    unverifiedRoleId: unverified.id,
    verifyChannelId: verifyChannel.id,
    logChannelId: logChannel.id,
    panelMessageId: panel.id,
    restrictedChannels: protectedChannels.length,
  }
}
