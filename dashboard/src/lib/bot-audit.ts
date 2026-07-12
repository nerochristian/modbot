import 'server-only'

import type { PoolClient } from 'pg'
import { botQuery } from '@/lib/bot-db'

type AuditActor = { id: string; name: string }

export async function recordGuildAudit(
  guildId: string,
  actor: AuditActor,
  action: string,
  target: string,
  changes: Record<string, unknown> = {},
  client?: PoolClient,
): Promise<void> {
  const sql = `INSERT INTO dashboard_audit (guild_id, user_id, user_name, action, target, changes)
    VALUES ($1::bigint, $2, $3, $4, $5, $6)`
  const values = [guildId, actor.id, actor.name, action, target, JSON.stringify(changes)]
  if (client) {
    await client.query(sql, values)
  } else {
    await botQuery(sql, values)
  }
}
