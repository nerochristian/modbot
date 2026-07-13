import 'server-only'

import { createHash, randomBytes } from 'node:crypto'
import { botQuery, withBotTransaction } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import { recordGuildAudit } from '@/lib/bot-audit'

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{43}$/
const APPEALABLE_ACTIONS = new Set(['warn', 'mute', 'timeout', 'kick', 'ban'])

function tokenHash(token: string): string {
  return createHash('sha256').update(token, 'utf8').digest('hex')
}

async function sendAppealDm(userId: string, appealUrl: string, caseNumber: number, action: string): Promise<void> {
  const botToken = process.env.DISCORD_TOKEN?.trim()
  if (!botToken) throw new Error('DISCORD_TOKEN is not configured')
  const dm = await fetch('https://discord.com/api/v10/users/@me/channels', {
    method: 'POST',
    headers: { Authorization: `Bot ${botToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient_id: userId }),
    cache: 'no-store',
  })
  if (!dm.ok) throw new Error(`Discord DM channel creation failed (${dm.status})`)
  const channel = await dm.json() as { id?: string }
  if (!channel.id) throw new Error('Discord did not return a DM channel')
  const sent = await fetch(`https://discord.com/api/v10/channels/${channel.id}/messages`, {
    method: 'POST',
    headers: { Authorization: `Bot ${botToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: `A moderation action (**${action}**, case #${caseNumber}) was recorded for you. ` +
        `If you believe it should be reviewed, submit one appeal within 7 days: ${appealUrl}`,
      allowed_mentions: { parse: [] },
    }),
    cache: 'no-store',
  })
  if (!sent.ok) throw new Error(`Discord DM delivery failed (${sent.status})`)
}

export async function issueAppealToken(input: {
  guildId: string
  caseId: string
  caseNumber: number
  targetUserId: string
  action: string
  publicBaseUrl: string
}) {
  if (!APPEALABLE_ACTIONS.has(input.action)) return { eligible: false as const }
  await ensureDashboardBackendSchema()
  const token = randomBytes(32).toString('base64url')
  const hash = tokenHash(token)
  const expiresAt = new Date(Date.now() + 7 * 86_400_000)
  const rows = await botQuery<{ id: string }>(
    `INSERT INTO dashboard_appeal_tokens (
       token_hash, guild_id, case_id, user_id, expires_at, used_at, appeal_id,
       delivery_status, delivery_error
     ) VALUES ($1, $2::bigint, $3::bigint, $4::bigint, $5, NULL, NULL, 'pending', NULL)
     ON CONFLICT (guild_id, case_id) DO UPDATE SET
       token_hash = EXCLUDED.token_hash, user_id = EXCLUDED.user_id, expires_at = EXCLUDED.expires_at,
       used_at = NULL, appeal_id = NULL, delivery_status = 'pending', delivery_error = NULL,
       created_at = CURRENT_TIMESTAMP
     RETURNING id::text`,
    [hash, input.guildId, input.caseId, input.targetUserId, expiresAt],
  )
  const appealUrl = `${input.publicBaseUrl.replace(/\/$/, '')}/appeal/${token}`
  let deliveryStatus = 'sent'
  let deliveryError: string | null = null
  try {
    await sendAppealDm(input.targetUserId, appealUrl, input.caseNumber, input.action)
  } catch (error) {
    deliveryStatus = 'failed'
    deliveryError = error instanceof Error ? error.message.slice(0, 500) : String(error).slice(0, 500)
  }
  await botQuery(
    `UPDATE dashboard_appeal_tokens SET delivery_status = $2, delivery_error = $3 WHERE id = $1::bigint`,
    [rows[0].id, deliveryStatus, deliveryError],
  )
  return {
    eligible: true as const,
    appealUrl,
    expiresAt: expiresAt.toISOString(),
    deliveryStatus,
  }
}

type PortalTokenRow = {
  id: string
  guild_id: string
  case_id: string
  user_id: string
  expires_at: Date
  used_at: Date | null
  appeal_id: string | null
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
       tokens.expires_at, tokens.used_at, tokens.appeal_id::text, cases.case_number,
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
  if (new Date(row.expires_at).getTime() <= Date.now()) return { kind: 'expired' as const }
  if (row.used_at) return { kind: 'used' as const }
  return {
    kind: 'ok' as const,
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

export async function submitAppealWithToken(token: string, message: string) {
  if (!TOKEN_PATTERN.test(token)) return { kind: 'not_found' as const }
  await ensureDashboardBackendSchema()
  const hash = tokenHash(token)
  return withBotTransaction(async (client) => {
    const tokenResult = await client.query<PortalTokenRow>(
      `SELECT tokens.id::text, tokens.guild_id::text, tokens.case_id::text, tokens.user_id::text,
         tokens.expires_at, tokens.used_at, tokens.appeal_id::text, cases.case_number,
         LOWER(cases.action) AS action, cases.reason, cases.status AS case_status, cases.created_at
       FROM dashboard_appeal_tokens tokens
       JOIN cases ON cases.guild_id = tokens.guild_id AND cases.id = tokens.case_id
       WHERE tokens.token_hash = $1 FOR UPDATE OF tokens`,
      [hash],
    )
    const row = tokenResult.rows[0]
    if (!row) return { kind: 'not_found' as const }
    if (new Date(row.expires_at).getTime() <= Date.now()) return { kind: 'expired' as const }
    if (row.used_at) return { kind: 'used' as const }

    await client.query('SELECT pg_advisory_xact_lock(hashtext($1))', [`dashboard-appeal-${row.guild_id}`])
    const next = await client.query<{ appeal_number: number }>(
      `SELECT COALESCE(MAX(appeal_number), 0)::int + 1 AS appeal_number
       FROM dashboard_appeals WHERE guild_id = $1::bigint`,
      [row.guild_id],
    )
    const inserted = await client.query<{ id: string; appeal_number: number }>(
      `INSERT INTO dashboard_appeals (guild_id, appeal_number, case_id, user_id, message, status)
       VALUES ($1::bigint, $2, $3::bigint, $4::bigint, $5, 'pending')
       RETURNING id::text, appeal_number`,
      [row.guild_id, next.rows[0]?.appeal_number ?? 1, row.case_id, row.user_id, message],
    )
    await client.query(
      `UPDATE dashboard_appeal_tokens SET used_at = CURRENT_TIMESTAMP, appeal_id = $2::bigint
       WHERE id = $1::bigint`,
      [row.id, inserted.rows[0].id],
    )
    await client.query(
      `UPDATE cases SET status = 'appealed', updated_at = CURRENT_TIMESTAMP
       WHERE guild_id = $1::bigint AND id = $2::bigint`,
      [row.guild_id, row.case_id],
    )
    await recordGuildAudit(
      row.guild_id,
      { id: row.user_id, name: `Discord user ${row.user_id}` },
      'appeal.submitted',
      inserted.rows[0].id,
      { caseId: row.case_id, appealNumber: inserted.rows[0].appeal_number },
      client,
    )
    return { kind: 'ok' as const, appeal: { id: inserted.rows[0].id, ref: inserted.rows[0].appeal_number } }
  })
}
