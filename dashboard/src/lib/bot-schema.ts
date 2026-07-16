import 'server-only'

import { botQuery } from '@/lib/bot-db'

let schemaPromise: Promise<void> | null = null

async function initializeSchema(): Promise<void> {
  await botQuery(`
    CREATE TABLE IF NOT EXISTS dashboard_moderation_commands (
      id BIGSERIAL PRIMARY KEY,
      idempotency_key TEXT NOT NULL,
      guild_id BIGINT NOT NULL,
      requested_by_id TEXT NOT NULL,
      requested_by_discord_id BIGINT,
      requested_by_name TEXT NOT NULL,
      target_user_id BIGINT NOT NULL,
      action TEXT NOT NULL,
      reason TEXT NOT NULL,
      duration_seconds INTEGER,
      status TEXT NOT NULL DEFAULT 'pending',
      case_id BIGINT,
      reversal_of_case_id BIGINT,
      error_code TEXT,
      error_message TEXT,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      completed_at TIMESTAMP,
      UNIQUE (guild_id, idempotency_key)
    )
  `)
  await botQuery(`
    CREATE INDEX IF NOT EXISTS idx_dashboard_commands_guild_created
    ON dashboard_moderation_commands(guild_id, created_at DESC)
  `)
  await botQuery(`
    CREATE TABLE IF NOT EXISTS dashboard_appeals (
      id BIGSERIAL PRIMARY KEY,
      guild_id BIGINT NOT NULL,
      appeal_number INTEGER NOT NULL,
      case_id BIGINT NOT NULL,
      user_id BIGINT NOT NULL,
      message TEXT NOT NULL,
      answers_json TEXT NOT NULL DEFAULT '{}',
      status TEXT NOT NULL DEFAULT 'pending',
      decision TEXT,
      reviewed_by_id TEXT,
      reviewed_by_name TEXT,
      submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      reviewed_at TIMESTAMP,
      staff_channel_id BIGINT,
      staff_message_id BIGINT,
      staff_delivery_error TEXT,
      UNIQUE (guild_id, appeal_number)
    )
  `)
  await botQuery(`
    CREATE INDEX IF NOT EXISTS idx_dashboard_appeals_guild_status
    ON dashboard_appeals(guild_id, status, submitted_at DESC)
  `)
  await botQuery(`
    CREATE TABLE IF NOT EXISTS dashboard_appeal_tokens (
      id BIGSERIAL PRIMARY KEY,
      token_hash TEXT NOT NULL UNIQUE,
      guild_id BIGINT NOT NULL,
      case_id BIGINT NOT NULL,
      user_id BIGINT NOT NULL,
      expires_at TIMESTAMP NOT NULL,
      used_at TIMESTAMP,
      appeal_id BIGINT,
      delivery_status TEXT NOT NULL DEFAULT 'pending',
      delivery_error TEXT,
      questions_json TEXT NOT NULL DEFAULT '[]',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE (guild_id, case_id)
    )
  `)
  await botQuery(`
    CREATE INDEX IF NOT EXISTS idx_dashboard_appeal_tokens_hash_active
    ON dashboard_appeal_tokens(token_hash, expires_at, used_at)
  `)
  await botQuery(`
    CREATE TABLE IF NOT EXISTS dashboard_reports (
      id BIGSERIAL PRIMARY KEY,
      guild_id BIGINT NOT NULL,
      requested_by_id TEXT NOT NULL,
      requested_by_name TEXT NOT NULL,
      name TEXT NOT NULL,
      type TEXT NOT NULL,
      format TEXT NOT NULL,
      params TEXT NOT NULL DEFAULT '{}',
      status TEXT NOT NULL DEFAULT 'ready',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
  `)
  await botQuery(`
    CREATE INDEX IF NOT EXISTS idx_dashboard_reports_guild_user_created
    ON dashboard_reports(guild_id, requested_by_id, created_at DESC)
  `)

  const caseColumns = [
    "ADD COLUMN IF NOT EXISTS severity TEXT NOT NULL DEFAULT 'low'",
    "ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open'",
    'ADD COLUMN IF NOT EXISTS channel TEXT',
    'ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP',
    "ADD COLUMN IF NOT EXISTS execution_status TEXT NOT NULL DEFAULT 'succeeded'",
    'ADD COLUMN IF NOT EXISTS dashboard_command_id BIGINT',
    'ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP',
  ]
  for (const definition of caseColumns) {
    await botQuery(`ALTER TABLE cases ${definition}`)
  }
  const appealColumns = [
    "ADD COLUMN IF NOT EXISTS answers_json TEXT NOT NULL DEFAULT '{}'",
    'ADD COLUMN IF NOT EXISTS staff_channel_id BIGINT',
    'ADD COLUMN IF NOT EXISTS staff_message_id BIGINT',
    'ADD COLUMN IF NOT EXISTS staff_delivery_error TEXT',
  ]
  for (const definition of appealColumns) {
    await botQuery(`ALTER TABLE dashboard_appeals ${definition}`)
  }
  await botQuery(`ALTER TABLE dashboard_appeal_tokens ADD COLUMN IF NOT EXISTS questions_json TEXT NOT NULL DEFAULT '[]'`)
  await botQuery(`
    CREATE TABLE IF NOT EXISTS dashboard_schema_migrations (
      key TEXT PRIMARY KEY,
      applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
  `)
  const backfill = await botQuery<{ key: string }>(`
    INSERT INTO dashboard_schema_migrations (key)
    VALUES ('20260712_case_severity_backfill')
    ON CONFLICT (key) DO NOTHING
    RETURNING key
  `)
  if (backfill.length > 0) {
    await botQuery(`
      UPDATE cases
      SET severity = CASE LOWER(action)
        WHEN 'ban' THEN 'critical'
        WHEN 'kick' THEN 'high'
        WHEN 'mute' THEN 'medium'
        WHEN 'timeout' THEN 'medium'
        ELSE 'low'
      END
    `)
  }
}

export function ensureDashboardBackendSchema(): Promise<void> {
  if (!schemaPromise) {
    schemaPromise = initializeSchema().catch((error) => {
      schemaPromise = null
      throw error
    })
  }
  return schemaPromise
}
