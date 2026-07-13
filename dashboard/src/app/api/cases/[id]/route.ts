import { apiError, handleError, ok, requireMutation } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { ensureDashboardBackendSchema } from '@/lib/bot-schema'
import { recordGuildAudit } from '@/lib/bot-audit'
import { updateCaseSchema } from '@/lib/validation'

function validId(id: string): boolean {
  return /^\d+$/.test(id)
}

export async function PATCH(request: Request, ctx: RouteContext<'/api/cases/[id]'>) {
  try {
    const guard = await requireMutation(request, 'cases.write')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId!
    await ensureDashboardBackendSchema()
    const { id } = await ctx.params
    if (!validId(id)) return apiError('Case not found', 404)
    const data = updateCaseSchema.parse(await request.json())

    const sets: string[] = []
    const values: unknown[] = [guildId, id]
    if (data.status) {
      values.push(data.status)
      sets.push(`status = $${values.length}`)
      values.push(data.status === 'open' ? 1 : 0)
      sets.push(`active = $${values.length}`)
    }
    if (data.reason) {
      values.push(data.reason)
      sets.push(`reason = $${values.length}`)
    }
    if (data.severity) {
      values.push(data.severity)
      sets.push(`severity = $${values.length}`)
    }
    if (sets.length === 0) return ok({ success: true })
    const rows = await botQuery<{ id: string }>(
      `UPDATE cases SET ${sets.join(', ')}, updated_at = CURRENT_TIMESTAMP
       WHERE guild_id = $1::bigint AND id = $2::bigint RETURNING id::text`,
      values,
    )
    if (!rows[0]) return apiError('Case not found', 404)
    await recordGuildAudit(guildId, guard, 'case.updated', id, data)
    return ok({ success: true, id })
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(request: Request, ctx: RouteContext<'/api/cases/[id]'>) {
  try {
    const guard = await requireMutation(request, 'cases.delete')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId!
    await ensureDashboardBackendSchema()
    const { id } = await ctx.params
    if (!validId(id)) return apiError('Case not found', 404)
    const rows = await botQuery<{ id: string }>(
      `UPDATE cases SET status = 'resolved', active = 0, updated_at = CURRENT_TIMESTAMP
       WHERE guild_id = $1::bigint AND id = $2::bigint RETURNING id::text`,
      [guildId, id],
    )
    if (!rows[0]) return apiError('Case not found', 404)
    await recordGuildAudit(guildId, guard, 'case.archived', id)
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
