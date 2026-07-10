import 'server-only'

import { botQuery } from '@/lib/bot-db'

export async function getBotGuildSettings(guildId: string): Promise<Record<string, unknown>> {
  const rows = await botQuery<{ settings: string | Record<string, unknown> }>(
    'SELECT settings FROM guild_settings WHERE guild_id = $1::bigint',
    [guildId],
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
  const rows = await botQuery<{ settings: string | Record<string, unknown> }>(
    `UPDATE guild_settings
     SET settings = (COALESCE(NULLIF(settings, ''), '{}')::jsonb || $2::jsonb)::text
     WHERE guild_id = $1::bigint
     RETURNING settings`,
    [guildId, JSON.stringify(changes)],
  )
  if (!rows[0]) throw new Error('Guild settings are not initialized')
  const value = rows[0].settings
  return typeof value === 'object' ? value : JSON.parse(value)
}
