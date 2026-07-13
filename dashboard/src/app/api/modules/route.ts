import { handleError, ok, requireUser } from '@/lib/api'
import { listModules } from '@/lib/modules-service'

export async function GET() {
  try {
    const guard = await requireUser('settings.read')
    if (guard instanceof Response) return guard
    return ok(await listModules(guard.selectedGuildId!))
  } catch (error) {
    return handleError(error)
  }
}
