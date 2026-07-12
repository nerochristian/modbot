import 'server-only'

import { Pool, type PoolClient, type QueryResultRow } from 'pg'

const globalForBotDb = globalThis as unknown as { aegisBotPool?: Pool }

function botConnectionString(): string | undefined {
  // Prefer an explicit BOT_DATABASE_URL; otherwise fall back to the bot's own
  // DATABASE_URL when it points at Postgres. next.config.ts wires this in dev
  // from the root .env, but in production (env vars set directly, no .env file)
  // that indirection may not run — so re-derive it here too.
  const explicit = process.env.BOT_DATABASE_URL?.trim()
  if (explicit) return explicit
  const botDbUrl = process.env.DATABASE_URL?.trim()
  if (botDbUrl?.startsWith('postgres')) return botDbUrl
  return undefined
}

function createPool(): Pool {
  const connectionString = botConnectionString()
  if (!connectionString?.startsWith('postgres')) {
    throw new Error(
      'Bot database is not configured: set BOT_DATABASE_URL (or a Postgres DATABASE_URL) ' +
        'to the bot PostgreSQL database.',
    )
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

export async function withBotTransaction<T>(work: (client: PoolClient) => Promise<T>): Promise<T> {
  const client = await pool().connect()
  try {
    await client.query('BEGIN')
    const result = await work(client)
    await client.query('COMMIT')
    return result
  } catch (error) {
    await client.query('ROLLBACK').catch(() => undefined)
    throw error
  } finally {
    client.release()
  }
}

export async function botDatabaseHealthy(): Promise<boolean> {
  try {
    await botQuery('SELECT 1 AS ok')
    return true
  } catch {
    return false
  }
}
