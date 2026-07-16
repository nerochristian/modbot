import { handleError, ok, requireMutation } from '@/lib/api'
import { recordGuildAudit } from '@/lib/bot-audit'
import { automaticallySetupVerification } from '@/lib/verification-setup-service'

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'config.write')
    if (guard instanceof Response) return guard
    const result = await automaticallySetupVerification(guard.selectedGuildId!)
    await recordGuildAudit(guard.selectedGuildId!, guard, 'verification.auto_setup', 'verification', result)
    return ok(result)
  } catch (error) {
    return handleError(error)
  }
}
