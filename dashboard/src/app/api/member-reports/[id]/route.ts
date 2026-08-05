import { apiError, handleError, ok, requireMutation } from '@/lib/api'
import { botQuery } from '@/lib/bot-db'
import { recordGuildAudit } from '@/lib/bot-audit'

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const guard = await requireMutation(request, 'reports.write')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params
    if (!/^\d+$/.test(id)) return apiError('Invalid report ID', 400)
    const body = await request.json().catch(() => ({})) as { resolved?: boolean }
    if (typeof body.resolved !== 'boolean') return apiError('Resolved must be true or false', 400)
    const resolved = body.resolved ? 1 : 0
    const rows = await botQuery<{ id: string }>(
      `UPDATE reports SET resolved = $3::bigint, resolved_by = CASE WHEN $3::bigint = 1 THEN $4::bigint ELSE NULL END
       WHERE guild_id = $1::bigint AND id = $2::bigint RETURNING id::text`,
      [guard.selectedGuildId!, id, resolved, guard.discordId],
    )
    if (!rows[0]) return apiError('Report not found', 404)
    await recordGuildAudit(
      guard.selectedGuildId!,
      guard,
      body.resolved ? 'member_report.resolved' : 'member_report.reopened',
      id,
    )
    return ok({ id, resolved: body.resolved })
  } catch (error) {
    return handleError(error)
  }
}
