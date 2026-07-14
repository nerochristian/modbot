import 'server-only'

import { botQuery, withBotTransaction } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import { recordGuildAudit } from '@/lib/bot-audit'
import {
  executeModerationAction,
  getBotGuild,
  getBotGuildMember,
  getBotGuildMemberRoles,
  sendBotChannelMessage,
} from '@/lib/discord'
import { getBotGuildSettings } from '@/lib/bot-settings'

export type ModerationActor = {
  id: string
  discordId: string
  name: string
}

export type CreateModerationInput = {
  guildId: string
  actor: ModerationActor
  targetUserId: string
  action: 'note' | 'warn' | 'mute' | 'timeout' | 'kick' | 'ban' | 'unban'
  reason: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  channel?: string | null
  durationHours?: number | null
  idempotencyKey: string
}

export class ProtectedModerationTargetError extends Error {
  constructor(message = 'This member has a protected role and cannot be muted, kicked, or banned.') {
    super(message)
    this.name = 'ProtectedModerationTargetError'
  }
}

function settingBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === 'boolean') return value
  if (value === 1 || value === '1' || value === 'true' || value === 'on' || value === 'yes') return true
  if (value === 0 || value === '0' || value === 'false' || value === 'off' || value === 'no') return false
  return fallback
}

async function assertTargetIsNotProtected(
  input: CreateModerationInput,
  settings: Record<string, unknown>,
): Promise<void> {
  if (!['mute', 'timeout', 'kick', 'ban'].includes(input.action)) return
  const botId = process.env.DISCORD_CLIENT_ID?.trim()
  if (botId && input.targetUserId === botId) {
    throw new ProtectedModerationTargetError('Docket cannot moderate itself. Choose a server member instead.')
  }
  const [guild, member, roles, botMember] = await Promise.all([
    getBotGuild(input.guildId),
    getBotGuildMember(input.guildId, input.targetUserId),
    getBotGuildMemberRoles(input.guildId),
    botId ? getBotGuildMember(input.guildId, botId) : Promise.resolve(null),
  ])
  if (input.targetUserId === guild.owner_id) {
    throw new ProtectedModerationTargetError('The server owner cannot be moderated.')
  }
  if (member.user.bot) {
    throw new ProtectedModerationTargetError('Bots cannot be moderated from the case system.')
  }

  const roleById = new Map(roles.map((role) => [role.id, role]))
  const targetRoles = member.roles.map((id) => roleById.get(id)).filter((role) => role !== undefined)
  const administratorRole = targetRoles.find((role) => {
    try {
      return (BigInt(role.permissions || '0') & BigInt(8)) === BigInt(8)
    } catch {
      return false
    }
  })
  if (administratorRole) {
    throw new ProtectedModerationTargetError('Discord administrators cannot be moderated from the dashboard.')
  }
  if (botMember) {
    const targetPosition = Math.max(0, ...targetRoles.map((role) => role.position))
    const botPosition = Math.max(0, ...botMember.roles.map((id) => roleById.get(id)?.position ?? 0))
    if (targetPosition >= botPosition) {
      throw new ProtectedModerationTargetError(
        'Docket\'s role must be above this member\'s highest role before Discord will allow that action.',
      )
    }
  }
  const configured = Array.isArray(settings.protected_roles) ? settings.protected_roles : []
  const protectedRoles = new Set(configured.map(String).filter((id) => /^\d{15,22}$/.test(id)))
  if (protectedRoles.size === 0) return
  try {
    if (member.roles.some((roleId) => protectedRoles.has(roleId))) {
      throw new ProtectedModerationTargetError()
    }
  } catch (error) {
    if (error instanceof ProtectedModerationTargetError) throw error
    if (error instanceof Error && error.message.includes('(404)')) return
    throw error
  }
}

export type ModerationCaseRow = {
  id: string
  case_number: number
  user_id: string
  moderator_id: string
  action: string
  reason: string
  duration: string | null
  created_at: Date
  updated_at: Date
  active: number | string
  severity: string
  status: string
  channel: string | null
  expires_at: Date | null
  execution_status: string
  command_id: string | null
  error_message: string | null
}

const CASE_SELECT = `SELECT c.id::text, c.case_number, c.user_id::text, c.moderator_id::text,
  LOWER(c.action) AS action, c.reason, c.duration, c.created_at, c.updated_at, c.active,
  c.severity, c.status, c.channel, c.expires_at, c.execution_status,
  cmd.id::text AS command_id, cmd.error_message
  FROM cases c
  LEFT JOIN dashboard_moderation_commands cmd ON cmd.id = c.dashboard_command_id`

export async function getModerationCase(guildId: string, caseId: string): Promise<ModerationCaseRow | null> {
  await ensureDashboardBackendSchema()
  const rows = await botQuery<ModerationCaseRow>(
    `${CASE_SELECT} WHERE c.guild_id = $1::bigint AND c.id = $2::bigint`,
    [guildId, caseId],
  )
  return rows[0] ?? null
}

async function markCommand(
  commandId: string,
  caseId: string,
  status: 'succeeded' | 'failed',
  error?: unknown,
): Promise<void> {
  const message = error instanceof Error ? error.message.slice(0, 500) : error ? String(error).slice(0, 500) : null
  await withBotTransaction(async (client) => {
    await client.query(
      `UPDATE dashboard_moderation_commands
       SET status = $2, error_code = $3, error_message = $4, updated_at = CURRENT_TIMESTAMP,
           completed_at = CURRENT_TIMESTAMP
       WHERE id = $1::bigint`,
      [commandId, status, status === 'failed' ? 'discord_action_failed' : null, message],
    )
    await client.query(
      `UPDATE cases SET execution_status = $3, status = $4, active = $5,
         updated_at = CURRENT_TIMESTAMP WHERE id = $1::bigint AND dashboard_command_id = $2::bigint`,
      [caseId, commandId, status, status === 'failed' ? 'failed' : 'open', status === 'succeeded' ? 1 : 0],
    )
  })
}

async function createPendingCase(input: CreateModerationInput): Promise<{ row: ModerationCaseRow; replayed: boolean }> {
  return withBotTransaction(async (client) => {
    const commandResult = await client.query<{ id: string; case_id: string | null }>(
      `INSERT INTO dashboard_moderation_commands (
         idempotency_key, guild_id, requested_by_id, requested_by_discord_id, requested_by_name,
         target_user_id, action, reason, duration_seconds, status
       ) VALUES ($1, $2::bigint, $3, $4::bigint, $5, $6::bigint, $7, $8, $9, 'pending')
       ON CONFLICT (guild_id, idempotency_key) DO NOTHING
       RETURNING id::text, case_id::text`,
      [
        input.idempotencyKey,
        input.guildId,
        input.actor.id,
        input.actor.discordId,
        input.actor.name,
        input.targetUserId,
        input.action,
        input.reason,
        input.durationHours ? input.durationHours * 3600 : null,
      ],
    )
    if (commandResult.rowCount === 0) {
      const existing = await client.query<{ case_id: string | null }>(
        `SELECT case_id::text FROM dashboard_moderation_commands
         WHERE guild_id = $1::bigint AND idempotency_key = $2`,
        [input.guildId, input.idempotencyKey],
      )
      const caseId = existing.rows[0]?.case_id
      if (!caseId) throw new Error('An identical moderation request is already being prepared')
      const replay = await client.query<ModerationCaseRow>(
        `${CASE_SELECT} WHERE c.guild_id = $1::bigint AND c.id = $2::bigint`,
        [input.guildId, caseId],
      )
      if (!replay.rows[0]) throw new Error('The existing moderation request has no case record')
      return { row: replay.rows[0], replayed: true }
    }

    const commandId = commandResult.rows[0].id
    await client.query('SELECT pg_advisory_xact_lock(hashtext($1))', [`dashboard-case-${input.guildId}`])
    const numberResult = await client.query<{ case_number: number }>(
      'SELECT COALESCE(MAX(case_number), 0)::int + 1 AS case_number FROM cases WHERE guild_id = $1::bigint',
      [input.guildId],
    )
    const duration = input.durationHours ? `${input.durationHours}h` : null
    const expiresAt = input.durationHours && ['mute', 'timeout'].includes(input.action)
      ? new Date(Date.now() + input.durationHours * 3_600_000)
      : null
    const inserted = await client.query<{ id: string }>(
      `INSERT INTO cases (
         guild_id, case_number, user_id, moderator_id, action, reason, duration, active,
         severity, status, channel, expires_at, execution_status, dashboard_command_id, updated_at
       ) VALUES (
         $1::bigint, $2, $3::bigint, $4::bigint, $5, $6, $7, 1,
         $8, 'pending', $9, $10, 'pending', $11::bigint, CURRENT_TIMESTAMP
       ) RETURNING id::text`,
      [
        input.guildId,
        numberResult.rows[0]?.case_number ?? 1,
        input.targetUserId,
        input.actor.discordId,
        input.action,
        input.reason,
        duration,
        input.severity,
        input.channel ?? null,
        expiresAt,
        commandId,
      ],
    )
    const caseId = inserted.rows[0].id
    await client.query(
      'UPDATE dashboard_moderation_commands SET case_id = $2::bigint, updated_at = CURRENT_TIMESTAMP WHERE id = $1::bigint',
      [commandId, caseId],
    )

    if (input.action === 'warn') {
      await client.query(
        'INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES ($1::bigint, $2::bigint, $3::bigint, $4)',
        [input.guildId, input.targetUserId, input.actor.discordId, input.reason],
      )
    } else if (input.action === 'note') {
      await client.query(
        'INSERT INTO mod_notes (guild_id, user_id, moderator_id, note) VALUES ($1::bigint, $2::bigint, $3::bigint, $4)',
        [input.guildId, input.targetUserId, input.actor.discordId, input.reason],
      )
    }

    const rowResult = await client.query<ModerationCaseRow>(
      `${CASE_SELECT} WHERE c.guild_id = $1::bigint AND c.id = $2::bigint`,
      [input.guildId, caseId],
    )
    return { row: rowResult.rows[0], replayed: false }
  })
}

export async function createModerationCase(input: CreateModerationInput): Promise<{ row: ModerationCaseRow; replayed: boolean }> {
  await ensureDashboardBackendSchema()
  const settings = await getBotGuildSettings(input.guildId)
  await assertTargetIsNotProtected(input, settings)
  const pending = await createPendingCase(input)
  if (pending.replayed) {
    if (pending.row.execution_status === 'pending' && ['warn', 'note'].includes(input.action) && pending.row.command_id) {
      await markCommand(pending.row.command_id, pending.row.id, 'succeeded')
      await recordGuildAudit(input.guildId, input.actor, `case.${input.action}`, input.targetUserId, {
        caseId: pending.row.id,
        commandId: pending.row.command_id,
        recoveredPendingCommand: true,
        executionStatus: 'succeeded',
      })
      return { row: (await getModerationCase(input.guildId, pending.row.id)) ?? pending.row, replayed: true }
    }
    return pending
  }

  const row = pending.row
  const commandId = row.command_id
  if (!commandId) throw new Error('Moderation command was not created')
  try {
    if (!['warn', 'note'].includes(input.action)) {
      await executeModerationAction(
        input.guildId,
        input.targetUserId,
        input.action,
        input.durationHours ?? 0,
        {
          reason: input.reason,
          dmUser: settingBoolean(settings.moderation_dm_users, true),
          preserveBanMessages: settingBoolean(settings.moderation_preserve_ban_messages, true),
        },
      )
    }
    await markCommand(commandId, row.id, 'succeeded')
    await recordGuildAudit(input.guildId, input.actor, `case.${input.action}`, input.targetUserId, {
      caseId: row.id,
      commandId,
      reason: input.reason,
      durationHours: input.durationHours ?? null,
      executionStatus: 'succeeded',
    })
    const logChannel = String(settings.mod_log_channel ?? settings.log_channel_mod ?? '').trim()
    if (/^\d{15,22}$/.test(logChannel)) {
      const duration = input.durationHours ? `\nDuration: ${input.durationHours} hour(s)` : ''
      await sendBotChannelMessage(
        logChannel,
        `**${input.action.toUpperCase()}** <@${input.targetUserId}>\nModerator: ${input.actor.name} (${input.actor.discordId})\nReason: ${input.reason}${duration}`,
      ).catch(() => undefined)
    }
  } catch (error) {
    await markCommand(commandId, row.id, 'failed', error)
    await recordGuildAudit(input.guildId, input.actor, `case.${input.action}.failed`, input.targetUserId, {
      caseId: row.id,
      commandId,
      error: error instanceof Error ? error.message : String(error),
      executionStatus: 'failed',
    }).catch(() => undefined)
  }
  return { row: (await getModerationCase(input.guildId, row.id)) ?? row, replayed: false }
}

async function executeReversalRequest(guildId: string, userId: string, action: 'unban' | 'clear_timeout'): Promise<void> {
  const token = process.env.DISCORD_TOKEN?.trim()
  if (!token) throw new Error('DISCORD_TOKEN is not configured')
  const path = action === 'unban'
    ? `/guilds/${guildId}/bans/${userId}`
    : `/guilds/${guildId}/members/${userId}`
  const response = await fetch(`https://discord.com/api/v10${path}`, {
    method: action === 'unban' ? 'DELETE' : 'PATCH',
    headers: {
      Authorization: `Bot ${token}`,
      ...(action === 'clear_timeout' ? { 'Content-Type': 'application/json' } : {}),
    },
    body: action === 'clear_timeout' ? JSON.stringify({ communication_disabled_until: null }) : undefined,
    cache: 'no-store',
  })
  if (!response.ok && response.status !== 404) {
    throw new Error(`Discord reversal failed (${response.status})`)
  }
}

export async function executeModerationReversal(input: {
  guildId: string
  caseId: string
  targetUserId: string
  originalAction: string
  reason: string
  actor: ModerationActor
  idempotencyKey: string
}): Promise<void> {
  await ensureDashboardBackendSchema()
  const reversalAction = input.originalAction === 'ban'
    ? 'unban'
    : ['mute', 'timeout'].includes(input.originalAction) ? 'clear_timeout' : null
  if (!reversalAction) return

  const commands = await botQuery<{ id: string; status: string }>(
    `INSERT INTO dashboard_moderation_commands (
       idempotency_key, guild_id, requested_by_id, requested_by_discord_id, requested_by_name,
       target_user_id, action, reason, status, reversal_of_case_id
     ) VALUES ($1, $2::bigint, $3, $4::bigint, $5, $6::bigint, $7, $8, 'pending', $9::bigint)
     ON CONFLICT (guild_id, idempotency_key) DO UPDATE SET
       status = CASE WHEN dashboard_moderation_commands.status = 'failed' THEN 'pending' ELSE dashboard_moderation_commands.status END,
       error_code = NULL, error_message = NULL, updated_at = CURRENT_TIMESTAMP
     RETURNING id::text, status`,
    [input.idempotencyKey, input.guildId, input.actor.id, input.actor.discordId, input.actor.name, input.targetUserId, reversalAction, input.reason, input.caseId],
  )
  const command = commands[0]
  if (command.status === 'succeeded') return
  try {
    await executeReversalRequest(input.guildId, input.targetUserId, reversalAction)
    await botQuery(
      `UPDATE dashboard_moderation_commands SET status = 'succeeded', completed_at = CURRENT_TIMESTAMP,
       updated_at = CURRENT_TIMESTAMP WHERE id = $1::bigint`,
      [command.id],
    )
  } catch (error) {
    await botQuery(
      `UPDATE dashboard_moderation_commands SET status = 'failed', error_code = 'discord_reversal_failed',
       error_message = $2, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = $1::bigint`,
      [command.id, error instanceof Error ? error.message.slice(0, 500) : String(error).slice(0, 500)],
    )
    throw error
  }
}

export function isValidIdempotencyKey(value: string): boolean {
  return /^[A-Za-z0-9._:-]{8,128}$/.test(value)
}
