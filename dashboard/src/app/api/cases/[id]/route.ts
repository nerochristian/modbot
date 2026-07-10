import { apiError, handleError, ok, requireUser } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { getSelectedGuild } from '@/lib/guild-context'
import { updateCaseSchema } from '@/lib/validation'

function validId(id: string): boolean {
  return /^\d+$/.test(id)
}

export async function PATCH(request: Request, ctx: RouteContext<'/api/cases/[id]'>) {
  try {
    const guard = await requireUser('cases.write')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const { id } = await ctx.params
    if (!validId(id)) return apiError('Case not found', 404)
    const data = updateCaseSchema.parse(await request.json())

    const sets: string[] = []
    const values: unknown[] = [guild.id, id]
    if (data.status) {
      values.push(data.status === 'open')
      sets.push(`active = $${values.length}`)
    }
    if (data.reason) {
      values.push(data.reason)
      sets.push(`reason = $${values.length}`)
    }
    if (sets.length === 0) return ok({ success: true })
    const rows = await botQuery<{ id: string }>(
      `UPDATE cases SET ${sets.join(', ')} WHERE guild_id = $1::bigint AND id = $2::bigint RETURNING id::text`,
      values,
    )
    if (!rows[0]) return apiError('Case not found', 404)
    return ok({ success: true, id })
  } catch (error) {
    return handleError(error)
  }
}

export async function DELETE(_request: Request, ctx: RouteContext<'/api/cases/[id]'>) {
  try {
    const guard = await requireUser('cases.delete')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return apiError('Choose a connected server first', 409)
    const { id } = await ctx.params
    if (!validId(id)) return apiError('Case not found', 404)
    const rows = await botQuery<{ id: string }>(
      'DELETE FROM cases WHERE guild_id = $1::bigint AND id = $2::bigint RETURNING id::text',
      [guild.id, id],
    )
    if (!rows[0]) return apiError('Case not found', 404)
    return ok({ success: true })
  } catch (error) {
    return handleError(error)
  }
}
