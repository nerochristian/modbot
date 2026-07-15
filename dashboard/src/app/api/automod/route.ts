import { apiError, handleError, ok, requireUser } from '@/lib/api'
import { listAutomodRules } from '@/lib/automod-service'

export async function GET() {
  try {
    const guard = await requireUser('automod.read')
    if (guard instanceof Response) return guard
    return ok(await listAutomodRules(guard.selectedGuildId!), {
      headers: {
        'Cache-Control': 'private, no-store, no-cache, must-revalidate',
      },
    })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST() {
  return apiError('AutoMod modules are fixed by the bot runtime; update an existing module instead.', 405)
}
