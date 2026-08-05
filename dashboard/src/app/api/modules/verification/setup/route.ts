import { apiError, handleError, ok, requireMutation } from '@/lib/api'
import { recordGuildAudit } from '@/lib/bot-audit'
import { automaticallySetupVerification } from '@/lib/verification-setup-service'

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'config.write')
    if (guard instanceof Response) return guard
    const body = await request.json().catch(() => ({})) as { method?: unknown }
    if (body.method !== 'website' && body.method !== 'discord') {
      return apiError('Choose website or Discord verification.', 400)
    }
    const result = await automaticallySetupVerification(guard.selectedGuildId!, body.method)
    await recordGuildAudit(guard.selectedGuildId!, guard, 'verification.auto_setup', 'verification', result)
    return ok(result)
  } catch (error) {
    return handleError(error)
  }
}
