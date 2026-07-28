import 'server-only'

import { createHash, randomBytes } from 'node:crypto'
import { botQuery, withBotTransaction } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import { recordGuildAudit } from '@/lib/bot-audit'
import { getBotGuildSettings } from '@/lib/bot-settings'
import { DEFAULT_APPEAL_QUESTIONS, type TicketQuestion } from '@/lib/modules-contract'

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{43}$/
const APPEALABLE_ACTIONS = new Set(['automod', 'warn', 'mute', 'timeout', 'kick', 'ban', 'tempban', 'softban', 'quarantine'])

type DiscordUserProfile = { username?: string; global_name?: string | null }
type DiscordGuildProfile = { name?: string; icon?: string | null }
type DiscordApplicationEmoji = { id: string; name: string; animated?: boolean }

let applicationEmojiCache: { expiresAt: number; items: DiscordApplicationEmoji[] } | null = null

function discordBotToken(): string {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  return token
}

async function discordGet<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`https://discord.com/api/v10${path}`, {
      headers: { Authorization: `Bot ${discordBotToken()}` },
      cache: 'no-store',
    })
    return response.ok ? response.json() as Promise<T> : null
  } catch {
    return null
  }
}

async function applicationEmojis(): Promise<DiscordApplicationEmoji[]> {
  if (applicationEmojiCache && applicationEmojiCache.expiresAt > Date.now()) return applicationEmojiCache.items
  const applicationId = process.env.DISCORD_CLIENT_ID?.trim()
  if (!applicationId) return []
  const payload = await discordGet<{ items?: DiscordApplicationEmoji[] }>(`/applications/${applicationId}/emojis`)
  const items = Array.isArray(payload?.items) ? payload.items : []
  applicationEmojiCache = { expiresAt: Date.now() + 10 * 60_000, items }
  return items
}

async function statusEmoji(kind: 'ban' | 'kick' | 'mute' | 'warn' | 'lock' | 'info' | 'id') {
  const defaults = {
    ban: ['STATUS_BAN_EMOJI_NAME', 'mod_ban', '🔨'],
    kick: ['STATUS_KICK_EMOJI_NAME', 'mod_kick', '🥾'],
    mute: ['STATUS_MUTE_EMOJI_NAME', 'mod_mute', '🔇'],
    warn: ['STATUS_WARN_EMOJI_NAME', 'mod_warn', '⚠️'],
    lock: ['STATUS_LOCK_EMOJI_NAME', 'mod_lock', '🔒'],
    info: ['STATUS_INFO_EMOJI_NAME', 'mod_info', 'ℹ️'],
    id: ['STATUS_ID_EMOJI_NAME', 'mod_id', '🆔'],
  } as const
  const [envName, defaultName, fallback] = defaults[kind]
  const name = process.env[envName]?.trim() || defaultName
  const emoji = (await applicationEmojis()).find((item) => item.name === name)
  return emoji
    ? { mention: `<${emoji.animated ? 'a' : ''}:${emoji.name}:${emoji.id}>`, component: { id: emoji.id, name: emoji.name, animated: Boolean(emoji.animated) } }
    : { mention: fallback, component: { name: fallback } }
}

function tokenHash(token: string): string {
  return createHash('sha256').update(token, 'utf8').digest('hex')
}

function escapeDiscordMarkdown(value: string): string {
  return value.replace(/([\\`*_{}\[\]()<>#+\-.!|])/g, '\\$1')
}

function questionsFrom(value: unknown): TicketQuestion[] {
  if (!Array.isArray(value)) return structuredClone(DEFAULT_APPEAL_QUESTIONS)
  const seen = new Set<string>()
  const questions = value.flatMap((raw): TicketQuestion[] => {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return []
    const item = raw as Record<string, unknown>
    const id = String(item.id ?? '').trim().toLowerCase()
    const label = String(item.label ?? '').trim()
    if (!/^[a-z0-9_-]{2,40}$/.test(id) || seen.has(id) || label.length < 2 || label.length > 80) return []
    seen.add(id)
    return [{
      id,
      label,
      placeholder: String(item.placeholder ?? '').trim().slice(0, 160),
      style: item.style === 'short' ? 'short' : 'paragraph',
      required: item.required !== false,
    }]
  }).slice(0, 5)
  return questions.length ? questions : structuredClone(DEFAULT_APPEAL_QUESTIONS)
}

function parseQuestions(value: string | null | undefined): TicketQuestion[] {
  try { return questionsFrom(JSON.parse(value || '[]')) } catch { return structuredClone(DEFAULT_APPEAL_QUESTIONS) }
}

async function discordMessage(channelId: string, payload: Record<string, unknown>): Promise<{ id: string }> {
  const response = await fetch(`https://discord.com/api/v10/channels/${channelId}/messages`, {
    method: 'POST',
    headers: { Authorization: `Bot ${discordBotToken()}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    cache: 'no-store',
  })
  if (!response.ok) throw new Error(`Discord message delivery failed (${response.status})`)
  return response.json() as Promise<{ id: string }>
}

async function dmChannel(userId: string): Promise<string> {
  const response = await fetch('https://discord.com/api/v10/users/@me/channels', {
    method: 'POST',
    headers: { Authorization: `Bot ${discordBotToken()}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient_id: userId }),
    cache: 'no-store',
  })
  if (!response.ok) throw new Error(`Discord DM channel creation failed (${response.status})`)
  const channel = await response.json() as { id?: string }
  if (!channel.id) throw new Error('Discord did not return a DM channel')
  return channel.id
}

async function sendPunishmentDm(input: {
  guildId: string
  userId: string
  caseNumber: number
  action: string
  reason: string
  duration?: string | null
  punishmentExpiresAt?: Date | null
  appealUrl?: string | null
  expiresAt?: Date | null
  dmChannelId?: string | null
}): Promise<void> {
  const action = input.action.toLowerCase()
  const actionText = ({
    automod: 'Your message was **removed**',
    warn: 'You received a **warning**',
    mute: 'You have been **muted**',
    timeout: 'You have been **timed out**',
    kick: 'You have been **kicked**',
    ban: 'You have been **banned**',
    tempban: 'You have been **temporarily banned**',
    softban: 'You have been **softbanned**',
    quarantine: 'You have been **quarantined**',
  } as Record<string, string>)[action] ?? 'Moderation action'
  const emojiKind = action === 'automod' || action === 'warn'
    ? 'warn'
    : action === 'mute' || action === 'timeout'
      ? 'mute'
      : action === 'kick'
        ? 'kick'
        : action === 'quarantine'
          ? 'lock'
          : 'ban'
  const [profile, guild, actionEmoji, infoEmoji, idEmoji] = await Promise.all([
    discordGet<DiscordUserProfile>(`/users/${input.userId}`),
    discordGet<DiscordGuildProfile>(`/guilds/${input.guildId}`),
    statusEmoji(emojiKind),
    statusEmoji('info'),
    statusEmoji('id'),
  ])
  const title = escapeDiscordMarkdown(profile?.global_name || profile?.username || 'Member').slice(0, 80)
  const actionLine = `${actionEmoji.mention} ${actionText}${input.duration && !input.punishmentExpiresAt ? ` for **${input.duration}**` : ''}`
  const guildIcon = guild?.icon
    ? `https://cdn.discordapp.com/icons/${input.guildId}/${guild.icon}.${guild.icon.startsWith('a_') ? 'gif' : 'png'}?size=256`
    : undefined
  const punishmentTimestamp = input.punishmentExpiresAt
    ? Math.floor(input.punishmentExpiresAt.getTime() / 1000)
    : null
  const header = `## ${title} !!” 🥢\n${actionLine}${punishmentTimestamp ? `\nuntil <t:${punishmentTimestamp}:R>` : ''}`
  const details = `**Reason :**\n> ${(input.reason || 'No reason provided').slice(0, 700)}\n-# ${idEmoji.mention} \`user:${input.userId} date:${new Date().toISOString().slice(0, 10)}\``
  const headerComponent = guildIcon
    ? { type: 9, components: [{ type: 10, content: header }], accessory: { type: 11, media: { url: guildIcon } } }
    : { type: 10, content: header }
  const components: Record<string, unknown>[] = [{
    type: 17,
    accent_color: ['ban', 'tempban', 'softban'].includes(action) ? 0xed4245 : 0xf0b232,
    components: [
      headerComponent,
      { type: 14, divider: true, spacing: 1 },
      { type: 10, content: details },
    ],
  }]
  if (punishmentTimestamp) {
    components.push({ type: 10, content: `Available again <t:${punishmentTimestamp}:R>` })
  }
  if (input.appealUrl) {
    components.push({
      type: 1,
      components: [{ type: 2, style: 5, label: 'Appeal here', url: input.appealUrl, emoji: infoEmoji.component }],
    })
  }
  await discordMessage(input.dmChannelId || await dmChannel(input.userId), {
    flags: 1 << 15,
    components,
    allowed_mentions: { parse: [] },
  })
}

export async function issueAppealToken(input: {
  guildId: string
  caseId: string
  caseNumber: number
  targetUserId: string
  action: string
  reason: string
  duration?: string | null
  punishmentExpiresAt?: Date | null
  publicBaseUrl: string
  dmChannelId?: string | null
}) {
  await ensureDashboardBackendSchema()
  const settings = await getBotGuildSettings(input.guildId)
  if (!APPEALABLE_ACTIONS.has(input.action.toLowerCase())) return { eligible: false as const }
  const enabled = settings.appeals_enabled !== false
  const open = settings.appeals_open !== false
  const eligible = enabled && open && /^https?:\/\//.test(input.publicBaseUrl)
  if (!eligible) {
    try {
      await sendPunishmentDm({ guildId: input.guildId, userId: input.targetUserId, caseNumber: input.caseNumber, action: input.action, reason: input.reason, duration: input.duration, punishmentExpiresAt: input.punishmentExpiresAt, dmChannelId: input.dmChannelId })
      return { eligible: false as const, deliveryStatus: 'sent' as const }
    } catch (error) {
      return { eligible: false as const, deliveryStatus: 'failed' as const, deliveryError: error instanceof Error ? error.message.slice(0, 500) : String(error).slice(0, 500) }
    }
  }

  const token = randomBytes(32).toString('base64url')
  const hash = tokenHash(token)
  const expiryDays = Math.min(30, Math.max(1, Number(settings.appeal_expiry_days) || 7))
  const expiresAt = new Date(Date.now() + expiryDays * 86_400_000)
  const questions = questionsFrom(settings.appeal_questions)
  const rows = await botQuery<{ id: string }>(
    `INSERT INTO dashboard_appeal_tokens (
       token_hash, guild_id, case_id, user_id, expires_at, used_at, appeal_id,
       delivery_status, delivery_error, questions_json
     ) VALUES ($1, $2::bigint, $3::bigint, $4::bigint, $5, NULL, NULL, 'pending', NULL, $6)
     ON CONFLICT (guild_id, case_id) DO UPDATE SET
       token_hash = EXCLUDED.token_hash, user_id = EXCLUDED.user_id, expires_at = EXCLUDED.expires_at,
       used_at = NULL, appeal_id = NULL, delivery_status = 'pending', delivery_error = NULL,
       questions_json = EXCLUDED.questions_json, created_at = CURRENT_TIMESTAMP
     RETURNING id::text`,
    [hash, input.guildId, input.caseId, input.targetUserId, expiresAt, JSON.stringify(questions)],
  )
  const appealUrl = `${input.publicBaseUrl.replace(/\/$/, '')}/appeal/${token}`
  let deliveryStatus = 'sent'
  let deliveryError: string | null = null
  try {
    await sendPunishmentDm({ ...input, userId: input.targetUserId, appealUrl, expiresAt })
  } catch (error) {
    deliveryStatus = 'failed'
    deliveryError = error instanceof Error ? error.message.slice(0, 500) : String(error).slice(0, 500)
  }
  await botQuery(
    `UPDATE dashboard_appeal_tokens SET delivery_status = $2, delivery_error = $3 WHERE id = $1::bigint`,
    [rows[0].id, deliveryStatus, deliveryError],
  )
  return { eligible: true as const, appealUrl, expiresAt: expiresAt.toISOString(), deliveryStatus }
}

type PortalTokenRow = {
  id: string
  guild_id: string
  case_id: string
  user_id: string
  expires_at: Date
  used_at: Date | null
  appeal_id: string | null
  questions_json: string
  case_number: number
  action: string
  reason: string
  case_status: string
  created_at: Date
}

async function findPortalToken(token: string): Promise<PortalTokenRow | null> {
  if (!TOKEN_PATTERN.test(token)) return null
  await ensureDashboardBackendSchema()
  const rows = await botQuery<PortalTokenRow>(
    `SELECT tokens.id::text, tokens.guild_id::text, tokens.case_id::text, tokens.user_id::text,
       tokens.expires_at, tokens.used_at, tokens.appeal_id::text, tokens.questions_json, cases.case_number,
       LOWER(cases.action) AS action, cases.reason, cases.status AS case_status, cases.created_at
     FROM dashboard_appeal_tokens tokens
     JOIN cases ON cases.guild_id = tokens.guild_id AND cases.id = tokens.case_id
     WHERE tokens.token_hash = $1`,
    [tokenHash(token)],
  )
  return rows[0] ?? null
}

export async function getAppealPortalCase(token: string) {
  const row = await findPortalToken(token)
  if (!row) return { kind: 'not_found' as const }
  const settings = await getBotGuildSettings(row.guild_id)
  if (settings.appeals_enabled === false || settings.appeals_open === false) return { kind: 'closed' as const }
  if (new Date(row.expires_at).getTime() <= Date.now()) return { kind: 'expired' as const }
  if (row.used_at) return { kind: 'used' as const }
  return {
    kind: 'ok' as const,
    questions: parseQuestions(row.questions_json),
    case: {
      ref: Number(row.case_number),
      action: row.action,
      reason: row.reason,
      status: row.case_status,
      createdAt: new Date(row.created_at).toISOString(),
      expiresAt: new Date(row.expires_at).toISOString(),
    },
  }
}

function validateAnswers(questions: TicketQuestion[], answers: Record<string, string>): Record<string, string> {
  const accepted = new Set(questions.map((question) => question.id))
  const normalized: Record<string, string> = {}
  for (const question of questions) {
    const value = String(answers[question.id] ?? '').trim()
    const limit = question.style === 'short' ? 300 : 2000
    if (question.required && value.length < 3) throw new Error(`${question.label} needs an answer`)
    if (value.length > limit) throw new Error(`${question.label} is too long`)
    if (value) normalized[question.id] = value
  }
  if (Object.keys(answers).some((key) => !accepted.has(key))) throw new Error('The appeal contains an unknown question')
  if (Object.values(normalized).join('').length > 6000) throw new Error('The appeal is too long')
  return normalized
}

async function notifyStaff(input: {
  appealId: string
  appealNumber: number
  guildId: string
  userId: string
  caseId: string
  caseNumber: number
  action: string
  reason: string
  questions: TicketQuestion[]
  answers: Record<string, string>
}): Promise<void> {
  const settings = await getBotGuildSettings(input.guildId)
  const channelId = String(settings.appeal_staff_channel ?? '').trim()
  if (!/^\d{15,22}$/.test(channelId)) {
    await botQuery(`UPDATE dashboard_appeals SET staff_delivery_error = 'Staff review channel is not configured' WHERE id = $1::bigint`, [input.appealId])
    return
  }
  const fields = [
    { name: 'Member', value: `<@${input.userId}> · \`${input.userId}\``, inline: false },
    { name: 'Linked case', value: `CASE-${String(input.caseNumber).padStart(4, '0')} · ${input.action.toUpperCase()}`, inline: true },
    { name: 'Original reason', value: input.reason.slice(0, 1024), inline: false },
    ...input.questions.filter((question) => input.answers[question.id]).map((question) => ({
      name: question.label.slice(0, 256),
      value: input.answers[question.id].slice(0, 1024),
      inline: false,
    })),
  ].slice(0, 25)
  const publicBase = (process.env.DASHBOARD_PUBLIC_URL || process.env.FRONTEND_PUBLIC_URL || '').replace(/\/$/, '')
  try {
    const sent = await discordMessage(channelId, {
      embeds: [{ title: `New appeal · APL-${String(input.appealNumber).padStart(4, '0')}`, description: 'A member requested staff review of a moderation case.', color: 0x5865f2, fields, footer: { text: 'Docket · Appeals review queue' } }],
      components: publicBase ? [{ type: 1, components: [{ type: 2, style: 5, label: 'Review in dashboard', url: `${publicBase}/dashboard/appeals` }] }] : [],
      allowed_mentions: { parse: [] },
    })
    await botQuery(`UPDATE dashboard_appeals SET staff_channel_id = $2::bigint, staff_message_id = $3::bigint, staff_delivery_error = NULL WHERE id = $1::bigint`, [input.appealId, channelId, sent.id])
  } catch (error) {
    const message = error instanceof Error ? error.message.slice(0, 500) : String(error).slice(0, 500)
    await botQuery(`UPDATE dashboard_appeals SET staff_channel_id = $2::bigint, staff_delivery_error = $3 WHERE id = $1::bigint`, [input.appealId, channelId, message])
  }
}

export async function submitAppealWithToken(token: string, answers: Record<string, string>) {
  if (!TOKEN_PATTERN.test(token)) return { kind: 'not_found' as const }
  await ensureDashboardBackendSchema()
  const hash = tokenHash(token)
  const result = await withBotTransaction(async (client) => {
    const tokenResult = await client.query<PortalTokenRow>(
      `SELECT tokens.id::text, tokens.guild_id::text, tokens.case_id::text, tokens.user_id::text,
         tokens.expires_at, tokens.used_at, tokens.appeal_id::text, tokens.questions_json, cases.case_number,
         LOWER(cases.action) AS action, cases.reason, cases.status AS case_status, cases.created_at
       FROM dashboard_appeal_tokens tokens
       JOIN cases ON cases.guild_id = tokens.guild_id AND cases.id = tokens.case_id
       WHERE tokens.token_hash = $1 FOR UPDATE OF tokens`,
      [hash],
    )
    const row = tokenResult.rows[0]
    if (!row) return { kind: 'not_found' as const }
    const settings = await getBotGuildSettings(row.guild_id)
    if (settings.appeals_enabled === false || settings.appeals_open === false) return { kind: 'closed' as const }
    if (new Date(row.expires_at).getTime() <= Date.now()) return { kind: 'expired' as const }
    if (row.used_at) return { kind: 'used' as const }
    const questions = parseQuestions(row.questions_json)
    const normalizedAnswers = validateAnswers(questions, answers)
    const message = questions.map((question) => normalizedAnswers[question.id]).filter(Boolean).join('\n\n').slice(0, 6000)

    await client.query('SELECT pg_advisory_xact_lock(hashtext($1))', [`dashboard-appeal-${row.guild_id}`])
    const next = await client.query<{ appeal_number: number }>(`SELECT COALESCE(MAX(appeal_number), 0)::int + 1 AS appeal_number FROM dashboard_appeals WHERE guild_id = $1::bigint`, [row.guild_id])
    const inserted = await client.query<{ id: string; appeal_number: number }>(
      `INSERT INTO dashboard_appeals (guild_id, appeal_number, case_id, user_id, message, answers_json, status)
       VALUES ($1::bigint, $2, $3::bigint, $4::bigint, $5, $6, 'pending') RETURNING id::text, appeal_number`,
      [row.guild_id, next.rows[0]?.appeal_number ?? 1, row.case_id, row.user_id, message, JSON.stringify(normalizedAnswers)],
    )
    await client.query(`UPDATE dashboard_appeal_tokens SET used_at = CURRENT_TIMESTAMP, appeal_id = $2::bigint WHERE id = $1::bigint`, [row.id, inserted.rows[0].id])
    await client.query(`UPDATE cases SET status = 'appealed', updated_at = CURRENT_TIMESTAMP WHERE guild_id = $1::bigint AND id = $2::bigint`, [row.guild_id, row.case_id])
    await recordGuildAudit(row.guild_id, { id: row.user_id, name: `Discord user ${row.user_id}` }, 'appeal.submitted', inserted.rows[0].id, { caseId: row.case_id, appealNumber: inserted.rows[0].appeal_number }, client)
    return { kind: 'ok' as const, appeal: { id: inserted.rows[0].id, ref: inserted.rows[0].appeal_number }, notification: { appealId: inserted.rows[0].id, appealNumber: inserted.rows[0].appeal_number, guildId: row.guild_id, userId: row.user_id, caseId: row.case_id, caseNumber: row.case_number, action: row.action, reason: row.reason, questions, answers: normalizedAnswers } }
  })
  if (result.kind === 'ok') await notifyStaff(result.notification)
  return result.kind === 'ok' ? { kind: 'ok' as const, appeal: result.appeal } : result
}

export async function notifyAppealDecision(input: { userId: string; appealNumber: number; caseNumber: number; status: 'approved' | 'denied'; decision?: string | null; staffChannelId?: string | null }) {
  const description = input.status === 'approved' ? 'Staff approved your appeal and reversed the supported punishment.' : 'Staff denied your appeal. The original moderation action remains in place.'
  const payload = { embeds: [{ title: `Appeal ${input.status}`, description, color: input.status === 'approved' ? 0x57f287 : 0xed4245, fields: [{ name: 'Appeal', value: `APL-${String(input.appealNumber).padStart(4, '0')}`, inline: true }, { name: 'Case', value: `CASE-${String(input.caseNumber).padStart(4, '0')}`, inline: true }, ...(input.decision ? [{ name: 'Staff response', value: input.decision.slice(0, 1024), inline: false }] : [])], footer: { text: 'Docket · Appeals review queue' } }], allowed_mentions: { parse: [] } }
  try {
    const channelId = await dmChannel(input.userId)
    await discordMessage(channelId, payload).catch(() => undefined)
  } catch {
    // Appellant has DMs closed; the review itself already succeeded.
  }
  if (input.staffChannelId) await discordMessage(input.staffChannelId, { ...payload, content: `Appeal APL-${String(input.appealNumber).padStart(4, '0')} was **${input.status}**.` }).catch(() => undefined)
}
