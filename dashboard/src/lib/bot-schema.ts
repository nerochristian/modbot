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
      status TEXT NOT NULL DEFAULT 'pending',
      decision TEXT,
      reviewed_by_id TEXT,
      reviewed_by_name TEXT,
      submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      reviewed_at TIMESTAMP,
      UNIQUE (guild_id, appeal_number)
    )
  `)
  await botQuery(`
    CREATE INDEX IF NOT EXISTS idx_dashboard_appeals_guild_status
    ON dashboard_appeals(guild_id, status, submitted_at DESC)
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
