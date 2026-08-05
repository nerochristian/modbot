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
  'verification_panel_message_id',
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
  'automod_log_channel',
  'report_log_channel',
  'welcome_channel',
  'auto_role',
] as const

export async function getBotGuildSettings(guildId: string): Promise<Record<string, unknown>> {
  const rows = await botQuery<{ settings: string | Record<string, unknown> }>(
    `SELECT COALESCE(
       jsonb_object_agg(
         entry.key,
         CASE
           WHEN entry.key = ANY($2::text[]) AND jsonb_typeof(entry.value) = 'number'
             THEN to_jsonb(entry.value #>> '{}')
           ELSE entry.value
         END
       ) FILTER (WHERE entry.key IS NOT NULL),
       '{}'::jsonb
     )::text AS settings
     FROM guild_settings AS guild
     LEFT JOIN LATERAL jsonb_each(COALESCE(NULLIF(guild.settings, ''), '{}')::jsonb) AS entry ON TRUE
     WHERE guild.guild_id = $1::bigint
     GROUP BY guild.guild_id`,
    [guildId, SNOWFLAKE_SETTING_KEYS],
  )
  const value = rows[0]?.settings
  if (!value) return {}
  if (typeof value === 'object') return value
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

export async function patchBotGuildSettings(
  guildId: string,
  changes: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  await botQuery<{ guild_id: string }>(
    `INSERT INTO guild_settings (guild_id, settings)
     VALUES ($1::bigint, $2::jsonb::text)
     ON CONFLICT (guild_id) DO UPDATE
     SET settings = (
       COALESCE(NULLIF(guild_settings.settings, ''), '{}')::jsonb || EXCLUDED.settings::jsonb
     )::text
     RETURNING guild_id`,
    [guildId, JSON.stringify(changes)],
  )
  return getBotGuildSettings(guildId)
}
