import { handleError, ok, requireUser } from '@/lib/api'
import { getBotGuildResources } from '@/lib/discord'

export async function GET() {
  try {
    const guard = await requireUser('settings.read')
    if (guard instanceof Response) return guard
    return ok(await getBotGuildResources(guard.selectedGuildId!))
  } catch (error) {
    return handleError(error)
  }
}
