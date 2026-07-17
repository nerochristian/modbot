import 'server-only'

import { botQuery } from '@/lib/bot-db'

const SNOWFLAKE_SETTING_KEYS = [
  'owner_role',
  'admin_role',
  'manager_role',
  'supervisor_role',
  'senior_mod_role',
  'mod_role',
  'trial_mod_role',
  'staff_role',
  'antiraid_quarantine_role',
  'verified_role',
  'verification_role',
  'unverified_role',
  'verify_channel',
  'verification_channel',
  'verify_log_channel',
  'verification_log_channel',
  'waiting_verify_voice_channel',
  'ticket_category',
  'ticket_support_role',
  'ticket_log_channel',
  'log_channel_mod',
  'mod_log_channel',
  'log_channel_audit',
  'log_channel_message',
  'log_channel_voice',
  'log_channel_automod',
  'log_channel_report',
  'log_channel_ticket',
  'audit_log_channel',
  'message_log_channel',
  'voice_log_channel',
  'log_channel_mod',
  'mod_log_channel',
  'log_channel_audit',
  'log_channel_message',
  'log_channel_voice',
  'log_channel_automod',
  'log_channel_report',
  'log_channel_ticket',
  'audit_log_channel',
  'message_log_channel',
  'voice_log_channel',
  'automod_log_channel',
  'report_log_channel',
  'welcome_channel',
  'auto_role',
] as const

export async function getBotGuildSettings(guildId: string): Promise<Record<string, unknown>> {
  const rows = await botQuery<{ settings: string | Record<string, unknown> }>(
    `SELECT settings FROM guild_settings WHERE guild_id = $1::bigint`,
    [guildId],
  )
  const value = rows[0]?.settings
  if (!value) return {}
  
  let parsed: any = typeof value === 'string' ? {} : value
  if (typeof value === 'string') {
    try {
      parsed = JSON.parse(value)
    } catch {
      return {}
    }
  }
  
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    for (const key of SNOWFLAKE_SETTING_KEYS) {
      if (typeof parsed[key] === 'number') {
        parsed[key] = String(parsed[key])
      }
    }
    return parsed
  }
  return {}
}

export async function patchBotGuildSettings(
  guildId: string,
  changes: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const current = await getBotGuildSettings(guildId)
  const updated = { ...current, ...changes }
  
  await botQuery<{ guild_id: string }>(
    `INSERT INTO guild_settings (guild_id, settings)
     VALUES ($1::bigint, $2)
     ON CONFLICT (guild_id) DO UPDATE
     SET settings = $2
     RETURNING guild_id`,
    [guildId, JSON.stringify(updated)],
  )
  return updated
}
