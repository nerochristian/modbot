import { apiError, handleError, ok, requireMutation } from '@/lib/api'
import { applyAutomodTemplate } from '@/lib/automod-service'
import { recordGuildAudit } from '@/lib/bot-audit'

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'automod.write')
    if (guard instanceof Response) return guard
    const body = await request.json().catch(() => null)
    const settings = body?.settings
    if (!settings || typeof settings !== 'object' || Array.isArray(settings)) {
      return apiError('A template settings payload is required', 400)
    }
    const result = await applyAutomodTemplate(guard.selectedGuildId!, settings as Record<string, unknown>)
    await recordGuildAudit(
      guard.selectedGuildId!,
      guard,
      'automod.template.applied',
      String(body?.name ?? 'custom'),
      { keys: result.applied },
    )
    return ok(result)
  } catch (error) {
    if (error instanceof Error && /not allowed|unknown rule|must be|not persisted/i.test(error.message)) {
      return apiError(error.message, 400)
    }
    return handleError(error)
  }
}
