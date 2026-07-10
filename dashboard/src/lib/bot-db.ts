import 'server-only'

import { Pool, type QueryResultRow } from 'pg'

const globalForBotDb = globalThis as unknown as { aegisBotPool?: Pool }

function createPool(): Pool {
  const connectionString = process.env.BOT_DATABASE_URL?.trim()
  if (!connectionString?.startsWith('postgres')) {
    throw new Error('BOT_DATABASE_URL is not configured with the bot PostgreSQL database')
  }
  return new Pool({
    connectionString,
    max: 5,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 8_000,
    application_name: 'aegis-dashboard',
  })
}

function pool(): Pool {
  if (!globalForBotDb.aegisBotPool) globalForBotDb.aegisBotPool = createPool()
  return globalForBotDb.aegisBotPool
}

export async function botQuery<T extends QueryResultRow>(text: string, values: unknown[] = []): Promise<T[]> {
  const result = await pool().query<T>(text, values)
  return result.rows
}

export async function botDatabaseHealthy(): Promise<boolean> {
  try {
    await botQuery('SELECT 1 AS ok')
    return true
  } catch {
    return false
  }
}
